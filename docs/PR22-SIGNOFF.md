# PR #22 — Manual sign-off checklist

**Branch:** `ui/proof-dashboard-polish`  
**Status:** ON HOLD — do not merge until every item below is checked in a real Windows session.

> **Critical:** Manual sign-off must run on branch `ui/proof-dashboard-polish` with `python startup_manager_gui.py`.  
> Testing `main` or an old packaged `.exe` will show stale UI (Settings in sidebar, Telemetry button, stacked chrome) and is **not valid** for PR #22.

Automated gates (`pytest`, `ui_merge_gates`, `verify_release_surface`, tray smoke) must be green first. This document covers what automation cannot fully prove.

**Do not commit screenshots to the repo.** Capture locally for review; use this doc as the PASS/FAIL rubric.

## Launch

```powershell
git pull
python scripts/generate_icons.py   # only if regenerating from SVG
python startup_manager_gui.py
```

Optional automated tray lifecycle checks (do not replace visual confirmation of notification-area icon):

```powershell
python scripts/tray_visual_gate.py
python scripts/tray_process_gate.py
```

After Quit from tray or window close, confirm no Cleanroom Python process remains:

```powershell
Get-Process python,pythonw,Cleanroom -ErrorAction SilentlyContinue
```

Expected: no leftover Cleanroom `python` process and no tray icon.

## Icon pipeline (premium product identity)

**Source:** `assets/brand/cleanroom-icon.svg`  
**Generate:** `python scripts/generate_icons.py` → `cleanroom-icon.png`, `cleanroom-icon-tray.png`, `cleanroom-icon.ico`  
**Consumers:** titlebar (`iconbitmap`), tray (`ui/tray.py`), PyInstaller + Inno Setup (already wired to `assets/brand/`).

Manual proof — icon must read as **archive + custody + trust**, not generic recycle/broom:

- [ ] **Desktop shortcut** (if installed): sharp, not blurry; no stale old shield-with-C artwork.
- [ ] **Taskbar:** recognizable at small size; edges crisp.
- [ ] **Tray:** uses optimized 32×32 asset; readable in notification area overflow.
- [ ] **Titlebar:** matches taskbar; not default Tk feather.
- [ ] **16×16:** shield + archive mark still distinguishable (open ICO at 16px in Explorer or VS Code).
- [ ] No obvious stale icon in exe metadata after rebuild (installer pass is separate; dev run uses assets above).

## Visual screenshot set (local capture only)

Capture at **1150×720 default** unless noted. Mark each PASS/FAIL.

| # | Capture | PASS means |
|---|---------|------------|
| 1 | **Home** @ 1150×720 | Compact hero, custody chip in global header, no double-header stack |
| 2 | **Home** maximized | Content centered or fills sanely; no crushed sidebar |
| 3 | **Cleaner empty** | Empty card only — no dead details pane |
| 4 | **Cleaner with candidates** | Split pane + grouped tree + details; sash visible |
| 5 | **Archive** | Loading/empty/results intentional; actions grouped |
| 6 | **Proof Ledger** | Compact hero; trust inline; table + details |
| 7 | **Startup** | Compact header; split pane works |
| 8 | **Uninstaller** | Empty/selection states clear |
| 9 | **Settings** opened from **top-right** header (not sidebar-only path) | Same Settings page; pill nav |
| 10 | **Tools → Explorer Context Menus** | Dark modal editor opens |
| 11 | **Tray icon + right-click menu** | One icon; product menu hierarchy |
| 12 | **920×580** compact layout | Usable; Settings still reachable |
| 13 | **150% scaling** (Windows display or gate) | No clipped chrome; sidebar usable |

## Global chrome

- [ ] **Settings** button visible in top-right header on every page (Home, Cleaner, Archive, Proof Ledger, Startup, Uninstaller, Restore, Settings).
- [ ] **`Ctrl+,`** opens the Settings tab (same page as sidebar would use — not a duplicate modal).
- [ ] **More ▾** menu opens from header.
- [ ] Global header shows app identity + custody chip; **no duplicate “Cleanroom” title block** in page content.
- [ ] **Archive-first ON** chip appears on Home and Cleaner only (not on unrelated workspace pages).

## Page hierarchy (no double-header stack)

- [ ] Settings, Startup, Uninstaller, Proof Ledger, Archive do **not** show stacked giant header bands.
- [ ] Home feels branded but compact (single hero row + cards).
- [ ] Cleaner has one clear primary action area (Scan / Preview / Archive & Clean).

