# Cleanroom Project Audit for Future ChatGPT Sessions

Last updated: 2026-06-27
Workspace: `C:\Users\KickA\smart_clean_tool`

## Executive Summary

This repository is primarily a **Windows desktop app called Cleanroom**: a local-only, archive-first cleanup utility with proof/receipt workflows, restore support, archive custody checks, and a large Tk/CustomTkinter GUI.

The **active, well-tested product surface is the Cleanroom desktop path**, not the older "Smart Cleaner" web/scheduler experiment. The current codebase is in a good functional state:

- `366` tests pass locally with `python -m pytest -p no:xonsh tests/`
- core modules compile successfully
- packaging/build scripts and release docs are present

The repo also contains **legacy or partially integrated smart-clean modules** (`dashboard.py`, `smart_config.py`, `smart_scheduler.py`, `archive_manager.py`, `README_SMART.md`). These are useful context, but they should not be assumed production-ready without additional validation.

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
- `ruff`: initially failed with `66` findings; after targeted cleanup in audited modules it is down to `61`

## Audit Findings

### Healthy / strong areas

- The desktop app path is broad and well-covered by tests.
- Receipt and proof workflows are more structured than a typical utility app.
- Archive-first behavior is a clear architectural theme across cleanup, uninstall leftovers, registry repair, and prune flows.
- The repo has CI (`.github/workflows/ci.yml`) for tests and public-surface checks.

### Important risks / cleanup debt

#### 1. Lint status does not match release messaging

`docs/RELEASE-v1.0.7-rc1.md` says `ruff clean`, but the current local `ruff check .` still reports `61` findings after targeted cleanup.

Most are maintainability issues rather than obvious runtime breakage, but future work should treat the repo as **test-clean, not lint-clean**.

#### 2. `enable_telemetry.py` is malformed / merged together

`enable_telemetry.py` currently contains two different implementations concatenated into one file:

- a JSON-based local opt-in helper at the top
- a second CLI/YAML-editing script appended below

This causes `ruff` errors (`E402`, `F811`) and makes the module confusing to maintain. Tests still pass, so this is likely hidden by limited usage rather than being truly clean.

#### 3. Legacy "Smart Cleaner" modules are still present and appear partially stale

The following files look like an older product direction that survived the Cleanroom rebrand:

- `dashboard.py`
- `smart_config.py`
- `smart_scheduler.py`
- `archive_manager.py`
- `README_SMART.md`

Concerns:

- branding is still "Smart Cleaner" in several places
- these modules are not represented in the main test suite the way the Cleanroom path is
- they reference alternate config flows (`smart_config.yaml`, profile-based cleanup)
- they appear only loosely integrated with the current desktop-first product

#### 4. `dashboard.py` likely has a broken delete path

`dashboard.py` calls `archive_manager.apply_prune(...)`, but `archive_manager.py` does not define a module-level `apply_prune` function. It uses `archive_custody.apply_prune(...)` internally instead.

That strongly suggests the dashboard archive-delete API is broken unless another indirection is added later.

#### 5. Release/status docs have some drift

Examples:

- `README.md` advertises latest release `v1.0.6`
- `docs/RELEASE-v1.0.7-rc1.md` exists with newer claims
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
- that the repo is lint-clean
- that release-candidate notes automatically reflect the current tree

## Recommended Next Steps

If the next task is maintenance/hardening, the highest-leverage steps are:

1. Split/fix `enable_telemetry.py`
2. Decide whether `dashboard.py` / `smart_*` modules are supported or should be retired
3. Add CI linting if lint cleanliness matters
4. Reconcile release docs/status docs with actual current state
5. Keep future feature work centered on the tested Cleanroom path unless explicitly reviving the legacy smart modules

## Best Commands for Future Sessions

```powershell
python startup_manager_gui.py
python -m pytest -p no:xonsh tests/
python -m ruff check .
python main.py --headless-clean
```

## Bottom Line

This is a **real, fairly advanced Windows cleanup app** with strong testing around its current desktop/receipt/proof architecture. The main product path is healthy.

The biggest source of confusion is that the repo still carries an older "smart cleaner" branch of ideas and docs alongside the current Cleanroom code. Future work should treat those files as **legacy or experimental until revalidated**.
