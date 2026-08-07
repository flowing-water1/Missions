#!/usr/bin/env python3
"""检查 handoff 是否真挂在 mission CSV 的 REVIEW 收口链上。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from lint_handoff import lint
from run_vision_review import validate_review_result
from validate_deferred_ledger import COVERAGE_RE, load_csv_deferred
from validate_outcome_contract import load_contract


HANDOFF_SUFFIX = ".handoff.md"
OUTCOME_RE = re.compile(r"(?:^|;\s*)outcome_contract:([^;]+)")
REVIEW_JSON_RE = re.compile(r"(?:^|;\s*)review_json:([^;]+)")
REVIEW_RESULT_RE = re.compile(r"(?:^|;\s*)review_result:([^;]+)")
HUMANIZED_RE = re.compile(r"(?:^|;\s*)handoff_humanized:([^;]+)")
DEFERRED_MARKER_RE = re.compile(r"<!--\s*deferred:(DF-\d{3,})\s*-->")


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


def load_outcome_contract(csv_path: Path) -> tuple[dict | None, list[str]]:
    try:
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        return None, [f"CSV read failed while discovering outcome contract: {exc}"]

    values: list[str] = []
    for row in rows:
        match = OUTCOME_RE.search(str(row.get("notes") or ""))
        if match:
            value = match.group(1).strip()
            if value not in values:
                values.append(value)
    if not values:
        return None, []
    if len(values) > 1:
        return None, ["CSV references multiple outcome contracts: " + ", ".join(values)]

    value_path = Path(normalize_path_text(values[0])).expanduser()
    contract_path = value_path if value_path.is_absolute() else csv_path.parent / value_path
    data, errors = load_contract(contract_path.resolve())
    return data, errors


def load_review_json(csv_path: Path) -> tuple[dict | None, list[str]]:
    try:
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        return None, [f"CSV read failed while discovering review JSON: {exc}"]

    review_rows = [
        row
        for row in rows
        if str(row.get("id") or "").upper().startswith("REVIEW-")
        or str(row.get("area") or "").lower() == "review"
    ]
    if not review_rows:
        return None, ["CSV contains no REVIEW row for review JSON selection"]
    latest_notes = str(review_rows[-1].get("notes") or "")
    review_match = REVIEW_JSON_RE.search(latest_notes)
    if not review_match:
        return None, []
    value_path = Path(normalize_path_text(review_match.group(1).strip())).expanduser()
    review_path = value_path if value_path.is_absolute() else csv_path.parent / value_path
    if not review_path.is_file():
        return None, [f"review JSON does not exist: {review_path.resolve()}"]
    try:
        data = json.loads(review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"review JSON is not valid JSON: {review_path.resolve()}: {exc}"]
    if not isinstance(data, dict):
        return None, ["review JSON root must be an object"]
    errors: list[str] = []
    result_match = REVIEW_RESULT_RE.search(latest_notes)
    if not result_match:
        errors.append("latest REVIEW notes missing review_result:<result>")
    elif result_match.group(1).strip() != data.get("result"):
        errors.append("CSV review_result differs from review JSON result")
    return data, errors


def markdown_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def validate_handoff_against_review(text: str, contract: dict, review: dict) -> list[str]:
    errors: list[str] = []
    rows = markdown_rows(text)
    questions = {
        item.get("id"): item.get("question")
        for item in contract.get("reader_questions", [])
        if isinstance(item, dict)
    }
    for answer in review.get("outcome_answers", []):
        if not isinstance(answer, dict):
            continue
        question_id = answer.get("question_id")
        question = questions.get(question_id)
        expected = [
            question,
            answer.get("verdict"),
            answer.get("answer"),
            "; ".join(answer.get("evidence_refs") or []),
            answer.get("confidence"),
            answer.get("boundary"),
            answer.get("next_action"),
        ]
        if not any(len(row) >= 7 and row[:7] == expected for row in rows):
            errors.append(f"handoff answer differs from review JSON for {question_id}")

    for claim in contract.get("blocked_claims", []):
        if not isinstance(claim, dict):
            continue
        expected = [claim.get("claim"), claim.get("reason"), claim.get("release_condition")]
        if not any(len(row) >= 3 and row[:3] == expected for row in rows):
            errors.append(f"handoff blocked claim differs from Outcome Contract: {claim.get('claim')}")
    return errors


def check_contract(handoff_path: Path, csv_path: Path | None = None) -> list[str]:
    missing: list[str] = []

    if not handoff_path.name.endswith(HANDOFF_SUFFIX):
        missing.append("handoff 文件名必须以 .handoff.md 结尾")

    try:
        text = handoff_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"handoff 读取失败: {exc}"]

    effective_csv_path = csv_path or infer_csv_path(handoff_path)
    if effective_csv_path is None:
        missing.append("无法从 handoff 路径推导同名前缀 CSV")
        return missing
    if not effective_csv_path.exists():
        missing.append(f"CSV 不存在: {effective_csv_path}")
        return missing

    outcome_contract, outcome_errors = load_outcome_contract(effective_csv_path)
    missing.extend(outcome_errors)
    if outcome_contract is None:
        missing.extend(lint(text))
    else:
        review_json, review_errors = load_review_json(effective_csv_path)
        missing.extend(review_errors)
        if review_json is None and not review_errors:
            missing.append("Outcome Contract handoff requires review_json:<path> in CSV notes")
        elif review_json is not None:
            missing.extend(validate_review_result(review_json, outcome_contract))
            missing.extend(validate_handoff_against_review(text, outcome_contract, review_json))
        missing.extend(
            lint(
                text,
                reader_questions=outcome_contract.get("reader_questions", []),
                blocked_claims=outcome_contract.get("blocked_claims", []),
            )
        )

    review_notes, csv_missing = load_review_notes(effective_csv_path)
    missing.extend(csv_missing)
    if review_notes:
        humanized_match = HUMANIZED_RE.search(review_notes[-1])
        if not humanized_match or humanized_match.group(1).strip().lower() != "true":
            missing.append("latest REVIEW notes must record handoff_humanized:true")
        has_handoff_path = any(
            note_value_matches_handoff(value, handoff_path, effective_csv_path)
            for value in handoff_note_values(review_notes[-1])
        )
        if not has_handoff_path:
            missing.append("latest REVIEW notes 未记录 handoff:<path>")

    findings, _, deferred_errors, _ = load_csv_deferred(
        effective_csv_path.resolve(), Path.cwd().resolve()
    )
    missing.extend(deferred_errors)
    open_ids = {
        finding_id for finding_id, item in findings.items()
        if item.get("status") == "open"
    }
    markers = set(DEFERRED_MARKER_RE.findall(text))
    for finding_id in sorted(markers - open_ids):
        missing.append(f"handoff references unknown or closed deferred finding: {finding_id}")
    if open_ids:
        if "## 待讨论" not in text:
            missing.append("handoff missing 待讨论 section for open deferred findings")
        for finding_id in sorted(open_ids - markers):
            missing.append(f"handoff missing open deferred finding: {finding_id}")
        latest_notes = review_notes[-1] if review_notes else ""
        coverage_match = COVERAGE_RE.search(latest_notes)
        expected_covered = len(open_ids & markers)
        expected_total = len(open_ids)
        if not coverage_match:
            missing.append("latest REVIEW notes missing deferred_coverage:<covered>/<open>")
        elif (int(coverage_match.group(1)), int(coverage_match.group(2))) != (
            expected_covered,
            expected_total,
        ):
            missing.append(
                "CSV deferred_coverage differs from handoff coverage: "
                f"expected {expected_covered}/{expected_total}"
            )

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
