#!/usr/bin/env python3
"""Gate: row-based tables expose right-click context menus via _show_row_popover."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUI = (ROOT / 'startup_manager_gui.py').read_text(encoding='utf-8')

REQUIRED = (
    ('Home recommendations', '_on_recommendation_card_right', '_show_row_popover'),
    ('Cleaner candidates', '_on_cleanup_right_click', '_show_row_popover'),
    ('Archive custody', '_on_archive_right_click', '_show_row_popover'),
    ('Proof ledger', '_on_activity_right_click', '_show_row_popover'),
    ('Startup rows', '_on_startup_right_click', '_show_row_popover'),
    ('Uninstaller rows', '_on_uninstall_right_click', '_show_row_popover'),
    ('Settings paths', '_on_settings_paths_right_click', '_show_row_popover'),
    ('Explorer custom menus', '_on_shell_custom_right', '_show_row_popover'),
)

BIND_REQUIRED = (
    ("set_paths_list.bind('<Button-3>'", 'Settings folder list'),
    ("cleanup_tree.bind('<Button-3>'", 'Cleaner tree'),
    ("custom_list.bind('<Button-3>'", 'Explorer custom list'),
)


def main() -> int:
    failed = []
    for label, handler, popover in REQUIRED:
        if handler not in GUI:
            failed.append(f'{label}: missing {handler}')
            continue
        block = GUI.split(f'def {handler}', 1)[-1].split('\n    def ', 1)[0]
        if popover not in block:
            failed.append(f'{label}: {handler} does not call {popover}')
    for needle, label in BIND_REQUIRED:
        if needle not in GUI:
            failed.append(f'{label}: missing bind {needle}')
    if failed:
        print('context_menu_gate: FAIL')
        for line in failed:
            print(f'  - {line}')
        return 1
    print('context_menu_gate: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
