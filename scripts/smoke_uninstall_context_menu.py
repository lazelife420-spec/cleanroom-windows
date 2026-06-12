"""Quick smoke test for uninstaller right-click context menu."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ['CLEANROOM_DISABLE_ANIMATIONS'] = '1'

from tkinter import messagebox

import startup_manager_gui as gui_module


def main() -> int:
    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
        setattr(messagebox, fn, lambda *a, **k: True if fn == 'askyesno' else None)

    app = gui_module.StartupManagerGUI()
    app.update_idletasks()
    app.refresh_uninstaller = lambda: None  # keep synthetic entries
    app._finish_launch_sequence()
    app.uninstall_entries = [{
        'name': 'Test App',
        'version': '1.0',
        'publisher': 'Acme',
        'install_date': '2024-01-01',
        'size_kb': 1024,
        'uninstall_string': 'unins.exe /S',
        'quiet_uninstall_string': 'unins.exe /SILENT',
        'hive': 'HKEY_LOCAL_MACHINE',
        'key': r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'subkey': 'TestApp',
    }]
    app._populate_uninstall_tree()
    iid = app.uninstall_tree.get_children()[0]
    app.uninstall_tree.selection_set(iid)

    app._ensure_uninstall_context_menu()
    menu = app._uninst_context_menu
    labels = [
        menu.entrycget(i, 'label')
        for i in range(menu.index('end') + 1)
        if menu.type(i) != 'separator'
    ]
    required = (
        'Uninstall…', 'Scan Leftovers…', 'Force Remove…',
        'Check / Uncheck', 'Copy program name', 'Copy uninstall command',
        'Copy registry key', 'Refresh list',
    )
    missing = [r for r in required if r not in labels]
    if missing:
        print('FAIL: missing menu items:', missing)
        app.destroy()
        return 1

    class FakeEvent:
        x_root = 100
        y_root = 100
        x = 50
        y = 10

    # Right-click selects row under cursor when possible
    app._on_uninstall_right_click(FakeEvent())
    app.update()

    entry = app.uninstall_entries[0]
    key_text = app._uninstall_registry_key_text(entry)
    assert 'TestApp' in key_text
    assert 'HKEY_LOCAL_MACHINE' in key_text

    app._uninstall_ctx_toggle_check()
    assert 0 in app.uninst_checked
    app._uninstall_ctx_check_all()
    assert 0 in app.uninst_checked
    app._uninstall_ctx_uncheck_all()
    assert 0 not in app.uninst_checked

    # Copy helpers run without error (clipboard may be unavailable headless)
    app._uninstall_copy_name()
    app._uninstall_copy_command()
    app._uninstall_copy_registry_key()

    app.destroy()
    print('CONTEXT MENU SMOKE: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
