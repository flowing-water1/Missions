#!/usr/bin/env python3
"""Commit named task paths without disturbing unrelated staged changes."""

from __future__ import annotations

import subprocess
import os
from pathlib import Path


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, check=False)
    if check and proc.returncode != 0:
        message = (proc.stderr or proc.stdout).decode(errors="replace").strip()
        raise RuntimeError(message or f"git {' '.join(args)} failed with {proc.returncode}")
    return proc


def index_patch(repo: Path) -> bytes:
    return _git(repo, "diff", "--cached", "--binary").stdout


def staged_paths(repo: Path) -> set[str]:
    output = _git(repo, "diff", "--cached", "--name-only", "-z").stdout
    return {item.decode(errors="surrogateescape") for item in output.split(b"\0") if item}


def _normalized_relative(repo: Path, path: Path) -> str:
    candidate = path if path.is_absolute() else repo / path
    try:
        relative = candidate.resolve().relative_to(repo.resolve()).as_posix().rstrip("/")
    except ValueError as exc:
        raise RuntimeError(f"task path escapes repository: {path}") from exc
    if not relative or relative == ".":
        raise RuntimeError("task path must not be the repository root")
    return relative


def _paths_overlap(left: str, right: str) -> bool:
    if os.name == "nt":
        left, right = left.casefold(), right.casefold()
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def commit_paths(repo: Path, paths: list[Path], message: str) -> str:
    repo = repo.resolve()
    task_paths = [_normalized_relative(repo, path) for path in paths]
    staged = staged_paths(repo)
    overlap = sorted(
        staged_path
        for staged_path in staged
        if any(_paths_overlap(task_path, staged_path) for task_path in task_paths)
    )
    if overlap:
        raise RuntimeError("task path already has staged changes: " + ", ".join(overlap))
    before = index_patch(repo)
    _git(repo, "add", "--", *task_paths)
    try:
        _git(repo, "commit", "--only", "-m", message, "--", *task_paths)
    except Exception:
        if index_patch(repo) != before:
            raise RuntimeError("commit failed and index delta could not be preserved exactly")
        raise
    if index_patch(repo) != before:
        raise RuntimeError("unrelated staged patch changed during task commit")
    return _git(repo, "rev-parse", "HEAD").stdout.decode().strip()
