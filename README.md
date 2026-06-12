# Cleanroom

<p align="center">
  <img src="assets/brand/cleanroom-logo.png" alt="Cleanroom — Clean safely. Prove everything. Undo anytime." width="640">
</p>

A Windows cleaner that archives first, proves every action, and lets you roll back.

Cleanroom is not a fake "1,247 issues fixed" optimizer. It is a proof-first cleanup tool: every action is archived, measured, recorded, and reversible.

> **Cleanroom is the anti-CCleaner: archive-first cleanup with receipts, custody checks, and rollback.**

**Clean safely. Prove everything. Undo anytime.**

Repository: [`cleanroom-windows`](https://github.com/Z3r0DayZion-install/cleanroom-windows)

![Cleanroom Review](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.3/cleanroom-review.png)

![Cleanroom Activity Ledger](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.3/cleanroom-activity-ledger.png)

![Cleanroom Proof Pack Demo](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases/download/v1.0.3/cleanroom-proof-pack-demo.png)

---

## Why Cleanroom exists

| Typical optimizers | Cleanroom |
|--------------------|-----------|
| "Fixed 1,247 registry errors!" | Shows exact paths and registry keys |
| Deletes permanently | **Archives** to Cleanroom Archive |
| No undo | **Cleanroom Rewind** — roll back a whole day |
| Fake "space freed" totals | **OS-measured** free-space before/after |
| Scare tactics | **Custody Trust Score** — verify artifacts on disk |
| Closed source, bundled junk | Open source, **132+ tests**, local-only |

---

## Product line

| Feature | What it does |
|---------|----------------|
| **Cleanroom** | Main app — review, cleaner, uninstaller, startup, registry snapshot |
| **Cleanroom Receipt** | Itemized proof after every cleanup |
| **Cleanroom Archive** | Where moved files and `.reg` exports live |
| **Cleanroom Rewind** | Undo an entire day of actions |
| **Custody Trust Score** | 0–100 — % of archived artifacts verified on disk |
| **Proof Pack (HTML)** | Shareable audit report for your full history |

For README and launch screenshots, open the bundled demo Proof Pack (100% custody verified — not a gaps-detected example):

[`docs/demo/cleanroom-proof-pack-demo.html`](docs/demo/cleanroom-proof-pack-demo.html)

Launch screenshots live in [`assets/screenshots/`](assets/screenshots/).

---

## Quick start

```powershell
python -m pip install -r requirements.txt
python startup_manager_gui.py
```

### Tests

```powershell
python -m pytest -p no:xonsh tests/
```

### Build

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
powershell -ExecutionPolicy Bypass -File build_installer.ps1
# -> dist\Cleanroom\Cleanroom.exe
# -> dist\Cleanroom-Setup-1.0.3.exe
```

### Verify provenance

Release artifacts are built by GitHub Actions and include artifact attestations. After downloading `Cleanroom-Setup-1.0.3.exe` from [Releases](https://github.com/Z3r0DayZion-install/cleanroom-windows/releases):

```powershell
gh attestation verify .\Cleanroom-Setup-1.0.3.exe --repo Z3r0DayZion-install/cleanroom-windows
```

Compare the SHA256 hash against `SHA256SUMS.txt` attached to the same release.

### Headless (scheduled)

```powershell
Cleanroom.exe --headless-clean
```

---

## Data locations

All local under `%LOCALAPPDATA%\Cleanroom\`.

Upgrading from Smart Clean? On first launch, Cleanroom copies `%LOCALAPPDATA%\SmartClean\` → `Cleanroom\`, leaves SmartClean as backup, and writes a **Cleanroom Migration Receipt** (`migration_receipt.txt`).

| Path | Purpose |
|------|---------|
| `cleanup_log.json` | Master action log |
| `receipts/` | Cleanroom Receipts |
| `audits/` | Proof Pack HTML exports |
| `disk_history.json` | Disk Foresight snapshots |
| `ui_prefs.json` | Theme + power-user prefs |

---

## Architecture

```
brand.py                 # Product identity + data paths
startup_manager_gui.py   # Tkinter GUI
proof.py                 # OS measurement + custody checks
ledger.py                # Activity feed + trust score
audit.py                 # Proof Pack HTML export
receipts.py              # Cleanroom Receipts
foresight.py             # Disk-full prediction
timeline.py              # Cleanroom Rewind day buckets
uninstaller.py           # Programs list, leftovers, force remove
registry_health.py       # Evidence-based registry repair
```

---

## License

MIT — see [LICENSE](LICENSE).
