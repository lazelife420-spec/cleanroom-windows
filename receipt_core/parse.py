"""RECEIPT Core parser — reads .cleanroom-receipt and legacy .txt receipts
into the typed Receipt schema.  Partial receipts are valid; missing fields
become warnings, not errors.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from receipt_core.paths import RECEIPT_EXT, RECEIPT_EXTENSIONS
from receipt_core.schema import (
    Artifact,
    CustodySummary,
    ProofRecord,
    Receipt,
    ReceiptType,
)

# ---------------------------------------------------------------------------
# row-level matchers
# ---------------------------------------------------------------------------

_RE_TITLE = re.compile(
    r'CLEANROOM\s*[-—–]\s*(RECEIPT|PRUNE\s*RECEIPT|CUSTODY\s*CHECK)'
)
_RE_DATE = re.compile(
    r'^\s*Date:\s+(?P<date>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
)
_RE_ITEMS_MOVED = re.compile(r'^\s*Items\s+moved:\s+(?P<n>\d+)')
_RE_SPACE_MOVED = re.compile(
    r'^\s*Space\s+moved:\s+(?P<size>[\d.]+)\s*(?P<unit>B|KB|MB|GB|TB)'
)
_RE_DISK_LIFE = re.compile(r'^\s*Disk\s+life:\s+~(?P<days>[\d.]+)\s+extra\s+days')
_RE_ITEMS_PRUNED = re.compile(r'^\s*Items\s+pruned:\s+(?P<n>\d+)')
_RE_BYTES_PRUNED = re.compile(
    r'^\s*Bytes\s+pruned:\s+(?P<size>[\d.]+)\s*(?P<unit>B|KB|MB|GB|TB)'
)
# proof section rows
_RE_FREE_BEFORE = re.compile(
    r'^\s*Free\s+space\s+before:\s+(?P<size>[\d.]+)\s*(?P<unit>B|KB|MB|GB|TB)'
)
_RE_FREE_AFTER = re.compile(
    r'^\s*Free\s+space\s+after:\s+(?P<size>[\d.]+)\s*(?P<unit>B|KB|MB|GB|TB)'
)
_RE_MEASURED_DELTA = re.compile(
    r'^\s*Measured\s+change:\s+(?P<size>[\d.]+)\s*(?P<unit>B|KB|MB|GB|TB)'
)
_RE_CLAIMED_BYTES = re.compile(
    r'\((?P<size>[\d.]+)\s*(?P<unit>B|KB|MB|GB|TB)\s+was\s+MOVED\s+to\s+the\s+archive'
)
_RE_CUSTODY_TOTAL = re.compile(
    r'^\s*Custody\s+check:\s+(?P<verified>\d+)/(?P<total>\d+)\s+archived\s+item'
)
_RE_CUSTODY_MISSING = re.compile(
    r'^\s*WARNING:\s+(?P<missing>\d+)\s+item\(s\)\s+NOT\s+found'
)
# prune artefact rows
_RE_PRUNED_ITEM = re.compile(
    r'^\s*(?P<size>[\d.]+)\s*(?P<unit>B|KB|MB|GB|TB)\s+(?P<path>\S.*)'
)
_RE_PRUNED_MORE = re.compile(r'^\s*…\s+and\s+(?P<n>\d+)\s+more$')
# legacy .txt detection
_RE_LEGACY_EXT = re.compile(r'\.txt$', re.IGNORECASE)

_HEADER_BOUNDARY = re.compile(r'^-{10,}$')
_PROOF_HEADER = 'PROOF (measured by the OS, not estimated):'


# ---------------------------------------------------------------------------
# unit helpers
# ---------------------------------------------------------------------------

_UNITS: dict[str, int] = {'B': 1, 'KB': 1024, 'MB': 1024 ** 2,
                          'GB': 1024 ** 3, 'TB': 1024 ** 4}


def _to_bytes(size_str: str, unit: str) -> int:
    try:
        return round(float(size_str) * _UNITS[unit.upper()])
    except (KeyError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def parse_file(path: str | Path) -> Receipt:
    """Parse a receipt file from disk into a Receipt schema object."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"receipt file not found: {path}")

    raw = path.read_text(encoding='utf-8', errors='replace')
    legacy = bool(_RE_LEGACY_EXT.search(path.suffix))
    receipt = parse_text(raw, legacy=legacy)
    receipt.source_path = str(path.resolve())
    return receipt


