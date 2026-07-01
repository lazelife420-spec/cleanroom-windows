# Cleanroom — Handoff

Short summary
- Cleanroom is a safe, archive-first Windows system-care suite with a Tkinter GUI (Optimizer / Activity / Startup / Cleaner / Uninstaller / Restore / Settings). Product doctrine: *archive first, prove every action, roll back*. Six themes (Emerald Pro = IObit-style green). Signature features: Disk Foresight, Cleanroom Rewind, Cleanroom Receipts, Custody Trust Score, Proof Pack.
- Active supported product path: Cleanroom desktop GUI + CLI/headless. Active runtime boundaries live in `cleanup_profiles.py` and `archive_runtime.py`; legacy smart-cleaner implementation/docs are archived under `legacy/smart_cleaner/`, with root compatibility shims retained for `smart_config.py`, `archive_manager.py`, and `smart_scheduler.py`.

Key files
- `brand.py`: product identity (`APP_DISPLAY`, `APP_TAGLINE`, `APP_MOTTO`, brand assets, `user_data_dir()` with one-time SmartClean→Cleanroom migration + Migration Receipt)
- `main.py`: core scanner/cleaner (scan_candidates, apply_actions, dedupe_candidates)
- `restore.py`: restore helpers (load_log, entries_from_log, restore_one)
- `startup_manager.py` / `startup_manager_admin.py`: startup listing and admin registry helpers
- `enable_telemetry.py`: telemetry opt-in helpers (`is_opted_in`, `set_opt_in`)
- `recommendations.py`: headless recommendation + health-score engine (unit-tested)
- `uninstaller.py`: installed-programs listing (registry Uninstall keys), uninstall runner, leftover scan + archive (unit-tested)
- `foresight.py`: Disk Foresight — free-space snapshot history + least-squares disk-full forecast (unit-tested)
- `timeline.py`: Time Machine — groups cleanup-log actions into day buckets, rolls a whole day back (unit-tested)
- `receipts.py`: Cleanup Receipts — human-readable post-clean record incl. Foresight "days bought" (unit-tested)
- `registry_health.py`: safe registry health scanner — evidence-based only (missing files), archive-first repairs (unit-tested)
- `ledger.py`: activity feed + trust score (unit-tested)
- `audit.py`: HTML proof audit export (unit-tested)
- `proof.py`: proof-of-work engine
- `cleanup_config.yaml`: user-configurable scan paths and archive settings
- `build_exe.ps1`: PyInstaller build (GUI, one-file, windowed)
- `tests/`: pytest unit tests + GUI E2E tests (`test_gui_e2e.py`)

