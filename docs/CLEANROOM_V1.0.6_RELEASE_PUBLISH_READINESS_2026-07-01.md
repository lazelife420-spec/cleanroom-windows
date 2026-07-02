# Cleanroom v1.0.6 — Release Publish Readiness Receipt

**Date:** 2026-07-01  
**Audited by:** Kiro automated readiness audit  
**Status:** READY_TO_PUBLISH

---

## Repo

| Field            | Value                                      |
|------------------|--------------------------------------------|
| nameWithOwner    | lazelife420-spec/cleanroom-windows         |
| Branch           | main                                       |
| HEAD commit      | 6d20c61c2e7b30c91048306d59adc8c4ed737a59   |
| Commit message   | fix: correct public repo account to lazelife420-spec everywhere (#20) |
| Working tree     | clean — nothing to commit                  |
| Tag to create    | v1.0.6                                     |

---

## Version Truth

| Source           | Version | Match |
|------------------|---------|-------|
| brand.py         | 1.0.6   | ✓     |
| installer.iss    | 1.0.6   | ✓     |
| SHA256SUMS.txt   | v1.0.6  | ✓     |
| CHANGELOG.md     | v1.0.6  | ✓     |
| docs/RELEASE-v1.0.6.md | present | ✓ |

No stale v1.0.4 or v1.0.5 public-current claims found.

---

## Release Workflow

| Field                  | Value                                                |
|------------------------|------------------------------------------------------|
| Workflow file          | .github/workflows/release.yml                        |
| Trigger                | push tag matching `v*`                               |
| Expected tag format    | v1.0.6                                               |
| Build env              | windows-latest (GitHub Actions)                      |
| Test gate              | python -m pytest tests/ -p no:xonsh -q               |
| Installer builder      | Inno Setup via build_installer.ps1                   |
| SHA256SUMS generator   | scripts/generate_sha256sums.py                       |
| Attestation            | actions/attest-build-provenance@v4                   |
| Release publisher      | gh release create (CI token)                         |

Expected release artifacts:
- `dist/Cleanroom-Setup-1.0.6.exe`
- `SHA256SUMS.txt`
- `assets/screenshots/cleanroom-review.png`
- `assets/screenshots/cleanroom-activity-ledger.png`
- `assets/screenshots/cleanroom-proof-pack-demo.png`
- `docs/demo/cleanroom-proof-pack-demo.html`

---

## SHA256SUMS.txt (repo root — recorded from prior CI build)

```
# Cleanroom v1.0.6 release checksums (SHA256)
B947C52312D032186FF487C7FA063F9A9EDDA0E27445734469405A3AAF94340C  Cleanroom-Setup-1.0.6.exe
1C8FB143A0BC0C7B9A5C8BBF3F08071C481058459F63CBD9F4946D8FBE209311  Cleanroom/Cleanroom.exe
```

Expected SHA256 for installer: `B947C52312D032186FF487C7FA063F9A9EDDA0E27445734469405A3AAF94340C`

Note: SHA256SUMS.txt exists in the repo but `dist/` does not exist on this machine.
The release workflow is CI-driven. Pushing `v1.0.6` tag triggers GitHub Actions to build,
compute SHA256, and publish. Local build not attempted — a local build would produce a
different binary hash (different build environment) and would not match the recorded checksum.
The authoritative hash will be produced and attested by CI.

---

## Local Artifact State

| Artifact                        | Present locally | Notes                          |
|---------------------------------|-----------------|--------------------------------|
| dist/Cleanroom-Setup-1.0.6.exe  | NO              | Built by CI on tag push        |
| SHA256SUMS.txt (repo root)      | YES             | Contains 64-char hash          |
| dist/Cleanroom/Cleanroom.exe    | NO              | Built by CI on tag push        |

---

## Test Results

| Command                                         | Result           |
|-------------------------------------------------|------------------|
| python -m pytest tests/ -p no:xonsh -q          | 366 passed ✓     |
| python scripts/verify_release_surface.py --tag v1.0.6 | PASSED ✓  |

### verify_release_surface.py output

```
OK: Brand/public surface scan passed
OK: Public docs clean (no forbidden terms, no raw screenshot URLs)
OK: Release docs scan passed (8 file(s))
OK: Screenshot assets and demo Proof Pack present
OK: Forbidden UI label scan passed
OK: Tag v1.0.6 alignment verified (brand, docs, README, checksums)

Release surface verification PASSED
```

---

## Build Tool Availability (local)

| Tool              | Available | Version / Path                                              |
|-------------------|-----------|-------------------------------------------------------------|
| Python            | YES       | (pytest ran successfully)                                   |
| PyInstaller       | YES       | 6.16.0                                                      |
| Inno Setup (ISCC) | YES       | C:\Users\KickA\AppData\Local\Programs\Inno Setup 6\ISCC.exe |

All tools required for local build are present, but local build is not the release path.
Release artifacts must come from CI to be attestable and match SHA256SUMS.txt.

---

## Publish Commands (DO NOT RUN UNTIL USER APPROVES)

```powershell
# Step 1 — Create and push the tag
git tag -a v1.0.6 -m "Cleanroom v1.0.6"
git push origin v1.0.6
```

CI will then:
1. Run 366 tests
2. Build `dist/Cleanroom-Setup-1.0.6.exe` via PyInstaller + Inno Setup
3. Generate SHA256SUMS.txt from the built artifacts
4. Attest provenance via actions/attest-build-provenance@v4
5. Create GitHub Release with all artifacts attached

After CI completes, run the Cleanroom unlock checklist:
```powershell
gh release view v1.0.6 --repo lazelife420-spec/cleanroom-windows --json tagName,name,assets
# download installer + SHA256SUMS.txt
# compute SHA256 of installer
# compare to SHA256SUMS entry
# write CLEANROOM_UNLOCK_CHECKLIST_2026-07-01.md
```

---

## Constraints

- Do NOT update Proof Foundry /proof until the unlock checklist receipt says GREEN
- Do NOT update landing pages until /proof is updated
- Do NOT alter release tags once pushed
- Do NOT use guessed URLs — all URLs come from `gh release view` output only
- Cache Vault rc4 is a separate lane — do not mix

---

## Final Verdict

**READY_TO_PUBLISH**

All gates pass:
- ✓ 366/366 tests pass
- ✓ version consistent across brand.py, installer.iss, SHA256SUMS.txt, CHANGELOG, release notes
- ✓ release surface verification PASSED (no forbidden terms, correct URLs, screenshots present)
- ✓ SHA256SUMS.txt present with 64-char hash for Cleanroom-Setup-1.0.6.exe
- ✓ release workflow identified and confirmed CI-driven
- ✓ all build tools available locally (for reference; CI is the publish path)
- ✓ working tree clean at HEAD 6d20c61

**Waiting for user approval to push tag v1.0.6 and trigger CI release.**

After tag push → CI completes → run CLEANROOM_UNLOCK_CHECKLIST → if GREEN → update /proof.
