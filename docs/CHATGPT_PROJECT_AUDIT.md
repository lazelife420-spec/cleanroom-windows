# Cleanroom Project Audit for Future ChatGPT Sessions

Last updated: 2026-06-28
Workspace: `C:\Users\KickA\smart_clean_tool`

## Executive Summary

This repository is primarily a **Windows desktop app called Cleanroom**: a local-only, archive-first cleanup utility with proof/receipt workflows, restore support, archive custody checks, and a large Tk/CustomTkinter GUI.

The **active, well-tested product surface is the Cleanroom desktop path**, not the older "Smart Cleaner" web/scheduler experiment. The current codebase is in a good functional state:

- `366` tests pass locally with `python -m pytest -p no:xonsh tests/`
- `python -m ruff check .` is clean under the current repo config
- core modules compile successfully
- packaging/build scripts and release docs are present

The repo also contains **legacy or compatibility smart-clean modules**.
The archived implementation/docs now live under `legacy/smart_cleaner/`, while
root `smart_config.py`, `archive_manager.py`, and `smart_scheduler.py` remain
as compatibility shims. They are useful context, but they should not be assumed
production-ready without additional validation.

## What Is Implemented and Verified

### 1. Main product: Cleanroom desktop app

Primary entrypoints:

- `startup_manager_gui.py`: main GUI entrypoint
- `main.py`: CLI/headless cleanup engine
- `receipt_desktop/app.py`: standalone receipt viewer entrypoint

Core user-facing capabilities present in code and covered by tests:

- cleanup scanning and archive-first apply flow
- restore / rewind flows
- startup item management
- uninstaller and leftover archiving
- registry health checks and archive-first repair
- proof/ledger/audit export flows
- receipt parsing, rendering, validation, and desktop viewing
- tray, icons, layout, theming, and GUI lifecycle
- performance/incremental scanning engine

### 2. Receipt system

The receipt system has been refactored into a layered design:

- `receipts.py`: compatibility shim and file I/O
- `receipt_core/`: typed schema, parsing, render, custody, trust, export
- `receipt_desktop/`: standalone receipt viewer app
- `receipt_bridge.py`: handoff/opening logic

This area is heavily tested and appears to be one of the more mature parts of the repo.

### 3. Performance engine

The large-file-set scanning work is real and integrated:

- `performance_engine.py`
- `main.py` fast scan path
- GUI controls in `startup_manager_gui.py`
- docs in `docs/PERFORMANCE_ENGINE.md`

`STATUS.md` matches the current local test result: `366` passing tests.

## Code Map

These files are the best starting points for future work:

- `startup_manager_gui.py`: app shell, tabs, actions, GUI orchestration
- `main.py`: scanning, candidate generation, apply flow, headless CLI
- `cleanup_profiles.py`: active cleanup profile/config runtime boundary
- `archive_runtime.py`: active archive-management runtime boundary
- `archive_custody.py`: archive browsing, ranking, pruning, summaries
- `receipts.py` and `receipt_core/`: receipt pipeline
- `uninstaller.py`: installed-program detection, leftovers, force remove
- `registry_health.py`: conservative registry issue detection/repair
- `ledger.py`: activity feed and trust calculations
- `audit.py`: HTML proof/audit export
- `brand.py`: product identity and local data-dir migration
- `ui/`: reusable UI helpers, proof dashboard pieces, tray/window helpers

## Local Verification Performed

Commands run during this audit:

```powershell
python -m pytest -p no:xonsh tests/
python -m compileall main.py startup_manager_gui.py performance_engine.py receipt_core receipt_desktop ui
python -m ruff check .
```

Results:

- `pytest`: `366 passed`
- `compileall`: passed for requested modules
- `ruff`: clean under the current repo config

## Audit Findings

### Healthy / strong areas

- The desktop app path is broad and well-covered by tests.
- Receipt and proof workflows are more structured than a typical utility app.
- Archive-first behavior is a clear architectural theme across cleanup, uninstall leftovers, registry repair, and prune flows.
- The repo has CI (`.github/workflows/ci.yml`) for tests and public-surface checks.

### Important risks / cleanup debt

#### 1. Legacy "Smart Cleaner" modules are archived, but still compatibility-only

The following files reflect an older product direction that survived the Cleanroom rebrand:

- `dashboard.py`
- `smart_config.py`
- `smart_scheduler.py`
- `legacy/smart_cleaner/smart_scheduler.py`
- `archive_manager.py`
- `legacy/smart_cleaner/README_SMART.md`

Concerns:

- branding is still "Smart Cleaner" in several places
- the archived modules are not represented in the main test suite the way the Cleanroom path is
- they reference alternate config flows (`smart_config.yaml`, profile-based cleanup)
- they are no longer part of the primary supported runtime path

#### 2. `dashboard.py` likely has a broken delete path

`dashboard.py` used to call `archive_manager.apply_prune(...)` directly. The
active runtime now routes through `archive_runtime.py`, while
`archive_manager.py` remains a compatibility shim.

Future work should still treat the legacy web dashboard path cautiously, but it
is no longer part of the active runtime dependency chain.

#### 3. Release/status docs have some drift

Examples:

- `README.md` advertises latest release `v1.0.6`
- `docs/RELEASE-v1.0.7-rc1.md` exists with newer repo-state claims than the tagged GitHub release
- `HANDOFF.md` contains older milestone/test-count history mixed with still-useful architecture notes

The documentation is valuable, but future sessions should cross-check docs against code/tests before assuming a release claim is current.

## What Future ChatGPT Should Assume

Safe assumptions:

- the main product is **Cleanroom**, not Smart Cleaner
- the active app path is **Windows desktop GUI + CLI/headless support**
- receipt/proof/archive/restore behavior is central to the product
- `366` tests passing is a trustworthy current signal

Unsafe assumptions:

- that all docs are perfectly current
- that legacy smart modules are production-ready
- that release-candidate notes automatically reflect the current tree

## Recommended Next Steps

If the next task is maintenance/hardening, the highest-leverage steps are:

1. Reconcile release docs/status docs with actual current tagged release
2. Decide whether the legacy `dashboard.py` path should remain compatibility-only or be retired later
3. Keep future feature work centered on the tested Cleanroom path unless explicitly reviving the legacy smart modules

## Best Commands for Future Sessions

```powershell
python startup_manager_gui.py
python -m pytest -p no:xonsh tests/
python -m ruff check .
python main.py --headless-clean
```

## Bottom Line

This is a **real, fairly advanced Windows cleanup app** with strong testing around its current desktop/receipt/proof architecture. The main product path is healthy.

The biggest source of confusion is that the repo still carries an older "smart cleaner" branch of ideas and docs alongside the current Cleanroom code. Those materials are now archived or shimmed, and future work should treat them as **legacy or experimental until revalidated**.
