**Cleanroom is a local-only Windows cleanup utility that archives first, proves every action, and lets you restore before anything is permanently pruned.**

This is not a fake "1,247 issues fixed" optimizer. Cleanroom produces receipts, custody checks, activity ledgers, proof packs, and restore paths — all on your PC, with no cloud account or telemetry.

**v1.0.5** ships proof dashboard consolidation: scan lifecycle polish, R.E.C.E.I.P.T. receipt identity, archive custody truth fixes, context menus, and the optional Cleanroom → RECEIPT bridge. Built from `main` after PR #22 and PR #27 merge.

## Screenshots (proof-loop UI)

![Cleanroom Review](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.5/cleanroom-review.png)

![Cleanroom Activity Ledger](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.5/cleanroom-activity-ledger.png)

![Cleanroom Proof Pack — custody evidence](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.5/cleanroom-proof-pack-demo.png)

## Highlights

- **Proof dashboard consolidation** — Home, Cleaner, Archive, Proof Ledger with consistent hierarchy and CTAs
- **R.E.C.E.I.P.T. receipt identity** — Structured receipt modal with Preview / Archive Complete badges
- **Scan lifecycle polish** — Progress ring, Stop Scan, rescan reset, receipt-ready gating
- **Archive custody truth** — Loading states, footer truthfulness, action gating until records load
- **Context menus** — Home, Cleaner, Archive, Proof Ledger row actions with precondition guards
- **Force Remove guardrails** — Confirmation and eligibility before orphaned-entry removal
- **Open in RECEIPT** — Optional hand-off from Cleanroom receipt viewer to RECEIPT app (PR #27)
- Archive-first cleanup, custody trust, tray, `.cleanroom-receipt` — unchanged doctrine

## Downloads

- `Cleanroom-Setup-1.0.5.exe`
- `SHA256SUMS.txt`

## Verification

Check the installer hash before running:

```powershell
Get-FileHash .\Cleanroom-Setup-1.0.5.exe -Algorithm SHA256
```

Compare against `SHA256SUMS.txt` from this release.

## Verify provenance

Release artifacts are built by GitHub Actions and include artifact attestations:

```powershell
gh attestation verify .\Cleanroom-Setup-1.0.5.exe --repo Z3r0DayZion-install/cleanroom-windows
```
