#!/usr/bin/env python3
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_deferred_ledger.py")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "area", "notes"])
        writer.writeheader()
        writer.writerows(rows)


def finding(kind: str = "deferred_improvement", status: str = "open") -> dict:
    return {
        "id": "DF-001",
        "kind": kind,
        "status": status,
        "title": "评估样本覆盖不足",
        "summary": "现有样本没有覆盖长对话中的偏好迁移。",
        "source_issue_ids": ["DEV-01"],
        "evidence_refs": ["trace:abc123"],
        "why_deferred": "不影响本轮已批准的写入链路验收。",
        "discussion_question": "下一轮是否扩充长对话样本？",
    }


def write_ledger(path: Path, item: dict) -> None:
    payload = {
        "schema_version": 1,
        "csv": "sample.csv",
        "findings": [item],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def run_validate(csv_path: Path, workdir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path), "--workdir", str(workdir)],
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
    )


class DeferredLedgerValidationTests(unittest.TestCase):
    def test_valid_open_finding_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "sample.csv"
            write_csv(csv_path, [{
                "id": "DEV-01",
                "area": "backend",
                "notes": "deferred_ledger:sample.deferred.json; deferred_findings:DF-001",
            }])
            write_ledger(root / "sample.deferred.json", finding())

            result = run_validate(csv_path, root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("deferred_ledger_ok", result.stdout)

    def test_current_scope_gap_cannot_be_deferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "sample.csv"
            write_csv(csv_path, [{
                "id": "DEV-01",
                "area": "backend",
                "notes": "deferred_ledger:sample.deferred.json; deferred_findings:DF-001",
            }])
            write_ledger(root / "sample.deferred.json", finding(kind="current_scope_gap"))

            result = run_validate(csv_path, root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid kind", result.stderr)

    def test_every_finding_must_be_referenced_by_csv_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "sample.csv"
            write_csv(csv_path, [{
                "id": "DEV-01",
                "area": "backend",
                "notes": "deferred_ledger:sample.deferred.json",
            }])
            write_ledger(root / "sample.deferred.json", finding())

            result = run_validate(csv_path, root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("unreferenced finding ids: DF-001", result.stderr)

    def test_finding_reference_requires_ledger_tag_on_same_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "sample.csv"
            write_csv(csv_path, [
                {
                    "id": "SETUP-01",
                    "area": "backend",
                    "notes": "deferred_ledger:sample.deferred.json",
                },
                {
                    "id": "DEV-01",
                    "area": "backend",
                    "notes": "deferred_findings:DF-001",
                },
            ])
            write_ledger(root / "sample.deferred.json", finding())

            result = run_validate(csv_path, root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("DEV-01 has deferred findings but no deferred_ledger tag", result.stderr)


if __name__ == "__main__":
    unittest.main()
