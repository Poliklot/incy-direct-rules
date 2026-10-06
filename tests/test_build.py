from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("builder", ROOT / "scripts" / "build.py")
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


class RuleTests(unittest.TestCase):
    def test_bare_domain_is_suffix_rule_not_keyword(self):
        self.assertEqual(builder.normalize_rule("GitHub.COM"), "domain:github.com")

    def test_explicit_modes(self):
        self.assertEqual(builder.normalize_rule("full:API.Example.COM"), "full:api.example.com")
        self.assertEqual(builder.normalize_rule("domain:example.com"), "domain:example.com")

    def test_punycode_domain(self):
        self.assertEqual(builder.normalize_rule("xn--e1afmkfd.xn--p1ai"),
                         "domain:xn--e1afmkfd.xn--p1ai")

    def test_reject_invalid_rules(self):
        invalid = ["https://example.com", "example.com/path", "example.com:443",
                   "example.com?token=secret", "*.example.com", "regexp:.*",
                   "geosite:ru", "keyword:example.com", "localhost", "127.0.0.1",
                   "999.999.999.999", "::1", "example..com", "-example.com",
                   "example-.com", "example.com.", "user@example.com",
                   "example .com", "foo_bar.example.com", "пример.рф",
                   "a" * 64 + ".com", ".".join(["a" * 63] * 4)]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                builder.normalize_rule(value)


class GroupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def write(self, name, text):
        (self.directory / name).write_text(text, encoding="utf-8")

    def test_comments_blank_lines_and_sort_order(self):
        self.write("b.txt", "# Второй\n\nfull:api.example.org # API\n")
        self.write("a.txt", "\n# Первый\n# Описание\nExample.COM # Сайт\n")
        groups = builder.read_groups(self.directory)
        self.assertEqual([group.title for group in groups], ["Первый", "Второй"])
        self.assertEqual(groups[0].description, ["Описание"])
        self.assertEqual(groups[0].rules[0].value, "domain:example.com")
        self.assertEqual(groups[0].rules[0].comment, "Сайт")

    def test_duplicate_across_groups_is_an_error_with_locations(self):
        self.write("a.txt", "# Первый\nExample.com\n")
        self.write("b.txt", "# Второй\ndomain:example.com\n")
        with self.assertRaisesRegex(ValueError, r"b.txt:2: дубль.*a.txt:2"):
            builder.read_groups(self.directory)

    def test_parent_and_subdomains_are_preserved(self):
        self.write("a.txt", "# GitHub\ngithub.com\napi.github.com\nfull:github.com\n")
        group = builder.read_groups(self.directory)[0]
        self.assertEqual(len(group.rules), 3)

    def test_missing_title(self):
        self.write("a.txt", "example.com\n")
        with self.assertRaisesRegex(ValueError, "первая строка"):
            builder.read_groups(self.directory)

    def test_empty_group(self):
        self.write("a.txt", "# Пустой\n# Только комментарий\n")
        with self.assertRaisesRegex(ValueError, "не содержит доменов"):
            builder.read_groups(self.directory)

    def test_empty_directory(self):
        with self.assertRaisesRegex(ValueError, "не найдены"):
            builder.read_groups(self.directory)

    def test_error_identifies_source_line(self):
        self.write("a.txt", "# Первый\n\nhttps://example.com\n")
        with self.assertRaisesRegex(ValueError, "a.txt:3"):
            builder.read_groups(self.directory)

    def test_source_symlink_is_rejected(self):
        self.write("target", "# Домены\nexample.com\n")
        (self.directory / "a.txt").symlink_to(self.directory / "target")
        with self.assertRaisesRegex(ValueError, "символические ссылки"):
            builder.read_groups(self.directory)

    def test_comments_and_headings_are_html_escaped(self):
        self.write("a.txt", '# <script>alert(1)</script>\nexample.com # <img src=x>\n')
        html = builder.render_groups(builder.read_groups(self.directory))
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;img src=x&gt;", html)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "dist"
        self.base = json.loads((ROOT / "profile.base.json").read_text(encoding="utf-8"))

    def test_base_is_valid(self):
        builder.validate_base(self.base)

    def test_profile_invariants(self):
        changes = [("GlobalProxy", "false"), ("GlobalProxy", True), ("Name", ""),
                   ("FakeDNS", False), ("DirectIp", ["0.0.0.0/0"]),
                   ("BlockSites", ["geosite:ru"]), ("ProxySites", ["example.com"]),
                   ("DomainStrategy", "IPIfNonMatch"), ("RemoteDNSIP", "bad-ip"),
                   ("DomesticDNSType", "invalid"), ("DnsHosts", []),
                   ("DnsHosts", {"full:example.com": "1.1.1.1"}),
                   ("RemoteDNSDomain", "http://dns.example.com/dns-query"),
                   ("RemoteDNSDomain", "https://user:secret@dns.example.com/dns-query"),
                   ("RemoteDNSDomain", "https://dns.example.com/dns-query?token=secret")]
        for field, value in changes:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                base = deepcopy(self.base)
                base[field] = value
                builder.validate_base(base)

    def test_unknown_fields_do_not_leak_to_profile(self):
        self.base["subscriptionURL"] = "sensitive"
        with self.assertRaisesRegex(ValueError, "набор полей"):
            builder.validate_base(self.base)

    def test_build_output_schema_hash_and_safe_import(self):
        receipt = builder.build(ROOT, self.output, 1700000000, "a" * 40)
        payload = (self.output / "profile.json").read_bytes()
        profile = json.loads(payload)
        rules = profile.pop("DirectSites")
        self.assertEqual(profile.pop("LastUpdated"), "1700000000")
        self.assertEqual(profile, self.base)
        self.assertGreater(len(rules), 0)
        self.assertEqual(len(rules), len(set(rules)))
        self.assertTrue(all(rule.startswith(("domain:", "full:")) for rule in rules))
        self.assertEqual((self.output / "direct.txt").read_text().splitlines(), rules)
        digest = hashlib.sha256(payload).hexdigest()
        self.assertEqual((self.output / "profile.json.sha256").read_text(), digest + "\n")
        self.assertEqual(receipt["sha256"], digest)
        self.assertEqual(receipt["revision"], "a" * 40)
        self.assertEqual(json.loads((self.output / "build.json").read_text()), receipt)
        html = (self.output / "index.html").read_text()
        self.assertIn("incy://autorouting/add/" + builder.PROFILE_URL, html)
        self.assertNotIn("autorouting/onadd/", html)
        self.assertEqual(html.count(builder.REPOSITORY + "/edit/main/rules/direct/"), receipt["groups"])
        self.assertNotIn("$rule_groups", html)

    def test_build_is_deterministic(self):
        builder.build(ROOT, self.output, 1700000000)
        first = {path.name: path.read_bytes() for path in self.output.iterdir()}
        builder.build(ROOT, self.output, 1700000000)
        self.assertEqual(first, {path.name: path.read_bytes() for path in self.output.iterdir()})

    def test_failed_validation_does_not_change_previous_build(self):
        self.output.mkdir()
        (self.output / "profile.json").write_text("previous good build")
        with self.assertRaises(ValueError):
            builder.build(ROOT, self.output, 0)
        self.assertEqual((self.output / "profile.json").read_text(), "previous good build")

    def test_invalid_revision(self):
        with self.assertRaisesRegex(ValueError, "revision"):
            builder.build(ROOT, self.output, 1700000000, "not-a-sha")
        self.assertFalse(self.output.exists())

    def test_invalid_rules_do_not_replace_previous_build(self):
        root = Path(self.temporary.name) / "source"
        directory = root / "rules" / "direct"
        directory.mkdir(parents=True)
        (directory / "a.txt").write_text("# Первый\nexample.com\n")
        (directory / "b.txt").write_text("# Второй\nexample.com\n")
        self.output.mkdir()
        (self.output / "profile.json").write_text("previous good build")
        with self.assertRaisesRegex(ValueError, "дубль"):
            builder.build(root, self.output, 1700000000)
        self.assertEqual((self.output / "profile.json").read_text(), "previous good build")

    def test_cli_exits_nonzero_on_bad_input(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py"),
                                 "--updated-at", "0", "--output", str(self.output)],
                                text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Ошибка сборки", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
