#!/usr/bin/env python3
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_handoff_contract.py")


FIELDS = [
    "id",
    "priority",
    "phase",
    "area",
    "title",
    "description",
    "acceptance_criteria",
    "test_mcp",
    "required_skills",
    "required_mcp",
    "review_initial_requirements",
    "review_regression_requirements",
    "dev_state",
    "review_initial_state",
    "review_regression_state",
    "git_state",
    "owner",
    "refs",
    "notes",
]


VALID_HANDOFF = """# 施工交工单：样例任务

独立性: strong, direct-spawn-agent
日期: 2026-07-07

## 总结

这轮完成了样例任务，当前没有阻塞。

## 目标对账

| spec 目标 | 状态 | 实际效果 | 备注 |
|---|---|---|---|
| 生成交工单 | 完成 | REVIEW 行能找到交工单 | 无 |

## 施工细节

按 CSV review 行生成 handoff。

## 验证情况

contract check 通过。

## 后续可操作

没有额外操作。
"""


OUTCOME_HANDOFF = """# 样例任务 -- 施工交工单

独立性: strong, direct-spawn-agent
日期: 2026-07-13

## 先看结论

本轮整体判定为 partial，决定性结果是恢复链路已运行，但只覆盖 CSV。

## 这份交工单告诉你什么

它解释真实测试证据，不生产运行结果。

## 你现在可以确定什么

| 你关心的问题 | 判定 | 直接答案 | 关键证据 | 可信度 | 结论边界 | 下一步 |
|---|---|---|---|---|---|---|
| Can an interrupted import resume without duplication? | pass | 可以恢复且没有重复数据。 | tests/recovery.log | high | 只覆盖 CSV。 | 扩展格式矩阵。 |

## 决定整体状态的结果

恢复请求走完整产品链路并保持幂等。

## 目前仍不能声称什么

| 不能声称的结论 | 原因 | 解除条件 |
|---|---|---|
| All import formats are production ready. | 只测试 CSV。 | 运行完整格式矩阵。 |

## 本轮实际改变了什么

| spec 目标 | 状态 | 实际效果 | 备注 |
|---|---|---|---|
| 支持恢复 | 完成 | 用户可以恢复 CSV 导入 | 其他格式未验证 |

## 验证与下一步

运行了恢复 E2E；下一步扩展格式矩阵。
"""


