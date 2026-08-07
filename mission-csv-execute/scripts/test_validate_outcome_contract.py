#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_outcome_contract.py")


def valid_contract() -> dict:
    return {
        "source": "docs/spec.md",
        "execution_scope": "full spec",
        "artifact_role": {
            "kind": "design",
            "producer": "approved spec",
            "consumers": ["mission review", "handoff"],
            "authority": "implementation and validation scope",
            "not_authority": "actual runtime result",
        },
        "desired_effects": [
            {
                "id": "EFFECT-001",
                "statement": "Users can recover interrupted imports.",
                "source_ref": "docs/spec.md:10",
            }
        ],
        "reader_questions": [
            {
                "id": "OUTCOME-001",
                "question": "Can an interrupted import resume without duplication?",
                "why_it_matters": "This is the user-visible capability.",
                "evidence_required": "real_e2e",
                "scope": "targeted recovery scenario",
                "source_ref": "docs/spec.md:20",
                "status": "pending",
            }
        ],
        "decisive_result": {
            "question": "What proves recovery works end to end?",
            "success_condition": "The resumed import completes without duplicate rows.",
            "failure_condition": "The import restarts, loses rows, or duplicates rows.",
            "source_refs": ["docs/spec.md:20"],
        },
        "blocked_claims": [
            {
                "claim": "All import formats are production ready.",
                "reason": "Only CSV recovery is in scope.",
                "release_condition": "Run the full format matrix.",
                "source_ref": "docs/spec.md:30",
            }
        ],
    }


def run_validate(path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
    )


class OutcomeContractValidationTests(unittest.TestCase):
    def test_valid_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.outcomes.json"
            path.write_text(json.dumps(valid_contract()), encoding="utf-8")

            result = run_validate(path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("outcome_contract_ok", result.stdout)

    def test_duplicate_question_ids_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = valid_contract()
            payload["reader_questions"].append(dict(payload["reader_questions"][0]))
            path = Path(tmp) / "sample.outcomes.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            result = run_validate(path)

            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate reader question id: OUTCOME-001", result.stderr)

    def test_non_pending_question_status_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = valid_contract()
            payload["reader_questions"][0]["status"] = "pass"
            path = Path(tmp) / "sample.outcomes.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            result = run_validate(path)

            self.assertEqual(result.returncode, 1)
            self.assertIn("status must be pending", result.stderr)

    def test_invalid_artifact_kind_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = valid_contract()
            payload["artifact_role"]["kind"] = "report"
            path = Path(tmp) / "sample.outcomes.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            result = run_validate(path)

            self.assertEqual(result.returncode, 1)
            self.assertIn("artifact_role has invalid kind: report", result.stderr)

    def test_empty_consumers_and_source_refs_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = valid_contract()
            payload["artifact_role"]["consumers"] = []
            payload["decisive_result"]["source_refs"] = []
            path = Path(tmp) / "sample.outcomes.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            result = run_validate(path)

            self.assertEqual(result.returncode, 1)
            self.assertIn("artifact_role consumers must be a non-empty string array", result.stderr)
            self.assertIn("decisive_result source_refs must be a non-empty string array", result.stderr)


if __name__ == "__main__":
    unittest.main()
