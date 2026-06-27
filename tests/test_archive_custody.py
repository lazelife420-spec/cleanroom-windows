"""Tests for archive_custody.py — browser records and safe archive-only prune."""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import archive_custody as ac
import receipts


def test_rank_zero_byte_safe(tmp_path):
    f = tmp_path / 'z.bin'
    f.write_bytes(b'')
    rec = {'src': str(tmp_path / 'orig'), 'dest': str(f), 'when': '2020-01-01T00:00:00',
           'reason': 'zero-byte', 'size': 0}
    assert ac.rank_prune(rec, now=datetime(2026, 6, 1)) == ac.PRUNE_SAFE


def test_rank_recent_keep(tmp_path):
    f = tmp_path / 'new.zip'
    f.write_bytes(b'x' * 100)
    rec = {'src': str(tmp_path / 'dl' / 'new.zip'), 'dest': str(f),
           'when': datetime.now().isoformat(), 'reason': 'installer', 'size': 100}
    assert ac.rank_prune(rec) == ac.PRUNE_KEEP


def test_rank_protected_path_keep(tmp_path):
    f = tmp_path / 'arch' / 'doc.txt'
    f.parent.mkdir(parents=True)
    f.write_text('x')
    rec = {'src': r'C:\Users\me\Documents\important.doc', 'dest': str(f),
           'when': '2020-01-01T00:00:00', 'reason': 'other', 'size': 1}
    assert ac.rank_prune(rec, now=datetime(2026, 6, 1)) == ac.PRUNE_KEEP


def test_build_archive_records_from_log(tmp_path):
    archive = tmp_path / 'archive' / 'old.zip'
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b'payload')
    actions = [{
        'src': str(tmp_path / 'Downloads' / 'old.zip'),
        'dest': str(archive),
        'when': '2026-06-01T10:00:00',
        'reason': 'installer/archive',
        'size': 7,
    }]
    records = ac.build_archive_records(actions, config={'age_days': {'installers': 30}})
    assert len(records) == 1
    assert records[0]['restorable'] is True
    assert records[0]['prune_rank'] in ac.PRUNE_RANK_ORDER


def test_apply_prune_never_touches_original(tmp_path, monkeypatch):
    original = tmp_path / 'live' / 'file.txt'
    archive = tmp_path / 'custody' / 'file.txt'
    archive.parent.mkdir(parents=True)
    original.parent.mkdir(parents=True)
    original.write_text('live copy')
    archive.write_text('archived copy')
    log_path = tmp_path / 'cleanup_log.json'
    log_path.write_text(json.dumps([{
        'src': str(original),
        'dest': str(archive),
        'when': '2020-01-01T00:00:00',
        'reason': 'temp',
        'size': 14,
    }]), encoding='utf-8')
    receipt_dir = tmp_path / 'receipts'
    monkeypatch.setattr(receipts, 'RECEIPT_DIR', receipt_dir)

    rec = ac.build_archive_records(json.loads(log_path.read_text()))[0]
    result = ac.apply_prune([rec], log_path, receipt_dir=receipt_dir, dry_run=False)

    assert original.read_text() == 'live copy'
    assert not archive.exists()
    assert len(result['pruned']) == 1
    assert result['receipt_path'] is not None
    assert result['receipt_path'].is_file()
    body = result['receipt_path'].read_text(encoding='utf-8')
    assert 'PRUNE RECEIPT' in body
    assert 'Original live files were not touched' in body

    log = json.loads(log_path.read_text())
    assert any(e.get('action') == 'prune' for e in log)


def test_apply_prune_dry_run_no_delete(tmp_path):
    archive = tmp_path / 'custody' / 'file.txt'
    archive.parent.mkdir(parents=True)
    archive.write_text('x')
    log_path = tmp_path / 'log.json'
    rec = {'src': str(tmp_path / 'a'), 'dest': str(archive), 'size': 1}
    result = ac.apply_prune([rec], log_path, dry_run=True)
    assert archive.exists()
    assert result['bytes_pruned'] == 1
    assert not log_path.exists() or json.loads(log_path.read_text()) == []


def test_summarize_prune_events():
    actions = [
        {'action': 'prune', 'size': 100},
        {'action': 'prune', 'size': 50},
        {'src': 'a', 'dest': 'b', 'size': 10},
    ]
    s = ac.summarize_prune_events(actions)
    assert s['prune_events'] == 2
    assert s['bytes_pruned'] == 150


def test_format_prune_receipt():
    text = receipts.format_prune_receipt(
        [{'dest': r'C:\arch\a.zip', 'size': 1024}], bytes_pruned=1024)
    assert 'CLEANROOM — PRUNE RECEIPT' in text
    assert 'Clean safely. Prove everything. Undo anytime.' in text
