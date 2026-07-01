Cleanroom is a Windows cleaner that archives first, proves every action, and lets you roll back.

This is not a fake "1,247 issues fixed" optimizer. Cleanroom produces receipts, custody checks, activity ledgers, proof packs, and restore paths.

**v1.0.2** ships CustomTkinter UI polish (local-only), receipt printing animation, and per-user install config — built and published by CI from tag `v1.0.2`.

## Screenshots (proof-loop UI)

![Cleanroom Review](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.2/cleanroom-review.png)

![Cleanroom Activity Ledger](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.2/cleanroom-activity-ledger.png)

![Cleanroom Proof Pack — custody evidence](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.2/cleanroom-proof-pack-demo.png)

## Highlights

- CustomTkinter shell: header, sidebar, proof-flow bar, custody hero, archive-first banner
- Local-only notice in Settings (no cloud, account, or telemetry)
- Receipt printing animation after real proof moments (Preview Receipt, Archive & Clean, Proof Pack)
- Proof Output panel on Review tab
- Per-user `cleanup_config.yaml` on first installed run (no dev-path leakage)
- PyInstaller bundles CustomTkinter themes (`_internal/customtkinter`)
- Sandbox manual gate scripts for isolated install verification
- Archive-first cleanup, receipts, custody trust, Proof Pack — unchanged doctrine

## Downloads

- `Cleanroom-Setup-1.0.2.exe`
- `SHA256SUMS.txt`

## Verification

Check the installer hash before running:

```powershell
Get-FileHash .\Cleanroom-Setup-1.0.2.exe -Algorithm SHA256
```

Compare against `SHA256SUMS.txt` from this release.

## Verify provenance

Release artifacts are built by GitHub Actions and include artifact attestations:

```powershell
gh attestation verify .\Cleanroom-Setup-1.0.2.exe --repo lazelife420-spec/cleanroom-windows
```
