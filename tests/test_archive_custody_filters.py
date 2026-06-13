"""Tests for archive_custody filter/summarize helpers."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import archive_custody as ac


def _rec(when='2020-01-01T00:00:00', rank=ac.PRUNE_SAFE, dest=None, src='a', size=100):
    dest = dest or str(Path('C:/arch/x.bin'))
    return {'when': when, 'prune_rank': rank, 'dest': dest, 'src': src, 'size': size, 'restorable': True}


def test_filter_by_search_matches_paths():
    records = [_rec(src=r'C:\Downloads\old.exe', dest=r'C:\arch\old.exe')]
    assert ac.filter_by_search(records, 'downloads')
    assert not ac.filter_by_search(records, 'missing')


def test_filter_older_than_days(tmp_path):
    old = tmp_path / 'old.bin'
    old.write_bytes(b'x')
    new = tmp_path / 'new.bin'
    new.write_bytes(b'y')
    now = datetime(2026, 6, 1)
    records = [
        {**_rec(when='2020-01-01T00:00:00'), 'dest': str(old)},
        {**_rec(when=now.isoformat()), 'dest': str(new)},
    ]
    out = ac.filter_older_than_days(records, 30, now=now)
    assert len(out) == 1
    assert out[0]['dest'] == str(old)


def test_summarize_archive_records():
    records = [
        _rec(rank=ac.PRUNE_SAFE, size=100),
        _rec(rank=ac.PRUNE_KEEP, size=200),
    ]
    s = ac.summarize_archive_records(records)
    assert s['total'] == 2
    assert s['safe_count'] == 1
    assert s['bytes_total'] == 300
    assert s['safe_bytes'] == 100


def test_apply_prune_removes_directory(tmp_path):
    live = tmp_path / 'live_dir'
    arch = tmp_path / 'arch_dir'
    (arch / 'sub').mkdir(parents=True)
    (arch / 'sub' / 'file.txt').write_text('data')
    live.mkdir()
    log_path = tmp_path / 'log.json'
    rec = {'src': str(live), 'dest': str(arch), 'size': 4, 'reason': 'folder'}
    result = ac.apply_prune([rec], log_path, dry_run=False)
    assert not arch.exists()
    assert live.exists()
    assert len(result['pruned']) == 1
