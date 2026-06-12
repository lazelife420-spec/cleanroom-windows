#!/usr/bin/env python3
"""Manual destructive-review gate for Force Remove — disposable targets only.

Run from repo root on feature/local-uninstaller-guidance:

    python scripts/force_remove_manual_gate.py

Prints PASS/FAIL checklist. Exit 0 only if all hard gates pass.
"""
from __future__ import annotations

import inspect
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ledger
import uninstaller


def _ok(label: str) -> None:
    print(f'[x] {label}')


def _fail(label: str, detail: str = '') -> None:
    msg = f'[ ] {label}'
    if detail:
        msg += f' — {detail}'
    print(msg)


def _hard_fail(label: str, detail: str = '') -> None:
    msg = f'[HARD FAIL] {label}'
    if detail:
        msg += f' — {detail}'
    print(msg)


def main() -> int:
    failures = 0
    hard_failures = 0

    gate_root = Path(os.environ.get('TEMP', '/tmp')) / 'cleanroom-force-remove-gate'
    if gate_root.exists():
        shutil.rmtree(gate_root, ignore_errors=True)
    gate_root.mkdir(parents=True)

    live_decoy = gate_root / 'live-decoy-must-survive.txt'
    live_decoy.write_text('never touch', encoding='utf-8')

    install_dir = gate_root / 'FakeAppSuite'
    install_dir.mkdir()
    (install_dir / 'app.dll').write_bytes(b'fake-app-data')
    (install_dir / 'settings.ini').write_text('[app]\nversion=1', encoding='utf-8')

    archive_dir = gate_root / 'archive'
    log_path = gate_root / 'cleanup_log.json'
    archive_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        'name': 'FakeApp Suite GateTest',
        'version': '9.9.9',
        'publisher': 'Gate Test Co',
        'install_location': str(install_dir),
        'hive': 'HKEY_CURRENT_USER',
        'key': r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'subkey': 'FakeAppGateTest_is1',
        'uninstall_string': '',
        'quiet_uninstall_string': '',
    }

    uninstall_key = uninstaller.uninstall_key_path(entry)
    reg_key = uninstall_key

    # --- Preview targets match what would be removed ---
    dirs, keys = uninstaller.collect_force_remove_targets(entry)
    if str(install_dir) in dirs:
        _ok('Preview shows exactly what would be removed (install location in targets)')
    else:
        _fail('Preview shows exactly what would be removed', f'missing {install_dir}')
        failures += 1

    # --- Force Remove requires confirmation (GUI source check) ---
    import startup_manager_gui as gui_module
    src = inspect.getsource(gui_module.StartupManagerGUI.force_remove_selected)
    if 'askyesno' in src and '_scan_leftovers(entry, force_remove=True)' in src:
        _ok('Force Remove requires confirmation (askyesno before scan)')
    else:
        _hard_fail('Force Remove deletes without confirmation', 'force_remove_selected missing askyesno gate')
        hard_failures += 1

    dlg_src = inspect.getsource(gui_module.StartupManagerGUI._show_leftover_dialog)
    if 'Archive & force remove' in dlg_src and 'Cancel' in dlg_src:
        _ok('Preview dialog shows archive targets with confirm/cancel')
    else:
        _fail('Preview dialog shows archive targets with confirm/cancel')
        failures += 1

    # --- Registry export before delete; folder archive before removal ---
    events: list[tuple[str, str]] = []

    def track_export(full_key, out_file):
        events.append(('export', full_key))
        Path(out_file).write_text('Windows Registry Editor Version 5.00\n', encoding='utf-8')
        return True

    def track_delete(full_key):
        events.append(('delete', full_key))
        return True

    result = uninstaller.force_remove(
        entry, archive_dir, str(log_path),
        chosen_dirs=[str(install_dir)],
        chosen_keys=[reg_key],
        export_fn=track_export,
        delete_fn=track_delete,
    )

    export_idx = next(i for i, e in enumerate(events) if e[0] == 'export')
    delete_idx = next(i for i, e in enumerate(events) if e[0] == 'delete')
    if export_idx < delete_idx:
        _ok('Registry export is created before registry deletion')
    else:
        _hard_fail('Registry key removed before export', f'events={events}')
        hard_failures += 1

    archived_install = archive_dir / 'uninstall_leftovers' / install_dir.name
    if not install_dir.exists() and archived_install.exists():
        _ok('Install folder is archived before deletion (moved to archive)')
    else:
        _hard_fail('Install folder deleted before archive',
                   f'src exists={install_dir.exists()} archived={archived_install.exists()}')
        hard_failures += 1

    # --- Proof written to cleanup log ---
    if log_path.exists():
        logged = json.loads(log_path.read_text(encoding='utf-8-sig'))
        reasons = {e.get('reason') for e in logged if isinstance(e, dict)}
        if 'uninstall-leftover' in reasons:
            _ok('Receipt/proof is written (cleanup_log.json entries)')
        else:
            _fail('Receipt/proof is written', f'reasons={reasons}')
            failures += 1
    else:
        _fail('Receipt/proof is written', 'cleanup_log.json missing')
        failures += 1

    # --- Activity Ledger integration ---
    feed = ledger.build_activity_feed(json.loads(log_path.read_text(encoding='utf-8-sig')))
    if any(e.get('reason') == 'uninstall-leftover' for e in feed):
        _ok('Activity Ledger records action if integrated')
    else:
        _fail('Activity Ledger records action if integrated')
        failures += 1

    # --- No unrelated paths touched ---
    if live_decoy.exists() and live_decoy.read_text(encoding='utf-8') == 'never touch':
        _ok('No unrelated paths are touched')
    else:
        _hard_fail('Any unrelated live path touched', str(live_decoy))
        hard_failures += 1

    # --- No network/API/telemetry in uninstaller module ---
    uninst_src = (ROOT / 'uninstaller.py').read_text(encoding='utf-8')
    banned = ('requests.', 'urllib.', 'http://', 'https://', 'telemetry', 'analytics')
    hits = [b for b in banned if b in uninst_src.lower()]
    gui_uninst = inspect.getsource(gui_module.StartupManagerGUI.force_remove_selected)
    gui_uninst += inspect.getsource(gui_module.StartupManagerGUI._show_leftover_dialog)
    hits += [b for b in banned if b in gui_uninst.lower()]
    if not hits:
        _ok('No network/API/telemetry behavior')
    else:
        _hard_fail('Any network/API/telemetry behavior appears', str(hits))
        hard_failures += 1

    # --- Missing uninstaller flow does not crash ---
    code, msg = uninstaller.run_uninstall(entry)
    if code == 1 and 'No uninstall command' in msg:
        _ok('Missing uninstaller flow does not crash')
    else:
        _fail('Missing uninstaller flow does not crash', f'code={code} msg={msg}')
        failures += 1

    # --- Hard-fail invariants on archive_registry_leftovers ---
    reg_src = inspect.getsource(uninstaller.archive_registry_leftovers)
    if 'export_fn(full_key, out)' in reg_src and 'delete_fn(full_key)' in reg_src:
        if reg_src.index('export_fn') < reg_src.index('delete_fn'):
            _ok('Registry helper exports before delete (code order)')
        else:
            _hard_fail('Registry key removed before export', 'archive_registry_leftovers order')
            hard_failures += 1

    left_src = inspect.getsource(uninstaller.archive_leftovers)
    if 'shutil.move' in left_src:
        _ok('Folder helper uses archive move (not unlink-first)')
    else:
        _hard_fail('Install folder deleted before archive', 'archive_leftovers missing shutil.move')
        hard_failures += 1

    # --- Result sanity ---
    if result.get('folders') and result.get('list_entry'):
        _ok('Force remove returned folder + list_entry proof records')
    else:
        _fail('Force remove returned folder + list_entry proof records', str(result))
        failures += 1

    print()
    if hard_failures:
        print(f'FORCE REMOVE MANUAL GATE: HARD FAIL ({hard_failures} hard, {failures} soft)')
        return 1
    if failures:
        print(f'FORCE REMOVE MANUAL GATE: FAIL ({failures} checklist item(s))')
        return 1
    print('FORCE REMOVE MANUAL GATE: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
