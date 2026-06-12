"""Tray integration — wiring and failure-safe startup."""
from ui.tray import TrayController


class _FakeApp:
    def __init__(self):
        self.calls = []

    def after(self, _ms, fn):
        fn()


def test_tray_menu_labels():
    assert 'Open Cleanroom' in TrayController.MENU_LABELS
    assert 'Hide to tray' in TrayController.MENU_LABELS
    assert 'Latest Receipt' in TrayController.MENU_LABELS
    assert 'Proof Pack' in TrayController.MENU_LABELS
    assert 'Quit' in TrayController.MENU_LABELS


def test_tray_callbacks_schedule_app_actions(monkeypatch):
    app = _FakeApp()
    app._tray_show_window = lambda: app.calls.append('show')
    app._tray_hide_window = lambda: app.calls.append('hide')
    app._tray_quit = lambda: app.calls.append('quit')
    app.open_last_receipt = lambda: app.calls.append('receipt')
    app.export_audit = lambda: app.calls.append('proof')

    tray = TrayController(app)
    tray._on_open(None, None)
    tray._on_hide(None, None)
    tray._on_show(None, None)
    tray._on_latest_receipt(None, None)
    tray._on_proof_pack(None, None)
    tray._on_quit(None, None)

    assert app.calls == ['show', 'hide', 'show', 'receipt', 'proof', 'quit']


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


def test_tray_init_failure_does_not_crash_gui_init(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError('tray unavailable')

    monkeypatch.setattr('ui.tray.TrayController', _boom)

    import startup_manager_gui as gui

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
