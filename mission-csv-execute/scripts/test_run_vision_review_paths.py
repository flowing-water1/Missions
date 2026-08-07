#!/usr/bin/env python3
import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(__file__).with_name("run_vision_review.py")


def load_module():
    if str(SCRIPT.parent) not in sys.path:
        sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("run_vision_review", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_vision_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_result(**overrides):
    result = {
        "review_agent_mode": "codex-exec-independent",
        "review_independence": True,
        "review_requested_model": "gpt-5.6-sol",
        "review_observed_model": "gpt-5.6-sol",
        "review_model_evidence": "event-stream",
        "result": "vision_met",
        "claim_coverage": "1/1",
        "claim_coverage_status": "complete",
        "validation_limited": [],
        "summary": "Complete.",
        "gaps": [],
        "assumptions": [],
        "decision_debt": [],
        "deferred_findings": [],
        "human_required_blockers": [],
        "outcome_answers": [],
        "handoff_markdown": "# Sample -- 施工交工单",
    }
    result.update(overrides)
    return result


class RunVisionReviewPathTests(unittest.TestCase):
    def test_relative_claim_ledger_prefers_csv_directory_over_workdir(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            expected = run_dir / "sample.claims.json"
            expected.write_text("{}", encoding="utf-8")
            (root / "sample.claims.json").write_text("{}", encoding="utf-8")
            self.assertEqual(
                Path(module.resolve_existing_file("sample.claims.json", root, run_dir)),
                expected.resolve(),
            )

    def test_relative_output_file_prefers_csv_directory(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            self.assertEqual(
                module.output_file("sample.handoff.md", root, run_dir),
                (run_dir / "sample.handoff.md").resolve(),
            )

    def test_reviews_output_subdir_is_under_csv_directory(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            self.assertEqual(
                module.output_file("reviews/review-01.json", root, run_dir),
                (run_dir / "reviews" / "review-01.json").resolve(),
            )

    def test_repo_relative_issues_output_stays_repo_relative(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            self.assertEqual(
                module.output_file("issues/sample/sample.handoff.md", root, run_dir),
                (root / "issues" / "sample" / "sample.handoff.md").resolve(),
            )

    def test_output_path_cannot_escape_csv_artifact_root(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            with self.assertRaisesRegex(Exception, "output path escapes artifact root"):
                module.output_file("../../escaped.json", root, run_dir)

    def test_discovers_outcome_contract_from_csv_notes(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            csv_path = run_dir / "sample.csv"
            outcome_path = run_dir / "sample.outcomes.json"
            outcome_path.write_text("{}", encoding="utf-8")
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["id", "notes"])
                writer.writeheader()
                writer.writerow({"id": "REVIEW-01", "notes": "outcome_contract:sample.outcomes.json"})
            self.assertEqual(
                Path(module.discover_outcome_contract(str(csv_path), root)),
                outcome_path.resolve(),
            )

    def test_outcome_answers_must_cover_each_question_once(self) -> None:
        module = load_module()
        contract = {
            "reader_questions": [
                {"id": "OUTCOME-001", "question": "First?"},
                {"id": "OUTCOME-002", "question": "Second?"},
            ]
        }
        result = {
            "outcome_answers": [{
                "question_id": "OUTCOME-001",
                "verdict": "pass",
                "answer": "Yes.",
                "evidence_refs": ["tests/a.log"],
                "confidence": "high",
                "boundary": "Targeted scope only.",
                "next_action": "None.",
            }]
        }
        self.assertIn(
            "missing outcome answer: OUTCOME-002",
            module.validate_outcome_answers(result, contract),
        )

    def test_vision_met_rejects_non_pass_outcome(self) -> None:
        module = load_module()
        result = valid_result(outcome_answers=[{
            "question_id": "OUTCOME-001",
            "verdict": "partial",
            "answer": "Only part was verified.",
            "evidence_refs": ["tests/a.log"],
            "confidence": "high",
            "boundary": "One path remains unverified.",
            "next_action": "Run the remaining path.",
        }])
        contract = {"reader_questions": [{"id": "OUTCOME-001", "question": "First?"}]}
        self.assertIn(
            "vision_met requires every outcome verdict to be pass",
            module.validate_review_result(result, contract),
        )

    def test_gaps_found_requires_an_actual_gap_signal(self) -> None:
        module = load_module()
        result = valid_result(result="gaps_found")
        self.assertIn(
            "gaps_found requires a recorded gap signal",
            module.validate_review_result(result, None),
        )

    def test_reviewer_subagent_mode_is_independent(self) -> None:
        module = load_module()
        result = valid_result(
            review_agent_mode="reviewer-subagent",
            review_model_evidence="session-metadata",
        )
        self.assertEqual(module.validate_review_result(result, None), [])

    def test_self_review_can_close_but_is_not_independent(self) -> None:
        module = load_module()
        result = valid_result(
            review_agent_mode="self-review",
            review_independence=False,
            review_observed_model="unknown",
            review_model_evidence="unknown",
        )
        self.assertEqual(module.validate_review_result(result, None), [])

    def test_review_rejects_independence_mismatch(self) -> None:
        module = load_module()
        result = valid_result(review_agent_mode="self-review", review_independence=True)
        self.assertIn(
            "self-review requires review_independence=false",
            module.validate_review_result(result, None),
        )

    def test_legacy_review_modes_normalize_without_promoting_diff_only(self) -> None:
        module = load_module()
        expected = {
            "direct-spawn-agent": ("reviewer-subagent", True, False),
            "direct-same-model-subagent": ("reviewer-subagent", True, False),
            "codex-exec-subagent": ("codex-exec-independent", True, False),
            "codex-exec-independent": ("codex-exec-independent", True, False),
            "codex-review-diff-only": ("self-review", False, True),
            "codex-review-independent": ("self-review", False, True),
            "main-session-fallback": ("self-review", False, False),
            "pending": ("pending", "pending", False),
        }
        for legacy, normalized in expected.items():
            with self.subTest(legacy=legacy):
                self.assertEqual(module.normalize_review_mode(legacy), normalized)

    def test_resolves_windows_cmd_and_posix_launchers(self) -> None:
        module = load_module()
        self.assertEqual(
            module.resolve_codex_executable(lambda _: r"C:\Tools\codex.CMD"),
            r"C:\Tools\codex.CMD",
        )
        self.assertEqual(
            module.resolve_codex_executable(lambda _: "/usr/local/bin/codex"),
            "/usr/local/bin/codex",
        )
        self.assertIsNone(module.resolve_codex_executable(lambda _: None))

    def test_exec_command_uses_explicit_sol_and_read_only_flags(self) -> None:
        module = load_module()
        cmd = module.build_exec_command("/usr/bin/codex", "/repo", "gpt-5.6-sol")
        self.assertEqual(cmd[0], "/usr/bin/codex")
        self.assertIn("--ephemeral", cmd)
        self.assertIn("--json", cmd)
        self.assertEqual(cmd[cmd.index("-m") + 1], "gpt-5.6-sol")
        self.assertEqual(cmd[cmd.index("--sandbox") + 1], "read-only")

    def test_exec_prompt_is_always_encoded_as_utf8(self) -> None:
        module = load_module()
        completed = type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with mock.patch.object(module.subprocess, "run", return_value=completed) as run:
            module.run_codex_exec(["codex.CMD", "exec"], "中文 prompt")
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertTrue(run.call_args.kwargs["text"])

    def test_event_stream_model_evidence_ignores_model_authored_claim(self) -> None:
        module = load_module()
        assistant_result = valid_result(review_observed_model="fake-self-report")
        stdout = "\n".join([
            json.dumps({"type": "thread.started", "model": "gpt-5.6-sol"}),
            json.dumps({"item": {"type": "agent_message", "text": json.dumps(assistant_result)}}),
        ])
        final_message, observed_model = module.parse_json_events(stdout)
        self.assertEqual(json.loads(final_message)["review_observed_model"], "fake-self-report")
        self.assertEqual(observed_model, "gpt-5.6-sol")

    def test_review_prompt_has_no_model_self_report_field(self) -> None:
        module = load_module()
        args = SimpleNamespace(
            review_log=None,
            claim_ledger=None,
            outcome_contract=None,
            deferred_ledger=None,
            extra=None,
            source_doc=None,
            csv="issues/sample.csv",
            model="gpt-5.6-sol",
        )
        prompt = module.build_prompt(args)
        self.assertIn("current-scope gap", prompt)
        self.assertIn("## 待讨论", prompt)
        self.assertNotIn('"review_observed_model"', prompt)
        self.assertNotIn('"actual_model"', prompt)


if __name__ == "__main__":
    unittest.main()
