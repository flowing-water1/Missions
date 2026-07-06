#!/usr/bin/env python3
"""Validate persisted claim ledger references for mission CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


CLAIMS_RE = re.compile(r"(?:^|;\s*)claims:([^;]+)")
LEDGER_RE = re.compile(r"(?:^|;\s*)claim_ledger:([^;]+)")


def split_claim_ids(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def tag_value(pattern: re.Pattern[str], notes: str) -> str | None:
    match = pattern.search(notes or "")
    return match.group(1).strip() if match else None


def resolve_path(value: str, base_dir: Path, workdir: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    for root in (workdir, base_dir):
        candidate = (root / path).resolve()
        if candidate.exists():
            return candidate
    return (workdir / path).resolve()


def validate_ledger(ledger_path: Path, csv_path: Path, referenced_claims: set[str]) -> list[str]:
    errors: list[str] = []
    if not ledger_path.is_file():
        return [f"claim ledger does not exist: {ledger_path}"]
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"claim ledger is not valid JSON: {ledger_path}: {exc}"]

    if not isinstance(data, dict):
        return [f"claim ledger root must be an object: {ledger_path}"]
    if "claims" not in data or not isinstance(data["claims"], list):
        errors.append("claim ledger must contain a claims array")
        claims = []
    else:
        claims = data["claims"]

    ledger_ids: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claims[{index}] must be an object")
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            errors.append(f"claims[{index}] missing claim_id")
            continue
        ledger_ids.add(claim_id)
        for key in ("source_ref", "promise", "covered_by", "evidence_required", "production_path_required", "status"):
            if key not in claim:
                errors.append(f"{claim_id} missing {key}")
        if "covered_by" in claim and not isinstance(claim["covered_by"], list):
            errors.append(f"{claim_id} covered_by must be a list")

    missing = sorted(referenced_claims - ledger_ids)
    if missing:
        errors.append("claim ledger missing referenced claim ids: " + ", ".join(missing))

    csv_name = csv_path.name
    if data.get("csv") not in (None, csv_name, str(csv_path)):
        errors.append(f"claim ledger csv field does not match {csv_name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path")
    parser.add_argument("--workdir", default=".")
    args = parser.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    csv_path = resolve_path(args.csv_path, workdir, workdir)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig", newline="")))
    referenced_claims: set[str] = set()
    ledger_values: set[str] = set()
    errors: list[str] = []

    for row in rows:
        notes = row.get("notes", "")
        claims_value = tag_value(CLAIMS_RE, notes)
        ledger_value = tag_value(LEDGER_RE, notes)
        if claims_value:
            referenced_claims.update(split_claim_ids(claims_value))
            if not ledger_value:
                errors.append(f"{row.get('id', '<unknown>')} has claims but no claim_ledger tag")
        if ledger_value:
            ledger_values.add(ledger_value)

    if referenced_claims and not ledger_values:
        errors.append("CSV references claims but no claim_ledger tag was found")
    for value in sorted(ledger_values):
        ledger_path = resolve_path(value, csv_path.parent, workdir)
        errors.extend(validate_ledger(ledger_path, csv_path, referenced_claims))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("claim_ledger_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
