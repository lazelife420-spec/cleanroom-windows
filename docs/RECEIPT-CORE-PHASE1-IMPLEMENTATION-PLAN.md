# RECEIPT Core — Phase 1 Implementation Plan

**Status:** Planning only — no implementation in this branch  
**Baseline:** `main @ 0d7f05c` (v1.0.4 live, planning spec merged)  
**Branch:** `docs/receipt-core-phase1-implementation-plan`  
**Parent spec:** [`RECEIPT-CORE-RECEIPTVAULT-PLAN.md`](RECEIPT-CORE-RECEIPTVAULT-PLAN.md)

---

## Purpose

Define the **smallest safe first implementation PR** for RECEIPT Core extraction — before any code is written.

This plan answers:

```text
What moves first
What stays in Cleanroom
Exact module boundaries
Compatibility tests for .cleanroom-receipt and legacy .txt
```

**Explicitly not in Phase 1:**

```text
ReceiptVault UI
Database / index
JSON schema migration or sidecar files
audit.py HTML extraction (later PR)
Activity feed construction (stays in ledger.py / Cleanroom)
```

ReceiptVault remains **parked** until RECEIPT Core custody + trust + receipt-path boundaries are extracted and tested.

---

## Design decisions (locked for Phase 1)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Package layout | `receipt_core/` package | Matches parent spec; room to grow without monolith |
| Backward compat | `proof.py`, `ledger.py`, `receipts.py` become **thin shims** re-exporting Core | Zero import churn in GUI/tests in early PRs |
| Structured JSON schema | **Deferred** | Plain-text receipts unchanged; no migration risk |
| `brand.py` coupling | Core accepts `motto: str` param; no `import brand` inside Core | Keeps Core reusable |
| First PR scope | **Custody + disk proof only** | Pure functions, 8 existing tests, no file I/O |

---

## What stays in Cleanroom (unchanged through Phase 1)

These modules remain Cleanroom-owned for the full Phase 1 sequence:

| Module | Stays because |
|--------|----------------|
| `ledger.py` → `build_activity_feed`, `summarize_feed` | Log-shape normalization is app-specific |
| `audit.py` | Proof Pack HTML shell + file write (PR 4+, not PR 1) |
| `receipts.py` → `write_receipt`, `write_prune_receipt`, `read_receipt` | File I/O paths, `MAX_RECEIPTS` pruning, `brand.user_data_dir()` |
| `archive_custody.py` | Archive browser + prune execution |
| `startup_manager_gui.py` | GUI wiring |
| `main.py` | Headless cleanup orchestration |
| `cleanup_log.json` | Canonical action log — not replaced |

Core owns **proof semantics**. Cleanroom owns **when/where to write** and **log interpretation for UI tables**.

---

## Target `receipt_core/` layout (end of Phase 1 sequence)

Phase 1 is split into **four small PRs**. Only the first is coding-ready after this doc merges.

```text
receipt_core/
  __init__.py          — public API exports (minimal)
  custody.py           — PR 1: disk_free, volume_of, verify_entries, build_proof, format_proof
  trust.py             — PR 2: trust_score, format_trust_score_display
  paths.py             — PR 3: RECEIPT_EXT, is_receipt_path, list_receipt_files, _receipt_sort_key
  render.py            — PR 3: format_receipt, format_prune_receipt (motto param)
  _human.py            — shared byte formatting (internal)
```

```text
proof.py      → shim → receipt_core.custody
ledger.py     → shim for trust fns only; feed fns stay local
receipts.py   → shim for paths + render; write/read/prune stay local
audit.py      → unchanged until post–Phase 1
```

---

## PR sequence

### PR 1 — Custody extraction (smallest safe first PR)

**Branch:** `feat/receipt-core-custody`  
**Title:** Extract RECEIPT Core custody and disk proof

#### What moves

From `proof.py` → `receipt_core/custody.py`:

```text
disk_free()
volume_of()
verify_entries()
build_proof()
format_proof()
_human()              → receipt_core/_human.py (shared internal)
REG_PREFIX            → stays in proof.py OR moves if ledger needs it later; not in PR 1
```

#### What stays

