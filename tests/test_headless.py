"""Tests for headless scheduled cleanup and first-run config generation."""
from pathlib import Path
import os
import sys
import time

import yaml

tests_dir = Path(__file__).resolve().parent
project_dir = tests_dir.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import main as cleanup_main


def make_old(path, days):
    old = time.time() - days * 86400
    os.utime(path, (old, old))


def write_config(tmp_path, scan_dir, archive_dir, log_path):
    cfg_path = tmp_path / 'config.yaml'
    cfg_path.write_text(
        'paths:\n'
        f'  - {scan_dir}\n'
        'age_days:\n'
        '  temp: 7\n'
        '  installers: 30\n'
        'size_threshold_mb: 200\n'
        "extensions_archive: ['.zip']\n"
        f'archive_dir: {archive_dir}\n'
        f'log_file: {log_path}\n',
        encoding='utf-8')
    return cfg_path


def test_frozen_default_config_prefers_user_profile(tmp_path, monkeypatch):
    """Installed exe must not use dev hardcoded paths from repo cleanup_config.yaml."""
    import brand
    profile = tmp_path / 'WDAGUtilityAccount'
    profile.mkdir()
    monkeypatch.setenv('USERPROFILE', str(profile))
    monkeypatch.setenv('LOCALAPPDATA', str(profile / 'AppData' / 'Local'))
    monkeypatch.setenv('TEMP', str(profile / 'AppData' / 'Local' / 'Temp'))
    fake_local = profile / 'AppData' / 'Local' / 'Cleanroom'
    monkeypatch.setattr(brand, 'user_data_dir', lambda: fake_local)
    monkeypatch.setattr(cleanup_main, 'user_config_dir', lambda: fake_local)
    monkeypatch.setattr(cleanup_main.sys, 'frozen', True, raising=False)
    dev_cfg = tmp_path / 'install' / 'cleanup_config.yaml'
    dev_cfg.parent.mkdir(parents=True)
    dev_cfg.write_text('paths:\n  - C:\\Users\\KickA\\Downloads\n', encoding='utf-8')
    monkeypatch.setattr(cleanup_main, '_app_dir', lambda: dev_cfg.parent)

    path = cleanup_main.default_config_path()
    assert path == fake_local / 'cleanup_config.yaml'
    assert path.exists()
    parsed = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert any(str(p).startswith(str(profile)) for p in parsed['paths'])
    assert r'C:\Users\KickA\Downloads' not in [str(p) for p in parsed['paths']]


def test_generate_default_config(tmp_path):
    dest = tmp_path / 'Cleanroom' / 'cleanup_config.yaml'
    written = cleanup_main.generate_default_config(dest)
    assert dest.exists()
    parsed = yaml.safe_load(dest.read_text(encoding='utf-8'))
    assert parsed == written
    home = os.environ.get('USERPROFILE', str(Path.home()))
    assert any(p.startswith(home) for p in parsed['paths'])
    assert parsed['telemetry']['enabled'] is False
    # log/plan files live in the per-user data dir, not the source tree
    assert str(dest.parent) in parsed['log_file']


def test_run_headless_archives_and_logs(tmp_path):
    scan_dir = tmp_path / 'scan'
    scan_dir.mkdir()
    archive_dir = tmp_path / 'archive'
    log_path = tmp_path / 'cleanup_log.json'
    run_log = tmp_path / 'headless_run.log'

    old_zip = scan_dir / 'old.zip'
    old_zip.write_text('payload', encoding='utf-8')
    make_old(old_zip, 60)
    keeper = scan_dir / 'fresh.txt'
    keeper.write_text('recent', encoding='utf-8')

    cfg_path = write_config(tmp_path, scan_dir, archive_dir, log_path)
    rc = cleanup_main.run_headless(config_path=cfg_path, dedupe=False, log_to=run_log)

    assert rc == 0
    assert not old_zip.exists()
    assert (archive_dir / 'old.zip').exists()
    assert keeper.exists()
    assert log_path.exists()
    text = run_log.read_text(encoding='utf-8')
    assert 'archived 1 item(s)' in text


def test_run_headless_dedupe_separates_duplicates(tmp_path):
    scan_dir = tmp_path / 'scan'
    scan_dir.mkdir()
    archive_dir = tmp_path / 'archive'
    log_path = tmp_path / 'cleanup_log.json'
    run_log = tmp_path / 'headless_run.log'

    a = scan_dir / 'a.zip'
    b = scan_dir / 'b.zip'
    for f in (a, b):
        f.write_text('identical bytes', encoding='utf-8')
        make_old(f, 60)

    cfg_path = write_config(tmp_path, scan_dir, archive_dir, log_path)
    rc = cleanup_main.run_headless(config_path=cfg_path, dedupe=True, log_to=run_log)

    assert rc == 0
    assert len(list(archive_dir.glob('*.zip'))) == 1
    assert len(list((archive_dir / 'duplicates').glob('*.zip'))) == 1
    assert 'separated 1 duplicate(s)' in run_log.read_text(encoding='utf-8')


def test_run_headless_bad_config_fails_gracefully(tmp_path):
    run_log = tmp_path / 'headless_run.log'
    rc = cleanup_main.run_headless(config_path=tmp_path / 'missing.yaml', log_to=run_log)
    assert rc == 1
    assert 'ERROR' in run_log.read_text(encoding='utf-8')
