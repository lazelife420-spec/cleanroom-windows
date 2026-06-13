"""Direct unit tests for receipt_core.paths — parity with receipts.py shim."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import receipts
from receipt_core import paths


def test_extension_constants_match_shim():
    assert paths.RECEIPT_EXT == receipts.RECEIPT_EXT
    assert paths.LEGACY_RECEIPT_EXT == receipts.LEGACY_RECEIPT_EXT
    assert paths.RECEIPT_EXTENSIONS == receipts.RECEIPT_EXTENSIONS


def test_is_receipt_path_matches_shim(tmp_path):
    cleanroom = tmp_path / 'receipt_20260101_120000.cleanroom-receipt'
    cleanroom.write_text('body', encoding='utf-8')
    legacy = tmp_path / 'receipt_20260101_120000.txt'
    legacy.write_text('body', encoding='utf-8')
    prune_legacy = tmp_path / 'prune_receipt_20260101_120000.txt'
    prune_legacy.write_text('body', encoding='utf-8')
    random_txt = tmp_path / 'notes.txt'
    random_txt.write_text('not a receipt', encoding='utf-8')

    for p in (cleanroom, legacy, prune_legacy, random_txt):
        assert paths.is_receipt_path(p) == receipts.is_receipt_path(p)

    assert paths.is_receipt_path(cleanroom)
    assert paths.is_receipt_path(legacy)
    assert paths.is_receipt_path(prune_legacy)
    assert not paths.is_receipt_path(random_txt)


def test_list_receipt_files_matches_shim(tmp_path):
    legacy = tmp_path / 'receipt_20260101_120000.txt'
    legacy.write_text('old', encoding='utf-8')
    newer = tmp_path / 'receipt_20260602_100000.cleanroom-receipt'
    newer.write_text('new', encoding='utf-8')

    core = paths.list_receipt_files(tmp_path)
    shim = receipts.list_receipt_files(tmp_path)
    assert core == shim
    assert core == [legacy, newer]


def test_list_receipt_files_empty_dir(tmp_path):
    assert paths.list_receipt_files(tmp_path) == []
    assert paths.list_receipt_files(tmp_path / 'missing') == []


def test_list_receipt_files_prune_prefix(tmp_path):
    p = tmp_path / 'prune_receipt_20260602_100000.cleanroom-receipt'
    p.write_text('prune', encoding='utf-8')
    assert paths.list_receipt_files(tmp_path, prefix='prune_receipt') == [p]
