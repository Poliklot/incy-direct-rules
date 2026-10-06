#!/usr/bin/env python3
"""Build an INCY routing profile from commented domain groups, using only stdlib."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from html import escape
import ipaddress
import json
from pathlib import Path
import re
from string import Template
from urllib.parse import quote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/Poliklot/incy-direct-rules"
PROFILE_URL = "https://poliklot.github.io/incy-direct-rules/profile.json"
LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


@dataclass
class Rule:
    value: str
    comment: str


@dataclass
class Group:
    filename: str
    title: str
    description: list[str]
    rules: list[Rule]


def normalize_rule(value: str) -> str:
    mode, separator, domain = value.lower().partition(":")
    if not separator:
        mode, domain = "domain", mode
    if mode not in {"domain", "full"}:
        raise ValueError("разрешены домен, domain:домен или full:домен")
    labels = domain.split(".")
    if (len(domain) > 253 or len(labels) < 2 or labels[-1].isdigit()
            or any(not LABEL.fullmatch(label) for label in labels)):
        raise ValueError("нужен DNS-домен без URL, IP, wildcard, пробелов и пути")
    return f"{mode}:{domain}"


def read_groups(directory: Path) -> list[Group]:
    groups = []
    seen = {}
    for path in sorted(directory.glob("*.txt")):
        if path.is_symlink():
            raise ValueError(f"{path}: символические ссылки не разрешены")
        lines = path.read_text(encoding="utf-8").splitlines()
        first = next((line.strip() for line in lines if line.strip()), "")
        if not first.startswith("# ") or not first[2:].strip():
            raise ValueError(f"{path}: первая строка должна быть '# Название блока'")
        group = Group(path.name, first[2:].strip(), [], [])
        for number, line in enumerate(lines, 1):
            value, marker, comment = line.partition("#")
            value, comment = value.strip(), comment.strip()
            if not value:
                if marker and comment and comment != group.title:
                    group.description.append(comment)
                continue
            location = f"{path.name}:{number}"
            try:
                rule = normalize_rule(value)
            except ValueError as error:
                raise ValueError(f"{location}: {error}: {value!r}") from error
            if rule in seen:
                raise ValueError(f"{location}: дубль {rule}; уже есть в {seen[rule]}")
            seen[rule] = location
            group.rules.append(Rule(rule, comment))
        if not group.rules:
            raise ValueError(f"{path.name}: блок не содержит доменов")
        groups.append(group)
    if not groups:
        raise ValueError(f"{directory}: не найдены блоки *.txt с доменами")
    return groups


def validate_base(base: dict) -> None:
    """Keep this profile limited to explicit Direct-domain exceptions."""
    if not isinstance(base, dict):
        raise ValueError("profile.base.json должен содержать объект")
    expected = {"Name", "GlobalProxy", "RemoteDNSType", "RemoteDNSDomain",
                "RemoteDNSIP", "DomesticDNSType", "DomesticDNSDomain",
                "DomesticDNSIP", "DnsHosts", "DirectIp", "ProxySites",
                "ProxyIp", "BlockSites", "BlockIp", "DomainStrategy", "FakeDNS"}
    if set(base) != expected:
        raise ValueError("profile.base.json: неверный набор полей; DirectSites и LastUpdated генерируются")
    if not isinstance(base["Name"], str) or not base["Name"].strip():
        raise ValueError("Name должен быть непустой строкой")
    if base["GlobalProxy"] != "true":
        raise ValueError('GlobalProxy должен быть строкой "true": прочий трафик через прокси')
    if base["FakeDNS"] not in ("true", "false"):
        raise ValueError('FakeDNS должен быть строкой "true" или "false"')
    if base["DomainStrategy"] != "AsIs":
        raise ValueError('DomainStrategy должен быть "AsIs": здесь только доменные исключения')
    for field in ("DirectIp", "ProxySites", "ProxyIp", "BlockSites", "BlockIp"):
        if base[field] != []:
            raise ValueError(f"{field} должен быть пустым: этот репозиторий управляет только Direct-доменами")
    for prefix in ("Remote", "Domestic"):
        if base[f"{prefix}DNSType"] not in ("DoH", "DoU"):
            raise ValueError(f"{prefix}DNSType: разрешены DoH и DoU")
        ipaddress.ip_address(base[f"{prefix}DNSIP"])
        address = base[f"{prefix}DNSDomain"]
        if not isinstance(address, str):
            raise ValueError(f"{prefix}DNSDomain должен быть строкой")
        if base[f"{prefix}DNSType"] == "DoH":
            url = urlsplit(address)
            if (url.scheme != "https" or not url.hostname or url.username
                    or url.password or url.query or url.fragment):
                raise ValueError(f"{prefix}DNSDomain: нужен HTTPS URL без credentials, query и fragment")
    if not isinstance(base["DnsHosts"], dict):
        raise ValueError("DnsHosts должен быть объектом")
    for host, address in base["DnsHosts"].items():
        if ":" in host:
            raise ValueError("DnsHosts: ключ должен быть доменом без префикса правила")
        normalize_rule(host)
        ipaddress.ip_address(address)


def render_groups(groups: list[Group]) -> str:
    sections = []
    for group in groups:
        descriptions = "".join(f"<p>{escape(line)}</p>" for line in group.description)
        rows = "".join(
            f"<li><code>{escape(rule.value)}</code>"
            + (f"<span>{escape(rule.comment)}</span>" if rule.comment else "")
            + "</li>" for rule in group.rules
        )
        edit_url = f"{REPOSITORY}/edit/main/rules/direct/{quote(group.filename)}"
        sections.append(
            f"<details><summary>{escape(group.title)} <span>({len(group.rules)})</span></summary>"
            f"{descriptions}<ul>{rows}</ul><p><a href='{escape(edit_url, quote=True)}'>"
            "Редактировать этот блок на GitHub</a></p></details>"
        )
    return "\n".join(sections)


def build(root: Path, output: Path, updated_at: int, revision: str = "local") -> dict:
    if updated_at <= 0:
        raise ValueError("updated-at должен быть положительным Unix timestamp")
    if revision != "local" and not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision должен быть полным commit SHA либо 'local'")
    groups = read_groups(root / "rules" / "direct")
    base = json.loads((root / "profile.base.json").read_text(encoding="utf-8"))
    validate_base(base)
    profile = dict(base, DirectSites=[rule.value for group in groups for rule in group.rules],
                   LastUpdated=str(updated_at))
    payload = (json.dumps(profile, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    published_at = datetime.fromtimestamp(updated_at, timezone(timedelta(hours=3))).strftime(
        "%d.%m.%Y, %H:%M МСК"
    )
    import_url = "incy://autorouting/add/" + PROFILE_URL
    html = Template((root / "web" / "index.html").read_text(encoding="utf-8")).substitute(
        profile_name=escape(profile["Name"]), rule_count=len(profile["DirectSites"]),
        group_count=len(groups), rule_groups=render_groups(groups),
        import_url=escape(import_url, quote=True), published_at=escape(published_at),
    )
    receipt = {"revision": revision, "updated_at": updated_at,
               "rules": len(profile["DirectSites"]), "groups": len(groups), "sha256": digest}
    files = {"profile.json": payload, "profile.json.sha256": (digest + "\n").encode(),
             "direct.txt": ("\n".join(profile["DirectSites"]) + "\n").encode(),
             "index.html": html.encode("utf-8"), ".nojekyll": b"",
             "build.json": (json.dumps(receipt, indent=2) + "\n").encode()}
    # Nothing is written until every input, rule and template has been validated.
    output.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        (output / filename).write_bytes(content)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--updated-at", type=int, required=True, help="Unix timestamp of the source commit")
    parser.add_argument("--revision", default="local", help="full source commit SHA")
    arguments = parser.parse_args()
    try:
        receipt = build(ROOT, arguments.output, arguments.updated_at, arguments.revision)
    except (ValueError, TypeError, OSError) as error:
        parser.exit(1, f"Ошибка сборки: {error}\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
