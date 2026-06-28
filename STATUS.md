# Project Status — smart_clean_tool

Last updated: 2026-06-26

## Current Focus

Performance engine integration is **complete**. The parallel, incremental scanner is now wired into the core CLI (`main.py`) and the GUI (`startup_manager_gui.py`), with user-facing controls and a benchmark/clear-cache workflow.

## Repo boundary

Cleanroom desktop GUI + CLI/headless remains the active supported product path.
Active runtime boundary modules now live at the repo root:

- `cleanup_profiles.py`
- `archive_runtime.py`

Legacy smart-cleaner implementation/docs are archived under
`legacy/smart_cleaner/`, while root `smart_config.py`, `archive_manager.py`,
and `smart_scheduler.py` remain compatibility shims.

## What was delivered

### 1. Performance engine (`performance_engine.py`)
- Parallel directory scanning with `ThreadPoolExecutor`
- SQLite-backed incremental scan state
- Memory-aware governor that pauses when RSS approaches the limit
- Memory-mapped hashing for large files
- Size-first duplicate detection
- `benchmark_scan()` for full-vs-incremental comparison
- `clear_scan_cache()` for resetting incremental state

### 2. Core integration (`main.py`)
- `scan_candidates_fast()` — fast path that respects the same candidate rules as the standard scanner, with per-folder skipping support
- `dedupe_candidates()` — uses `performance_engine.batch_hash_files()` for parallel hashing, with a sequential fallback
- CLI flag `--fast-scan`
- Config keys: `performance_scan`, `performance.max_workers`, `performance.memory_limit_mb`, `performance.incremental`

### 3. GUI integration (`startup_manager_gui.py`)
- Scan worker automatically uses `scan_candidates_fast()` when `performance_scan` is enabled
- New **Settings → Advanced → Performance scanner** card with:
  - Enable/disable toggle
  - `Max worker threads` spinbox (`0 = auto`)
  - `Memory limit (MB)` spinbox
  - `Incremental scan` toggle
  - Live status header showing `workers • memory • mode` and an `Enabled`/`Disabled` pill
  - **Run Benchmark…** button (background full vs. incremental benchmark)
  - **Clear Cache** button (resets `performance_cache`, `dedupe_cache`, `benchmark_cache`)
- All settings are saved to/loaded from `cleanup_config.yaml`

### 4. Tests
- `tests/test_performance_engine.py` — engine unit tests
- `tests/test_main.py` — fast scan, folder skipping, dedupe, and config round-trip tests
- **Total: 366 tests passing**

### 5. Documentation
- `docs/PERFORMANCE_ENGINE.md` — updated with GUI integration, benchmark, and cache-clear details
- `README.md` — test count updated to **366+**
- `CHANGELOG.md` — performance engine entries added
- `STATUS.md` — this file

## Files modified in this work

- `performance_engine.py`
- `main.py`
- `startup_manager_gui.py`
- `tests/test_performance_engine.py`
- `tests/test_main.py`
- `docs/PERFORMANCE_ENGINE.md`
- `README.md`
- `CHANGELOG.md`

## Audit results

| Check | Result |
|-------|--------|
| Full test suite | **366 passed** |
| `py_compile startup_manager_gui.py` | OK |
| `py_compile main.py` | OK |
| `py_compile performance_engine.py` | OK |
| `ruff check main.py startup_manager_gui.py performance_engine.py tests/test_main.py tests/test_performance_engine.py` | **All checks passed** |

No regressions detected in the existing test suite.

## Audit findings

- Fixed several pre-existing ruff warnings in `startup_manager_gui.py`:
  - Removed unused local variables (`measured`, `written_to`, `total`, `has_path`).
  - Renamed ambiguous `l` list-comprehension variable to `line`.
  - Auto-fixed whitespace and formatting issues.
- The remaining ruff warnings across the rest of the codebase are primarily pre-existing unused imports (`F401`) and do not affect the performance engine integration.

## Where the project stands

- The performance engine is fully integrated end-to-end.
- The GUI exposes all major performance controls without requiring manual YAML edits.
- Cache management is available for troubleshooting incremental state issues.
- Documentation and changelog are current.

## Potential next steps

- Add a `--benchmark` CLI command that reuses the same benchmark logic as the GUI.
- Expose benchmark results as a saved receipt or HTML proof pack.
- Add telemetry/logging for scan performance metrics (optional, respecting the existing local-only policy).
- Consider moving `STATUS.md` content into a wiki or release notes once the next version is tagged.
