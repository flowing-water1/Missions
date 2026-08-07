#!/usr/bin/env python3
"""Append REVIEW-01 to a valid compatibility CSV when it has no review row."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


FIELDNAMES = [
    "id", "priority", "phase", "area", "title", "description",
    "acceptance_criteria", "test_mcp", "required_skills", "required_mcp",
    "review_initial_requirements", "review_regression_requirements", "dev_state",
    "review_initial_state", "review_regression_state", "git_state", "owner",
    "refs", "notes",
]


def _scope(rows: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for row in rows:
        parts.append(
            " | ".join(
                f"{key}={row.get(key, '').strip()}"
                for key in ("id", "description", "acceptance_criteria", "refs", "notes")
                if row.get(key, "").strip()
            )
        )
    return "; ".join(part for part in parts if part)


def ensure_review_row(path: Path) -> bool:
    path = path.expanduser().resolve()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDNAMES:
            raise ValueError("CSV must use the standard 19-column header")
        rows = list(reader)
    if any(row.get("id", "").startswith("REVIEW-") for row in rows):
        return False

    phases = [int(row["phase"]) for row in rows if row.get("phase", "").isdigit()]
    review = dict.fromkeys(FIELDNAMES, "")
    review.update(
        {
            "id": "REVIEW-01",
            "priority": "P0",
            "phase": str(max(phases, default=0) + 1),
            "area": "review",
            "title": "Review compatibility CSV against delivered work",
            "description": "Review every ordinary row's declared scope, acceptance data, delivered diff, and validation evidence.",
            "acceptance_criteria": "WHEN all ordinary rows are closed THEN run reviewer-subagent, codex-exec-independent, or self-review and classify every finding; WHEN current-scope gaps exist THEN append follow-up rows and another REVIEW row; WHEN no current-scope gaps remain THEN record the actual review mode and close.",
            "test_mcp": "MANUAL",
            "review_initial_requirements": "Verify all ordinary rows are closed before review.",
            "review_regression_requirements": "Review source CSV scope: " + _scope(rows),
            "dev_state": "未开始",
            "review_initial_state": "未开始",
            "review_regression_state": "未开始",
            "git_state": "未提交",
            "refs": str(path),
            "notes": (
                f"review_kind:vision; source_csv:{path}; "
                "review_agent_mode:pending; review_independence:pending; "
                "review_requested_model:gpt-5.6-sol; review_observed_model:unknown; "
                "review_model_evidence:unknown; claim_coverage:unknown; "
                "claim_coverage_status:pending"
            ),
        }
    )
    rows.append(review)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    changed = ensure_review_row(args.csv_path)
    print("appended REVIEW-01" if changed else "review row already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