def parse_text(text: str, *, legacy: bool = False) -> Receipt:
    """Parse raw receipt text into a Receipt schema object.

    *legacy* should be True when the source file had a ``.txt`` suffix.
    """
    lines = text.splitlines()
    receipt = Receipt(raw_text=text, legacy=legacy)

    # --- detect type from the title block ---
    for line in lines[:10]:
        m = _RE_TITLE.search(line)
        if m:
            kind = m.group(1).upper()
            if 'PRUNE' in kind:
                receipt.receipt_type = ReceiptType.PRUNE
            elif 'CUSTODY' in kind:
                receipt.receipt_type = ReceiptType.CUSTODY_CHECK
            else:
                receipt.receipt_type = ReceiptType.CLEANUP
            break

    # --- scan rows ---
    in_proof = False
    for line in lines:
        # date
        dm = _RE_DATE.match(line)
        if dm:
            receipt.created_at = dm.group('date')
            continue

        if receipt.receipt_type == ReceiptType.PRUNE:
            _parse_prune_line(line, receipt)
        else:
            _parse_cleanup_line(line, receipt)

        # track proof section
        if not in_proof and _PROOF_HEADER in line:
            in_proof = True
            if receipt.proof is None:
                receipt.proof = ProofRecord()
            continue

        if in_proof and receipt.proof is not None:
            _parse_proof_line(line, receipt.proof)

    if not receipt.created_at:
        receipt.warnings.append('created_at missing — receipt may be incomplete')
    if receipt.artifact_count == 0:
        receipt.warnings.append('no structured artifact rows found')

    return receipt


# ---------------------------------------------------------------------------
# internal line parsers
# ---------------------------------------------------------------------------


def _parse_cleanup_line(line: str, receipt: Receipt) -> None:
    # items moved
    im = _RE_ITEMS_MOVED.match(line)
    if im:
        receipt.action_id = f"cleanup-{im.group('n')}"
        return

    # space moved
    sm = _RE_SPACE_MOVED.match(line)
    if sm:
        try:
            receipt.artifacts.append(
                Artifact(source_path='', reason='summary',
                         size_bytes=_to_bytes(sm.group('size'), sm.group('unit')))
            )
        except (KeyError, ValueError):
            receipt.warnings.append(f'could not parse space-moved row: {line!r}')
        return

    # disk life
    dl = _RE_DISK_LIFE.match(line)
    if dl:
        receipt.summary = f"{dl.group('days')} extra days"
        return

    # custody missing warning (already in proof section)
    cm = _RE_CUSTODY_MISSING.match(line)
    if cm:
        receipt.warnings.append(
            f'{cm.group("missing")} archived item(s) NOT found in the archive'
        )
        return


def _parse_prune_line(line: str, receipt: Receipt) -> None:
    # items pruned
    ip_ = _RE_ITEMS_PRUNED.match(line)
    if ip_:
        receipt.action_id = f"prune-{ip_.group('n')}"
        return

    # bytes pruned
    bp = _RE_BYTES_PRUNED.match(line)
    if bp:
        receipt.summary = f"{bp.group('size')}{bp.group('unit')} pruned"
        try:
            receipt.artifacts.append(
                Artifact(source_path='', reason='summary',
                         size_bytes=_to_bytes(bp.group('size'), bp.group('unit')))
            )
        except (KeyError, ValueError):
            receipt.warnings.append(f'could not parse bytes-pruned row: {line!r}')
        return

    # individual pruned entries
    pi = _RE_PRUNED_ITEM.match(line)
    if pi:
        try:
            b = _to_bytes(pi.group('size'), pi.group('unit'))
        except (KeyError, ValueError):
            b = 0
        receipt.artifacts.append(
            Artifact(source_path=pi.group('path'), archive_path=pi.group('path'),
                     size_bytes=b, action='pruned')
        )
        return

    # "… and N more"
    more = _RE_PRUNED_MORE.match(line)
    if more:
        receipt.warnings.append(
            f"Receipt truncated: {more.group('n')} entries not shown"
        )
        return


def _parse_proof_line(line: str, proof: ProofRecord) -> None:
    fb = _RE_FREE_BEFORE.match(line)
    if fb:
        proof.before_free = _to_bytes(fb.group('size'), fb.group('unit'))
        return

    fa = _RE_FREE_AFTER.match(line)
    if fa:
        proof.after_free = _to_bytes(fa.group('size'), fa.group('unit'))
        proof.measured_delta = proof.after_free - proof.before_free
        return

    md = _RE_MEASURED_DELTA.match(line)
    if md:
        proof.measured_delta = _to_bytes(md.group('size'), md.group('unit'))
        return

    cb = _RE_CLAIMED_BYTES.search(line)
    if cb:
        proof.claimed_bytes = _to_bytes(cb.group('size'), cb.group('unit'))
        return

    ct = _RE_CUSTODY_TOTAL.match(line)
    if ct:
        total = int(ct.group('total'))
        verified = int(ct.group('verified'))
        proof.custody = CustodySummary(
            total=total, verified=verified,
            missing=total - verified,
        )
        return

    cm = _RE_CUSTODY_MISSING.match(line)
    if cm and proof.custody is not None:
        missing = int(cm.group('missing'))
        proof.custody.missing = missing
        return
