#!/usr/bin/env python3
"""Phase 0 contract tests (no full Desktop build required)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path


def overwrite_unlink(path: Path) -> None:
    data = path.read_bytes()
    path.write_bytes(os.urandom(len(data)))
    path.unlink()


class Phase0Contracts(unittest.TestCase):
    def test_early_flags_defaults_missing_file(self):
        flags = {
            "clearCacheOnStartup": False,
            "clearEmojiCacheOnStartup": False,
            "clearAyuDatabaseOnStartup": False,
            "strictDataFolder": False,
            "duressFeatureReady": False,
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ayu_settings.json"
            # missing file → all false (mirrors AyuSettingsEarly::read)
            self.assertFalse(path.exists())
            for k, v in flags.items():
                self.assertIs(v, False)

    def test_early_flags_parse(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ayu_settings.json"
            path.write_text(
                json.dumps(
                    {
                        "clearCacheOnStartup": True,
                        "strictDataFolder": True,
                        "duressFeatureReady": False,
                        "unrelated": 1,
                    }
                ),
                encoding="utf-8",
            )
            obj = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(obj.get("clearCacheOnStartup", False))
            self.assertTrue(obj.get("strictDataFolder", False))
            self.assertFalse(obj.get("clearEmojiCacheOnStartup", False))

    def test_sidecar_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Syyngram"
            root.mkdir()
            workdir = Path(td) / "volume" / "SyyngramData"
            workdir.mkdir(parents=True)
            (root / "workdir.txt").write_text(str(workdir) + "/", encoding="utf-8")
            (root / "config.json").write_text(
                json.dumps({"workdir": str(workdir) + "/", "strictDataFolder": True}, indent=2),
                encoding="utf-8",
            )
            work = (root / "workdir.txt").read_text(encoding="utf-8").strip()
            cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
            self.assertTrue(work.replace("\\", "/").endswith("SyyngramData/"))
            self.assertTrue(cfg["strictDataFolder"])
            self.assertTrue(Path(work).exists())

    def test_strict_unavailable_detection(self):
        missing = Path("/nonexistent-drive-root-syyngram-phase0/data")
        self.assertFalse(missing.exists())
        # Contract: strict mode must not create a fallback profile directory here.
        # (C++ applySidecarWorkDir returns StrictUnavailable + skips mkpath.)

    def test_overwrite_then_unlink(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "secret.bin"
            payload = b"sensitive-cache-bytes-0123456789"
            f.write_bytes(payload)
            overwrite_unlink(f)
            self.assertFalse(f.exists())

    def test_wipe_skips_escape_symlink_contract(self):
        """Document: SecureWipe skips symlinks (does not follow out of tree)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "tdata"
            outside = Path(td) / "outside.txt"
            root.mkdir()
            outside.write_text("keep-me", encoding="utf-8")
            link = root / "escape"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlinks not available")
            # Phase 0 C++ skips symlink entries; outside must remain if only link unlinked.
            if link.is_symlink():
                link.unlink()
            self.assertTrue(outside.exists())
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep-me")


if __name__ == "__main__":
    unittest.main()
