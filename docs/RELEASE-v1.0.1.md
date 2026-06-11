Cleanroom is a Windows cleaner that archives first, proves every action, and lets you roll back.

This is not a fake "1,247 issues fixed" optimizer. Cleanroom produces receipts, custody checks, activity ledgers, proof packs, and restore paths.

**v1.0.1** is the first fully CI-built release: built from tag, checksummed, screenshot-validated, and provenance-attested by GitHub Actions.

## Screenshots (proof-loop UI)

![Cleanroom Review](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.1/cleanroom-review.png)

![Cleanroom Activity Ledger](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.1/cleanroom-activity-ledger.png)

![Cleanroom Proof Pack — CUSTODY VERIFIED 100/100](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.1/cleanroom-proof-pack-demo.png)

## Highlights

- Archive-first cleanup
- Preview Receipt before action
- Cleanroom Receipt after action
- Custody Trust Score with evidence drilldown
- Cleanroom Activity Ledger
- Cleanroom Rewind restore path
- Proof Pack HTML export
- Legacy data migration receipt (one-time upgrade path)
- CI-built installer with SHA256 checksums and artifact attestations
- 135+ tests passing

## Downloads

- `Cleanroom-Setup-1.0.1.exe`
- `SHA256SUMS.txt`

## Verification

Check the installer hash before running:

```powershell
Get-FileHash .\Cleanroom-Setup-1.0.1.exe -Algorithm SHA256
```

Compare against `SHA256SUMS.txt` from this release.

## Verify provenance

Release artifacts are built by GitHub Actions and include artifact attestations:

```powershell
gh attestation verify .\Cleanroom-Setup-1.0.1.exe --repo Z3r0DayZion-install/cleanroom-windows
```
