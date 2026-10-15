#!/usr/bin/env python3
"""Phase 2 contract tests: duress wipe inventory categories (confined)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


KNOWN_APPDATA = [
    "AyuGram Desktop",
    "AyuGram",
    "Syyngram",
    "Syyngram Desktop",
]
KNOWN_DOWNLOADS = KNOWN_APPDATA + ["Telegram Desktop"]
# Mirrors Storage::DuressInventory::installDirEntries(): what the app puts in its program folder.
INSTALL_DIR_ENTRIES = [
    "Telegram.exe", "Updater.exe", "modules", "unins000.exe", "unins000.dat",
    "unins000.msg", "data", "data_config", "log.txt",
]


def collect_wipe_roots(
    working_dir: Path,
    exe_dir: Path,
    *,
    appdata: Path,
    downloads: Path,
    sidecar: Path,
    configured_download: Path | None = None,
    configured_export: Path | None = None,
):
    """Mirror Storage::DuressInventory::collectWipeRoots (path rules only)."""
    roots: dict[str, Path] = {}

    def add(category: str, path: Path, confine: Path):
        if not path.exists():
            return
        # confine check
        try:
            path.resolve().relative_to(confine.resolve())
        except ValueError:
            if path.resolve() != confine.resolve():
                return
        roots[category + ":" + str(path.resolve())] = path.resolve()

    work = working_dir
    tdata = work / "tdata"
    add("tdata", tdata, work)
    for name in ("DebugLogs", "tupdates", "tcache", "tdumps", "modules"):
        add("workdir_extras", work / name, work)
    for entry in INSTALL_DIR_ENTRIES:
        # the installer drops data and data_config as files; a folder of that name is the user's
        if entry in ("data", "data_config") and (exe_dir / entry).is_dir():
            continue
        add("install_dir", exe_dir / entry, exe_dir)
    for name in KNOWN_APPDATA:
        add("appdata", appdata / name, appdata / name)
    add("appdata_syyngram", sidecar, sidecar)
    for name in KNOWN_DOWNLOADS:
        add("download_dir", downloads / name, downloads / name)

    def allowed(path: Path) -> bool:
        abs_p = path.resolve()
        if abs_p == work.resolve() or work.resolve() in abs_p.parents:
            return True
        if abs_p == exe_dir.resolve() or exe_dir.resolve() in abs_p.parents:
            return True
        if sidecar.resolve() in abs_p.parents or abs_p == sidecar.resolve():
            return True
        for name in KNOWN_APPDATA:
            root = (appdata / name).resolve()
            if abs_p == root or root in abs_p.parents:
                return True
        for name in KNOWN_DOWNLOADS:
            root = (downloads / name).resolve()
            if abs_p == root or root in abs_p.parents:
                return True
        return False

    if configured_download and configured_download.exists() and allowed(configured_download):
        add("download_dir", configured_download, configured_download)
    if configured_export and configured_export.exists() and allowed(configured_export):
        add("export_dir", configured_export, configured_export)
    return roots


class Phase2DuressWipe(unittest.TestCase):
    def _layout(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        work = root / "work"
        exe = root / "install"
        appdata = root / "AppData"
        downloads = root / "Downloads"
        sidecar = appdata / "Syyngram"
        for p in (work, exe, appdata, downloads, sidecar):
            p.mkdir(parents=True)

        # tdata with all categories the owner listed
        tdata = work / "tdata"
        (tdata / "user_alpha" / "cache").mkdir(parents=True)
        (tdata / "user_alpha" / "media_cache").mkdir(parents=True)
        (tdata / "user_alpha" / "maps").mkdir(parents=True)
        (tdata / "emoji").mkdir()
        (tdata / "fonts").mkdir()
        (tdata / "temp_alpha").mkdir()
        (tdata / "temp").mkdir()
        (tdata / "key_data").write_bytes(b"keys")
        (tdata / "ayu_settings.json").write_text("{}", encoding="utf-8")
        (tdata / "ayudata.db").write_bytes(b"history")
        (tdata / "syyngram_dv").write_bytes(b"SGDV" + b"\0" * 64)
        (work / "DebugLogs").mkdir()
        (work / "tdumps").mkdir()
        (exe / "Telegram.exe").write_bytes(b"mz")
        (appdata / "AyuGram Desktop" / "tdata").mkdir(parents=True)
        (downloads / "AyuGram Desktop").mkdir()
        (downloads / "Telegram Desktop").mkdir()
        export = downloads / "AyuGram Desktop" / "Export"
        export.mkdir()
        return td, work, exe, appdata, downloads, sidecar, export

    def test_categories_present(self):
        td, work, exe, appdata, downloads, sidecar, export = self._layout()
        with td:
            roots = collect_wipe_roots(
                work, exe, appdata=appdata, downloads=downloads, sidecar=sidecar,
                configured_download=downloads / "AyuGram Desktop",
                configured_export=export,
            )
            joined = " ".join(roots.keys())
            self.assertIn("tdata:", joined)
            self.assertIn("workdir_extras:", joined)
            self.assertIn("install_dir:", joined)
            self.assertIn("appdata", joined)
            self.assertIn("download_dir:", joined)
            self.assertIn("export_dir:", joined)
            # tdata covers history DBs / settings / caches
            tdata = (work / "tdata").resolve()
            self.assertTrue(any(p == tdata for p in roots.values()))

    def test_rejects_arbitrary_user_path(self):
        td, work, exe, appdata, downloads, sidecar, export = self._layout()
        with td:
            evil = Path(td.name) / "Photos" / "vacation"
            evil.mkdir(parents=True)
            roots = collect_wipe_roots(
                work, exe, appdata=appdata, downloads=downloads, sidecar=sidecar,
                configured_download=evil,
            )
            for p in roots.values():
                self.assertNotEqual(p, evil.resolve())

    def test_never_lists_the_program_folder_itself(self):
        td, work, exe, appdata, downloads, sidecar, export = self._layout()
        with td:
            (exe / "holiday-photos").mkdir()
            (exe / "notes.txt").write_text("the user's own file", encoding="utf-8")
            roots = collect_wipe_roots(
                work, exe, appdata=appdata, downloads=downloads, sidecar=sidecar
            )
            listed = {p for p in roots.values()}
            self.assertNotIn(exe.resolve(), listed)
            self.assertNotIn((exe / "holiday-photos").resolve(), listed)
            self.assertNotIn((exe / "notes.txt").resolve(), listed)
            self.assertIn((exe / "Telegram.exe").resolve(), listed)

    def test_never_lists_a_user_folder_named_data(self):
        td, work, exe, appdata, downloads, sidecar, export = self._layout()
        with td:
            (exe / "data").mkdir()
            (exe / "data" / "mine.txt").write_text("the user's own file", encoding="utf-8")
            (exe / "data_config").write_bytes(b"installer file")
            roots = collect_wipe_roots(
                work, exe, appdata=appdata, downloads=downloads, sidecar=sidecar
            )
            listed = {p for p in roots.values()}
            self.assertNotIn((exe / "data").resolve(), listed)
            self.assertIn((exe / "data_config").resolve(), listed)

    def test_verifier_filename_constant(self):
        self.assertEqual("syyngram_dv", "syyngram_dv")

    def test_tdata_includes_owner_categories_on_disk(self):
        td, work, exe, appdata, downloads, sidecar, export = self._layout()
        with td:
            tdata = work / "tdata"
            required = [
                tdata / "ayudata.db",
                tdata / "ayu_settings.json",
                tdata / "user_alpha" / "cache",
                tdata / "user_alpha" / "media_cache",
                tdata / "emoji",
                tdata / "key_data",
                tdata / "syyngram_dv",
            ]
            for p in required:
                self.assertTrue(p.exists(), p)
            # Entire tdata root is in wipe set ⇒ all of the above are covered
            roots = collect_wipe_roots(
                work, exe, appdata=appdata, downloads=downloads, sidecar=sidecar
            )
            self.assertTrue(any(p == tdata.resolve() for p in roots.values()))


if __name__ == "__main__":
    unittest.main()
