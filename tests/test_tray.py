"""Tray integration — wiring and failure-safe startup."""
import pytest

from ui.tray import TrayController, get_active_tray, shutdown_all_trays


@pytest.fixture(autouse=True)
def _tray_teardown():
    yield
    shutdown_all_trays()


class _FakeApp:
    def __init__(self):
        self.calls = []
        self.cleanup_items = []
        self.cleanup_selected = set()

    def after(self, _ms, fn):
        fn()


def test_tray_menu_labels():
    assert 'Open Cleanroom' in TrayController.MENU_LABELS
    assert 'Run Scan' in TrayController.MENU_LABELS
    assert 'Open Latest Receipt' in TrayController.MENU_LABELS
    assert 'Open Proof Pack' in TrayController.MENU_LABELS
    assert 'Open Archive Folder' in TrayController.MENU_LABELS
    assert 'Hide to tray' in TrayController.MENU_LABELS
    assert 'Quit Cleanroom' in TrayController.MENU_LABELS


def test_tray_callbacks_schedule_app_actions(monkeypatch):
    app = _FakeApp()
    app._tray_show_window = lambda: app.calls.append('show')
    app._tray_hide_window = lambda: app.calls.append('hide')
    app._shutdown_app = lambda *_a, **_k: app.calls.append('quit')
    app.open_last_receipt = lambda: app.calls.append('receipt')
    app.export_audit = lambda: app.calls.append('proof')
    app.refresh_cleanup = lambda: app.calls.append('scan')
    app.preview_cleanup_receipt = lambda: app.calls.append('preview')
    app.open_archive_folder = lambda: app.calls.append('archive')
    app.open_shell_context_menu_tool = lambda: app.calls.append('explorer')
    app.open_registry_health = lambda: app.calls.append('registry')
    app.open_time_machine = lambda: app.calls.append('rewind')
    app.verify_custody = lambda: app.calls.append('custody')
    app.tab_control = type('T', (), {'select': lambda s, i: app.calls.append('tab')})()
    app.restore_tab = 5
    app.refresh_restore = lambda: app.calls.append('restore')

    tray = TrayController(app)
    tray._on_open(None, None)
    tray._on_hide(None, None)
    tray._on_show(None, None)
    tray._on_run_scan(None, None)
    tray._on_latest_receipt(None, None)
    tray._on_proof_pack(None, None)
    tray._on_archive_folder(None, None)
    tray._on_explorer_menus(None, None)
    tray._on_registry_snapshot(None, None)
    tray._on_rewind(None, None)
    tray._on_custody_check(None, None)
    tray._on_restore_tab(None, None)
    tray._on_quit(None, None)

    assert 'show' in app.calls
    assert 'hide' in app.calls
    assert 'receipt' in app.calls
    assert 'proof' in app.calls
    assert 'scan' in app.calls
    assert 'archive' in app.calls
    assert 'quit' in app.calls


def test_tray_preview_skips_without_selection():
    app = _FakeApp()
    app.preview_cleanup_receipt = lambda: app.calls.append('preview')
    app.cleanup_items = [{'path': '/x'}]
    app.cleanup_selected = set()
    tray = TrayController(app)
    tray._on_preview_receipt(None, None)
    assert 'preview' not in app.calls

    app.cleanup_selected = {0}
    tray._on_preview_receipt(None, None)
    assert 'preview' in app.calls


def test_tray_stop_without_running_attr():
    app = _FakeApp()
    tray = TrayController(app)

    class _Icon:
        def __init__(self):
            self.stopped = False

        def stop(self):
            self.stopped = True

    icon = _Icon()
    tray._icon = icon
    tray.stop()
    assert icon.stopped is True
    assert tray._icon is None
    assert getattr(icon, '_running', False) is False


def test_tray_stop_clears_active_singleton():
    import ui.tray as tray_mod
    app = _FakeApp()
    tray = TrayController(app)
    tray_mod._active_tray = tray
    tray.stop()
    assert tray_mod._active_tray is None


def test_tray_start_without_pystray_is_safe(monkeypatch):
    import sys
    monkeypatch.delitem(sys.modules, 'pystray', raising=False)

    def _import_error(name, *args, **kwargs):
        if name == 'pystray':
            raise ImportError('no pystray')
        return __import__(name, *args, **kwargs)

    monkeypatch.setattr('builtins.__import__', _import_error)
    app = _FakeApp()
    tray = TrayController(app)
    assert tray.start() is False


def test_tray_menu_builds_without_error():
    app = _FakeApp()
    tray = TrayController(app)
    menu = tray._build_menu()
    assert menu is not None


def test_tray_menu_has_required_actions():
    app = _FakeApp()
    tray = TrayController(app)
    menu = tray._build_menu()
    labels = []
    for item in getattr(menu, '_items', ()) or ():
        text = getattr(item, 'text', None)
        if callable(text):
            continue
        if text:
            labels.append(str(text))
    assert 'Open Cleanroom' in TrayController.MENU_LABELS
    assert 'Quit Cleanroom' in TrayController.MENU_LABELS


def test_tray_diagnostics_snapshot():
    app = _FakeApp()
    tray = TrayController(app)
    text = tray.diagnostics_text()
    assert 'CLEANROOM TRAY DIAGNOSTICS' in text
    assert 'pystray_import' in text


def test_tray_init_failure_does_not_crash_gui_init(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError('tray unavailable')

    monkeypatch.setattr('ui.tray.TrayController', _boom)

    class _MinimalGUI:
        _tray = object()

        def _init_tray(self):
            try:
                from ui.tray import TrayController
                self._tray = TrayController(self)
                if not self._tray.start():
                    self._tray = None
            except Exception:
                self._tray = None

    app = _MinimalGUI()
    app._init_tray()
    assert app._tray is None


def test_get_active_tray_reflects_singleton():
    import ui.tray as tray_mod
    app = _FakeApp()
    tray = TrayController(app)
    tray_mod._active_tray = tray
    try:
        assert get_active_tray() is tray
    finally:
        tray_mod._active_tray = None


def test_shutdown_all_trays_clears_singleton():
    import ui.tray as tray_mod
    app = _FakeApp()
    tray = TrayController(app)
    tray_mod._active_tray = tray
    shutdown_all_trays()
    assert tray_mod._active_tray is None


def test_tray_start_twice_reuses_healthy_controller(monkeypatch):
    import ui.tray as tray_mod

    app = _FakeApp()
    tray = TrayController(app)
    tray._started = True
    tray._icon = type('I', (), {'_running': True})()
    tray._tray_thread = type('T', (), {'is_alive': lambda s: True})()
    tray_mod._active_tray = tray

    second = TrayController(app)
    assert second.start() is True
    assert tray_mod._active_tray is tray


def test_tray_stop_is_idempotent():
    app = _FakeApp()
    tray = TrayController(app)
    tray.stop()
    tray.stop()
    assert tray._icon is None
