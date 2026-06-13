"""Direct unit tests for receipt_core.render — golden-string parity with receipts.py shim."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import brand
import proof
import receipts
from receipt_core import custody, render

MOTTO = brand.APP_MOTTO
FIXED_NOW = datetime(2026, 6, 2, 10, 0, 0)


def _entry(dest, size=10, src=None, reason='large-file'):
    return {'src': src or f'C:\\junk\\{Path(dest).name}', 'dest': str(dest),
            'reason': reason, 'size': size, 'when': '2026-06-10T12:00:00'}


def test_format_receipt_minimal_golden():
    entries = [_entry(Path('x'), size=5)]
    expected = receipts.format_receipt(entries, now=FIXED_NOW)
    core = render.format_receipt(entries, now=FIXED_NOW, motto=MOTTO)
    assert core == expected
    assert core == (
        '==============================================\n'
        '         CLEANROOM — RECEIPT\n'
        f'  {MOTTO}\n'
        '==============================================\n'
        '  Date:        2026-06-02 10:00:00\n'
        '  Items moved: 1\n'
        '  Space moved: 5.0B\n'
        '----------------------------------------------\n'
        '  By reason:\n'
        '    large-file               1\n'
        '----------------------------------------------\n'
        '  Nothing was deleted. Everything was moved to\n'
        '  the archive and can be restored from the\n'
        '  Restore tab (or rolled back via Cleanroom Rewind).\n'
        '==============================================\n'
    )


def test_format_receipt_timeline_golden():
    moved = [
        {'src': 'a', 'dest': 'a2', 'reason': 'installer/archive', 'size': 1024 ** 3,
         'when': '2026-06-01T10:00:00'},
        {'src': 'b', 'dest': 'b2', 'reason': 'zero-byte', 'size': 0,
         'when': '2026-06-01T10:01:00'},
    ]
    expected = receipts.format_receipt(moved, days_bought=12.4, now=FIXED_NOW)
    core = render.format_receipt(moved, days_bought=12.4, now=FIXED_NOW, motto=MOTTO)
    assert core == expected
    assert '1.0GB' in core
    assert '~12 extra days' in core


def test_format_prune_receipt_golden():
    entries = [{'dest': r'C:\arch\a.zip', 'size': 1024}]
    expected = receipts.format_prune_receipt(entries, bytes_pruned=1024, now=FIXED_NOW)
    core = render.format_prune_receipt(
        entries, bytes_pruned=1024, now=FIXED_NOW, motto=MOTTO)
    assert core == expected
    assert 'CLEANROOM — PRUNE RECEIPT' in core
    assert r'C:\arch\a.zip' in core


def test_format_receipt_with_proof_matches_shim(tmp_path):
    f = tmp_path / 'kept.bin'
    f.write_bytes(b'z' * 50)
    entries = [_entry(f, size=50)]
    prf = proof.build_proof(500, 500, entries)
    expected = receipts.format_receipt(entries, proof=prf, now=FIXED_NOW)
    core = render.format_receipt(entries, proof=prf, now=FIXED_NOW, motto=MOTTO)
    assert core == expected
    assert 'PROOF (measured by the OS, not estimated):' in core


def test_format_receipt_proof_explains_archive_move(tmp_path):
    f = tmp_path / 'kept.bin'
    f.write_bytes(b'z' * 100)
    prf = custody.build_proof(10_000_000, 10_000_100, [_entry(f, size=1024 * 1024)])
    core = render.format_receipt([_entry(f, size=1024 * 1024)], proof=prf,
                                 now=FIXED_NOW, motto=MOTTO)
    shim = receipts.format_receipt([_entry(f, size=1024 * 1024)], proof=prf,
                                   now=FIXED_NOW)
    assert core == shim
    assert 'MOVED to the archive' in core


def test_format_receipt_without_proof():
    entries = [_entry(Path('x'), size=5)]
    core = render.format_receipt(entries, now=FIXED_NOW, motto=MOTTO)
    shim = receipts.format_receipt(entries, now=FIXED_NOW)
    assert core == shim
    assert 'PROOF' not in core


def test_format_prune_receipt_truncates_over_100_items():
    entries = [{'dest': f'C:\\arch\\{i}.zip', 'size': 1} for i in range(105)]
    core = render.format_prune_receipt(entries, now=FIXED_NOW, motto=MOTTO)
    shim = receipts.format_prune_receipt(entries, now=FIXED_NOW)
    assert core == shim
    assert '… and 5 more' in core
