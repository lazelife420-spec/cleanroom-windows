# Cleanroom Unlock Checklist — v1.0.6

**Date:** 2026-07-01  
**Audited by:** Kiro automated unlock checklist  
**Final Verdict: GREEN**

---

## Repo

| Field         | Value                                    |
|---------------|------------------------------------------|
| nameWithOwner | lazelife420-spec/cleanroom-windows       |
| Tag           | v1.0.6                                   |
| Release name  | Cleanroom v1.0.6 — Proof-first Windows cleanup with rollback |
| Tag commit    | 6d20c61c2e7b30c91048306d59adc8c4ed737a59 |
| Release created by | GitHub Actions CI (release.yml)    |

---

## Checklist Steps

### 1. Authenticated gh release view
```
gh release view v1.0.6 --repo lazelife420-spec/cleanroom-windows --json tagName,name,assets
```
Result: Release found. Tag v1.0.6. ✓

### 2. Asset confirmation

| Asset                        | Present | Size       | Content-Type              |
|------------------------------|---------|------------|---------------------------|
| Cleanroom-Setup-1.0.6.exe    | ✓       | 16,435,865 bytes (15.7 MB) | application/x-msdownload |
| SHA256SUMS.txt               | ✓       | 231 bytes  | text/plain                |
| cleanroom-review.png         | ✓       | 160,945 bytes | image/png              |
| cleanroom-activity-ledger.png | ✓      | 176,034 bytes | image/png              |
| cleanroom-proof-pack-demo.png | ✓      | 44,179 bytes  | image/png              |
| cleanroom-proof-pack-demo.html | ✓     | 4,599 bytes   | text/html              |

Both required artifacts present. ✓

### 3. URLs resolved by gh
URLs sourced exclusively from `gh release download` (authenticated). No URLs guessed or invented.

### 4. Installer download
```
gh release download v1.0.6 --repo lazelife420-spec/cleanroom-windows
  --pattern "Cleanroom-Setup-1.0.6.exe"
  --dir %TEMP%\cleanroom_unlock_106
```
Download: SUCCESS ✓  
File size on disk: 16,435,865 bytes ✓

### 5. SHA256SUMS.txt download and content
```
gh release download v1.0.6 --repo lazelife420-spec/cleanroom-windows
  --pattern "SHA256SUMS.txt"
  --dir %TEMP%\cleanroom_unlock_106
```
Download: SUCCESS ✓

SHA256SUMS.txt content:
```
# Cleanroom v1.0.6 release checksums (SHA256)
56DCBFD13E7D9814921C4651BF13B61A18D0FAECE8F5EA3CA8CE55C067FEFED5  Cleanroom-Setup-1.0.6.exe
1B0416F272A8223CA6B2FA64CF1555ADE293C0DBA40117F38D75ABBFA08762B8  Cleanroom/Cleanroom.exe
```

Entry for `Cleanroom-Setup-1.0.6.exe`: 64-character SHA256 present ✓

### 6. Installer SHA256 computation
```powershell
(Get-FileHash "Cleanroom-Setup-1.0.6.exe" -Algorithm SHA256).Hash
```

### 7. Hash comparison

| | Value |
|---|---|
| Expected (SHA256SUMS.txt) | `56DCBFD13E7D9814921C4651BF13B61A18D0FAECE8F5EA3CA8CE55C067FEFED5` |
| Computed (downloaded file) | `56DCBFD13E7D9814921C4651BF13B61A18D0FAECE8F5EA3CA8CE55C067FEFED5` |
| Match | **YES ✓** |

### 8. CI workflow result
Release workflow (release.yml) completed: ✓ PASSED (2m 21s)  
CI workflow (ci.yml) completed: ✓ PASSED  
Artifact provenance attested via actions/attest-build-provenance@v4 ✓

---

## Pre-publish history note

The original local tag v1.0.6 pointed to commit f8ab8c8 (2026-06-23, PR #35 branding merge).
That tag was stale — it predated the repo-account correction commits (Z3r0DayZion-install → lazelife420-spec),
security hardening, dependency bumps, and action version updates. Pushing f8ab8c8 would have caused
the CI release surface check to fail. The local tag was deleted and retagged at HEAD 6d20c61 with
explicit user approval before pushing.

---

## Constraints observed

- ✓ No URLs guessed — all downloads via authenticated `gh release download`
- ✓ No Proof Foundry /proof updated
- ✓ No landing pages updated
- ✓ No manual asset uploads — all artifacts built and published by CI
- ✓ Cache Vault rc4 not touched
- ✓ No infrastructure changes

---

## Final Verdict

**GREEN**

All 8 checklist steps passed:
- ✓ GitHub Release v1.0.6 exists (CI-published)
- ✓ Cleanroom-Setup-1.0.6.exe asset present (15.7 MB)
- ✓ SHA256SUMS.txt asset present with 64-char hash
- ✓ Installer download successful
- ✓ SHA256SUMS.txt download successful
- ✓ SHA256 computed from downloaded installer
- ✓ Hash matches SHA256SUMS.txt exactly
- ✓ Release built and attested by GitHub Actions CI

**Cleanroom v1.0.6 is eligible to move from AMBER / verification_pending to GREEN.**

Next step (requires separate user approval): update Proof Foundry /proof to reflect Cleanroom v1.0.6.
