# Cleanroom v1.0.7-rc1

**Build date:** 2026-06-26  
**Commit:** e450eb2  
**SHA-256:** 5027631E14F272E5ACA83898F6FB208A4A29764E7DB8E291DDF49B750CEA2A59

Cleanroom remains an **archive-first, proof-loop** Windows cleanup utility:
it moves before it deletes, records receipts for every action, and keeps
restore/custody flows honest.

This release candidate reflects the current repo state: `366` tests passing,
`python -m ruff check .` clean under the current repo config, and the
Cleanroom desktop GUI + CLI/headless flow as the active supported product path.

## Highlights
- Parallel incremental scanner (performance engine)
- Telemetry shim repaired and repo lint cleaned under the current configuration
- Legacy smart-clean modules remain present, but they are not the primary supported surface
- 366 tests passing, ruff clean

![Cleanroom Review](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.6/cleanroom-review.png)

## Smoke proof
Packaged smoke script: PASS (first-run, archive, receipt, clean exit)

> Status: final release-candidate docs; prior "ruff debt" messaging has been removed
> to match the current repo state.
