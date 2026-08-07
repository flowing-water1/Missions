#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import register_reviewer


VALID_CONFIG = b'[model]\nname = "example"\n\n[agents.default]\nconfig_file = "agents/default.toml"\n'
VALID_FRAGMENT = b'[agents.reviewer]\nconfig_file = "agents/reviewer.toml"\n'


class RegisterReviewerTests(unittest.TestCase):
    def test_registers_fragment_and_creates_exact_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            fragment = root / "reviewer.toml"
            backup = root / "backup" / "config.toml.pre-reviewer"
            config.write_bytes(VALID_CONFIG)
            fragment.write_bytes(VALID_FRAGMENT)

            register_reviewer.register(config, fragment, backup)

            self.assertEqual(backup.read_bytes(), VALID_CONFIG)
            self.assertIn(VALID_FRAGMENT.rstrip(), config.read_bytes())
            register_reviewer.validate_registration(config, fragment)

    def test_invalid_source_is_not_changed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            fragment = root / "reviewer.toml"
            backup = root / "backup.toml"
            original = b"not = [valid\n"
            config.write_bytes(original)
            fragment.write_bytes(VALID_FRAGMENT)

            with self.assertRaises(Exception):
                register_reviewer.register(config, fragment, backup)

            self.assertEqual(config.read_bytes(), original)

    def test_fragment_mismatch_is_not_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            fragment = root / "reviewer.toml"
            backup = root / "backup.toml"
            config.write_bytes(VALID_CONFIG)
            fragment.write_text(
                '[agents.reviewer]\nconfig_file = "wrong.toml"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "fragment must contain only"):
                register_reviewer.register(config, fragment, backup)

            self.assertEqual(config.read_bytes(), VALID_CONFIG)

    def test_post_write_validation_failure_restores_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            fragment = root / "reviewer.toml"
            backup = root / "backup.toml"
            config.write_bytes(VALID_CONFIG)
            fragment.write_bytes(VALID_FRAGMENT)

            with mock.patch.object(
                register_reviewer,
                "validate_registration",
                side_effect=ValueError("forced failure"),
            ):
                with self.assertRaisesRegex(ValueError, "forced failure"):
                    register_reviewer.register(config, fragment, backup)

            self.assertEqual(config.read_bytes(), VALID_CONFIG)
            self.assertEqual(backup.read_bytes(), VALID_CONFIG)


if __name__ == "__main__":
    unittest.main()
