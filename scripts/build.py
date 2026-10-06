#!/usr/bin/env python3
"""Собрать Direct-модули INCY и каталог из списков с комментариями (только stdlib)."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re
from string import Template
import tempfile
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/Poliklot/incy-direct-rules"
PUBLIC_URL = "https://poliklot.github.io/incy-direct-rules"
NAME = "Poliklot Direct"
LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
FILENAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.txt")
MARKER = ".incy-generated"
MARKER_CONTENT = "incy-direct-modules\n"
LEGACY_FILES = {"profile.json", "profile.json.sha256", "direct.txt", "index.html",
                "build.json", ".nojekyll"}


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

    @property
    def module_path(self) -> str:
        return f"modules/{Path(self.filename).stem}.module"


def validate_rule(value: str) -> str:
    mode, separator, domain = value.partition(":")
    if separator:
        if mode not in {"domain", "full"}:
            raise ValueError("разрешены домен, domain:домен или full:домен")
    else:
        domain = value
    labels = domain.lower().split(".")
    if (len(domain) > 253 or len(labels) < 2 or labels[-1].isdigit()
            or any(not LABEL.fullmatch(label) for label in labels)):
        raise ValueError("нужен DNS-домен без URL, IP, wildcard, пробелов и пути")
    return value


def module_rule(value: str) -> str:
    """Явное сопоставление нового формата: домен+поддомены либо точное имя."""
    validate_rule(value)
    mode, separator, domain = value.partition(":")
    if not separator:
        domain = value
    kind = "DOMAIN" if separator and mode == "full" else "DOMAIN-SUFFIX"
    return f"{kind},{domain},DIRECT"


def read_groups(directory: Path) -> list[Group]:
    groups = []
    seen = {}
    for path in sorted(directory.glob("*.txt")):
        if path.is_symlink():
            raise ValueError(f"{path}: символические ссылки не разрешены")
        if not FILENAME.fullmatch(path.name) or path.stem == "all":
            raise ValueError(f"{path.name}: нужно короткое lowercase-kebab-case имя; all зарезервировано")
        lines = path.read_text(encoding="utf-8").splitlines()
        if any(any(ord(char) < 32 and char != "\t" for char in line) for line in lines):
            raise ValueError(f"{path.name}: управляющие символы не разрешены")
        first = next((line.strip() for line in lines if line.strip()), "")
        if not first.startswith("# ") or not first[2:].strip():
            raise ValueError(f"{path.name}: первая строка должна быть '# Название блока'")
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
                rule = validate_rule(value)
                duplicate_key = module_rule(rule).lower()
            except ValueError as error:
                raise ValueError(f"{location}: {error}: {value!r}") from error
            if duplicate_key in seen:
                raise ValueError(f"{location}: дубль {rule}; уже есть в {seen[duplicate_key]}")
            seen[duplicate_key] = location
            group.rules.append(Rule(rule, comment))
        if not group.rules:
            raise ValueError(f"{path.name}: блок не содержит доменов")
        groups.append(group)
    if not groups:
        raise ValueError(f"{directory}: не найдены блоки *.txt с доменами")
    return groups


def render_module(groups: list[Group], title: str, updated_at: int, revision: str) -> bytes:
    lines = [f"#!name={NAME} — {title}",
             "#!desc=Direct-правила по выбору владельца; без личных IP, DNS, скриптов и MITM.",
             f"# Исходники: {REPOSITORY}",
             f"# Версия: {revision}; Unix timestamp: {updated_at}", "", "[Rule]"]
    for group in groups:
        lines.extend(["", f"# {group.title}"])
        lines.extend(f"# {line}" for line in group.description)
        for rule in group.rules:
            if rule.comment:
                lines.append(f"# {rule.comment}")
            lines.append(module_rule(rule.value))
    return ("\n".join(lines) + "\n").encode("utf-8")


def import_url(path: str) -> str:
    # onadd добавляет и включает модуль. Это НЕ импорт профиля маршрутизации.
    return f"incy://module/onadd/{PUBLIC_URL}/{path}"


def render_groups(groups: list[Group]) -> str:
    sections = []
    for group in groups:
        slug = Path(group.filename).stem
        url = f"{PUBLIC_URL}/{group.module_path}"
        descriptions = "".join(f"<p>{escape(line)}</p>" for line in group.description)
        rows = "".join(
            f"<li><code>{escape(rule.value)}</code>"
            + (f"<span>{escape(rule.comment)}</span>" if rule.comment else "")
            + "</li>" for rule in group.rules
        )
        edit_url = f"{REPOSITORY}/edit/main/rules/direct/{quote(group.filename)}"
        sections.append(
            f"<article class='module' id='{slug}'>"
            f"<div class='module-heading'><h3>{escape(group.title)}</h3>"
            f"<span class='count'>{len(group.rules)} правил</span></div>"
            f"{descriptions}<div class='actions'>"
            f"<a class='add' href='{escape(import_url(group.module_path), quote=True)}'>Добавить и включить</a>"
            f"<a href='{escape(group.module_path, quote=True)}'>Посмотреть .module</a></div>"
            f"<label for='url-{slug}'>URL для импорта в «Модули»</label>"
            f"<div class='copy-row'><input id='url-{slug}' readonly spellcheck='false' "
            f"value='{escape(url, quote=True)}'><button type='button' data-copy='url-{slug}' "
            f"aria-label='Копировать URL: {escape(group.title, quote=True)}'>Копировать URL</button></div>"
            f"<details><summary>Домены и комментарии</summary><ul>{rows}</ul>"
            f"<p><a href='{escape(edit_url, quote=True)}'>Редактировать блок на GitHub</a></p>"
            "</details></article>"
        )
    return "\n".join(sections)


def validate_output(root: Path, output: Path) -> None:
    """Не заменять исходники, symlink или произвольную непустую папку."""
    if output.is_symlink():
        raise ValueError("output не должен быть символической ссылкой")
    resolved = output.resolve()
    source = root.resolve()
    if resolved == source or resolved in source.parents:
        raise ValueError("output не может заменять папку исходников")
    if source in resolved.parents and resolved != source / "dist":
        raise ValueError("внутри исходников output может быть только dist/")
    if not output.exists():
        return
    if not output.is_dir():
        raise ValueError("output должен быть папкой")
    entries = list(output.iterdir())
    if not entries:
        return
    marker = output / MARKER
    if marker.is_file() and not marker.is_symlink() and marker.read_text() == MARKER_CONTENT:
        return
    # Одноразовая миграция собственного старого dist, а не любой папки с JSON.
    if (resolved == source / "dist" and {entry.name for entry in entries} == LEGACY_FILES
            and all(entry.is_file() and not entry.is_symlink() for entry in entries)):
        return
    raise ValueError("output не является папкой сборки; выбери новую пустую папку")


def write_output(root: Path, output: Path, files: dict[str, bytes]) -> None:
    validate_output(root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temporary:
        staging = Path(temporary) / "new"
        staging.mkdir()
        for filename, content in files.items():
            path = staging / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        previous = Path(temporary) / "previous"
        had_previous = output.exists()
        if had_previous:
            output.rename(previous)
        try:
            staging.rename(output)
        except OSError:
            if had_previous:
                previous.rename(output)
            raise
    # Вся папка управляемая: исчезают старые модули и прежний profile.json.


def build(root: Path, output: Path, updated_at: int, revision: str = "local") -> dict:
    if updated_at <= 0:
        raise ValueError("updated-at должен быть положительным Unix timestamp")
    if revision != "local" and not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision должен быть полным commit SHA либо 'local'")
    groups = read_groups(root / "rules" / "direct")
    modules = {"modules/all.module": render_module(groups, "все блоки", updated_at, revision)}
    modules.update({group.module_path: render_module([group], group.title, updated_at, revision)
                    for group in groups})
    artifacts = {path: hashlib.sha256(payload).hexdigest() for path, payload in modules.items()}
    receipt = {"revision": revision, "updated_at": updated_at,
               "rules": sum(len(group.rules) for group in groups), "groups": len(groups),
               "modules": len(modules), "artifacts": artifacts}
    published_at = datetime.fromtimestamp(updated_at, timezone(timedelta(hours=3))).strftime(
        "%d.%m.%Y, %H:%M МСК"
    )
    html = Template((root / "web" / "index.html").read_text(encoding="utf-8")).substitute(
        name=escape(NAME), rule_count=receipt["rules"], group_count=len(groups),
        rule_groups=render_groups(groups), published_at=escape(published_at),
        all_url=escape(f"{PUBLIC_URL}/modules/all.module", quote=True),
        all_import_url=escape(import_url("modules/all.module"), quote=True),
    )
    files = dict(modules)
    files.update({path + ".sha256": (digest + "\n").encode()
                  for path, digest in artifacts.items()})
    files.update({"index.html": html.encode("utf-8"), ".nojekyll": b"",
                  MARKER: MARKER_CONTENT.encode(),
                  "direct.txt": ("\n".join(rule.value for group in groups for rule in group.rules) + "\n").encode(),
                  "build.json": (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode()})
    # Никакие личные профили, IP или настройки приложения не читаются.
    # Все входные данные и шаблоны проверены до замены предыдущей сборки.
    write_output(root, output, files)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--updated-at", type=int, required=True, help="Unix timestamp исходного коммита")
    parser.add_argument("--revision", default="local", help="полный SHA исходного коммита")
    arguments = parser.parse_args()
    try:
        receipt = build(ROOT, arguments.output, arguments.updated_at, arguments.revision)
    except (ValueError, TypeError, OSError) as error:
        parser.exit(1, f"Ошибка сборки: {error}\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
