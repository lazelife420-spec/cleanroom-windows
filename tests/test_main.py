import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / 'main.py'
CFG = ROOT / 'cleanup_config.yaml'


def test_main_json_output():
    # Run main.py in JSON dry-run mode
    p = subprocess.run([sys.executable, str(MAIN), '--config', str(CFG), '--json'], capture_output=True, text=True, check=True)
    data = json.loads(p.stdout)
    assert 'candidates' in data
    assert isinstance(data['candidates'], list)
    # Expect at least one candidate from previous runs
    assert data['count'] == len(data['candidates'])
    assert data['total_bytes'] >= 0


def _import_main():
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import main as m
    return m


def test_scan_candidates_respects_exclude_patterns(tmp_path, monkeypatch):
    m = _import_main()
    test_root = tmp_path / 'testfolder'
    test_root.mkdir()
    include_file = test_root / 'keep.txt'
    exclude_file = test_root / 'skip.txt'
    include_file.write_text('keep')
    exclude_file.write_text('skip')
    cfg = {
        'paths': [str(test_root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': ['*skip.txt'],
        'whitelist': [],
    }
    candidates = m.scan_candidates(cfg)
    assert any('keep.txt' in c['path'] for c in candidates)
    assert not any('skip.txt' in c['path'] for c in candidates)


def test_scan_candidates_respects_whitelist(tmp_path, monkeypatch):
    m = _import_main()
    test_root = tmp_path / 'testfolder'
    test_root.mkdir()
    kept_file = test_root / 'keep.txt'
    white_file = test_root / 'whitelist.txt'
    kept_file.write_text('keep')
    white_file.write_text('white')
    cfg = {
        'paths': [str(test_root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': [],
        'whitelist': ['*whitelist.txt'],
    }
    candidates = m.scan_candidates(cfg)
    assert any('keep.txt' in c['path'] for c in candidates)
    assert not any('whitelist.txt' in c['path'] for c in candidates)


def test_scan_candidates_fast_finds_same_files(tmp_path, monkeypatch):
    m = _import_main()
    test_root = tmp_path / 'testfolder'
    test_root.mkdir()
    old_file = test_root / 'old.txt'
    old_file.write_text('old content')
    cfg = {
        'paths': [str(test_root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': [],
        'whitelist': [],
    }
    standard = m.scan_candidates(cfg)
    fast = m.scan_candidates_fast(cfg)
    assert len(fast) == len(standard)
    assert any('old.txt' in c['path'] for c in fast)


def test_scan_candidates_fast_respects_exclude_patterns(tmp_path, monkeypatch):
    m = _import_main()
    test_root = tmp_path / 'testfolder'
    test_root.mkdir()
    (test_root / 'keep.txt').write_text('keep')
    (test_root / 'skip.txt').write_text('skip')
    cfg = {
        'paths': [str(test_root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': ['*skip.txt'],
        'whitelist': [],
    }
    candidates = m.scan_candidates_fast(cfg)
    assert any('keep.txt' in c['path'] for c in candidates)
    assert not any('skip.txt' in c['path'] for c in candidates)


def test_scan_candidates_fast_skips_folders(tmp_path, monkeypatch):
    m = _import_main()
    test_root = tmp_path / 'testfolder'
    test_root.mkdir()
    (test_root / 'light.txt').write_text('light')
    big_dir = test_root / 'big'
    big_dir.mkdir()
    (big_dir / 'heavy.txt').write_text('heavy')
    cfg = {
        'paths': [str(test_root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': [],
        'whitelist': [],
    }

    skipped = []

    def skip_check(folder):
        if 'big' in folder:
            skipped.append(folder)
            return True
        return False

    candidates = m.scan_candidates_fast(cfg, skip_folder_check=skip_check)
    paths = {Path(c['path']).name for c in candidates}
    assert 'light.txt' in paths
    assert not any('heavy.txt' in c['path'] for c in candidates)
    assert skipped


def test_dedupe_candidates_detects_duplicates(tmp_path):
    m = _import_main()
    test_root = tmp_path / 'testfolder'
    test_root.mkdir()
    (test_root / 'a.txt').write_text('duplicate')
    (test_root / 'b.txt').write_text('duplicate')
    (test_root / 'c.txt').write_text('unique')

    candidates = [
        {'path': str(test_root / 'a.txt'), 'size': (test_root / 'a.txt').stat().st_size},
        {'path': str(test_root / 'b.txt'), 'size': (test_root / 'b.txt').stat().st_size},
        {'path': str(test_root / 'c.txt'), 'size': (test_root / 'c.txt').stat().st_size},
    ]
    keep, remove = m.dedupe_candidates(candidates)
    keep_paths = {Path(c['path']).name for c in keep}
    remove_paths = {Path(c['path']).name for c in remove}
    assert 'a.txt' in keep_paths or 'b.txt' in keep_paths
    assert 'c.txt' in keep_paths
    assert 'a.txt' in remove_paths or 'b.txt' in remove_paths
    assert len(remove) == 1


def test_performance_config_round_trip(tmp_path):
    m = _import_main()
    import yaml
    cfg = {
        'paths': [str(tmp_path)],
        'performance_scan': True,
        'performance': {
            'max_workers': 8,
            'memory_limit_mb': 1024,
            'incremental': False,
        },
    }
    cfg_path = tmp_path / 'cfg.yaml'
    cfg_path.write_text(yaml.safe_dump(cfg), encoding='utf-8')
    loaded = m.load_config(str(cfg_path))
    assert loaded['performance_scan'] is True
    assert loaded['performance']['max_workers'] == 8
    assert loaded['performance']['memory_limit_mb'] == 1024
    assert loaded['performance']['incremental'] is False
