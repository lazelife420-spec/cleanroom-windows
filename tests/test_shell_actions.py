"""Tests for shell_actions archive/delete helpers."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import shell_actions as sa


def test_archive_path_moves_file(tmp_path, monkeypatch):
    cfg = {
        'archive_dir': str(tmp_path / 'archive'),
        'log_file': str(tmp_path / 'cleanup_log.json'),
    }
    src = tmp_path / 'Downloads' / 'old.txt'
    src.parent.mkdir(parents=True)
    src.write_text('payload')
    monkeypatch.setattr(sa, '_load_config', lambda _path=None: cfg)
    ok, msg = sa.archive_path(src)
    assert ok
    assert not src.exists()
    log = json.loads(Path(cfg['log_file']).read_text(encoding='utf-8'))
    assert len(log) == 1
    assert log[0]['reason'] == 'shell-archive'


def test_delete_refuses_live_path_outside_archive(tmp_path, monkeypatch):
    cfg = {
        'archive_dir': str(tmp_path / 'archive'),
        'log_file': str(tmp_path / 'cleanup_log.json'),
    }
    live = tmp_path / 'live.txt'
    live.write_text('live', encoding='utf-8')
    monkeypatch.setattr(sa, '_load_config', lambda _path=None: cfg)
    ok, msg = sa.delete_archive_path(live)
    assert not ok
    assert 'not under' in msg.lower()
    assert live.exists()


def test_delete_refuses_orphan_in_archive(tmp_path, monkeypatch):
    cfg = {
        'archive_dir': str(tmp_path / 'archive'),
        'log_file': str(tmp_path / 'cleanup_log.json'),
    }
    arch = tmp_path / 'archive' / 'orphan.txt'
    arch.parent.mkdir(parents=True)
    arch.write_text('x', encoding='utf-8')
    Path(cfg['log_file']).write_text('[]', encoding='utf-8')
    monkeypatch.setattr(sa, '_load_config', lambda _path=None: cfg)
    ok, msg = sa.delete_archive_path(arch)
    assert not ok
    assert 'custody' in msg.lower()


def test_delete_custody_file_in_archive(tmp_path, monkeypatch):
    cfg = {
        'archive_dir': str(tmp_path / 'archive'),
        'log_file': str(tmp_path / 'cleanup_log.json'),
    }
    arch = tmp_path / 'archive' / 'kept.txt'
    arch.parent.mkdir(parents=True)
    arch.write_text('archived', encoding='utf-8')
    Path(cfg['log_file']).write_text(json.dumps([{
        'src': str(tmp_path / 'src.txt'),
        'dest': str(arch),
        'reason': 'temp',
        'size': 8,
        'when': '2020-01-01T00:00:00',
    }]), encoding='utf-8')
    monkeypatch.setattr(sa, '_load_config', lambda _path=None: cfg)
    ok, msg = sa.delete_archive_path(arch)
    assert ok
    assert not arch.exists()
