#!/usr/bin/env python3
"""Validate the installable SDLC Flow bundle with Python's standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


SKILL_NAME = "sdlc-flow"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
LINK_RE = re.compile(r"!?\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+['\"][^'\"]*['\"])?\)")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(?P<yaml>.*?)\r?\n---\r?\n", re.DOTALL)


class Checks:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def package_path(root: Path, relative: str, checks: Checks, label: str) -> Path | None:
    if not relative or Path(relative).is_absolute() or "\\" in relative:
        checks.errors.append(f"{label}: expected a relative POSIX path: {relative!r}")
        return None
    path = root / relative
    if not within(path, root):
        checks.errors.append(f"{label}: path escapes skill directory: {relative!r}")
        return None
    return path


def validate_frontmatter(skill_dir: Path, checks: Checks) -> None:
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        checks.errors.append("missing SKILL.md")
        return
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        checks.errors.append("SKILL.md must begin with YAML frontmatter")
        return
    # This package uses simple one-line values for its required keys. A full YAML
    # parser is deliberately left to the upstream Agent Skills reference validator.
    values: dict[str, list[str]] = {}
    for line in match.group("yaml").splitlines():
        field = re.match(r"^([a-z][a-z0-9-]*):\s*(.*)$", line)
        if field:
            values.setdefault(field.group(1), []).append(field.group(2).strip())
    for key in ("name", "description", "license"):
        checks.require(len(values.get(key, [])) == 1, f"frontmatter needs exactly one {key}")
    if len(values.get("name", [])) == 1:
        name = values["name"][0].strip("\"'")
        checks.require(bool(NAME_RE.fullmatch(name)) and len(name) <= 64, "invalid Agent Skills name")
        checks.require(name == skill_dir.name == SKILL_NAME, "name must match skills/sdlc-flow")
    if len(values.get("description", [])) == 1:
        description = values["description"][0].strip("\"'")
        checks.require(0 < len(description) <= 1024, "description must be 1-1024 characters")
        checks.require(description not in (">", "|"), "use a one-line description in this package")
    if len(values.get("license", [])) == 1:
        checks.require(bool(values["license"][0].strip("\"'")), "license must be nonempty")
        checks.require((skill_dir / "LICENSE").is_file(), "missing bundled skill LICENSE")


def validate_links(root: Path, markdown_files: list[Path], checks: Checks, files_only: bool) -> None:
    for markdown in markdown_files:
        for raw in LINK_RE.findall(markdown.read_text(encoding="utf-8")):
            target = raw.strip("<>")
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or target.startswith("#"):
                continue
            if target.startswith("/"):
                checks.errors.append(f"{markdown.relative_to(root)}: absolute link is not portable: {target}")
                continue
            path = (markdown.parent / unquote(parts.path)).resolve()
            if not within(path, root):
                checks.errors.append(f"{markdown.relative_to(root)}: link escapes package: {target}")
                continue
            exists = path.is_file() if files_only else path.exists()
            checks.require(exists, f"{markdown.relative_to(root)}: missing linked target: {target}")


def validate_sources(skill_dir: Path, checks: Checks) -> None:
    lock_path = skill_dir / "SOURCES.lock.json"
    notices = skill_dir / "THIRD_PARTY_NOTICES.md"
    checks.require(notices.is_file() and bool(notices.read_text(encoding="utf-8").strip()) if notices.is_file() else False,
                   "missing or empty THIRD_PARTY_NOTICES.md")
    if not lock_path.is_file():
        checks.errors.append("missing SOURCES.lock.json")
        return
    try:
        manifest = json.loads(lock_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        checks.errors.append(f"invalid SOURCES.lock.json: {exc}")
        return
    if not isinstance(manifest, dict):
        checks.errors.append("SOURCES.lock.json must be an object")
        return
    checks.require(manifest.get("schema_version") == 1, "SOURCES.lock.json schema_version must be 1")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        checks.errors.append("SOURCES.lock.json needs at least one source")
        return
    declared: set[Path] = set()
    notices_text = notices.read_text(encoding="utf-8") if notices.is_file() else ""
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            checks.errors.append(f"{label} must be an object")
            continue
        for key in ("name", "url", "revision", "license", "license_file"):
            checks.require(isinstance(source.get(key), str) and bool(source[key].strip()), f"{label}.{key} is required")
        url = source.get("url", "")
        if isinstance(url, str):
            checks.require(urlsplit(url).scheme == "https", f"{label}.url must be HTTPS")
        revision = source.get("revision", "")
        if isinstance(revision, str):
            checks.require(bool(REVISION_RE.fullmatch(revision)), f"{label}.revision must be an immutable 40-character commit SHA")
        name = source.get("name", "")
        license_id = source.get("license", "")
        if isinstance(name, str) and name:
            checks.require(name in notices_text, f"{label}.name missing from THIRD_PARTY_NOTICES.md")
        if isinstance(license_id, str) and license_id:
            checks.require(license_id in notices_text, f"{label}.license missing from THIRD_PARTY_NOTICES.md")
        files = source.get("files")
        if not isinstance(files, list) or not files:
            checks.errors.append(f"{label}.files needs at least one file")
            continue
        source_paths: set[Path] = set()
        for file_index, item in enumerate(files):
            file_label = f"{label}.files[{file_index}]"
            if not isinstance(item, dict):
                checks.errors.append(f"{file_label} must be an object")
                continue
            relative = item.get("path")
            upstream = item.get("upstream_path")
            digest = item.get("sha256")
            checks.require(isinstance(upstream, str) and bool(upstream.strip()), f"{file_label}.upstream_path is required")
            checks.require(isinstance(digest, str) and bool(SHA256_RE.fullmatch(digest)), f"{file_label}.sha256 must be lowercase hex")
            if not isinstance(relative, str):
                checks.errors.append(f"{file_label}.path is required")
                continue
            path = package_path(skill_dir, relative, checks, file_label)
            if path is None:
                continue
            checks.require(path.resolve().is_relative_to((skill_dir / "vendor").resolve()), f"{file_label}.path must be in vendor/")
            checks.require(path not in declared, f"duplicate manifest path: {relative}")
            declared.add(path)
            source_paths.add(path)
            if path.is_symlink():
                checks.errors.append(f"vendored file must be a regular file: {relative}")
            elif not path.is_file():
                checks.errors.append(f"missing vendored file: {relative}")
            elif isinstance(digest, str) and SHA256_RE.fullmatch(digest):
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                checks.require(actual == digest, f"hash mismatch: {relative}")
        license_file = source.get("license_file")
        if isinstance(license_file, str):
            license_path = package_path(skill_dir, license_file, checks, f"{label}.license_file")
            if license_path is not None:
                checks.require(license_path in source_paths, f"{label}.license_file must be declared and hashed")
                checks.require(license_path.is_file(), f"missing license file: {license_file}")
                if license_path.is_file():
                    checks.require(bool(license_path.read_bytes()), f"empty license file: {license_file}")
    vendor = skill_dir / "vendor"
    if vendor.is_dir():
        actual_paths = {path for path in vendor.rglob("*") if path.is_file() or path.is_symlink()}
        for path in sorted(actual_paths - declared):
            checks.errors.append(f"unlisted vendored file: {path.relative_to(skill_dir)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, default=None, help="validate an installed skill copy")
    parser.add_argument("--repo-root", type=Path, default=None, help="also require exactly one SKILL.md in the repository")
    args = parser.parse_args()
    checkout_root = Path(__file__).resolve().parents[1]
    skill_dir = (args.skill_dir or checkout_root / "skills" / SKILL_NAME).resolve()
    repo_root = (args.repo_root or (checkout_root if args.skill_dir is None else None))
    checks = Checks()
    checks.require(skill_dir.is_dir(), f"missing skill directory: {skill_dir}")
    if repo_root is not None:
        repo_root = repo_root.resolve()
        checks.require((repo_root / "LICENSE").is_file(), "missing repository LICENSE")
        found = [path for path in repo_root.rglob("SKILL.md") if ".git" not in path.parts and "node_modules" not in path.parts]
        checks.require(found == [skill_dir / "SKILL.md"], f"expected one discoverable SKILL.md; found: {found}")
        repo_docs = [repo_root / "README.md", repo_root / "docs" / "selection.md"]
        for document in repo_docs:
            checks.require(document.is_file(), f"missing repository document: {document.relative_to(repo_root)}")
        validate_links(repo_root, [document for document in repo_docs if document.is_file()], checks, files_only=False)
    nested = [path for path in skill_dir.rglob("SKILL.md") if path != skill_dir / "SKILL.md"]
    checks.require(not nested, f"vendored files must not add another SKILL.md: {nested}")
    if skill_dir.is_dir():
        validate_frontmatter(skill_dir, checks)
        runtime_markdown = [path for path in skill_dir.rglob("*.md") if "vendor" not in path.relative_to(skill_dir).parts]
        validate_links(skill_dir, runtime_markdown, checks, files_only=True)
        validate_sources(skill_dir, checks)
    if checks.errors:
        for error in checks.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {skill_dir} is one complete, linked, hash-verified Agent Skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
