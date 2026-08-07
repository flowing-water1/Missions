#!/usr/bin/env python3
"""Validate deferred-finding ledger references for a mission CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


LEDGER_RE = re.compile(r"(?:^|;\s*)deferred_ledger:([^;]+)")
FINDINGS_RE = re.compile(r"(?:^|;\s*)deferred_findings:([^;]+)")
COVERAGE_RE = re.compile(r"(?:^|;\s*)deferred_coverage:(\d+)/(\d+)")
FINDING_ID_RE = re.compile(r"DF-\d{3,}")
ALLOWED_KINDS = {"deferred_improvement", "future_decision"}
ALLOWED_STATUSES = {"open", "promoted", "dismissed"}
REQUIRED_STRING_FIELDS = {
    "title",
    "summary",
    "why_deferred",
    "discussion_question",
}


def tag_value(pattern: re.Pattern[str], notes: str) -> str | None:
    match = pattern.search(notes or "")
    return match.group(1).strip() if match else None


def split_ids(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def resolve_path(value: str, base_dir: Path, workdir: Path) -> Path:
    path = Path(value.strip().strip("\"'")).expanduser()
    if path.is_absolute():
        return path.resolve()
    for root in (base_dir, workdir):
        candidate = (root / path).resolve()
        if candidate.exists():
            return candidate
    return (base_dir / path).resolve()


def _non_empty_strings(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def validate_ledger_data(
    data: object,
    ledger_path: Path,
    csv_path: Path,
    csv_issue_ids: set[str],
    referenced_ids: set[str],
) -> tuple[list[str], dict[str, dict]]:
    errors: list[str] = []
    findings_by_id: dict[str, dict] = {}
    if not isinstance(data, dict):
        return [f"deferred ledger root must be an object: {ledger_path}"], findings_by_id
    if data.get("schema_version") != 1:
        errors.append("deferred ledger schema_version must be 1")
    if data.get("csv") not in (None, csv_path.name, str(csv_path)):
        errors.append(f"deferred ledger csv field does not match {csv_path.name}")
    findings = data.get("findings")
    if not isinstance(findings, list):
        return errors + ["deferred ledger must contain a findings array"], findings_by_id

    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"findings[{index}] must be an object")
            continue
        finding_id = finding.get("id")
        if not isinstance(finding_id, str) or not FINDING_ID_RE.fullmatch(finding_id):
            errors.append(f"findings[{index}] has invalid id: {finding_id}")
            continue
        if finding_id in findings_by_id:
            errors.append(f"duplicate deferred finding id: {finding_id}")
            continue
        findings_by_id[finding_id] = finding
        kind = finding.get("kind")
        if kind not in ALLOWED_KINDS:
            errors.append(f"{finding_id} has invalid kind: {kind}")
        status = finding.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{finding_id} has invalid status: {status}")
        for key in sorted(REQUIRED_STRING_FIELDS):
            if not isinstance(finding.get(key), str) or not finding[key].strip():
                errors.append(f"{finding_id} missing {key}")
        for key in ("source_issue_ids", "evidence_refs"):
            if not _non_empty_strings(finding.get(key)):
                errors.append(f"{finding_id} {key} must be a non-empty string array")
        source_ids = finding.get("source_issue_ids")
        if isinstance(source_ids, list):
            unknown = sorted(set(source_ids) - csv_issue_ids)
            if unknown:
                errors.append(f"{finding_id} has unknown source issue ids: {', '.join(unknown)}")

    unknown_refs = sorted(referenced_ids - set(findings_by_id))
    if unknown_refs:
        errors.append("CSV references unknown deferred finding ids: " + ", ".join(unknown_refs))
    unreferenced = sorted(set(findings_by_id) - referenced_ids)
    if unreferenced:
        errors.append("unreferenced finding ids: " + ", ".join(unreferenced))
    return errors, findings_by_id


def load_csv_deferred(
    csv_path: Path, workdir: Path
) -> tuple[dict[str, dict], Path | None, list[str], list[dict[str, str]]]:
    try:
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        return {}, None, [f"CSV read failed: {exc}"], []

    errors: list[str] = []
    ledger_values: set[str] = set()
    referenced_ids: set[str] = set()
    csv_issue_ids = {str(row.get("id") or "") for row in rows if row.get("id")}
    for row in rows:
        notes = str(row.get("notes") or "")
        ledger_value = tag_value(LEDGER_RE, notes)
        findings_value = tag_value(FINDINGS_RE, notes)
        if ledger_value:
            ledger_values.add(ledger_value)
        if findings_value:
            referenced_ids.update(split_ids(findings_value))
            if not ledger_value:
                errors.append(f"{row.get('id', '<unknown>')} has deferred findings but no deferred_ledger tag")

    if len(ledger_values) > 1:
        errors.append("CSV references multiple deferred ledgers: " + ", ".join(sorted(ledger_values)))
        return {}, None, errors, rows
    if not ledger_values:
        if referenced_ids:
            errors.append("CSV references deferred findings but no deferred_ledger tag was found")
        return {}, None, errors, rows

    ledger_path = resolve_path(next(iter(ledger_values)), csv_path.parent, workdir)
    if not ledger_path.is_file():
        return {}, ledger_path, errors + [f"deferred ledger does not exist: {ledger_path}"], rows
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, ledger_path, errors + [f"deferred ledger is not valid JSON: {ledger_path}: {exc}"], rows
    ledger_errors, findings_by_id = validate_ledger_data(
        data, ledger_path, csv_path, csv_issue_ids, referenced_ids
    )
    errors.extend(ledger_errors)

    review_rows = [
        row for row in rows
        if str(row.get("id") or "").upper().startswith("REVIEW-")
        or str(row.get("area") or "").lower() == "review"
    ]
    if review_rows:
        notes = str(review_rows[-1].get("notes") or "")
        coverage = COVERAGE_RE.search(notes)
        if coverage:
            covered, total = int(coverage.group(1)), int(coverage.group(2))
            open_total = sum(1 for item in findings_by_id.values() if item.get("status") == "open")
            if total != open_total:
                errors.append(
                    f"deferred_coverage total {total} does not match open findings {open_total}"
                )
            if covered > total:
                errors.append("deferred_coverage covered count cannot exceed total")
    return findings_by_id, ledger_path, errors, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path")
    parser.add_argument("--workdir", default=".")
    args = parser.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    csv_path = resolve_path(args.csv_path, workdir, workdir)
    _, _, errors, _ = load_csv_deferred(csv_path, workdir)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("deferred_ledger_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
