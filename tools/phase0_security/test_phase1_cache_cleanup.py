#!/usr/bin/env python3
"""Phase 1 contract tests for startup cache target selection / wipe set."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path


def collect_targets(working_dir: Path, *, clear_cache=True, clear_emoji=False, clear_ayu_db=False):
    """Mirror Ayu::CacheCleanup::collectTargets path rules."""
    tdata = working_dir / "tdata"
    if not tdata.is_dir():
        return []
    targets: list[Path] = []

    def add(p: Path):
        if p.exists():
            targets.append(p.resolve())

    if clear_cache:
        add(tdata / "temp")
        for entry in tdata.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            if name.startswith("temp_"):
                add(entry)
            elif name.startswith("user_"):
                add(entry / "cache")
                add(entry / "media_cache")
    if clear_emoji:
        add(tdata / "emoji")
    if clear_ayu_db:
        add(tdata / "ayudata.db")
        for f in tdata.glob("ayudata_*.db"):
            if f.is_file():
                add(f)
    # unique preserve order
    seen = set()
    out = []
    for t in targets:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def unlink_tree(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()


class Phase1CacheCleanup(unittest.TestCase):
    def _fixture(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        tdata = root / "tdata"
        (tdata / "user_alpha" / "cache").mkdir(parents=True)
        (tdata / "user_alpha" / "media_cache").mkdir(parents=True)
        (tdata / "user_alpha" / "maps").mkdir(parents=True)
        (tdata / "temp_alpha").mkdir()
        (tdata / "temp").mkdir()
        (tdata / "emoji").mkdir()
        (tdata / "key_data").write_bytes(b"key-material")
        (tdata / "ayu_settings.json").write_text(
            json.dumps({"clearCacheOnStartup": True}), encoding="utf-8"
        )
        (tdata / "ayudata.db").write_bytes(b"sqlite")
        (tdata / "ayudata_123.db").write_bytes(b"rotated")
        (tdata / "user_alpha" / "cache" / "blob").write_bytes(b"cached")
        return td, root, tdata

    def test_collect_default_cache_only(self):
        td, root, tdata = self._fixture()
        with td:
            targets = collect_targets(root, clear_cache=True)
            names = {p.relative_to(tdata).as_posix() for p in targets}
            self.assertIn("temp", names)
            self.assertIn("temp_alpha", names)
            self.assertIn("user_alpha/cache", names)
            self.assertIn("user_alpha/media_cache", names)
            self.assertNotIn("emoji", names)
            self.assertNotIn("ayudata.db", names)
            self.assertNotIn("key_data", names)
            self.assertNotIn("ayu_settings.json", names)
            self.assertNotIn("user_alpha/maps", names)

    def test_collect_optional_emoji_and_db(self):
        td, root, tdata = self._fixture()
        with td:
            targets = collect_targets(
                root, clear_cache=False, clear_emoji=True, clear_ayu_db=True
            )
            names = {p.relative_to(tdata).as_posix() for p in targets}
            self.assertEqual(names, {"emoji", "ayudata.db", "ayudata_123.db"})

    def test_run_removes_caches_keeps_keys(self):
        td, root, tdata = self._fixture()
        with td:
            for path in collect_targets(root, clear_cache=True):
                unlink_tree(path)
            self.assertFalse((tdata / "user_alpha" / "cache").exists())
            self.assertFalse((tdata / "user_alpha" / "media_cache").exists())
            self.assertFalse((tdata / "temp").exists())
            self.assertFalse((tdata / "temp_alpha").exists())
            self.assertTrue((tdata / "key_data").exists())
            self.assertTrue((tdata / "ayu_settings.json").exists())
            self.assertTrue((tdata / "user_alpha" / "maps").exists())
            self.assertTrue((tdata / "ayudata.db").exists())  # not selected

    def test_early_settings_flag_true(self):
        td, root, tdata = self._fixture()
        with td:
            obj = json.loads((tdata / "ayu_settings.json").read_text(encoding="utf-8"))
            self.assertTrue(obj.get("clearCacheOnStartup", False))

    def test_missing_tdata_noop(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.assertEqual(collect_targets(root, clear_cache=True), [])


if __name__ == "__main__":
    unittest.main()
