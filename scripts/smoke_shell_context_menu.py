"""Smoke test for Archive/Restore in-app right-click context menus."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ['CLEANROOM_DISABLE_ANIMATIONS'] = '1'

from tkinter import messagebox

import archive_custody as ac
import startup_manager_gui as gui_module


def _menu_labels(menu):
    return [
        menu.entrycget(i, 'label')
        for i in range(menu.index('end') + 1)
        if menu.type(i) != 'separator'
    ]


def main() -> int:
    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno', 'askokcancel'):
        if fn == 'askyesno' or fn == 'askokcancel':
            setattr(messagebox, fn, lambda *a, **k: True)
        else:
            setattr(messagebox, fn, lambda *a, **k: None)

    app = gui_module.StartupManagerGUI()
    app.update_idletasks()
    app._finish_launch_sequence()

    app._archive_records_all = [{
        'when': '2020-01-01T00:00:00',
        'src': r'C:\orig\a.txt',
        'dest': r'C:\arch\a.txt',
        'reason': 'temp',
        'size': 10,
        'restorable': True,
        'receipt_path': None,
        'prune_rank': ac.PRUNE_SAFE,
    }]
    app._apply_archive_view_filters()
    app.archive_tree.selection_set('0')

    app._ensure_archive_context_menu()
    archive_labels = _menu_labels(app._archive_context_menu)
    for req in (
        'Restore Selected', 'Delete from Archive…', 'Open Archive Location',
        'Copy archive path', 'Select all safe to delete', 'Refresh',
    ):
        if req not in archive_labels:
            print('FAIL: Archive menu missing', req)
            app.destroy()
            return 1

    app._archive_copy_path()
    app._archive_copy_original_path()

    app.restore_entries = [(r'C:\orig\b.txt', r'C:\arch\b.txt', '2020-01-01', {})]
    app._update_restore_tree()
    app.restore_tree.selection_set(app.restore_tree.get_children()[0])

    app._ensure_restore_context_menu()
    restore_labels = _menu_labels(app._restore_context_menu)
    for req in (
        'Restore Selected', 'Delete from Archive…', 'Open Archived File',
        'Copy original path', 'Reload log',
    ):
        if req not in restore_labels:
            print('FAIL: Restore menu missing', req)
            app.destroy()
            return 1

    app._restore_copy_original()
    app._restore_copy_archive()

    app.destroy()
    print('IN-APP CONTEXT MENU SMOKE: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