```text
proof.py              — re-exports all public symbols from receipt_core.custody
                      — docstring preserved at shim level
```

#### Import graph after PR 1

```text
receipts.py           → still imports proof (shim) for format_proof in format_receipt
startup_manager_gui   → still imports proof_module
main.py               → still imports proof_module
tests/test_proof.py   → unchanged imports (proof.*)
```

#### New tests (PR 1)

```text
tests/test_receipt_core_custody.py
  — imports receipt_core.custody directly
  — duplicates critical assertions from test_proof.py (parity, not replacement)
  — proves boundary is testable without proof.py shim
```

Existing `tests/test_proof.py` must pass **unchanged** — shim parity gate.

#### Gates (PR 1)

```powershell
python -m pytest
python scripts/verify_release_surface.py --tag v1.0.4
```

No UI gate required (no GUI change). No installer change.

#### User-visible change

**None.** Receipt text, Proof Pack, trust display identical.

#### Stop conditions (PR 1)

```text
Any test_proof.py failure
Any receipt text diff in test_receipt_embeds_proof_section
Measured delta or custody math change
New network/import dependency in receipt_core/
```

---

### PR 2 — Trust score extraction

**Branch:** `feat/receipt-core-trust`  
**Depends on:** PR 1 merged

#### What moves

From `ledger.py` → `receipt_core/trust.py`:

```text
trust_score()
format_trust_score_display()
```

#### What stays in `ledger.py`

```text
build_activity_feed()
summarize_feed()
_present()              — private; used by feed only
```

#### Shim

```python
# ledger.py (after PR 2)
from receipt_core.trust import trust_score, format_trust_score_display
```

#### Tests

```text
tests/test_ledger.py         — unchanged imports
tests/test_receipt_core_trust.py — direct Core imports, parity with test_ledger trust tests
audit.py                     — still from ledger import format_trust_score_display (via shim)
```

#### User-visible change

**None.**

---

### PR 3 — Receipt paths + render extraction

**Branch:** `feat/receipt-core-receipt-render`  
**Depends on:** PR 2 merged

#### What moves

From `receipts.py` → `receipt_core/paths.py`:

```text
RECEIPT_EXT, LEGACY_RECEIPT_EXT, RECEIPT_EXTENSIONS
_receipt_sort_key()
list_receipt_files()
is_receipt_path()
```

From `receipts.py` → `receipt_core/render.py`:

```text
format_receipt()        — proof section via receipt_core.custody.format_proof
format_prune_receipt()
_human()                — use receipt_core._human
```

`format_receipt` signature adds optional `motto: str` with default from shim:

```python
# receipts.py shim
def format_receipt(..., motto=None, ...):
    return render.format_receipt(..., motto=motto or brand.APP_MOTTO, ...)
```

#### What stays in `receipts.py`

```text
RECEIPT_DIR, MAX_RECEIPTS
write_receipt(), write_prune_receipt(), read_receipt(), latest_receipt()
File mkdir, glob prune, path construction
```

#### Compatibility tests (required — PR 3)

Extend existing suite; all must pass:

| Test file | Covers |
|-----------|--------|
| `tests/test_receipt_filetype.py` | `.cleanroom-receipt` write extension |
| `tests/test_timeline.py` | receipt content, pruning caps |
| `tests/test_open_receipt_cli.py` | `is_receipt_path` gate |
| `tests/test_proof.py` | `receipts.format_receipt` + proof embed |
| `tests/test_receipt_core_paths.py` | **new** — direct Core path helpers |
| `tests/test_receipt_core_render.py` | **new** — golden-string receipt body parity |

Golden-string gate (PR 3):

```text
Capture format_receipt() output for fixed inputs before PR 3
Assert byte-identical output after extraction (motto, proof block, line order)
Same for format_prune_receipt()
Legacy .txt read path unchanged — read_receipt() still open-any-text
```

#### User-visible change

**None** if golden-string gate passes.

---

### PR 4 — Proof Pack section helpers (optional, post–Phase 1 minimum)

**Not required to close Phase 1 boundary.** Defer unless needed before ReceiptVault.

If done later:

```text
Extract HTML row builders + trust header from audit.py → receipt_core/render_audit.py
audit.py keeps export_html_audit() file write + page shell
```

