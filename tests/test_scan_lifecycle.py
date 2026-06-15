"""Scan lifecycle — cancel token, progress, and UI guards."""
import threading
import time
from pathlib import Path


def _import_main():
    import sys
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import main as m
    return m


def test_scan_candidates_cancel_returns_partial(tmp_path):
    m = _import_main()
    root = tmp_path / 'scanroot'
    root.mkdir()
    for i in range(20):
        (root / f'file{i}.txt').write_text('x')
    cancel = threading.Event()
    progress = []

    def work():
        time.sleep(0.01)
        cancel.set()

    t = threading.Thread(target=work, daemon=True)
    t.start()
    cfg = {
        'paths': [str(root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': [],
        'whitelist': [],
    }
    items = m.scan_candidates(cfg, cancel_check=cancel.is_set, on_progress=progress.append)
    t.join(timeout=2)
    assert cancel.is_set()
    assert isinstance(items, list)
    assert progress
    assert progress[-1].get('completed') is True


def test_scan_candidates_skip_folder_check(tmp_path):
    m = _import_main()
    root = tmp_path / 'scanroot'
    root.mkdir()
    skip_dir = root / 'heavy'
    skip_dir.mkdir()
    light = root / 'light.txt'
    light.write_text('x')
    for i in range(5):
        (skip_dir / f'big{i}.txt').write_text('y' * 20)
    skipped = []

    def skip_check(folder):
        if 'heavy' in folder.replace('\\', '/'):
            skipped.append(folder)
            return True
        return False

    cfg = {
        'paths': [str(root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': [],
        'whitelist': [],
    }
    items = m.scan_candidates(cfg, skip_folder_check=skip_check)
    paths = {Path(i['path']).name for i in items}
    assert 'light.txt' in paths
    assert not any(p.startswith('big') for p in paths)
    assert skipped


def test_scan_candidates_skips_archive_dir(tmp_path):
    m = _import_main()
    archive = tmp_path / 'archive'
    archive.mkdir()
    kept = tmp_path / 'downloads'
    kept.mkdir()
    old = kept / 'old.txt'
    old.write_text('old')
    cfg = {
        'paths': [str(kept), str(archive)],
        'archive_dir': str(archive),
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': [],
        'whitelist': [],
    }
    items = m.scan_candidates(cfg)
    paths = {Path(i['path']).name for i in items}
    assert 'old.txt' in paths


def test_refresh_cleanup_ignores_duplicate_start():
    import startup_manager_gui as gui

    class App:
        _cleaner_loading = False
        _scan_worker_id = 0
        _scan_cancel_event = None
        _scan_progress = {}
        _scan_diag = {}
        _scan_stopped = False
        _cleaner_error = ''
        tb_preview = type('B', (), {'configure': lambda *a, **k: None})()
        tb_apply = type('B', (), {'configure': lambda *a, **k: None})()
        cleanup_progress = type('P', (), {
            'pack': lambda *a, **k: None,
            'start': lambda *a, **k: None,
            'stop': lambda *a, **k: None,
            'pack_forget': lambda *a, **k: None,
        })()

        def _load_cleanup_config(self):
            return {'paths': []}

        def _sync_cleaner_state(self):
            pass

        def _sync_home_state(self, **kw):
            pass

        def _schedule_scan_progress_tick(self):
            pass

        def _run_bg(self, work, done):
            self._bg_calls = getattr(self, '_bg_calls', 0) + 1

    app = App()
    gui.StartupManagerGUI.refresh_cleanup(app)
    app._cleaner_loading = True
    gui.StartupManagerGUI.refresh_cleanup(app)
    assert app._bg_calls == 1


def test_tray_stop_scan_wires_to_app():
    from ui.tray import TrayController

    class App:
        def __init__(self):
            self.stopped = False

        def after(self, _ms, fn):
            fn()

        def stop_scan(self):
            self.stopped = True

    app = App()
    tray = TrayController(app)
    tray._on_stop_scan(None, None)
    assert app.stopped is True
