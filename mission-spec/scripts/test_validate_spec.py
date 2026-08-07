#!/usr/bin/env python3
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_spec.py")


def load_module():
    spec = importlib.util.spec_from_file_location("validate_spec", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load validate_spec.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def spec_text(status: str = "draft", extra: str = "") -> str:
    approved_at = "approved_at: 2026-07-29T14:34:30+08:00\n" if status == "approved" else ""
    return (
        "---\n"
        "mission: spec\n"
        f"status: {status}\n"
        "created: 2026-07-29\n"
        f"{approved_at}{extra}"
        "---\n\n"
        "# Example\n\n"
        "## Goal\n\nGoal.\n\n"
        "## Scope\n\nScope.\n\n"
        "## Design\n\nDesign.\n\n"
        "## Acceptance Criteria\n\n- Done.\n"
    )


class ValidateSpecTests(unittest.TestCase):
    def test_valid_draft(self) -> None:
        module = load_module()
        metadata, errors = module.validate_text(spec_text())
        self.assertEqual(errors, [])
        self.assertEqual(metadata["status"], "draft")

    def test_valid_approved_metadata(self) -> None:
        module = load_module()
        metadata, errors = module.validate_text(spec_text("approved"))
        self.assertEqual(errors, [])
        self.assertEqual(metadata["approved_at"], "2026-07-29T14:34:30+08:00")

    def test_approved_requires_approved_at(self) -> None:
        module = load_module()
        text = spec_text("draft").replace("status: draft", "status: approved")
        _, errors = module.validate_text(text)
        self.assertIn("approved spec requires approved_at", errors)

    def test_draft_rejects_approved_at(self) -> None:
        module = load_module()
        _, errors = module.validate_text(
            spec_text("draft", "approved_at: 2026-07-29T14:34:30+08:00\n")
        )
        self.assertIn("draft spec must not contain approved_at", errors)

    def test_rejects_invalid_dates_and_unknown_status(self) -> None:
        module = load_module()
        text = spec_text().replace("status: draft", "status: ready").replace(
            "created: 2026-07-29", "created: 2026-02-30"
        )
        _, errors = module.validate_text(text)
        self.assertIn("status must be draft or approved", errors)
        self.assertIn("created must be an ISO date", errors)

    def test_rejects_invalid_approved_timestamp(self) -> None:
        module = load_module()
        text = spec_text("approved").replace(
            "2026-07-29T14:34:30+08:00", "2026-07-29 14:34:30"
        )
        _, errors = module.validate_text(text)
        self.assertIn("approved_at must be an RFC 3339 timestamp with timezone", errors)

    def test_rejects_duplicate_and_unknown_keys(self) -> None:
        module = load_module()
        _, duplicate_errors = module.validate_text(spec_text("draft", "status: draft\n"))
        _, unknown_errors = module.validate_text(spec_text("draft", "owner: codex\n"))
        self.assertIn("duplicate frontmatter key: status", duplicate_errors)
        self.assertIn("unknown frontmatter key: owner", unknown_errors)

    def test_rejects_nested_array_alias_and_tag_values(self) -> None:
        module = load_module()
        cases = {
            "nested frontmatter values are not allowed": "created:\n  year: 2026\n",
            "frontmatter arrays are not allowed": "created: [2026-07-29]\n",
            "frontmatter aliases are not allowed": "created: *date\n",
            "frontmatter tags are not allowed": "created: !date 2026-07-29\n",
        }
        for expected, replacement in cases.items():
            with self.subTest(expected=expected):
                text = spec_text().replace("created: 2026-07-29\n", replacement)
                _, errors = module.validate_text(text)
                self.assertIn(expected, errors)

    def test_rejects_additional_frontmatter_block(self) -> None:
        module = load_module()
        text = spec_text() + "\n---\nstatus: draft\n---\n"
        _, errors = module.validate_text(text)
        self.assertIn("document contains an additional frontmatter block", errors)

    def test_allows_frontmatter_example_inside_fenced_code(self) -> None:
        module = load_module()
        text = spec_text() + "\n```yaml\n---\nmission: spec\nstatus: draft\n---\n```\n"
        _, errors = module.validate_text(text)
        self.assertEqual(errors, [])

    def test_approved_spec_must_be_committed_and_clean(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            path = repo / "docs" / "specs" / "example.md"
            path.parent.mkdir(parents=True)
            path.write_text(spec_text("approved"), encoding="utf-8")

            untracked_errors = module.validate_path(path, require_committed_approved=True)
            self.assertIn("approved spec must be committed", untracked_errors)

            subprocess.run(["git", "add", str(path)], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "add spec"], cwd=repo, check=True)
            self.assertEqual(module.validate_path(path, require_committed_approved=True), [])

            path.write_text(spec_text("approved") + "\nchanged\n", encoding="utf-8")
            dirty_errors = module.validate_path(path, require_committed_approved=True)
            self.assertIn("approved spec differs from HEAD and must return to draft", dirty_errors)


if __name__ == "__main__":
    unittest.main()
