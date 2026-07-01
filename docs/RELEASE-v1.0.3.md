**Cleanroom is a local-only Windows cleanup utility that archives first, proves every action, and lets you restore before anything is permanently pruned.**

This is not a fake "1,247 issues fixed" optimizer. Cleanroom produces receipts, custody checks, activity ledgers, proof packs, and restore paths — all on your PC, with no cloud account or telemetry.

**v1.0.3** ships the proof surface that matches the engine: in-app receipts, Archive Browser, archive-only prune receipts, honest Proof Pack trust scores, local program guidance, and a safer Force Remove flow. Built and published by CI from tag `v1.0.3`.

## Screenshots (proof-loop UI)

![Cleanroom Review](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.3/cleanroom-review.png)

![Cleanroom Activity Ledger](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.3/cleanroom-activity-ledger.png)

![Cleanroom Proof Pack — custody evidence](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.3/cleanroom-proof-pack-demo.png)

## Highlights

- **In-app receipts** — view, copy, and open cleanup/prune receipts without leaving the app
- **Archive Browser** — browse archived artifacts with custody status in the Activity tab
- **Archive-only prune receipts** — tiered recommendations with prune proof; nothing silently deleted
- **Proof Pack trust-score honesty** — never shows `100/100` when any archived artifact is missing
- **Local-only program guidance** — uninstall advice from local heuristics, no cloud lookup
- **Safer Force Remove** — preview targets, confirmation required, registry export before delete, install folders archived before removal
- Archive-first cleanup, custody trust, Cleanroom Rewind — unchanged doctrine

## Downloads

- `Cleanroom-Setup-1.0.3.exe`
- `SHA256SUMS.txt`

## Verification

Check the installer hash before running:

```powershell
Get-FileHash .\Cleanroom-Setup-1.0.3.exe -Algorithm SHA256
```

Compare against `SHA256SUMS.txt` from this release.

## Verify provenance

Release artifacts are built by GitHub Actions and include artifact attestations:

```powershell
gh attestation verify .\Cleanroom-Setup-1.0.3.exe --repo lazelife420-spec/cleanroom-windows
```
