#!/usr/bin/env python3
"""Manual gate: in-app + Explorer context menus (HKCU shell keys, custody-only delete).

Run from repo root:

    python scripts/shell_context_menu_manual_gate.py

Exit 0 only if all hard gates pass.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import archive_custody as ac
import shell_actions as sa
import shell_context_menu as scm

if sys.platform != 'win32':
    print('SKIP: Windows-only gate (registry + Explorer shell menus)')
    raise SystemExit(0)


def _ok(label: str) -> None:
    print(f'[x] {label}')


def _fail(label: str, detail: str = '') -> None:
    msg = f'[ ] {label}'
    if detail:
        msg += f' — {detail}'
    print(msg)


def main() -> int:
    failed = []

    def check(cond, label, detail=''):
        if cond:
            _ok(label)
        else:
            _fail(label, detail)
            failed.append(label)

    gate_root = Path(tempfile.mkdtemp(prefix='cleanroom-shell-gate-'))
    archive_dir = gate_root / 'archive'
    archive_dir.mkdir()
    live_file = gate_root / 'live-only.txt'
    live_file.write_text('never delete via custody', encoding='utf-8')
    archived = archive_dir / 'custody-item.txt'
    archived.write_text('archived copy', encoding='utf-8')

    log_path = gate_root / 'cleanup_log.json'
    log_path.write_text(json.dumps([{
        'src': str(gate_root / 'was-here.txt'),
        'dest': str(archived),
        'reason': 'temp',
        'size': 14,
        'when': '2020-01-01T00:00:00',
    }]), encoding='utf-8')

    cfg = {
        'archive_dir': str(archive_dir),
        'log_file': str(log_path),
    }

    def load_cfg(_path=None):
        return cfg

    sa._load_config = load_cfg  # noqa: SLF001 — gate injects disposable cfg

    ok, msg = sa.delete_archive_path(live_file)
    check(not ok and 'not under' in msg.lower(), 'Delete refuses non-archive live paths', msg)

    orphan = archive_dir / 'orphan.txt'
    orphan.write_text('no log entry', encoding='utf-8')
    ok2, msg2 = sa.delete_archive_path(orphan)
    check(not ok2 and 'custody' in msg2.lower(), 'Delete refuses archive paths without custody record', msg2)

    ok3, msg3 = sa.delete_archive_path(archived)
    check(ok3, 'Delete removes custody-backed archive copy', msg3)
    check(not archived.exists(), 'Archived custody file removed')
    check(live_file.exists(), 'Live decoy untouched after custody delete')

    src_move = gate_root / 'to-archive.txt'
    src_move.write_text('move me', encoding='utf-8')
    ok4, msg4 = sa.archive_path(src_move)
    check(ok4 and not src_move.exists(), 'Archive with Cleanroom moves source into archive (not silent delete)', msg4)
    check(any(archive_dir.iterdir()), 'Archive folder receives moved file')

    scm_src = (ROOT / 'shell_context_menu.py').read_text(encoding='utf-8')
    check('HKEY_CURRENT_USER' in scm_src, 'Shell installer uses HKCU only')
    check('HKEY_LOCAL_MACHINE' not in scm_src, 'Shell installer does not touch HKLM')

    gui_src = (ROOT / 'startup_manager_gui.py').read_text(encoding='utf-8')
    check('def _run_archive_delete' in gui_src, 'Central delete handler exists')
    check('_show_delete_archive_confirm' in gui_src,
          'Delete from Archive uses summary confirmation dialog')
    check("'Delete All Safe'" in gui_src, 'Delete all safe requires confirmation')
    check('open_shell_context_menu_tool' in gui_src, 'Explorer context menu builder present')
    check('_on_archive_right_click' in gui_src, 'In-app Archive right-click wired')
    check('_on_restore_right_click' in gui_src, 'In-app Restore right-click wired')

    cfg_path = gate_root / 'shell_menus.json'
    scm.menus_config_path = lambda: cfg_path  # noqa: SLF001
    test_cfg = scm.default_config()
    test_cfg['presets']['archive_file'] = True
    test_cfg['custom'].append({
        'id': 'custom_gate',
        'label': 'Gate Custom',
        'target': 'all_files',
        'action': 'open_archive_tab',
        'custom_args': '',
        'enabled': True,
    })
    scm.save_config(test_cfg)
    check(cfg_path.is_file(), 'Custom menus persist locally')

    fake_exe = str(gate_root / 'Cleanroom.exe')
    Path(fake_exe).write_text('', encoding='utf-8')
    scm.uninstall_all(test_cfg)
    installed = scm.install_all(fake_exe, test_cfg)
    check(len(installed) >= 2, 'Install to Explorer writes Cleanroom shell menus', f'{len(installed)}')
    keys = scm.list_installed_cleanroom_keys()
    check(len(keys) >= 2, 'Installed keys visible under HKCU', f'{keys!r}')
    for root, _name in keys:
        check(root.startswith('Software\\Classes'), 'Shell keys live under HKCU Software\\Classes only', root)

    remaining = scm.uninstall_cleanroom_shell_keys()
    check(len(remaining) == 0, 'Remove from Explorer clears all Cleanroom shell keys', f'{remaining!r}')

    reloaded = scm.load_config()
    check(reloaded['custom'][0]['label'] == 'Gate Custom', 'Custom menu config survives install/remove cycle')

    print('\n=== Summary ===')
    if failed:
        print(f'GATE FAILED ({len(failed)}):')
        for f in failed:
            print(f'  - {f}')
        print(f'\nGate folder preserved: {gate_root}')
        return 1
    print('SHELL CONTEXT MENU MANUAL GATE PASSED')
    print(f'Gate folder: {gate_root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