Recent changes (high-impact)
- Activity & Proof Ledger (new tab + sidebar): `ledger.py` turns the cleanup log into a chronological feed with per-item ✓/✗ custody status; `summarize_feed` + `trust_score` (0–100). The Activity tab shows a custody trust ring, stat cards (actions logged / restorable now / bytes in custody), and a filterable tree. Header badge `🔬 Trust: N%` updates from `refresh_activity`. Sidebar adds **Export Audit (HTML)** via `audit.py` — self-contained dark HTML report (custody status, trust score, reason breakdown, 500-row activity table, honest comparison copy). Saved to `%LOCALAPPDATA%\\Cleanroom\\audits\\`.
- Visual Proof Report dialog: after GUI cleanup, `_show_proof_report` replaces the plain messagebox with a card-based screen — items archived, space moved, OS free before/after/Δ, custody check, disk-days bought — plus honest note when same-volume archive moves don't change free space yet. Buttons: Open Receipt, View Activity Ledger, Done.
- Proof of work (`proof.py`): Cleanroom PROVES it did something instead of claiming it. (1) Free-space numbers in receipts/dialogs are measured from the OS (`shutil.disk_usage`) before+after the operation, never estimated — and when a clean moves files to an archive on the same volume (delta ≈ 0), the receipt says so explicitly ("MOVED to the archive, not deleted — free space changes when you prune"). (2) Custody check (`proof.verify_entries`): verifies each logged artifact (file/folder/.reg) exists on disk right now, with bytes-in-custody total. Wired into: GUI `apply_cleanup` (receipt gets a PROOF section via `receipts.format_receipt(..., proof=)`, completion dialog shows custody count), Prune Archive (OS-measured freed bytes on apply — pruning really deletes, so the measured number is the headline), single uninstall (OS-measured space freed appended to status), headless runs (`main.run_headless` logs custody + proof receipt), and a new sidebar tool "🔬 Verify Custody" that audits the ENTIRE history (all outstanding `entries_from_log` records — note: yields tuples, custody wants `t[3]` dicts) and reports N/N present + bytes in custody; missing items are attributed honestly (Prune Archive or outside interference). (de-startup-ified): the global sidebar is now app navigation — "Cleanroom" section buttons (Dashboard/Startup/Cleaner/Uninstaller/Restore/Settings, synced to the notebook via `<<NotebookTabChanged>>` → `_sync_nav_buttons`) plus a "Tools" section (Registry Health, Time Machine, Last Receipt, Schedule). Header badges are now suite-wide (❤ Health / 🚀 Startup / 🗑 Programs / 🧹 Reclaimable / ↩ Restorable; updated from refresh_optimizer + refresh_uninstaller) and the subtitle says "system care", not "startup manager". Startup-specific UI moved into the Startup tab: Total/Folders/Registry/Tasks/Disabled badges, category chips (All/Folders/Registry/Tasks/Disabled), and the search box (Ctrl+F now jumps to the Startup tab first). `total_label`/`cat_*`/`search_entry` attribute names unchanged, so existing code paths and tests still work.
- Registry Health (Optimizer → "🩺 Registry Health…"): deliberately NOT a WinASO-style "invalid entries" cleaner — it only flags registry entries that *verifiably* point at missing files: dead Run-key startup refs (`scan_dead_startup_refs`), broken App Paths registrations (`scan_broken_app_paths`), and orphaned uninstall entries whose uninstaller exe is gone (`scan_orphaned_uninstall_entries`, msiexec entries skipped). Conservative by design: host-launcher commands (rundll32/cmd/powershell/...) and PATH-resolvable names are never flagged (`is_broken_command`; `extract_exe_path` handles quoted/unquoted-with-spaces commands). Repairs are archive-first: whole keys via `reg export`, single *values* via a hand-built .reg (`format_value_reg`, REG_SZ escaped + REG_EXPAND_SZ as hex(2) UTF-16LE) written before deletion; logged with reason `broken-registry` (new palette color in all 6 themes) and restorable via `_smart_restore`/Restore tab/Time Machine like all other registry ops. Dialog defaults: startup-refs + app-paths checked, uninstall-entries unchecked; failed deletes consume their backup file and are reported (HKLM needs admin). Live round-trip verified on this machine (plant dead Run value → detect → repair → reg import restore → value identical). Scanners accept injected data for tests.
- IObit-style Uninstaller UX: checkbox column (☐/☑ click, Space, header ✓ toggles all visible) drives batch uninstall — checked items take priority over the row selection in `_selected_programs`. A per-row 🗑 action column uninstalls that single program on click. Smart filter chips above the list (`uninstaller.filter_programs`, unit-tested): All Programs / Large (≥1 GB) / Recently Installed (≤30 days) / Over a Year Old (unknown install dates excluded from date filters). Checked-state indices are cleared on every rescan (iids index into `uninstall_entries`).
- Power User Mode (Settings → checkbox, persisted as `power_user` in `ui_prefs.json`): denser Treeview rows (20px/9pt vs 24px/10pt) across ALL tabs and an extra "Registry Key" column (HKLM/HKCU + subkey) in the Uninstaller. Applied at `_init_style` time; toggling uses the same `wants_restart` rebuild as themes via the "Apply UI Settings" button (which now saves theme + power mode together).
- New "Emerald (Pro)" theme: green-accent dark palette modeled on IObit Uninstaller (graphite background, #22C55E accent), part of `THEME_ORDER`, covered by the palette integrity tests.
- Forced removal (broken uninstallers): "Force Remove…" on the Uninstaller tab (also offered automatically when an uninstaller exits nonzero) sweeps leftover folders + registry keys via the leftover dialog (registry keys default CHECKED in force mode, button reads "Remove & Archive") and then removes the orphaned Programs-list entry itself via `uninstaller.remove_uninstall_entry` — the Uninstall key is exported to .reg in the archive before deletion, logged like any other registry leftover, restorable from Restore/Time Machine. With zero leftovers found, the orphan entry is still removed. HKLM entries need admin; the GUI says so on failure.
- Registry leftover scanning (archive-first): `uninstaller.find_registry_leftovers` scans top-level HKCU/HKLM Software keys (incl. WOW6432Node) with the same token matching as folders, minus `PROTECTED_KEY_NAMES` (vendor umbrella keys like Microsoft/Google are never matched). `archive_registry_leftovers` exports each key to a `.reg` in `<archive>/uninstall_leftovers/registry`, deletes the key only after a successful export, and logs `src='REGISTRY::<key>'` / `dest=<.reg>` with reason `registry-leftover`. Restores route through `StartupManagerGUI._smart_restore`, which re-imports the `.reg` (and consumes it) for registry entries and falls back to `restore.restore_one` for files — used by Restore Selected / Restore All / Time Machine. In the leftover dialog, registry keys (🗝) default to UNCHECKED; folders (🗂) default checked.
- Batch uninstall queue: the Uninstaller tree is multi-select (`extended`); selecting several programs and clicking Uninstall runs each program's uninstaller sequentially in one worker with `[i/n]` progress (status updates marshalled through the bg queue) and a per-program exit-code summary at the end.
- Health-score history: `foresight.record_health`/`load_health_history` snapshot the Optimizer health score (6h throttle, 1000 cap) to `%LOCALAPPDATA%\Cleanroom\health_history.json`; a small band-colored sparkline renders under the health gauge label. GUI E2E sandbox monkeypatches `HISTORY_PATH`/`HEALTH_PATH`/`RECEIPT_DIR` so tests never touch real user data.
- Uninstaller tab (IObit-style): lists installed programs from the three registry Uninstall hives (HKLM 64/32-bit + HKCU) with name/publisher/version/size/date, live filter, sortable columns, count + total-size badges. Uninstall runs the program's own uninstaller (optional silent mode prefers QuietUninstallString; msiexec gets `/X … /qn`). After uninstall (or on demand) a leftover scan checks the top level of Program Files / AppData / ProgramData for folders matching the program name; checked leftovers are MOVED to `<archive>/uninstall_leftovers` and logged to the cleanup log with reason `uninstall-leftover`, so the Restore tab can bring them back. Core logic in `uninstaller.py` (pure helpers unit-tested; updates/system components filtered out via SystemComponent/ParentKeyName/ReleaseType).
- Theme system: six palettes — Dark (default), Light, Emerald (Pro), Midnight (OLED black + cyan), Nord, Cyberpunk (neon pink/purple) — defined in `PALETTES` with a mandatory key set (`THEME_KEYS`, includes `ON_ACCENT` for text on accent surfaces). `apply_palette()` sets module globals before widget construction; preference persists in `%LOCALAPPDATA%\Cleanroom\ui_prefs.json`. Switch via the 🎨 header button (cycles `THEME_ORDER`) or the Theme combobox + Apply in Settings; both rebuild the window through the `__main__` restart loop (`app.wants_restart`). Severity/reason colors are palette-aware. Palette integrity is unit-tested (`tests/test_themes.py`).
- Time Machine (Restore tab → 🕐 button): builds day buckets from the cleanup log (`timeline.build_timeline`, skipping `action=='restore'` bookkeeping records), shows per-day action count / moved bytes / still-restorable count / top reasons, and "Roll Back This Day" restores every still-archived entry via `restore.restore_one(apply=True)` in a background worker. Conflicts use restore.py's rename-don't-overwrite behavior.
- Cleanup Receipts: after every GUI apply (and headless run — see `main.run_headless`), `receipts.write_receipt` writes a text receipt to `%LOCALAPPDATA%\Cleanroom\receipts` (capped at 100): items moved, space freed, per-reason breakdown, and "~N extra days of disk life" computed from the Foresight slope. "Last Receipt" button on the Optimizer opens the newest one. GUI E2E tests monkeypatch `RECEIPT_DIR` into the sandbox so tests never write real receipts.
- Disk Foresight (novel feature): every app start records a free-space snapshot (throttled to 6h, capped at 1000) into `%LOCALAPPDATA%\Cleanroom\disk_history.json`; `foresight.py` fits a least-squares trend and the Optimizer card shows a canvas sparkline plus "Full in ~N days (date)" (color-coded urgency <30/<90 days) and "Cleaning now buys ~N more days" derived from current reclaimable bytes. Needs 3+ snapshots over ≥0.5 days before a trend is claimed; shows honest "collecting data" states until then.
- Fixed critical GUI bugs: missing `_clear_search_placeholder` (crashed at startup), telemetry dialog body spliced into `schedule_optimization`, duplicate `restore_selected_entry`/`restore_all_entries` definitions shadowing the working versions, and missing `datetime` import in `enable_telemetry.py` (made `set_opt_in` silently fail).
- Thread-safe background work: workers push results onto a queue drained from the Tk main thread every 50ms (`_run_bg`/`_poll_bg_queue`). Do NOT call `after()` from worker threads — it raises "main thread is not in main loop" when the mainloop isn't running (e.g. in tests).
- New `recommendations.py`: pure, headless recommendation + health-score engine (severity levels, reason-aware rules) rendered in a color-coded treeview on the Optimizer tab. Unit-tested.
- New scheduling wizard: hour/minute spinboxes, Daily/Weekly recurrence with weekday picker, dedupe option; `register_task.ps1` and `run_scheduled.ps1` extended with `-Schedule`/`-Days`/`-Dedupe` support.
- Cleaner per-item selection: checkbox column (click, Space, Select All/None buttons, header toggle); Apply archives only checked items; summary shows checked count/size.
- Restore file preview: PNG/GIF image thumbnails and text-file snippets render directly in the Preview pane; other types fall back to "Open Archived".
- Visual polish: unified palette, primary/secondary button styles with hover states, tab icons, sidebar shortcut hints, global status bar (with version stamp), striped rows everywhere, delayed tooltips.
- Optimizer dashboard: health ring gauge (canvas arc, band-colored) + big stat cards; header shows the app logo; empty lists show centered hints; Cleaner rows are color-coded by reason (`REASON_COLORS`).
- Accessibility: F5 refresh-all, Ctrl+F focus search, Ctrl+1..6 tab switching, Escape closes dialogs, modal dialogs (transient + grab), Enter previews restore entry.
- GUI E2E tests (`tests/test_gui_e2e.py`): drive the real Tk app against a tmp sandbox — scan, selective apply, restore round-trip, preview pane. The GUI constructor accepts `config_path`/`restore_log_path` kwargs for testability.
- Packaging: `build_exe.ps1` builds `dist\Cleanroom\Cleanroom.exe` (GUI, windowed, custom icon) bundling `cleanup_config.yaml`, brand icon + scheduling scripts; verified to launch.
- Installer: `installer.iss` + `build_installer.ps1` produce `dist\Cleanroom-Setup-1.0.0.exe` (Inno Setup 6 found at `%LOCALAPPDATA%\Programs\Inno Setup 6`). Config installs upgrade-safe (`onlyifdoesntexist`).
- Self-contained scheduled runs: `Cleanroom.exe --headless-clean [--config X] [--dedupe]` runs the cleaner with no UI/Python; logs to `%LOCALAPPDATA%\Cleanroom\headless_run.log`. The wizard schedules the exe itself when packaged (`register_task.ps1 -ExePath`); dev mode keeps the python wrapper.
- Config discovery (`main.default_config_path`): exe-dir copy → `%LOCALAPPDATA%\Cleanroom\cleanup_config.yaml` → generated on first frozen run from `%USERPROFILE%` (`generate_default_config`) → bundled copy. The GUI's Restore tab follows the config's `log_file`.
- Code signing: `sign_artifacts.ps1` signs exe + installer via signtool (`-PfxPath`/`-Thumbprint`/`-SelfSigned`); signtool confirmed present in the Windows SDK. A real OV/EV cert is still needed to satisfy SmartScreen.
- Reversible startup disable: disabling backs the entry up to `%LOCALAPPDATA%\Cleanroom\disabled_startup.json` (read first, then delete); "Disabled" sidebar category lists backups and re-enables them (`restore_disabled`); re-enable consumes the backup, failure keeps it. CLI: `--list-disabled` / `--restore NAME`.
- Settings tab (Ctrl+5): in-app editing of paths/archive dir/ages/thresholds/extensions/exclusions/whitelist; `_write_config` falls back to the per-user config when the active one is read-only; unknown config keys preserved on save.
- Prune Archive dialog (Optimizer tab): dry-run preview then permanent deletion of archived files older than N days (`prune_archive.prune`).
- Scheduled-task startup source: `startup_manager._list_logon_tasks` parses `schtasks /Query /FO CSV /V` (English column names — known localization limitation); read-only "Scheduled Tasks" category in the GUI.
- CI: 5 workflows on GitHub Actions — `ci.yml` (tests / public-surface brand+docs scan / migration receipt tests), `build-windows.yml` (portable exe + installer build with provenance attestation, on push to main/tags/PRs), `release.yml` (tag-triggered: build, checksum, attest, create GitHub Release), `codeql.yml` (security scanning on push/PR/weekly schedule), `release-dry-run.yml`. All currently green on `main`. Dependabot keeps `requirements.txt` and Actions versions current — check `gh pr list` periodically since Dependabot PRs against a stale base commit can fail CI for reasons unrelated to the actual bump (rebase with `@dependabot rebase` if so).
- Restore previews use Pillow when available (JPEG/WebP/BMP/ICO/TIFF); PNG/GIF work without it.
- App icon: `assets/brand/cleanroom-icon.ico` / `cleanroom-icon.png` (shield emblem crop), embedded in exe + window titlebar; full logo at `assets/brand/cleanroom-logo.png`.
- Test suite: 366 passing (`pytest -p no:xonsh tests/` — the globally installed xonsh pytest plugin breaks in headless consoles, hence the flag). Grew from 132 with the performance-engine work (see `STATUS.md`) — this file previously understated the count; keep this line and `STATUS.md` in sync going forward. One E2E occasionally hits a transient TclError creating the Tk window under full-suite load; re-run passes.

How to run (dev)
1. Ensure Python 3.14+ is available and run from project root.
2. Run the GUI:

```powershell
Set-Location -Path '<project-root>'
python startup_manager_gui.py
```

Run tests:

```powershell
python -m pytest -q -p no:xonsh tests/
```

Build the exe and installer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build_exe.ps1 -OneFile
# -> dist\Cleanroom.exe
powershell -NoProfile -ExecutionPolicy Bypass -File build_installer.ps1
# -> dist\Cleanroom-Setup-1.0.0.exe
```

What I verified
- Full test suite: `124 passed` (adds proof.py unit tests — custody verification over files/folders/missing artifacts, proof math, honest same-volume wording, receipt PROOF embedding — and an E2E asserting the apply flow writes a receipt with a verified custody section and that Verify Custody reports CUSTODY VERIFIED over live history).
- Previously: `115 passed` (adds registry_health unit tests — exe-path extraction, broken-command classification incl. host launchers/PATH names, injected-data scanners, .reg value formatting/escaping, archive-first repair flow with failure paths — and an E2E driving the Registry Health dialog with checked-issue routing; the uninstaller chips E2E now injects deterministic program data instead of racing the live registry scan).
- Registry Health live round-trip on this machine: planted dead HKCU Run value → detected → repaired (value deleted, .reg backup written, logged as `broken-registry`) → restored via `reg import` → value byte-identical; clean system scan reports 0 issues.
- GUI smoke test: screenshot reviewed for Emerald (Pro) theme in Power User Mode — chips, checkbox column, per-row 🗑, dense rows, and green Uninstall button all render correctly with 77 real programs (24.65 GB). Earlier screenshots covered Dark, Midnight, Nord, Cyberpunk.
- `dist\Cleanroom.exe` builds (with icon) and launches; installer compiles successfully.
- Headless mode verified against the built exe (no Python): archives candidates, writes cleanup log + run summary, exit code 0.

Known issues & notes
- Uninstalls launch the vendor's own uninstaller (like every uninstaller tool); some show their own UI and some require admin elevation. Leftover matching is name-token based (longest significant token) and intentionally conservative — it only scans top-level folders of the usual roots.
- Theme switch rebuilds the window (in-process restart loop in `__main__`); inside tests/embedding, set `wants_restart` handling accordingly.
- Foresight needs a few days of real usage before it can show a forecast (by design — no fake numbers). GUI writes snapshots to the real `%LOCALAPPDATA%` even under tests; harmless but worth knowing.
- The GUI relies on Windows-specific behavior for startup registry and `os.startfile` — on other platforms those features are no-ops or absent.
- Telemetry is strictly local and opt-in; no external telemetry transport implemented.
- The xonsh pytest plugin (globally installed) crashes pytest in headless consoles — always run with `-p no:xonsh`.
- Code-signing pipeline is ready (`sign_artifacts.ps1`) but unsigned until a real OV/EV certificate is provided; `-SelfSigned` exists for local testing only.

Priority next steps
1. Obtain an OV/EV code-signing certificate and run `sign_artifacts.ps1` in the release flow (user action required) — still the main release-readiness gap
2. Enable/disable actions for scheduled tasks (`schtasks /Change /TN x /DISABLE`) with the same backup-first pattern
3. Locale-independent scheduled-task listing (PowerShell `Get-ScheduledTask` or COM instead of English CSV columns)
4. Cleanup-log rotation/compaction (restore log grows unbounded)
5. Branch hygiene: ~40+ stale branches accumulated (audit/chore/docs/backup/devin/* branches past their merge) — worth a cleanup pass

Quick contact notes
- File to open first: `startup_manager_gui.py` (entrypoint)
- Config: `cleanup_config.yaml` controls scan paths and archive settings
