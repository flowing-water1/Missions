#!/usr/bin/env python3
"""Register the credential-free reviewer fragment in a live Codex config."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import tomllib
from pathlib import Path


EXPECTED = {"config_file": "agents/reviewer.toml"}


def load_toml(path: Path) -> dict:
    text = path.read_bytes().decode("utf-8-sig")
    return tomllib.loads(text)


def fragment_table(fragment: Path) -> dict:
    table = load_toml(fragment).get("agents", {}).get("reviewer")
    if table != EXPECTED:
        raise ValueError("fragment must contain only agents.reviewer.config_file=agents/reviewer.toml")
    return table


def validate_registration(config: Path, fragment: Path) -> None:
    expected = fragment_table(fragment)
    actual = load_toml(config).get("agents", {}).get("reviewer")
    if actual != expected:
        raise ValueError("live agents.reviewer table does not match the tracked fragment")


def atomic_write(path: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def register(config: Path, fragment: Path, backup: Path) -> None:
    config = config.resolve()
    fragment = fragment.resolve()
    original = config.read_bytes()
    parsed = load_toml(config)
    fragment_table(fragment)

    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(config, backup)

    existing = parsed.get("agents", {}).get("reviewer")
    if existing is not None:
        validate_registration(config, fragment)
        return

    newline = b"\r\n" if b"\r\n" in original else b"\n"
    fragment_bytes = fragment.read_bytes().lstrip(b"\xef\xbb\xbf")
    fragment_bytes = fragment_bytes.replace(b"\r\n", b"\n").replace(b"\n", newline).rstrip()
    updated = original.rstrip() + newline + newline + fragment_bytes + newline
    try:
        atomic_write(config, updated)
        validate_registration(config, fragment)
    except Exception:
        atomic_write(config, original)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--fragment", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    register(args.config, args.fragment, args.backup)
    print("reviewer registration validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
