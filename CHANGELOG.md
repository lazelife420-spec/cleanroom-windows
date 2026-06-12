# Changelog

## 2026-06-12 — v1.0.3 archive browser, proof honesty, uninstaller guidance

- Archive Browser + in-app receipts (view, copy, open file/folder).
- Archive prune receipts + custody-only prune proof with tiered recommendations.
- Proof Pack trust-score honesty fix: never display `100/100` when any artifact is missing.
- Local-only uninstaller guidance (`program_advice.py`).
- Safer Force Remove: preview, confirmation, registry export before delete, install-folder archive before removal.
- Manual gates: `archive_prune_manual_gate.py`, `force_remove_manual_gate.py`.

## 2026-06-11 — v1.0.2 CustomTkinter UI polish

- CustomTkinter local-only UI shell, receipt printing animation, Proof Output panel.
- Per-user install config on first run; PyInstaller bundles CustomTkinter assets.
- Manual Sandbox proof-loop gate passed; CI release via tag `v1.0.2`.

## 2026-06-10 — Rebrand to Cleanroom
- Product renamed **Smart Clean → Cleanroom** with doctrine: *archive first, prove every action, roll back*.
- New `brand.py`: central identity, `%LOCALAPPDATA%\Cleanroom` data dir; one-time SmartClean→Cleanroom migration with **Cleanroom Migration Receipt** (legacy dir left as backup).
- Feature naming: Cleanroom Receipt, Cleanroom Rewind (was Time Machine), Custody Trust Score, Proof Pack (HTML).
- EXE/installer: `Cleanroom.exe`, `Cleanroom-Setup-1.0.0.exe`. Scheduled task default: `CleanroomDaily`.
- Brand assets: `assets/brand/` (logo, emblem icon, `.ico` for Windows app/installer).
- README rewritten for GitHub launch; MIT LICENSE updated.

## 2026-06-09 — Night, settings/prune/tasks/CI
- New Settings tab (Ctrl+5): edit scan paths (folder picker), archive dir, age thresholds, size/confirm thresholds, archive extensions, exclude patterns, and whitelist in-app; saves to the active config (falls back to the per-user copy if read-only) and re-scans.
- Prune Archive dialog on the Optimizer tab: dry-run preview (count + size) then permanent delete of archived files older than N days, off the UI thread.
- Startup coverage: Task Scheduler logon-triggered tasks now listed (read-only) via `schtasks /Query` with a new "Scheduled Tasks" category and badge.
- GitHub Actions CI (`.github/workflows/ci.yml`): windows-latest, tests, exe build + artifact upload, best-effort installer build.
- 44 tests passing (schtasks CSV parsing + Settings round-trip E2E added); exe + installer rebuilt.

## 2026-06-09 — Night, reversible startup disable
- Disabling a startup entry now backs it up to `%LOCALAPPDATA%\SmartClean\disabled_startup.json` before removing the registry value — disable is fully reversible, matching the archive-first philosophy.
- New "Disabled" category in the Startup sidebar with a header badge; selecting a disabled entry turns the action button into "Re-enable Selected" (restores from backup, with elevation fallback).
- Re-enabling (by any path) consumes the backup; failed restores keep it for retry.
- CLI: `startup_manager_admin.py --list-disabled` and `--restore NAME`.
- 40 tests passing (6 store unit tests + GUI E2E for the Disabled category); exe + installer rebuilt.

## 2026-06-09 — Night, self-contained scheduling
- `SmartClean.exe --headless-clean [--config X] [--dedupe]`: runs the cleaner with no UI and no Python required; appends summaries to `%LOCALAPPDATA%\SmartClean\headless_run.log`. Verified end-to-end against the built exe.
- Scheduling wizard now registers the exe itself when running packaged (`register_task.ps1 -ExePath`); dev runs keep the PowerShell wrapper.
- First-run config generation: packaged app generates `%LOCALAPPDATA%\SmartClean\cleanup_config.yaml` from `%USERPROFILE%` defaults; discovery order is exe-dir → per-user → generate → bundled. GUI's Restore log now follows the config's `log_file`.
- `sign_artifacts.ps1`: signs `dist\SmartClean.exe` + installer via signtool (PFX, store thumbprint, or `-SelfSigned` for local testing).
- Shared `move_duplicates` helper in `main.py`; 33 tests passing (4 new headless/config tests).

## 2026-06-09 — Night, UI polish
- Optimizer dashboard redesigned: animated-free health ring gauge (score + band color) and big stat cards (startup items, cleanup candidates, reclaimable space).
- Branded header: app logo next to the title; status bar gains a hairline separator and version stamp.
- Empty-state hints in Startup/Cleaner/Restore lists (e.g. "Click Scan Now to search…").
- Cleaner rows color-coded by reason (large-file, installer/archive, partial-download, zero-byte).
- Hardened a flaky E2E assertion (log write happens after file moves).

## 2026-06-09 — Night
- App icon (`icon.ico` / `icon.png`): embedded in the exe and shown in the window titlebar.
- Config discovery: frozen exe now prefers an editable `cleanup_config.yaml` next to the exe, falling back to the bundled copy (`main.default_config_path`).
- Restore previews upgraded with Pillow: JPEG/WebP/BMP/ICO/TIFF thumbnails (PNG/GIF still work without Pillow).
- Installer: `installer.iss` (Inno Setup) + `build_installer.ps1`; produces `dist\SmartClean-Setup-1.0.0.exe` with Start Menu/desktop shortcuts and an upgrade-safe config.
- Scheduling wizard resolves `register_task.ps1` via resource lookup so it works from the frozen exe.
- 29 tests passing (added JPEG/text preview E2E test); exe and installer builds verified.

## 2026-06-09 — Evening
- Fixed critical GUI bugs: startup crash (missing `_clear_search_placeholder`), telemetry dialog spliced into `schedule_optimization`, duplicate restore methods shadowing the working ones, missing `datetime` import in `enable_telemetry.py`.
- Replaced cross-thread `after()` calls with a thread-safe queue polled from the Tk main thread (fixes "main thread is not in main loop").
- New `recommendations.py` headless engine: severity-ranked recommendations + health score, rendered in a color-coded table on the Optimizer tab.
- Scheduling wizard: hour/minute spinboxes, Daily/Weekly recurrence with weekday picker; `register_task.ps1`/`run_scheduled.ps1` gained `-Schedule`/`-Days`/`-Dedupe`.
- Cleaner: per-item checkboxes (click, Space, Select All/None, header toggle); Apply archives only checked items; summary shows checked count/size.
- Restore: file preview pane (PNG/GIF images, text snippets) alongside the existing dry-run preview.
- Visual polish (palette, button styles, tab icons, status bar, striped rows, delayed tooltips) and keyboard shortcuts (F5, Ctrl+F, Ctrl+1..4, Escape).
- Added GUI E2E tests (scan → selective apply → restore) and recommendation engine tests: 28 tests passing.
- `build_exe.ps1` now builds the GUI (`SmartClean.exe`, windowed, one-file) and bundles config + scheduling scripts; build verified to launch.

## 2026-06-09
- Implemented Startup Manager with read-only list and registry/folder scanning.
- Added enable/disable startup entry support (requires admin): `--startup-enable name=C:\path\to\app.exe` and `--startup-disable name`.
- Added `startup_manager_gui.py` viewer and admin module `startup_manager_admin.py`.
- Integrated telemetry toggle into GUI and CLI (`--telemetry on|off|status`).
- All tests passing (11 tests).
- Rebuilt EXE with startup manager integration.
