import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("builder", ROOT / "scripts" / "build.py")
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def parsed_module_rules(payload):
    """Независимый минимальный читатель публикуемого формата."""
    lines = payload.decode("utf-8").splitlines()
    if not lines[0].startswith("#!name=") or not lines[1].startswith("#!desc="):
        raise AssertionError("missing metadata")
    section = None
    rules = []
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        if line.startswith("["):
            if line != "[Rule]" or section is not None:
                raise AssertionError("unexpected section")
            section = line
            continue
        parts = line.split(",")
        if section != "[Rule]" or len(parts) != 3 or parts[2] != "DIRECT":
            raise AssertionError("unexpected rule")
        if parts[0] not in {"DOMAIN", "DOMAIN-SUFFIX"}:
            raise AssertionError("unsupported match type")
        rules.append(line)
    return rules


class RuleTests(unittest.TestCase):
    def test_suffix_default_preserves_spelling_and_case(self):
        self.assertEqual(builder.validate_rule("GitHub.COM"), "GitHub.COM")
        self.assertEqual(builder.module_rule("GitHub.COM"), "DOMAIN-SUFFIX,GitHub.COM,DIRECT")

    def test_explicit_modes(self):
        self.assertEqual(builder.module_rule("full:API.Example.COM"), "DOMAIN,API.Example.COM,DIRECT")
        self.assertEqual(builder.module_rule("domain:example.com"), "DOMAIN-SUFFIX,example.com,DIRECT")

    def test_punycode(self):
        self.assertEqual(builder.module_rule("xn--e1afmkfd.xn--p1ai"),
                         "DOMAIN-SUFFIX,xn--e1afmkfd.xn--p1ai,DIRECT")

    def test_invalid_rules_cannot_inject_module_syntax_or_private_ips(self):
        invalid = ["https://example.com", "example.com/path", "example.com:443",
                   "example.com?token=secret", "*.example.com", "regexp:.*",
                   "geosite:ru", "keyword:example.com", "localhost", "127.0.0.1",
                   "203.0.113.7", "203.0.113.0/24", "999.999.999.999", "::1",
                   "example..com", "-example.com", "example-.com", "example.com.",
                   "user@example.com", "example .com", "foo_bar.example.com",
                   "пример.рф", "example.com,PROXY", "example.com\n[MITM]",
                   "a" * 64 + ".com", ".".join(["a" * 63] * 4)]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                builder.module_rule(value)


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
        self.assertEqual(groups[0].rules[0].value, "Example.COM")
        self.assertEqual(groups[0].rules[0].comment, "Сайт")
        self.assertEqual(groups[0].module_path, "modules/a.module")

    def test_equivalent_suffix_rules_are_duplicates_with_locations(self):
        self.write("a.txt", "# Первый\nExample.com\n")
        self.write("b.txt", "# Второй\ndomain:example.com\n")
        with self.assertRaisesRegex(ValueError, r"b.txt:2: дубль.*a.txt:2"):
            builder.read_groups(self.directory)

    def test_subdomains_and_exact_modes_are_preserved(self):
        self.write("a.txt", "# GitHub\ngithub.com\napi.github.com\nfull:github.com\n")
        self.assertEqual(len(builder.read_groups(self.directory)[0].rules), 3)

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

    def test_invalid_rule_identifies_source_line(self):
        self.write("a.txt", "# Первый\n\nhttps://example.com\n")
        with self.assertRaisesRegex(ValueError, "a.txt:3"):
            builder.read_groups(self.directory)

    def test_symlink_rejected(self):
        self.write("target", "# Домены\nexample.com\n")
        (self.directory / "a.txt").symlink_to(self.directory / "target")
        with self.assertRaisesRegex(ValueError, "символические ссылки"):
            builder.read_groups(self.directory)

    def test_invalid_or_reserved_filename(self):
        for name in ("all.txt", "../All.txt", "bad_name.txt", "name with spaces.txt"):
            target = Path(name).name
            with self.subTest(name=target):
                self.write(target, "# Домены\nexample.com\n")
                with self.assertRaisesRegex(ValueError, "имя"):
                    builder.read_groups(self.directory)
                (self.directory / target).unlink()

    def test_control_character_in_comment_rejected(self):
        self.write("a.txt", "# Домены\nexample.com # плохо\x00\n")
        with self.assertRaisesRegex(ValueError, "управляющие"):
            builder.read_groups(self.directory)

    def test_html_escaped_and_comment_cannot_add_module_section(self):
        self.write("a.txt", '# <script>alert(1)</script>\n# [MITM]\nexample.com # <img src=x>\n')
        groups = builder.read_groups(self.directory)
        html = builder.render_groups(groups)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;img src=x&gt;", html)
        payload = builder.render_module(groups, "test", 1700000000, "local")
        self.assertEqual(parsed_module_rules(payload), ["DOMAIN-SUFFIX,example.com,DIRECT"])
        self.assertIn("# [MITM]", payload.decode())


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "dist"

    def source(self, rules="# Тест\nexample.com # Сайт\n"):
        root = Path(self.temporary.name) / "source"
        (root / "rules" / "direct").mkdir(parents=True, exist_ok=True)
        (root / "rules" / "direct" / "test.txt").write_text(rules)
        (root / "web").mkdir(exist_ok=True)
        (root / "web" / "index.html").write_bytes((ROOT / "web" / "index.html").read_bytes())
        return root

    def test_generated_modules_match_source_independently(self):
        receipt = builder.build(ROOT, self.output, 1700000000, "a" * 40)
        expected = []
        for path in sorted((ROOT / "rules" / "direct").glob("*.txt")):
            source_values = [line.partition("#")[0].strip() for line in path.read_text().splitlines()
                             if line.partition("#")[0].strip()]
            group_rules = []
            for value in source_values:
                if value.startswith("full:"):
                    group_rules.append("DOMAIN," + value[5:] + ",DIRECT")
                else:
                    domain = value[7:] if value.startswith("domain:") else value
                    group_rules.append("DOMAIN-SUFFIX," + domain + ",DIRECT")
            module = self.output / "modules" / (path.stem + ".module")
            self.assertEqual(parsed_module_rules(module.read_bytes()), group_rules)
            expected.extend(group_rules)
        self.assertEqual(parsed_module_rules((self.output / "modules" / "all.module").read_bytes()), expected)
        self.assertEqual(receipt["rules"], len(expected))
        self.assertEqual(receipt["groups"], len(list((ROOT / "rules" / "direct").glob("*.txt"))))
        self.assertEqual(receipt["modules"], receipt["groups"] + 1)
        self.assertEqual(len(expected), len(set(expected)))
        self.assertEqual(len(receipt["artifacts"]), receipt["modules"])

    def test_hashes_receipt_catalog_and_activation_labels(self):
        receipt = builder.build(ROOT, self.output, 1700000000, "a" * 40)
        for filename, digest in receipt["artifacts"].items():
            self.assertEqual(hashlib.sha256((self.output / filename).read_bytes()).hexdigest(), digest)
            self.assertEqual((self.output / (filename + ".sha256")).read_text(), digest + "\n")
        self.assertEqual(json.loads((self.output / "build.json").read_text()), receipt)
        html = (self.output / "index.html").read_text()
        self.assertEqual(html.count("incy://module/onadd/"), receipt["modules"])
        self.assertNotIn("incy://autorouting/", html)
        self.assertIn("Добавить и включить", html)
        self.assertEqual(html.count(builder.REPOSITORY + "/edit/main/rules/direct/"), receipt["groups"])
        for filename in receipt["artifacts"]:
            self.assertIn(builder.PUBLIC_URL + "/" + filename, html)
        self.assertNotIn("$rule_groups", html)
        self.assertEqual((self.output / builder.MARKER).read_text(), builder.MARKER_CONTENT)

    def test_module_comments_and_source_case_kept(self):
        root = self.source("# Мой блок\n# Причина\nExample.COM # Комментарий\nfull:api.example.org\n")
        builder.build(root, self.output, 1700000000)
        text = (self.output / "modules" / "test.module").read_text()
        self.assertIn("#!name=Poliklot Direct — Мой блок", text)
        self.assertIn("# Причина\n# Комментарий\nDOMAIN-SUFFIX,Example.COM,DIRECT", text)
        self.assertIn("DOMAIN,api.example.org,DIRECT", text)
        self.assertEqual((self.output / "direct.txt").read_text(), "Example.COM\nfull:api.example.org\n")

    def test_private_profiles_are_never_read_or_published(self):
        root = self.source()
        marker = "PRIVATE-PROFILE-MUST-NOT-LEAK"
        (root / "profile.base.json").write_text(json.dumps({"Name": marker, "DirectIp": ["203.0.113.7"]}))
        builder.build(root, self.output, 1700000000)
        for path in self.output.rglob("*"):
            if path.is_file():
                self.assertNotIn(marker.encode(), path.read_bytes())
                self.assertNotIn(b"203.0.113.7", path.read_bytes())
        self.assertFalse((self.output / "profile.json").exists())
        self.assertFalse((ROOT / "profile.base.json").exists())

    def test_deterministic(self):
        builder.build(ROOT, self.output, 1700000000)
        first = {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        builder.build(ROOT, self.output, 1700000000)
        second = {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(first, second)

    def test_deleted_module_and_obsolete_profile_disappear(self):
        root = self.source()
        (root / "rules" / "direct" / "old.txt").write_text("# Старый\nold.example.com\n")
        builder.build(root, self.output, 1700000000)
        (self.output / "profile.json").write_text("obsolete")
        (root / "rules" / "direct" / "old.txt").unlink()
        builder.build(root, self.output, 1700000001)
        self.assertFalse((self.output / "modules" / "old.module").exists())
        self.assertFalse((self.output / "modules" / "old.module.sha256").exists())
        self.assertFalse((self.output / "profile.json").exists())

    def test_own_legacy_dist_migrates(self):
        root = self.source()
        output = root / "dist"
        output.mkdir()
        for filename in builder.LEGACY_FILES:
            (output / filename).write_text("previous build")
        builder.build(root, output, 1700000000)
        self.assertFalse((output / "profile.json").exists())
        self.assertTrue((output / "modules" / "all.module").is_file())

    def test_validation_failure_preserves_previous_build(self):
        root = self.source()
        builder.build(root, self.output, 1700000000)
        before = (self.output / "modules" / "all.module").read_bytes()
        (root / "rules" / "direct" / "test.txt").write_text("# Ошибка\n203.0.113.7\n")
        with self.assertRaises(ValueError):
            builder.build(root, self.output, 1700000001)
        self.assertEqual((self.output / "modules" / "all.module").read_bytes(), before)

    def test_bad_timestamp_or_revision_creates_no_output(self):
        for timestamp, revision in ((0, "local"), (1700000000, "not-a-sha")):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                builder.build(ROOT, self.output, timestamp, revision)
            self.assertFalse(self.output.exists())

    def test_unmanaged_output_cannot_be_replaced(self):
        self.output.mkdir()
        precious = self.output / "notes.txt"
        precious.write_text("user content")
        with self.assertRaisesRegex(ValueError, "папкой сборки"):
            builder.build(ROOT, self.output, 1700000000)
        self.assertEqual(precious.read_text(), "user content")

    def test_source_directory_or_subdirectory_cannot_be_replaced(self):
        root = self.source()
        for output in (root, root.parent, root / "rules", root / "web"):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "исходников"):
                builder.build(root, output, 1700000000)
        self.assertTrue((root / "rules" / "direct" / "test.txt").is_file())

    def test_output_symlink_cannot_be_replaced(self):
        target = Path(self.temporary.name) / "keep"
        target.mkdir()
        self.output.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "символической"):
            builder.build(ROOT, self.output, 1700000000)
        self.assertTrue(self.output.is_symlink())

    def test_failed_stage_swap_restores_previous_build(self):
        root = self.source()
        builder.build(root, self.output, 1700000000)
        before = (self.output / "modules" / "all.module").read_bytes()
        rename = Path.rename
        def fail_new(path, target):
            if path.name == "new":
                raise OSError("simulated filesystem error")
            return rename(path, target)
        with patch.object(Path, "rename", fail_new), self.assertRaises(OSError):
            builder.build(root, self.output, 1700000001)
        self.assertEqual((self.output / "modules" / "all.module").read_bytes(), before)

    def test_cli_bad_input_exits_nonzero(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py"),
                                 "--updated-at", "0", "--output", str(self.output)],
                                text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Ошибка сборки", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
