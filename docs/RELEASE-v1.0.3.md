Cleanroom is a Windows cleaner that archives first, proves every action, and lets you roll back.

This is not a fake "1,247 issues fixed" optimizer. Cleanroom produces receipts, custody checks, activity ledgers, proof packs, and restore paths.

**v1.0.3** ships archive browser + in-app receipts, archive prune proof, Proof Pack trust-score honesty, and local-only uninstaller guidance with a safer Force Remove flow — built and published by CI from tag `v1.0.3`.

## Screenshots (proof-loop UI)

![Cleanroom Review](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.3/cleanroom-review.png)

![Cleanroom Activity Ledger](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.3/cleanroom-activity-ledger.png)

![Cleanroom Proof Pack — custody evidence](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.3/cleanroom-proof-pack-demo.png)

## Highlights

- **Archive Browser** — browse archived artifacts in-app with custody status
- **In-app receipts** — view, copy, and open cleanup/prune receipts without leaving the app
- **Archive prune receipts** — custody-only prune with tiered recommendations and prune proof
- **Proof Pack trust score** — never shows `100/100` when any archived artifact is missing
- **Uninstaller guidance** — local-only program advice (no cloud lookup)
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
gh attestation verify .\Cleanroom-Setup-1.0.3.exe --repo Z3r0DayZion-install/cleanroom-windows
```
