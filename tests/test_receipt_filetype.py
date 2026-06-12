"""Receipt file type (.cleanroom-receipt) and installer association."""
from datetime import datetime
from pathlib import Path

import receipts


def _entry(src='a', dest='b', size=100):
    return {'src': src, 'dest': dest, 'size': size, 'reason': 'temp'}


def test_new_receipt_uses_cleanroom_extension(tmp_path):
    path = receipts.write_receipt([_entry()], receipt_dir=tmp_path)
    assert path.suffix == receipts.RECEIPT_EXT
    assert path.name.endswith('.cleanroom-receipt')


def test_prune_receipt_uses_cleanroom_extension(tmp_path):
    path = receipts.write_prune_receipt([_entry()], receipt_dir=tmp_path)
    assert path.suffix == receipts.RECEIPT_EXT


def test_legacy_txt_receipt_still_reads(tmp_path):
    legacy = tmp_path / 'receipt_20260101_120000.txt'
    legacy.write_text('legacy receipt body', encoding='utf-8')
    assert receipts.read_receipt(legacy) == 'legacy receipt body'
    assert receipts.is_receipt_path(legacy)


def test_latest_receipt_finds_cleanroom_extension(tmp_path):
    legacy = tmp_path / 'receipt_20260101_120000.txt'
    legacy.write_text('old', encoding='utf-8')
    newer = receipts.write_receipt(
        [_entry()], receipt_dir=tmp_path, now=datetime(2026, 6, 2, 10, 0, 0))
    assert receipts.latest_receipt(tmp_path) == newer


def test_latest_receipt_finds_legacy_txt_when_only_txt(tmp_path):
    legacy = tmp_path / 'receipt_20260101_120000.txt'
    legacy.write_text('only legacy', encoding='utf-8')
    assert receipts.latest_receipt(tmp_path) == legacy


def test_is_receipt_path_rejects_random_txt(tmp_path):
    random_txt = tmp_path / 'notes.txt'
    random_txt.write_text('not a receipt', encoding='utf-8')
    assert not receipts.is_receipt_path(random_txt)


def test_installer_registers_cleanroom_receipt_association():
    text = Path(__file__).resolve().parents[1] / 'installer.iss'
    content = text.read_text(encoding='utf-8')
    assert '.cleanroom-receipt' in content
    assert 'CleanroomReceipt' in content
    assert '--open-receipt' in content
    assert '%1' in content
    assert 'uninsdeletekey' in content
