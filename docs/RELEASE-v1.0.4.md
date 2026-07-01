**Cleanroom is a local-only Windows cleanup utility that archives first, proves every action, and lets you restore before anything is permanently pruned.**

This is not a fake "1,247 issues fixed" optimizer. Cleanroom produces receipts, custody checks, activity ledgers, proof packs, and restore paths — all on your PC, with no cloud account or telemetry.

**v1.0.4** ships post-v1.0.3 Windows shell UX: responsive layout, notification-area tray, Cleanroom-owned receipt file type, and installer file association. Built and published by CI from tag `v1.0.4`.

## Screenshots (proof-loop UI)

![Cleanroom Review](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.4/cleanroom-review.png)

![Cleanroom Activity Ledger](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.4/cleanroom-activity-ledger.png)

![Cleanroom Proof Pack — custody evidence](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.4/cleanroom-proof-pack-demo.png)

## Highlights

- **Responsive layout fix** — important controls stay visible at common window sizes and 150% scaling
- **Windows tray icon** — Open Cleanroom, Hide to tray, Show, Latest Receipt, Proof Pack, Quit
- **`.cleanroom-receipt` file type** — new receipts use a Cleanroom-owned extension; content stays plain-text
- **Double-click receipt flow** — `.cleanroom-receipt` opens the in-app Cleanroom receipt viewer
- **Legacy `.txt` receipts** — older receipt files remain readable
- **Installer file association** — registers and uninstalls `.cleanroom-receipt` association cleanly
- Archive-first cleanup, custody trust, Cleanroom Rewind — unchanged doctrine

## Downloads

- `Cleanroom-Setup-1.0.4.exe`
- `SHA256SUMS.txt`

## Verification

Check the installer hash before running:

```powershell
Get-FileHash .\Cleanroom-Setup-1.0.4.exe -Algorithm SHA256
```

Compare against `SHA256SUMS.txt` from this release.

## Verify provenance

Release artifacts are built by GitHub Actions and include artifact attestations:

```powershell
gh attestation verify .\Cleanroom-Setup-1.0.4.exe --repo lazelife420-spec/cleanroom-windows
```
