#!/usr/bin/env python3
"""检查 handoff 是否真挂在 mission CSV 的 REVIEW 收口链上。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from lint_handoff import lint


HANDOFF_SUFFIX = ".handoff.md"


def infer_csv_path(handoff_path: Path) -> Path | None:
    name = handoff_path.name
    if not name.endswith(HANDOFF_SUFFIX):
        return None
    csv_name = name[: -len(HANDOFF_SUFFIX)] + ".csv"
    return handoff_path.with_name(csv_name)


def normalize_path_text(value: str) -> str:
    return value.strip().strip("\"'").replace("\\", "/").lstrip("./")


def note_value_matches_handoff(value: str, handoff_path: Path, csv_path: Path) -> bool:
    normalized = normalize_path_text(value)
    if not normalized:
        return False
    if normalized.startswith(("generation_failed", "lint_failed", "contract_failed")):
        return False

    value_path = Path(normalized)
    handoff_resolved = handoff_path.resolve()
    candidates = []
    if value_path.is_absolute():
        candidates.append(value_path)
    else:
        candidates.append((csv_path.parent / value_path))
        if value_path.parent != Path("."):
            candidates.append((Path.cwd() / value_path))

    for candidate in candidates:
        if candidate.resolve() == handoff_resolved:
            return True

    if value_path.parent != Path("."):
        return normalize_path_text(handoff_path.as_posix()).endswith(normalized)

    return False


def handoff_note_values(notes: str) -> list[str]:
    values: list[str] = []
    for part in notes.split(";"):
        token = part.strip()
        if token.startswith("handoff:"):
            values.append(token.split(":", 1)[1].strip())
    return values


def load_review_notes(csv_path: Path) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    try:
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return [], ["CSV 没有表头"]
            if "id" not in reader.fieldnames or "notes" not in reader.fieldnames:
                return [], ["CSV 缺少 id 或 notes 列"]
            rows = list(reader)
    except OSError as exc:
        return [], [f"CSV 读取失败: {exc}"]

    review_notes = [
        str(row.get("notes") or "")
        for row in rows
        if str(row.get("id") or "").upper().startswith("REVIEW-")
        or str(row.get("area") or "").lower() == "review"
    ]
    if not review_notes:
        missing.append("CSV 中没有 REVIEW-* 行")
    return review_notes, missing


def check_contract(handoff_path: Path, csv_path: Path | None = None) -> list[str]:
    missing: list[str] = []

    if not handoff_path.name.endswith(HANDOFF_SUFFIX):
        missing.append("handoff 文件名必须以 .handoff.md 结尾")

    try:
        text = handoff_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"handoff 读取失败: {exc}"]

    missing.extend(lint(text))

    effective_csv_path = csv_path or infer_csv_path(handoff_path)
    if effective_csv_path is None:
        missing.append("无法从 handoff 路径推导同名前缀 CSV")
        return missing
    if not effective_csv_path.exists():
        missing.append(f"CSV 不存在: {effective_csv_path}")
        return missing

    review_notes, csv_missing = load_review_notes(effective_csv_path)
    missing.extend(csv_missing)
    if review_notes:
        has_handoff_path = any(
            note_value_matches_handoff(value, handoff_path, effective_csv_path)
            for notes in review_notes
            for value in handoff_note_values(notes)
        )
        if not has_handoff_path:
            missing.append("REVIEW notes 未记录 handoff:<path>")

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="检查 mission handoff 是否挂在 CSV REVIEW 链上，并通过结构 lint"
    )
    parser.add_argument("handoff_path", help="要检查的 .handoff.md")
    parser.add_argument("--csv", dest="csv_path", help="显式指定 CSV；默认用同名前缀 .csv")
    args = parser.parse_args()

    handoff_path = Path(args.handoff_path)
    csv_path = Path(args.csv_path) if args.csv_path else None
    missing = check_contract(handoff_path, csv_path)
    if missing:
        sys.stderr.write(f"check_handoff_contract: {handoff_path} 不合格，缺以下合同条件：\n")
        for item in missing:
            sys.stderr.write(f"  - {item}\n")
        return 1

    sys.stdout.write(f"handoff_contract: passed {handoff_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
