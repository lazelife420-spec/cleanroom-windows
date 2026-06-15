# Cleanroom PR #22 — Visual / Manual Sign-Off

## Current truth

```text
PR #21 = merged already (0ba59cf on main)
PR #22 = open / ON HOLD (ui/proof-dashboard-polish)
Current PR #22 commit = e59677f
Title lockup = landed on PR #22 only
No v1.0.5 · No tag · No release prep
```

PR #21 (`feat/shell-context-menus`) is **already merged**. Do **not** cherry-pick title polish onto that branch. Do **not** treat PR #21 as open or on-hold.

**This checklist applies to PR #22 visual/manual sign-off only.**

---

## Goal

Confirm PR #22 feels like a proof-first Windows product — not a Python admin panel — before squash merge.

Includes: dashboard polish, Settings left rail, branded title lockup, module-focused workspaces, and no regressions from merged PR #21 shell/context-menu behavior.

---

## Branch / Scope

```text
PR #22: ui/proof-dashboard-polish
Branch: ui/proof-dashboard-polish
```

Do not add unrelated features. Do not rewrite the app. Do not touch release/version/tagging unless explicitly approved.

Hard constraints (unchanged):

- No cleanup/archive/prune/uninstaller **behavior** changes
- No PR #21 shell/context-menu **behavior** changes
- No version/tag/release changes without explicit approval

---

## Automated preflight (repo)

Run from repo root before manual session:

```powershell
python -m pytest
python scripts/ui_merge_gates.py --include-150
python scripts/verify_release_surface.py --tag v1.0.4
python scripts/shell_context_menu_manual_gate.py
```

All must pass before manual sign-off counts.

---

## Manual gate (PR #22)

```powershell
git pull
python startup_manager_gui.py
```

Verify:

- [ ] Home title lockup looks premium (`Cleanroom` + `Archive-first cleanup, with receipts.` + `Receipt-backed` pill)
- [ ] No boring repeated “Cleanroom” labels on one screen
- [ ] Workspace tabs keep focused titles (Cleaner, Proof Ledger, Archive Custody, etc.)
- [ ] Settings uses left section rail — **no bottom tabs**
- [ ] Explorer Context Menus remains inside **Tools**
- [ ] Home = full dashboard; work pages = compact headers (no full proof-card stack)
- [ ] No Not Responding on tab switches or heavy tables
- [ ] No TclError / terminal traceback
- [ ] One tray icon max (single-instance)
- [ ] 920×580 and 150% scaling still clean
- [ ] PR #21 context menus still work on main (in-app row menus + Explorer install/remove smoke)

Optional sanity (merged PR #21 behavior, not a merge blocker for #22 if already on main):

- [ ] Explorer shell menu install/remove in real Windows Explorer (HKCU only)
- [ ] Archive row right-click: restore, receipt, copy paths, delete confirm/cancel

Capture screenshots for anything visual or questionable (Home lockup, Settings rail, 1080px layout).

---

## Title lockup (implemented on PR #22)

Home sidebar identity:

```text
Cleanroom
Archive-first cleanup, with receipts.
[Receipt-backed]
```

Dynamic status line appears only when app state changes (scan, candidates, receipt ready, custody, etc.). Workspace pages show page-specific titles without duplicating the full lockup.

---

## Decision rule

```text
PASS manual checklist → squash merge PR #22
FAIL → fix only the failed PR #22 visual/runtime item(s); re-run gates
```

**Do not merge PR #22 until manual sign-off passes.**

PR #21 is closed — no further action on that PR.

---

## Report template

```text
Changed files:
Verification (automated):
Manual gate result (PR #22):
Screenshots:
Merge recommendation:
```

---

## Hard rules

- Do not merge PR #22 until manual sign-off passes.
- Do not tag. Do not release. No v1.0.5 prep.
- Do not cherry-pick to PR #21 or `feat/shell-context-menus`.
- Do not start a larger redesign.
- Do not add new product claims unless the app proves them.
