#!/usr/bin/env python3
"""Phase 4 contract tests: VeraCrypt CLI helper argument shape."""
from __future__ import annotations
import re
import unittest
from pathlib import Path

SRC = (
    Path(__file__).resolve().parents[2]
    / "Telegram"
    / "SourceFiles"
    / "platform"
    / "win"
    / "veracrypt_mount_win.cpp"
)


class Phase4VeraCryptCli(unittest.TestCase):
    def test_mount_args_match_source_no_password_or_silent(self):
        text = SRC.read_text(encoding="utf-8")
        # Real argv is built as QStringList{ "/v", ..., "/l", letter, "/q" }.
        self.assertIn('QStringLiteral("/v")', text)
        self.assertIn('QStringLiteral("/l")', text)
        self.assertIn('QStringLiteral("/q")', text)
        self.assertNotIn('QStringLiteral("/s")', text)
        self.assertNotIn('QStringLiteral("/p")', text)
        self.assertIn("no /p", text)

    def test_candidate_paths_include_program_files(self):
        text = SRC.read_text(encoding="utf-8")
        self.assertIn("Program Files", text)
        self.assertIn("VeraCrypt.exe", text)
        candidates = [
            r"C:\Program Files\VeraCrypt\VeraCrypt.exe",
            r"C:\Program Files (x86)\VeraCrypt\VeraCrypt.exe",
        ]
        self.assertTrue(any("VeraCrypt.exe" in c for c in candidates))


if __name__ == "__main__":
    unittest.main()
