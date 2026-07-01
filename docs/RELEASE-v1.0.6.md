**Cleanroom is a local-only Windows cleanup utility that archives first, proves every action, and lets you restore before anything is permanently pruned.**

Cleanroom is a Proof Foundry product.

**Product by The Proof Foundry™.** Build it. Prove it. Ship it.

**v1.0.6** is a small branding patch for the v1.0.5 proof surface. It adds official The Proof Foundry™ attribution across public docs, in-app surfaces, receipt surfaces, and installer metadata without changing cleanup behavior.

## Screenshots

![Cleanroom Review](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.6/cleanroom-review.png)

![Cleanroom Activity Ledger](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.6/cleanroom-activity-ledger.png)

![Cleanroom Proof Pack — custody evidence](https://github.com/lazelife420-spec/cleanroom-windows/releases/download/v1.0.6/cleanroom-proof-pack-demo.png)

## Highlights

- **The Proof Foundry™ branding** — public docs, first-run splash, app footer, and installer metadata identify Cleanroom as a Proof Foundry product.
- **Receipt attribution** — generated cleanup/prune/migration receipts and receipt viewers include `Product by The Proof Foundry™`.
- **Proof Pack footer** — exported proof packs include the Proof Foundry product line and `Build it. Prove it. Ship it.`
- **No behavior changes** — archive-first cleanup, receipts, custody trust, restore, tray, and `.cleanroom-receipt` behavior are unchanged from v1.0.5.

## Downloads

- `Cleanroom-Setup-1.0.6.exe`
- `SHA256SUMS.txt`

## Verification

Check the installer hash before running:

```powershell
Get-FileHash .\Cleanroom-Setup-1.0.6.exe -Algorithm SHA256
```

Compare against `SHA256SUMS.txt` from this release.

## Verify provenance

Release artifacts are built by GitHub Actions and include artifact attestations:

```powershell
gh attestation verify .\Cleanroom-Setup-1.0.6.exe --repo lazelife420-spec/cleanroom-windows
```
