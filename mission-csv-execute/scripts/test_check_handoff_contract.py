#!/usr/bin/env python3
import csv
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
            write_csv(root / "sample.csv", "review_result:limited_review; handoff:sample.handoff.md")

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
            write_csv(run_dir / "sample.csv", "review_result:limited_review; handoff:sample.handoff.md")

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


if __name__ == "__main__":
    unittest.main()
