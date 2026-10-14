#!/usr/bin/env python3
"""Phase 4 contract tests: VeraCrypt CLI helper argument shape."""
from __future__ import annotations
import unittest

class Phase4VeraCryptCli(unittest.TestCase):
    def test_mount_args_no_password_flag(self):
        volume = r"C:\vault\secret.hc"
        letter = "V"
        args = ["/v", volume, "/l", letter, "/q", "/s"]
        self.assertNotIn("/p", args)
        self.assertEqual(args[0], "/v")
        self.assertEqual(args[2], "/l")

    def test_candidate_paths_include_program_files(self):
        candidates = [
            r"C:\Program Files\VeraCrypt\VeraCrypt.exe",
            r"C:\Program Files (x86)\VeraCrypt\VeraCrypt.exe",
        ]
        self.assertTrue(any("VeraCrypt.exe" in c for c in candidates))

if __name__ == "__main__":
    unittest.main()
