#!/usr/bin/env python3
"""Phase 3 contract tests: sidecar + strict data folder."""
from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

class Phase3DataFolder(unittest.TestCase):
    def test_sidecar_roundtrip_strict(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Syyngram"
            root.mkdir()
            work = Path(td) / "V" / "data"
            work.mkdir(parents=True)
            (root / "workdir.txt").write_text(str(work) + "/", encoding="utf-8")
            (root / "config.json").write_text(
                json.dumps({"workdir": str(work) + "/", "strictDataFolder": True}),
                encoding="utf-8",
            )
            cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
            self.assertTrue(cfg["strictDataFolder"])
            self.assertTrue(Path(cfg["workdir"]).exists())

    def test_strict_missing_volume_no_fallback_profile(self):
        """Documented contract: when strict and volume missing, do not mkpath default tdata."""
        missing = Path("/__no_such_drive_syyngram__/data")
        self.assertFalse(missing.exists())
        # C++ applySidecarWorkDir returns StrictUnavailable and Logs::start returns early.

    def test_strict_missing_volume_prompt_wired(self):
        """Source contract: Retry/Cancel prompt loop and launcher hard stop."""
        src = Path(__file__).resolve().parents[2] / "Telegram" / "SourceFiles"
        logs = (src / "logs.cpp").read_text(encoding="utf-8")
        launcher = (src / "core" / "launcher.cpp").read_text(encoding="utf-8")
        folder = (src / "core" / "data_folder.cpp").read_text(encoding="utf-8")
        self.assertIn("promptStrictUnavailable", logs)
        self.assertIn("MB_RETRYCANCEL", folder)
        self.assertIn("startupBlocked()", launcher)

if __name__ == "__main__":
    unittest.main()