def write_outcome_contract(path: Path) -> None:
    payload = {
        "source": "docs/spec.md",
        "execution_scope": "CSV recovery",
        "artifact_role": {
            "kind": "design",
            "producer": "approved spec",
            "consumers": ["mission review", "handoff"],
            "authority": "CSV recovery scope",
            "not_authority": "runtime result",
        },
        "desired_effects": [
            {
                "id": "EFFECT-001",
                "statement": "Users can resume interrupted imports.",
                "source_ref": "docs/spec.md:10",
            }
        ],
        "reader_questions": [
            {
                "id": "OUTCOME-001",
                "question": "Can an interrupted import resume without duplication?",
                "why_it_matters": "This is the user-visible capability.",
                "evidence_required": "real_e2e",
                "scope": "CSV recovery",
                "source_ref": "docs/spec.md:20",
                "status": "pending",
            }
        ],
        "decisive_result": {
            "question": "What proves recovery works?",
            "success_condition": "Resume without duplicates.",
            "failure_condition": "Rows are lost or duplicated.",
            "source_refs": ["docs/spec.md:20"],
        },
        "blocked_claims": [
            {
                "claim": "All import formats are production ready.",
                "reason": "只测试 CSV。",
                "release_condition": "运行完整格式矩阵。",
                "source_ref": "docs/spec.md:30",
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_review_json(path: Path, verdict: str = "pass") -> None:
    payload = {
        "review_agent_mode": "codex-exec-independent",
        "review_independence": True,
        "review_requested_model": "gpt-5.6-sol",
        "review_observed_model": "unknown",
        "review_model_evidence": "unknown",
        "result": "vision_met" if verdict == "pass" else "gaps_found",
        "claim_coverage": "1/1",
        "claim_coverage_status": "complete",
        "validation_limited": [],
        "summary": "Recovery review.",
        "gaps": [] if verdict == "pass" else [{
            "id": "FOLLOWUP-01",
            "title": "Finish recovery",
            "source_ref": "docs/spec.md:20",
            "evidence_ref": "tests/recovery.log",
            "why_it_matters": "Recovery is incomplete.",
            "suggested_followup_issue": "Complete and rerun recovery.",
        }],
        "assumptions": [],
        "decision_debt": [],
        "deferred_findings": [],
        "human_required_blockers": [],
        "outcome_answers": [{
            "question_id": "OUTCOME-001",
            "verdict": verdict,
            "answer": "可以恢复且没有重复数据。" if verdict == "pass" else "恢复仍会产生重复数据。",
            "evidence_refs": ["tests/recovery.log"],
            "confidence": "high",
            "boundary": "只覆盖 CSV。",
            "next_action": "扩展格式矩阵。" if verdict == "pass" else "修复幂等写入后重跑。",
        }],
        "handoff_markdown": OUTCOME_HANDOFF,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_deferred_ledger(path: Path, status: str = "open") -> None:
    payload = {
        "schema_version": 1,
        "csv": "sample.csv",
        "findings": [{
            "id": "DF-001",
            "kind": "future_decision",
            "status": status,
            "title": "是否扩大评估样本",
            "summary": "现有样本没有覆盖超长对话。",
            "source_issue_ids": ["REVIEW-01"],
            "evidence_refs": ["trace:abc123"],
            "why_deferred": "不影响本轮已批准目标。",
            "discussion_question": "下一轮是否加入超长对话样本？",
        }],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, notes: str) -> None:
    row = {field: "" for field in FIELDS}
    row.update(
        {
            "id": "REVIEW-01",
            "priority": "P0",
            "phase": "review",
            "area": "review",
            "title": "Review task outcome",
            "dev_state": "已完成",
            "review_initial_state": "已完成",
            "review_regression_state": "已完成",
            "git_state": "已提交",
            "notes": notes,
        }
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)


def write_review_rows(path: Path, notes_values: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index, notes in enumerate(notes_values, start=1):
            row = {field: "" for field in FIELDS}
            row.update(
                {
                    "id": f"REVIEW-{index:02d}",
                    "priority": "P0",
                    "phase": "review",
                    "area": "review",
                    "title": "Review task outcome",
                    "dev_state": "已完成",
                    "review_initial_state": "已完成",
                    "review_regression_state": "已完成",
                    "git_state": "已提交",
                    "notes": notes,
                }
            )
            writer.writerow(row)


def run_contract(handoff: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(handoff), *args],
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
    )


class HandoffContractTests(unittest.TestCase):
    def test_valid_handoff_with_review_notes_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(VALID_HANDOFF, encoding="utf-8")
            write_csv(root / "sample.csv", "review_result:limited_review; handoff:sample.handoff.md; handoff_humanized:true")

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("handoff_contract: passed", result.stdout)

    def test_nested_run_directory_handoff_with_basename_note_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            handoff = run_dir / "sample.handoff.md"
            handoff.write_text(VALID_HANDOFF, encoding="utf-8")
            write_csv(run_dir / "sample.csv", "review_result:limited_review; handoff:sample.handoff.md; handoff_humanized:true")

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("handoff_contract: passed", result.stdout)

    def test_basename_note_does_not_match_handoff_outside_csv_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)
            stale_handoff = root / "sample.handoff.md"
            stale_handoff.write_text(VALID_HANDOFF, encoding="utf-8")
            write_csv(run_dir / "sample.csv", "review_result:limited_review; handoff:sample.handoff.md")

            result = run_contract(stale_handoff, "--csv", str(run_dir / "sample.csv"))

            self.assertEqual(result.returncode, 1)
            self.assertIn("REVIEW notes 未记录 handoff:<path>", result.stderr)

    def test_missing_sibling_csv_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            handoff = Path(tmp) / "orphan.handoff.md"
            handoff.write_text(VALID_HANDOFF, encoding="utf-8")

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("CSV 不存在", result.stderr)

    def test_review_notes_must_reference_handoff_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(VALID_HANDOFF, encoding="utf-8")
            write_csv(root / "sample.csv", "review_result:limited_review")

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("REVIEW notes 未记录 handoff:<path>", result.stderr)

    def test_legacy_handoff_requires_humanizer_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(VALID_HANDOFF, encoding="utf-8")
            write_csv(
                root / "sample.csv",
                "review_result:limited_review; handoff:sample.handoff.md",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("latest REVIEW notes must record handoff_humanized:true", result.stderr)

    def test_markdown_lint_failures_fail_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text("# Bad Handoff\n\nvision_met\n", encoding="utf-8")
            write_csv(root / "sample.csv", "review_result:limited_review; handoff:sample.handoff.md")

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("标题缺 '施工交工单'", result.stderr)
            self.assertIn("vision_met", result.stderr)

    def test_outcome_contract_handoff_with_all_questions_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(OUTCOME_HANDOFF, encoding="utf-8")
            write_outcome_contract(root / "sample.outcomes.json")
            write_review_json(root / "sample.review.json")
            write_csv(
                root / "sample.csv",
                "review_result:vision_met; handoff:sample.handoff.md; "
                "outcome_contract:sample.outcomes.json; review_json:sample.review.json; "
                "handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_outcome_contract_handoff_missing_question_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(
                OUTCOME_HANDOFF.replace(
                    "Can an interrupted import resume without duplication?",
                    "A different question",
                ),
                encoding="utf-8",
            )
            write_outcome_contract(root / "sample.outcomes.json")
            write_review_json(root / "sample.review.json")
            write_csv(
                root / "sample.csv",
                "review_result:gaps_found; handoff:sample.handoff.md; "
                "outcome_contract:sample.outcomes.json; review_json:sample.review.json; "
                "handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("handoff missing reader question OUTCOME-001", result.stderr)

    def test_outcome_question_must_be_in_a_verdict_table_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(
                OUTCOME_HANDOFF.replace(
                    "| Can an interrupted import resume without duplication? | pass | 可以恢复且没有重复数据。 | tests/recovery.log | high | 只覆盖 CSV。 | 扩展格式矩阵。 |",
                    "Can an interrupted import resume without duplication?\n\n结论写在别处。",
                ),
                encoding="utf-8",
            )
            write_outcome_contract(root / "sample.outcomes.json")
            write_review_json(root / "sample.review.json")
            write_csv(
                root / "sample.csv",
                "review_result:gaps_found; handoff:sample.handoff.md; "
                "outcome_contract:sample.outcomes.json; review_json:sample.review.json; "
                "handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("reader question OUTCOME-001 is not in a complete answer table row", result.stderr)

    def test_outcome_handoff_requires_a_verdict_enum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(
                OUTCOME_HANDOFF.replace("partial", "完成").replace("pass", "完成"),
                encoding="utf-8",
            )
            write_outcome_contract(root / "sample.outcomes.json")
            write_review_json(root / "sample.review.json")
            write_csv(
                root / "sample.csv",
                "review_result:gaps_found; handoff:sample.handoff.md; "
                "outcome_contract:sample.outcomes.json; review_json:sample.review.json; "
                "handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("outcome handoff missing verdict enum", result.stderr)

    def test_handoff_answer_must_match_review_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(OUTCOME_HANDOFF, encoding="utf-8")
            write_outcome_contract(root / "sample.outcomes.json")
            write_review_json(root / "sample.review.json", verdict="fail")
            write_csv(
                root / "sample.csv",
                "review_result:gaps_found; handoff:sample.handoff.md; "
                "outcome_contract:sample.outcomes.json; review_json:sample.review.json; "
                "handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("handoff answer differs from review JSON for OUTCOME-001", result.stderr)

    def test_latest_review_row_selects_its_review_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(OUTCOME_HANDOFF, encoding="utf-8")
            write_outcome_contract(root / "sample.outcomes.json")
            write_review_json(root / "review-01.json", verdict="fail")
            write_review_json(root / "review-02.json", verdict="pass")
            write_review_rows(
                root / "sample.csv",
                [
                    "review_result:gaps_found; review_json:review-01.json; "
                    "outcome_contract:sample.outcomes.json",
                    "review_result:vision_met; review_json:review-02.json; "
                    "handoff:sample.handoff.md; outcome_contract:sample.outcomes.json; "
                    "handoff_humanized:true",
                ],
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_latest_review_row_must_reference_handoff_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(VALID_HANDOFF, encoding="utf-8")
            write_review_rows(
                root / "sample.csv",
                [
                    "review_result:gaps_found; handoff:sample.handoff.md; handoff_humanized:true",
                    "review_result:vision_met; handoff_humanized:true",
                ],
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("latest REVIEW notes 未记录 handoff:<path>", result.stderr)

    def test_csv_review_result_must_match_review_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(OUTCOME_HANDOFF, encoding="utf-8")
            write_outcome_contract(root / "sample.outcomes.json")
            write_review_json(root / "sample.review.json", verdict="pass")
            write_csv(
                root / "sample.csv",
                "review_result:gaps_found; handoff:sample.handoff.md; "
                "outcome_contract:sample.outcomes.json; review_json:sample.review.json; "
                "handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("CSV review_result differs from review JSON result", result.stderr)

    def test_outcome_handoff_requires_humanizer_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(OUTCOME_HANDOFF, encoding="utf-8")
            write_outcome_contract(root / "sample.outcomes.json")
            write_review_json(root / "sample.review.json", verdict="pass")
            write_csv(
                root / "sample.csv",
                "review_result:vision_met; handoff:sample.handoff.md; "
                "outcome_contract:sample.outcomes.json; review_json:sample.review.json",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("latest REVIEW notes must record handoff_humanized:true", result.stderr)

    def test_open_deferred_finding_must_be_covered_in_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            handoff.write_text(VALID_HANDOFF, encoding="utf-8")
            write_deferred_ledger(root / "sample.deferred.json")
            write_csv(
                root / "sample.csv",
                "review_result:limited_review; handoff:sample.handoff.md; "
                "deferred_ledger:sample.deferred.json; deferred_findings:DF-001; "
                "deferred_coverage:0/1; handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn("handoff missing open deferred finding: DF-001", result.stderr)

    def test_humanized_deferred_section_with_hidden_marker_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            text = VALID_HANDOFF.replace(
                "## 后续可操作",
                "## 待讨论\n\n<!-- deferred:DF-001 -->\n"
                "### 是否扩大评估样本\n\n"
                "现有样本没有覆盖超长对话。下一轮要不要加入这类样本，需要你决定。\n\n"
                "## 后续可操作",
            )
            handoff.write_text(text, encoding="utf-8")
            write_deferred_ledger(root / "sample.deferred.json")
            write_csv(
                root / "sample.csv",
                "review_result:limited_review; handoff:sample.handoff.md; "
                "deferred_ledger:sample.deferred.json; deferred_findings:DF-001; "
                "deferred_coverage:1/1; handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_closed_deferred_finding_cannot_remain_in_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "sample.handoff.md"
            text = VALID_HANDOFF.replace(
                "## 后续可操作",
                "## 待讨论\n\n<!-- deferred:DF-001 -->\n已关闭的旧讨论。\n\n## 后续可操作",
            )
            handoff.write_text(text, encoding="utf-8")
            write_deferred_ledger(root / "sample.deferred.json", status="dismissed")
            write_csv(
                root / "sample.csv",
                "review_result:vision_met; handoff:sample.handoff.md; "
                "deferred_ledger:sample.deferred.json; deferred_findings:DF-001; "
                "handoff_humanized:true",
            )

            result = run_contract(handoff)

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "handoff references unknown or closed deferred finding: DF-001",
                result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
