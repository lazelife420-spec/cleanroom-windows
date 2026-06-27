"""Unit tests for receipt_core.parse — receipt text → schema bridge."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import brand
from receipt_core import custody, render
from receipt_core.parse import parse_file, parse_text
from receipt_core.schema import (
    ReceiptType,
)

MOTTO = brand.APP_MOTTO

# ---------------------------------------------------------------------------
# helpers — build realistic receipt text exactly as Cleanroom writes it
# ---------------------------------------------------------------------------


def _cleanup_text(entries=None, proof=None):
    if entries is None:
        entries = [_entry(Path('a.bin'), 64)]
    return render.format_receipt(entries, proof=proof, motto=MOTTO)


def _prune_text(entries=None, bytes_pruned=None):
    if entries is None:
        entries = [{'dest': r'C:\arch\a.zip', 'size': 1024}]
    return render.format_prune_receipt(entries, bytes_pruned=bytes_pruned, motto=MOTTO)


def _entry(dest, size=10, src=None, reason='large-file'):
    return {
        'src': src or f'C:\\junk\\{Path(dest).name}',
        'dest': str(dest),
        'reason': reason,
        'size': size,
        'when': '2026-06-10T12:00:00',
    }


# ---------------------------------------------------------------------------
# parse_text
# ---------------------------------------------------------------------------


class TestParseTextCleanup:
    def test_detects_cleanup_type(self):
        r = parse_text(_cleanup_text())
        assert r.receipt_type == ReceiptType.CLEANUP

    def test_extracts_date(self):
        r = parse_text(_cleanup_text())
        assert r.created_at != ''
        assert '2026' in r.created_at

    def test_preserves_raw_text(self):
        text = _cleanup_text()
        r = parse_text(text)
        assert r.raw_text == text

    def test_extracts_items_moved(self):
        text = _cleanup_text([_entry(Path('a.bin'), 10), _entry(Path('b.bin'), 20)])
        r = parse_text(text)
        assert r.action_id.startswith('cleanup-')

    def test_extracts_space_moved_as_artifact(self):
        text = _cleanup_text([_entry(Path('x.bin'), 500)])
        r = parse_text(text)
        assert r.total_bytes_claimed > 0

    def test_legacy_flag_is_preserved(self):
        r = parse_text(_cleanup_text(), legacy=True)
        assert r.legacy is True

    def test_missing_date_adds_warning(self):
        # drop title block + date line (first 5 lines of a standard receipt)
        lines = _cleanup_text().splitlines()
        text = '\n'.join(lines[5:])
        r = parse_text(text)
        assert any('created_at missing' in w for w in r.warnings)

    def test_partial_receipt_does_not_throw(self):
        # just the title — nothing else
        r = parse_text('CLEANROOM — RECEIPT')
        assert r.receipt_type == ReceiptType.CLEANUP


class TestParseTextPrune:
    def test_detects_prune_type(self):
        r = parse_text(_prune_text())
        assert r.receipt_type == ReceiptType.PRUNE

    def test_extracts_bytes_pruned(self):
        r = parse_text(_prune_text())
        assert r.total_bytes_claimed > 0

    def test_extracts_individual_pruned_items(self):
        entries = [
            {'dest': r'C:\arch\z1.zip', 'size': 100},
            {'dest': r'C:\arch\z2.zip', 'size': 200},
        ]
        r = parse_text(_prune_text(entries))
        assert r.artifact_count >= 2

    def test_truncated_notice_adds_warning(self):
        entries = [{'dest': f'C:\\arch\\{i}.zip', 'size': 1} for i in range(150)]
        r = parse_text(_prune_text(entries))
        assert any('truncated' in w.lower() for w in r.warnings)


class TestParseTextProof:
    def test_extracts_proof_when_present(self, tmp_path):
        f = tmp_path / 'kept.bin'
        f.write_bytes(b'x' * 100)
        entries = [_entry(f, size=100)]
        prf = custody.build_proof(1_000_000, 1_000_500, entries)
        r = parse_text(_cleanup_text(entries, proof=prf))
        assert r.proof is not None
        assert r.proof.before_free > 0
        assert r.proof.after_free > 0

    def test_custody_summary_in_proof(self, tmp_path):
        f = tmp_path / 'custody.bin'
        f.write_bytes(b'y' * 50)
        entries = [_entry(f, size=50)]
        prf = custody.build_proof(500, 500, entries)
        r = parse_text(_cleanup_text(entries, proof=prf))
        assert r.proof is not None
        assert r.proof.custody is not None
        assert r.proof.custody.verified == 1
        assert r.proof.custody.total == 1

    def test_missing_custody_adds_warning(self, tmp_path):
        f = tmp_path / 'gone.bin'
        entries = [_entry(f, size=50)]
        prf = custody.build_proof(0, 0, entries)
        r = parse_text(_cleanup_text(entries, proof=prf))
        assert any('NOT found' in w for w in r.warnings)

    def test_no_proof_section_does_not_crash(self):
        text = _cleanup_text(proof=None)
        r = parse_text(text)
        assert r.proof is None


class TestParseTextUnknown:
    def test_unknown_text_becomes_unknown_legacy(self):
        r = parse_text('This is just random text.\nNothing receipt-like here.')
        assert r.receipt_type == ReceiptType.UNKNOWN_LEGACY
        assert r.raw_text != ''
        assert any('created_at missing' in w for w in r.warnings)

    def test_unknown_text_preserves_raw(self):
        text = 'Arbitrary content'
        r = parse_text(text)
        assert r.raw_text == text

    def test_legacy_flag_on_unknown_with_txt(self):
        r = parse_text('random', legacy=True)
        assert r.legacy is True
        assert r.receipt_type == ReceiptType.UNKNOWN_LEGACY


class TestParseTextRoundtrip:
    """Parse what Cleanroom writes — verify fidelity."""

    def test_cleanup_roundtrip(self):
        entries = [_entry(Path('a.bin'), 100), _entry(Path('b.bin'), 200)]
        text = _cleanup_text(entries)
        r = parse_text(text)
        assert r.receipt_type == ReceiptType.CLEANUP
        assert r.raw_text == text
        assert r.artifact_count > 0

    def test_prune_roundtrip(self):
        entries = [{'dest': r'C:\arch\p.zip', 'size': 4096}]
        text = _prune_text(entries)
        r = parse_text(text)
        assert r.receipt_type == ReceiptType.PRUNE
        assert r.raw_text == text
        assert r.artifact_count > 0

    def test_parse_then_to_dict_is_sane(self):
        text = _cleanup_text([_entry(Path('x.bin'), 42)])
        r = parse_text(text)
        d = r.to_dict()
        assert d['receipt_type'] == 'cleanup'
        assert d['raw_text'] == text


# ---------------------------------------------------------------------------
# parse_file
# ---------------------------------------------------------------------------


class TestParseFile:
    def test_parses_real_receipt_file(self, tmp_path):
        receipt_file = tmp_path / 'receipt_20260101_120000.cleanroom-receipt'
        receipt_file.write_text(_cleanup_text(), encoding='utf-8')
        r = parse_file(receipt_file)
        assert r.receipt_type == ReceiptType.CLEANUP
        assert r.source_path == str(receipt_file.resolve())

    def test_parses_legacy_txt_receipt(self, tmp_path):
        legacy = tmp_path / 'receipt_20260101_120000.txt'
        legacy.write_text(_cleanup_text(), encoding='utf-8')
        r = parse_file(legacy)
        assert r.legacy is True
        assert r.receipt_type == ReceiptType.CLEANUP

    def test_raises_on_missing_file(self, tmp_path):
        missing = tmp_path / 'gone.cleanroom-receipt'
        with pytest.raises(FileNotFoundError):
            parse_file(missing)

    def test_sets_source_path(self, tmp_path):
        f = tmp_path / 'receipt_20260101_120000.cleanroom-receipt'
        f.write_text(_cleanup_text(), encoding='utf-8')
        r = parse_file(f)
        assert r.source_path == str(f.resolve())
