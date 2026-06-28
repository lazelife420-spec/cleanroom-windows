# Legacy Smart-Cleaner Dependency Audit

Last updated: 2026-06-28  
Audit branch: `audit/legacy-smart-cleaner-dependencies`  
Base commit: `9cfc482`

Historical note: this audit captured the repo state before runtime decoupling
and legacy archival. The follow-up sequence has since completed: active runtime
imports now point at `cleanup_profiles.py` / `archive_runtime.py`, and the
legacy scheduler/docs surface has moved under `legacy/smart_cleaner/`.

## Goal

Identify every remaining reference to the legacy smart-cleaner modules before
the archive/move sequence, and separate harmless documentation mentions from
active runtime dependencies.

Scope audited:

- `smart_config`
- `smart_scheduler`
- `dashboard`
- `archive_manager`
- `README_SMART`
- `smart_config.yaml`
- `legacy.smart_cleaner`
- `smart_cleaner`

## Summary

At the time of this audit, the legacy smart-cleaner surface was **not
archive-safe yet**.

There were still active runtime imports in the shipping tree:

- `main.py` imports `smart_config`
- `main.py` imports `archive_manager`
- `dashboard.py` imports `archive_manager`

There are **no direct test references** to the smart-cleaner modules, and this
audit found **no direct CI, packaging, installer, or release-script references**
to those module names.

## Runtime Imports

These references required code changes before any file move:

- [main.py](C:/Users/KickA/smart_clean_tool/main.py):747 imports `smart_config`
  for profile-based cleanup flow
- [main.py](C:/Users/KickA/smart_clean_tool/main.py):797 imports
  `archive_manager` for `--archive` summary/browse/manage CLI flows
- [dashboard.py](C:/Users/KickA/smart_clean_tool/dashboard.py):97 calls into
  `archive_manager.apply_prune(...)`
- [dashboard.py](C:/Users/KickA/smart_clean_tool/dashboard.py):560 imports
  `archive_manager` for archive summary and browsing
- [archive_manager.py](C:/Users/KickA/smart_clean_tool/archive_manager.py):12
  is a compatibility wrapper, which confirms there are still legacy callers

## Docs-Only References

These appear informational and would not block runtime if updated later:

- [docs/CHATGPT_PROJECT_AUDIT.md](C:/Users/KickA/smart_clean_tool/docs/CHATGPT_PROJECT_AUDIT.md)
  describes the legacy modules and their risks
- [README_SMART.md](C:/Users/KickA/smart_clean_tool/legacy/smart_cleaner/README_SMART.md)
  is the legacy product README and references `dashboard.py`, `smart_config.py`,
  `smart_scheduler.py`, and `smart_config.yaml`

Notes:

- Most `README.md`, release-note, and UI "dashboard" hits are about the
  current Cleanroom proof dashboard, not the legacy `dashboard.py` web app.
- At the time of the original dependency audit, `legacy.smart_cleaner` had no hits.

## Tests / Packaging / CI / Release Tooling

### Tests

- No direct references found under `tests/`

### CI

- [.github/workflows/ci.yml](C:/Users/KickA/smart_clean_tool/.github/workflows/ci.yml)
  does not reference the legacy smart-cleaner modules directly

### Release-surface checks

- [scripts/verify_release_surface.py](C:/Users/KickA/smart_clean_tool/scripts/verify_release_surface.py)
  does not import or require the legacy smart-cleaner modules directly

### Packaging / installer / scripts

- No direct references found in `.ps1`, `.iss`, or `.spec` files during this audit

## Recommended Move / Archive Plan

This recommendation has now been carried out in later PRs.

Recommended sequence:

1. Remove or replace the active `main.py` imports for `smart_config` and
   `archive_manager`. Completed.
2. Decide whether the legacy web dashboard is supported at all. If not,
   explicitly retire its CLI/docs path before moving it. Still open.
3. Once runtime imports are gone, re-run this audit and confirm the remaining
   references are docs-only. Completed in follow-up cleanup work.
4. Only then move the legacy smart-cleaner files into `legacy/` in a separate,
   no-behavior-change PR. Completed.

## Commands Used

```powershell
rg -n "smart_config" .
rg -n "smart_scheduler" .
rg -n "\bdashboard\b" .
rg -n "archive_manager" .
rg -n "README_SMART" .
rg -n "smart_config\.yaml" .
rg -n "legacy\.smart_cleaner" .
rg -n "smart_cleaner" .
rg -n -g "*.py" "import smart_config|from smart_config|import smart_scheduler|from smart_scheduler|import dashboard|from dashboard|import archive_manager|from archive_manager|from legacy\.smart_cleaner|import legacy\.smart_cleaner|smart_cleaner\." .
rg -n "smart_config|smart_scheduler|dashboard|archive_manager|README_SMART|smart_config\.yaml|legacy\.smart_cleaner|smart_cleaner" tests
python -m ruff check .
python -m pytest -p no:xonsh tests/
python scripts/verify_release_surface.py
```
