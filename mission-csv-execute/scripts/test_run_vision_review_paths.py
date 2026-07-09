#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("run_vision_review.py")


def load_module():
    spec = importlib.util.spec_from_file_location("run_vision_review", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_vision_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

            resolved = module.resolve_existing_file("sample.claims.json", root, run_dir)

            self.assertEqual(Path(resolved), expected.resolve())

    def test_relative_output_file_prefers_csv_directory(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)

            resolved = module.output_file("sample.handoff.md", root, run_dir)

            self.assertEqual(resolved, (run_dir / "sample.handoff.md").resolve())

    def test_reviews_output_subdir_is_under_csv_directory(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)

            resolved = module.output_file("reviews/review-01.json", root, run_dir)

            self.assertEqual(resolved, (run_dir / "reviews" / "review-01.json").resolve())

    def test_repo_relative_issues_output_stays_repo_relative(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "issues" / "sample"
            run_dir.mkdir(parents=True)

            resolved = module.output_file("issues/sample/sample.handoff.md", root, run_dir)

            self.assertEqual(resolved, (root / "issues" / "sample" / "sample.handoff.md").resolve())


if __name__ == "__main__":
    unittest.main()
