#!/usr/bin/env python3
import subprocess
import tempfile
import unittest
from pathlib import Path

import git_isolation


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=False)


class GitIsolationTests(unittest.TestCase):
    def repo(self, root: Path) -> None:
        run(root, "init", "-q")
        run(root, "config", "user.name", "Test")
        run(root, "config", "user.email", "test@example.com")
        (root / "task.txt").write_text("base\n", encoding="utf-8")
        (root / "user.txt").write_text("base\n", encoding="utf-8")
        run(root, "add", "task.txt", "user.txt")
        run(root, "commit", "-qm", "base")

    def test_commit_only_task_paths_preserves_unrelated_staged_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.repo(repo)
            (repo / "user.txt").write_text("user staged\n", encoding="utf-8")
            run(repo, "add", "user.txt")
            before = git_isolation.index_patch(repo)
            (repo / "task.txt").write_text("task change\n", encoding="utf-8")

            git_isolation.commit_paths(repo, [Path("task.txt")], "task commit")

            committed = run(repo, "show", "--pretty=format:", "--name-only", "HEAD").stdout.decode()
            self.assertEqual(committed.strip(), "task.txt")
            self.assertEqual(git_isolation.index_patch(repo), before)

    def test_same_path_staged_patch_blocks_without_changing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.repo(repo)
            (repo / "task.txt").write_text("user staged\n", encoding="utf-8")
            run(repo, "add", "task.txt")
            before = git_isolation.index_patch(repo)
            (repo / "task.txt").write_text("mission change\n", encoding="utf-8")
            head_before = run(repo, "rev-parse", "HEAD").stdout

            with self.assertRaisesRegex(RuntimeError, "already has staged changes"):
                git_isolation.commit_paths(repo, [Path("task.txt")], "must block")

            self.assertEqual(git_isolation.index_patch(repo), before)
            self.assertEqual(run(repo, "rev-parse", "HEAD").stdout, head_before)

    def test_staged_child_under_task_directory_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.repo(repo)
            directory = repo / "issues" / "sample"
            directory.mkdir(parents=True)
            child = directory / "sample.csv"
            child.write_text("base\n", encoding="utf-8")
            run(repo, "add", "issues/sample/sample.csv")
            run(repo, "commit", "-qm", "add issue")
            child.write_text("user staged\n", encoding="utf-8")
            run(repo, "add", "issues/sample/sample.csv")
            before = git_isolation.index_patch(repo)

            with self.assertRaisesRegex(RuntimeError, "already has staged changes"):
                git_isolation.commit_paths(repo, [Path("issues/sample")], "must block")

            self.assertEqual(git_isolation.index_patch(repo), before)


if __name__ == "__main__":
    unittest.main()
