#!/usr/bin/env python3
"""Validate canonical mission spec metadata and approval state."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


ALLOWED_KEYS = ("mission", "status", "created", "approved_at")
REQUIRED_SECTIONS = ("Goal", "Scope", "Design", "Acceptance Criteria")
KEY_VALUE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):[ \t]+([^\r\n]+)$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _has_additional_frontmatter(lines: list[str]) -> bool:
    delimiters: list[int] = []
    fence: str | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is None and line == "---":
            delimiters.append(index)
    for start, end in zip(delimiters, delimiters[1:]):
        block = [line for line in lines[start + 1 : end] if line.strip()]
        if block and any(re.match(r"^[A-Za-z][A-Za-z0-9_-]*:", line) for line in block):
            return True
    return False


def _valid_iso_date(value: str) -> bool:
    if not ISO_DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_rfc3339(value: str) -> bool:
    if not RFC3339_RE.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_text(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    metadata: dict[str, str] = {}
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return metadata, ["document must start with exactly one frontmatter block"]

    try:
        closing = lines.index("---", 1)
    except ValueError:
        return metadata, ["frontmatter block is not closed"]

    if _has_additional_frontmatter(lines[closing + 1 :]):
        errors.append("document contains an additional frontmatter block")

    frontmatter = lines[1:closing]
    nested_reported = False
    for line in frontmatter:
        match = KEY_VALUE_RE.fullmatch(line)
        if not match:
            if not nested_reported:
                errors.append("nested frontmatter values are not allowed")
                nested_reported = True
            continue
        key, value = match.groups()
        value = value.strip()
        if key in metadata:
            errors.append(f"duplicate frontmatter key: {key}")
            continue
        metadata[key] = value
        if value.startswith(("[", "{")):
            errors.append("frontmatter arrays are not allowed")
        if value.startswith(("*", "&")):
            errors.append("frontmatter aliases are not allowed")
        if value.startswith("!"):
            errors.append("frontmatter tags are not allowed")

    for key in metadata:
        if key not in ALLOWED_KEYS:
            errors.append(f"unknown frontmatter key: {key}")
    for key in ("mission", "status", "created"):
        if key not in metadata:
            errors.append(f"missing frontmatter key: {key}")

    if metadata.get("mission") != "spec":
        errors.append("mission must be spec")
    status = metadata.get("status")
    if status not in {"draft", "approved"}:
        errors.append("status must be draft or approved")
    if "created" in metadata and not _valid_iso_date(metadata["created"]):
        errors.append("created must be an ISO date")
    if status == "approved":
        approved_at = metadata.get("approved_at")
        if not approved_at:
            errors.append("approved spec requires approved_at")
        elif not _valid_rfc3339(approved_at):
            errors.append("approved_at must be an RFC 3339 timestamp with timezone")
    elif status == "draft" and "approved_at" in metadata:
        errors.append("draft spec must not contain approved_at")

    body = "\n".join(lines[closing + 1 :])
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"(?m)^##[ \t]+{re.escape(section)}[ \t]*$", body):
            errors.append(f"missing required section: {section}")
    return metadata, errors


def _git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        check=False,
        capture_output=True,
    )


def _validate_committed_clean(path: Path) -> list[str]:
    root_result = _git(path.parent, "rev-parse", "--show-toplevel")
    if root_result.returncode != 0:
        return ["approved spec must be inside a Git repository"]
    root = Path(root_result.stdout.decode(errors="replace").strip()).resolve()
    try:
        relative = path.resolve().relative_to(root).as_posix()
    except ValueError:
        return ["approved spec must be inside the containing Git repository"]

    committed = _git(root, "cat-file", "-e", f"HEAD:{relative}")
    if committed.returncode != 0:
        return ["approved spec must be committed"]
    dirty = _git(root, "diff", "--quiet", "HEAD", "--", relative)
    if dirty.returncode == 1:
        return ["approved spec differs from HEAD and must return to draft"]
    if dirty.returncode != 0:
        return ["unable to compare approved spec with HEAD"]
    return []


def validate_path(path: Path, require_committed_approved: bool = True) -> list[str]:
    path = path.expanduser().resolve()
    if not path.is_file():
        return [f"spec file does not exist: {path}"]
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return ["spec must be UTF-8 text"]
    metadata, errors = validate_text(text)
    if not errors and require_committed_approved and metadata.get("status") == "approved":
        errors.extend(_validate_committed_clean(path))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument(
        "--allow-uncommitted-approved",
        action="store_true",
        help="Validate metadata without requiring an approved spec to match HEAD.",
    )
    args = parser.parse_args()
    errors = validate_path(
        args.spec,
        require_committed_approved=not args.allow_uncommitted_approved,
    )
    if errors:
        for error in errors:
            sys.stderr.write(error + "\n")
        return 1
    print(f"valid mission spec: {args.spec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