ReceiptVault still **blocked** until PRs 1–3 merged and green.

---

## Module boundary rules

```text
receipt_core/     MAY import: stdlib only (pathlib, shutil, datetime, collections)
receipt_core/     MUST NOT import: brand, main, startup_manager_gui, audit, archive_custody
Cleanroom shims     MAY import: receipt_core, brand
GUI                 SHOULD import: shims (proof, ledger, receipts) not receipt_core directly
                      — exception: new Core-only tests import receipt_core directly
```

This keeps a single migration path: shims first, direct Core imports in app code only when explicitly lane-scoped.

---

## Compatibility matrix (must hold after PR 3)

| Artifact | Format | Read | Write | Test coverage |
|----------|--------|------|-------|---------------|
| Cleanup receipt | `.cleanroom-receipt` | ✓ | ✓ | `test_receipt_filetype`, `test_timeline` |
| Cleanup receipt | legacy `.txt` | ✓ | no new writes | `test_receipt_filetype`, `test_timeline` |
| Prune receipt | `.cleanroom-receipt` | ✓ | ✓ | `test_receipt_filetype` |
| Proof section in receipt | plain text | embedded | embedded | `test_proof.test_receipt_embeds_proof_section` |
| Shell open | `--open-receipt` | ✓ | n/a | `test_open_receipt_cli` |
| Installer association | `.cleanroom-receipt` | n/a | n/a | `test_receipt_filetype` (installer.iss strings) |
| Trust display | `NN/100` cap | n/a | n/a | `test_ledger.test_format_trust_score_display` |

**No schema migration:** structured JSON sidecar is out of scope until ReceiptVault lane explicitly requests it.

---

## What NOT to do in Phase 1

```text
[ ] Do not add receipt_core/serialize.py or JSON sidecars
[ ] Do not add ReceiptVault folder, SQLite, or index
[ ] Do not change .cleanroom-receipt extension or installer.iss
[ ] Do not refactor build_activity_feed into Core
[ ] Do not change cleanup_log.json shape
[ ] Do not bump APP_VERSION or cut a release (unless explicit release cycle)
[ ] Do not import receipt_core from PyInstaller hiddenimports until packaged smoke fails
```

---

## Implementation checklist (PR 1 only — ready after this doc merges)

```text
[ ] Create branch feat/receipt-core-custody from main
[ ] Add receipt_core/__init__.py, receipt_core/custody.py, receipt_core/_human.py
[ ] Move functions from proof.py; proof.py → shim
[ ] Add tests/test_receipt_core_custody.py
[ ] python -m pytest
[ ] python scripts/verify_release_surface.py --tag v1.0.4
[ ] PR title: Extract RECEIPT Core custody and disk proof
[ ] PR body: link this doc + list moved symbols + confirm no user-visible change
```

---

## Success criteria (full Phase 1 sequence, PRs 1–3)

```text
receipt_core.custody, .trust, .paths, .render exist and are directly unit-tested
proof.py, ledger.py (partial), receipts.py (partial) are shims — old imports work
175+ pytest green; release surface v1.0.4 green
Golden-string receipt parity passes
.cleanroom-receipt and legacy .txt compatibility matrix passes
No GUI, tray, installer, or cleanup behavior change
ReceiptVault lane still not started
```

---

## Relationship to ReceiptVault

```text
ReceiptVault MVP (Phase 2 in parent spec) requires:
  — receipt_core.paths.is_receipt_path / list_receipt_files (PR 3)
  — receipt_core.render or read_receipt shim for display (PR 3)
  — Optional: serialize layer (future, not Phase 1)

Do not start ReceiptVault until PR 3 merged and compatibility matrix green.
```

---

## Open items (resolve in PR 1 code review, not before)

| Item | Recommendation |
|------|----------------|
| `REG_PREFIX` in proof.py | Leave in proof.py until registry proof moves |
| PyInstaller bundle | Add `receipt_core` only if `build_exe` smoke fails |
| Public `receipt_core.__all__` | Export custody + trust + paths + render after PR 3 |

---

*Planning doc only. Start coding on `feat/receipt-core-custody` after this document is reviewed and merged.*
