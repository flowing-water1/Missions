#!/usr/bin/env python3
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("ensure_review_row.py")
FIELDNAMES = [
    "id", "priority", "phase", "area", "title", "description",
    "acceptance_criteria", "test_mcp", "required_skills", "required_mcp",
    "review_initial_requirements", "review_regression_requirements", "dev_state",
    "review_initial_state", "review_regression_state", "git_state", "owner",
    "refs", "notes",
]


def load_module():
    spec = importlib.util.spec_from_file_location("ensure_review_row", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EnsureReviewRowTests(unittest.TestCase):
    def write_csv(self, path: Path, rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)

    def ordinary_row(self) -> dict:
        row = dict.fromkeys(FIELDNAMES, "")
        row.update({
            "id": "TASK-01",
            "priority": "P1",
            "phase": "2",
            "area": "backend",
            "title": "Implement behavior",
            "description": "Deliver the compatibility behavior.",
            "acceptance_criteria": "WHEN called THEN return success",
            "test_mcp": "CONTRACT",
            "review_initial_requirements": "Inspect implementation.",
            "review_regression_requirements": "Run tests.",
            "dev_state": "未开始",
            "review_initial_state": "未开始",
            "review_regression_state": "未开始",
            "git_state": "未提交",
            "refs": "src/app.py:10",
            "notes": "risk:low",
        })
        return row

    def test_appends_review_without_inventing_sidecars(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "external.csv"
            self.write_csv(path, [self.ordinary_row()])
            changed = module.ensure_review_row(path)
            self.assertTrue(changed)
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            review = rows[-1]
            self.assertEqual(review["id"], "REVIEW-01")
            self.assertIn(f"source_csv:{path.resolve()}", review["notes"])
            self.assertIn("review_requested_model:gpt-5.6-sol", review["notes"])
            self.assertNotIn("source_doc:", review["notes"])
            self.assertNotIn("claim_ledger:", review["notes"])
            self.assertNotIn("outcome_contract:", review["notes"])
            self.assertIn("Deliver the compatibility behavior.", review["review_regression_requirements"])
            self.assertIn("src/app.py:10", review["review_regression_requirements"])

    def test_existing_review_is_unchanged(self) -> None:
        module = load_module()
        row = self.ordinary_row()
        review = self.ordinary_row()
        review["id"] = "REVIEW-01"
        review["area"] = "review"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "existing.csv"
            self.write_csv(path, [row, review])
            before = path.read_bytes()
            self.assertFalse(module.ensure_review_row(path))
            self.assertEqual(path.read_bytes(), before)

    def test_ordinary_review_area_still_gets_closing_review(self) -> None:
        module = load_module()
        row = self.ordinary_row()
        row["id"] = "DOC-01"
        row["area"] = "review"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ordinary-review-work.csv"
            self.write_csv(path, [row])
            self.assertTrue(module.ensure_review_row(path))
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([item["id"] for item in rows], ["DOC-01", "REVIEW-01"])

    def test_rejects_nonstandard_header(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("id,title\n1,x\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "standard 19-column header"):
                module.ensure_review_row(path)


if __name__ == "__main__":
    unittest.main()
