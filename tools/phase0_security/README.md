# Phase 0 security foundations — test notes

## Contract tests (no Desktop build)

```bash
python3 tools/phase0_security/test_phase0.py -v
```

Covers sidecar JSON/`workdir.txt` shape, early settings flag defaults, overwrite-unlink behavior, symlink non-follow contract.

## Full app build (Windows-first)

Follow `docs/building-win.md`. Phase 0 sources are listed in `Telegram/CMakeLists.txt`:

- `core/data_folder.{h,cpp}`
- `storage/storage_secure_wipe.{h,cpp}`
- `storage/storage_duress.{h,cpp}` (stub)
- `ayu/ayu_settings_early.{h,cpp}`
- `ayu/utils/ayu_cache_cleanup.{h,cpp}` (stub)

Manual checks after a Win build:

1. Write `%APPDATA%\Syyngram\workdir.txt` + `config.json` with `"strictDataFolder": true` pointing at a missing drive → app must not create `tdata` under the default AyuGram AppData profile.
2. Point sidecar at an existing folder → that folder becomes `cWorkingDir()`.
3. `-workdir` CLI overrides sidecar.
4. Set `"clearCacheOnStartup": true` in `tdata/ayu_settings.json` → log shows Phase 0 stub cleanup (no deletion until Phase 1).