## Sidebar

- [ ] **Main:** Home, Cleaner, Archive, Proof Ledger.
- [ ] **System:** Startup, Uninstaller, Restore.
- [ ] **Tools:** Explorer Menus, Registry Snapshot, Rewind, Receipt, Proof Pack, Custody Check, Lights Out.
- [ ] Active nav state is clearly distinct from hover.
- [ ] Collapsed sidebar (`«`) remains usable.
- [ ] Settings is **not** awkwardly buried as the only obvious path (header + `Ctrl+,` are primary).

## Split panes (table + details)

On **Cleaner, Archive, Proof Ledger, Startup, Uninstaller, Restore**:

- [ ] Drag the splitter — table and details widths change.
- [ ] Splitter has a visible affordance (not invisible).
- [ ] Details panel is not crushed; table is not an empty void.
- [ ] Restart app — split sizes persist.
- [ ] Layouts remain usable at **920×580**, **1150×720**, and **maximized**.

## Loading / empty / results states

- [ ] **Cleaner empty:** centered empty card only — no dead details panel beside an empty table.
- [ ] **Cleaner loading:** “Scanning folders…” — no contradictory footer (“Ready to scan” while scanning).
- [ ] **Archive loading:** “Loading archive custody…” (or equivalent busy state).
- [ ] **Startup / Uninstaller / Restore:** distinct loading, empty, and results states.
- [ ] **Proof Ledger:** distinct loading, empty, and results states.

## Tray (real Windows notification area)

**PASS requires:**

- Launch from source: `python startup_manager_gui.py`
- Cleanroom icon visible beside clock **or** inside hidden-icons overflow
- Exactly **one** tray icon (no duplicate pile)
- Right-click opens menu (Open, Scan, receipt/proof actions, Tools, Window, Quit)
- **Hide to tray** withdraws main window; **Show** / **Open** restores it
- **Quit** removes tray icon cleanly
- **Quit** terminates the Cleanroom `python` process (verify with `Get-Process python,pythonw,Cleanroom`)
- Relaunch creates **exactly one** icon (no duplicate pile)
- Second instance while running does not spawn duplicate tray icons or hidden processes
- No `_running` / pystray traceback on quit
- Menu actions (Latest Receipt, Proof Pack, etc.) do not crash
- Automated tray gates leave no orphan icons/processes (`tray_visual_gate.py`, `tray_process_gate.py`)

**FAIL if:**

- Icon flashes then disappears
- Icon is not visible anywhere in the notification area / overflow
- Menu cannot open
- Quit leaves orphan icon
- Quit leaves orphan `python` / `pythonw` / `Cleanroom` process
- Relaunch creates duplicate icons or processes
- User cannot close the tray/app from the tray menu
- Tray tests or gate scripts leave icons/processes behind

Manual checklist:

- [ ] Launch from source (`python startup_manager_gui.py`)
- [ ] Tray icon **visible** after launch (not flash-then-gone)
- [ ] Right-click opens full product menu
- [ ] **Hide to tray** / **Show** work
- [ ] **Quit** removes icon
- [ ] **Quit** exits Python process (`Get-Process python,pythonw,Cleanroom` empty)
- [ ] Relaunch = one icon only
- [ ] Second launch while running focuses existing app or exits cleanly (no duplicate tray)
- [ ] No pystray traceback in console

## Dialogs

- [ ] Normal flows use **dark Cleanroom modals** — no white app-owned `Toplevel` / native info boxes for:
  - Verify Custody results
  - Receipt viewer
  - Archive delete confirm / result
  - Explorer Context Menu Editor
  - Diagnostics
  - Registry Snapshot
  - Schedule cleanup
  - Proof report
- [ ] OS file/folder pickers may remain native (acceptable).
- [ ] pystray menu may stay OS-native (acceptable).

## PR #21 regression

- [ ] Explorer context menus still install and work (`scripts/smoke_shell_context_menu.py` PASS is necessary but not sufficient — spot-check in Explorer if possible).

## Stability

- [ ] No **Not Responding** during normal navigation.
- [ ] No **TclError** in console during sign-off pass.
- [ ] No **CTkImage** warning spam on launch.

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Icon visual | | | PASS / FAIL |
| Manual visual | | | PASS / FAIL |
| Tray visual | | | PASS / FAIL |

**After manual PASS:** squash-merge PR #22. Do **not** tag or release until explicitly requested.
