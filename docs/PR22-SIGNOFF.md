# PR #22 — Manual sign-off checklist

**Branch:** `ui/proof-dashboard-polish`  
**Status:** ON HOLD — do not merge until every item below is checked in a real Windows session.

Automated gates (`pytest`, `ui_merge_gates`, `verify_release_surface`, tray smoke) must be green first. This document covers what automation cannot fully prove.

## Launch

```powershell
git pull
python startup_manager_gui.py
```

Optional automated tray lifecycle check (does not replace visual confirmation of notification-area icon):

```powershell
python scripts/tray_visual_gate.py
```

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

- [ ] Tray icon **visible** in the notification area after launch.
- [ ] Right-click opens menu with: Open, Hide, Show, Run Scan, Latest Receipt, Proof Pack, Open Archive Folder, Quit (and tool entries as applicable).
- [ ] **Hide** withdraws main window; **Show** / **Open** restores it.
- [ ] **Quit** removes tray icon cleanly.
- [ ] Relaunch creates **one** icon only (no duplicate pile).
- [ ] No `_running` traceback on quit.
- [ ] Menu actions (Latest Receipt, Proof Pack, etc.) do not crash.

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

## PR #21 regression

- [ ] Explorer context menus still install and work (`scripts/smoke_shell_context_menu.py` PASS is necessary but not sufficient — spot-check in Explorer if possible).

## Stability

- [ ] No **Not Responding** during normal navigation.
- [ ] No **TclError** in console during sign-off pass.

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Manual visual | | | PASS / FAIL |
| Tray visual | | | PASS / FAIL |

**After manual PASS:** squash-merge PR #22. Do **not** tag or release until explicitly requested.
