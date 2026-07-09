#!/usr/bin/env python3
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_claim_ledger.py")


def write_csv(path: Path, notes: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "notes"])
        writer.writeheader()
        writer.writerow({"id": "DEV-01", "notes": notes})


def write_ledger(path: Path, claim_id: str) -> None:
    csv_name = path.name.removesuffix(".claims.json") + ".csv"
    payload = {
        "csv": csv_name,
        "claims": [
            {
                "claim_id": claim_id,
                "source_ref": "docs/spec.md:1",
                "promise": "sample promise",
                "covered_by": ["DEV-01"],
                "evidence_required": "unit",
                "production_path_required": True,
                "status": "covered",
            }
        ],
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


class ClaimLedgerValidationTests(unittest.TestCase):
    def test_basename_ledger_prefers_csv_directory_over_workdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            csv_path = run_dir / "sample.csv"
            write_csv(csv_path, "claim_ledger:sample.claims.json; claims:CLAIM-001")
            write_ledger(run_dir / "sample.claims.json", "CLAIM-001")
            write_ledger(root / "sample.claims.json", "STALE-CLAIM")

            result = run_validate(csv_path, root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("claim_ledger_ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
