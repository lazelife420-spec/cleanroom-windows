#!/usr/bin/env python3
# ruff: noqa: E402
"""Tray visual gate — real GUI session with pystray icon lifecycle checks.

Automated checks cover menu build, hide/show, quit cleanup, and singleton behavior.
Visible notification-area icon still requires manual confirmation — see docs/PR22-SIGNOFF.md.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import startup_manager_gui as gui

CHECKS: dict[str, bool | None] = {
    'tray_icon': None,
    'tray_menu': None,
    'menu_hierarchy': None,
    'open': None,
    'hide': None,
    'show': None,
    'latest_receipt': None,
    'proof_pack': None,
    'quit': None,
    'singleton': None,
}

_EXPECTED_MENU = (
    'Open Cleanroom',
    'Run Scan',
    'Preview Latest Receipt',
    'Open Latest Receipt',
    'Open Proof Pack',
    'Open Archive Folder',
    'Tools',
    'Window',
    'Hide to tray',
    'Show',
    'Quit Cleanroom',
)


def _fail(msg: str) -> None:
    print(f'FAIL: {msg}', file=sys.stderr)
    for k, v in CHECKS.items():
        mark = 'x' if v else ' '
        print(f'[{mark}] {k}')
    raise SystemExit(1)


def _pass_all() -> None:
    print('TRAY VISUAL GATE PASSED')
    for k, v in CHECKS.items():
        mark = 'x' if v else ' '
        print(f'[{mark}] {k}')
    raise SystemExit(0)


def _wait_for_tray(app, timeout: float = 12.0) -> object:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.update_idletasks()
        app.update()
        tray = getattr(app, '_tray', None)
        if tray is not None and tray.is_running:
            return tray
        time.sleep(0.15)
    return getattr(app, '_tray', None)


def run_gate(app: gui.StartupManagerGUI) -> None:
    tray = _wait_for_tray(app)
    if tray is None:
        _fail('tray not initialized after launch sequence')
    if not tray.is_running:
        err = getattr(tray, 'last_error', '') or 'tray not running'
        _fail(f'tray icon not running: {err}')

    CHECKS['tray_icon'] = True
    start = time.time()
    for target in (1.0, 3.0, 5.0):
        while time.time() - start < target:
            app.update_idletasks()
            app.update()
            time.sleep(0.1)
        if not tray.check_health():
            tray._log_diagnostics(f'gate@{int(target)}s')
            _fail(f'tray not healthy after {int(target)}s: {tray.diagnostics_text()}')
    try:
        menu = tray._build_menu()
        CHECKS['tray_menu'] = menu is not None
    except Exception as exc:
        _fail(f'tray menu build failed: {exc}')
    if not CHECKS['tray_menu']:
        _fail('tray menu missing')

    from ui.tray import TrayController
    missing = [label for label in _EXPECTED_MENU if label not in TrayController.MENU_LABELS]
    CHECKS['menu_hierarchy'] = not missing
    if missing:
        _fail(f'tray menu missing labels: {missing}')

    app._tray_show_window()
    app.update_idletasks()
    time.sleep(0.35)
    try:
        CHECKS['open'] = app.winfo_viewable() == 1
    except Exception:
        CHECKS['open'] = False
    if not CHECKS['open']:
        _fail('Open Cleanroom did not bring window forward')

    app._tray_hide_window()
    app.update_idletasks()
    time.sleep(0.35)
    CHECKS['hide'] = app.state() == 'withdrawn'
    if not CHECKS['hide']:
        _fail('Hide to tray did not withdraw window')

    app._tray_show_window()
    app.update_idletasks()
    time.sleep(0.35)
    try:
        CHECKS['show'] = app.winfo_viewable() == 1
    except Exception:
        CHECKS['show'] = False
    if not CHECKS['show']:
        _fail('Show did not restore window')

    from tkinter import messagebox
    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
        setattr(messagebox, fn, lambda *a, **k: True if fn == 'askyesno' else None)

    try:
        app.open_last_receipt()
        CHECKS['latest_receipt'] = True
    except Exception as exc:
        _fail(f'Latest Receipt crashed: {exc}')

    try:
        app.export_audit()
        CHECKS['proof_pack'] = True
    except Exception as exc:
        _fail(f'Proof Pack crashed: {exc}')

    import ui.tray as tray_mod
    first = getattr(app, '_tray', None)
    if first is not None:
        app._shutdown_app(reason='gate-quit')
    else:
        app._shutdown_app(reason='gate-quit-no-tray')
    time.sleep(0.5)
    CHECKS['quit'] = tray_mod.get_active_tray() is None
    if not CHECKS['quit']:
        _fail('shutdown did not clear active tray singleton')
    CHECKS['singleton'] = CHECKS['quit']
    _pass_all()


def main() -> None:
    from tkinter import messagebox
    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno', 'askokcancel'):
        if fn in ('askyesno', 'askokcancel'):
            setattr(messagebox, fn, lambda *a, **k: True)
        else:
            setattr(messagebox, fn, lambda *a, **k: None)

    app = gui.StartupManagerGUI()

    def _start():
        if not getattr(app, '_launch_done', False):
            return app.after(400, _start)
        run_gate(app)

    app.after(12000, _start)
    app.mainloop()


if __name__ == '__main__':
    main()
