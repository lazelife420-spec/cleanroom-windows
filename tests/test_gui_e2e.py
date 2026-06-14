"""End-to-end GUI tests: scan -> selective apply -> restore.

These drive the real Tk application against a temporary sandbox directory,
so nothing outside tmp_path is touched. Skipped automatically when no
display is available.
"""
from pathlib import Path
import os
import sys
import time

import pytest

tests_dir = Path(__file__).resolve().parent
project_dir = tests_dir.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import json

import tkinter as tk
from tkinter import messagebox

import startup_manager_admin
import startup_manager_gui as gui_module


def _display_available():
    try:
        tcl_dir = os.environ.get('TCL_LIBRARY', '')
        if tcl_dir and not (Path(tcl_dir) / 'init.tcl').is_file():
            return False
        root = tk.Tk()
        root.destroy()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    os.environ.get('GITHUB_ACTIONS') == 'true' or not _display_available(),
    reason='GUI e2e runs locally; CI uses screenshot capture gate instead',
)


def make_old(path, days):
    old = time.time() - days * 86400
    os.utime(path, (old, old))


def pump(app, cond, timeout=15.0):
    """Process Tk events until cond() is true or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.update()
        if cond():
            return True
        time.sleep(0.02)
    return cond()


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv('CLEANROOM_DISABLE_ANIMATIONS', '1')
    scan_dir = tmp_path / 'scan'
    scan_dir.mkdir()
    archive_dir = tmp_path / 'archive'
    log_path = tmp_path / 'cleanup_log.json'

    old_zip = scan_dir / 'old_installer.zip'
    old_zip.write_text('fake installer payload', encoding='utf-8')
    make_old(old_zip, 60)

    empty_tmp = scan_dir / 'empty.tmp'
    empty_tmp.write_bytes(b'')
    make_old(empty_tmp, 30)

    fresh = scan_dir / 'fresh_notes.txt'
    fresh.write_text('recent file, should never be a candidate', encoding='utf-8')

    cfg_path = tmp_path / 'config.yaml'
    cfg_path.write_text(
        'paths:\n'
        f'  - {scan_dir}\n'
        'age_days:\n'
        '  temp: 7\n'
        '  installers: 30\n'
        'size_threshold_mb: 200\n'
        "extensions_archive: ['.zip']\n"
        'exclude_patterns: []\n'
        'whitelist: []\n'
        f'archive_dir: {archive_dir}\n'
        f'log_file: {log_path}\n'
        'confirm_threshold_bytes: 99999999999999\n',
        encoding='utf-8')

    # Isolated disabled-startup backup store with one seeded entry
    store = tmp_path / 'disabled_startup.json'
    store.write_text(json.dumps([{
        'name': 'SeededApp',
        'command': 'C:\\seeded\\app.exe',
        'hive': 'HKEY_CURRENT_USER',
        'key': 'Software\\Microsoft\\Windows\\CurrentVersion\\Run',
        'disabled_at': '2026-06-09T00:00:00',
    }]), encoding='utf-8')
    monkeypatch.setattr(startup_manager_admin, 'DISABLED_STORE', store)

    # Keep test receipts/history out of the user's real %LOCALAPPDATA%
    import receipts as receipts_module
    import foresight as foresight_module
    monkeypatch.setattr(receipts_module, 'RECEIPT_DIR', tmp_path / 'receipts')
    monkeypatch.setattr(foresight_module, 'HISTORY_PATH', tmp_path / 'disk_history.json')
    monkeypatch.setattr(foresight_module, 'HEALTH_PATH', tmp_path / 'health_history.json')

    # Auto-answer every dialog so tests never block on a modal popup.
    dialogs = {'info': [], 'warning': [], 'error': [], 'yesno': []}
    monkeypatch.setattr(messagebox, 'showinfo', lambda *a, **k: dialogs['info'].append(a))
    monkeypatch.setattr(messagebox, 'showwarning', lambda *a, **k: dialogs['warning'].append(a))
    monkeypatch.setattr(messagebox, 'showerror', lambda *a, **k: dialogs['error'].append(a))
    monkeypatch.setattr(messagebox, 'askyesno', lambda *a, **k: dialogs['yesno'].append(a) or True)

    # Proof Report is modal — stub it so apply_cleanup tests don't hang.
    proof_captures = []

    def _capture_proof(self, log, prf, **kw):
        proof_captures.append({'log': log, 'proof': prf, **kw})

    monkeypatch.setattr(gui_module.StartupManagerGUI, '_show_proof_report', _capture_proof)

    app = gui_module.StartupManagerGUI(config_path=cfg_path, restore_log_path=log_path)
    app.update_idletasks()
    app._finish_launch_sequence()
    app.refresh_cleanup()
    assert pump(app, lambda: getattr(app, '_scan_session_done', False), timeout=30), \
        'startup scan did not finish'
    for tab_idx in (2, 4, 5):
        app._lazy_load_tab(tab_idx)
        app.update()
    app.withdraw()
    try:
        yield {
            'app': app,
            'scan_dir': scan_dir,
            'archive_dir': archive_dir,
            'log_path': log_path,
            'old_zip': old_zip,
            'empty_tmp': empty_tmp,
            'fresh': fresh,
            'dialogs': dialogs,
            'proof_captures': proof_captures,
        }
    finally:
        try:
            tray = getattr(app, '_tray', None)
            if tray:
                tray.stop()
                app._tray = None
        except Exception:
            pass
        try:
            app.destroy()
        except Exception:
            pass


def test_scan_finds_expected_candidates(sandbox):
    app = sandbox['app']
    assert pump(app, lambda: len(app.cleanup_items) == 2), \
        f'expected 2 candidates, got {len(app.cleanup_items)}: {app.cleanup_items}'
    reasons = {item['reason'] for item in app.cleanup_items}
    assert reasons == {'zero-byte', 'installer/archive'}
    paths = {item['path'] for item in app.cleanup_items}
    assert str(sandbox['fresh']) not in paths
    # everything checked by default and rendered in the tree
    assert app.cleanup_selected == {0, 1}
    assert len(app.cleanup_tree.get_children()) == 2


def test_selective_apply_archives_only_checked_items(sandbox):
    app = sandbox['app']
    assert pump(app, lambda: len(app.cleanup_items) == 2)

    # Uncheck the zero-byte file; archive only the old zip.
    zero_idx = next(i for i, item in enumerate(app.cleanup_items) if item['reason'] == 'zero-byte')
    app._toggle_cleanup_index(zero_idx)
    assert zero_idx not in app.cleanup_selected

    app.apply_cleanup()
    assert pump(app, lambda: not sandbox['old_zip'].exists())
    # the worker writes the log after moving files; wait for it too
    assert pump(app, lambda: sandbox['log_path'].exists())

    archived = list(sandbox['archive_dir'].glob('*'))
    assert [p.name for p in archived] == ['old_installer.zip']
    assert sandbox['empty_tmp'].exists(), 'unchecked file must not be touched'

    # apply triggers a restore-log reload; entry should appear
    assert pump(app, lambda: len(app.restore_entries) == 1)
    src, dest, ts, entry = app.restore_entries[0]
    assert src == str(sandbox['old_zip'])
    assert Path(dest).exists()


def test_apply_writes_receipt_with_proof_and_custody_verifies(sandbox):
    import receipts as receipts_module
    app = sandbox['app']
    assert pump(app, lambda: len(app.cleanup_items) == 2)
    app.apply_cleanup()
    assert pump(app, lambda: receipts_module.latest_receipt() is not None)
    assert pump(app, lambda: len(sandbox['proof_captures']) == 1)

    text = Path(receipts_module.latest_receipt()).read_text(encoding='utf-8')
    assert 'PROOF (measured by the OS, not estimated):' in text
    assert 'Custody check' in text
    assert '2/2 archived item(s) verified present' in text
    cap = sandbox['proof_captures'][0]
    assert cap['proof']['custody']['verified'] == 2

    app.refresh_activity()
    assert len(app.activity_tree.get_children()) == 2
    assert app.stat_act_present.cget('text') == '2'
    assert '100' in app.hdr_trust_value.cget('text')

    # Verify Custody tool over the whole history reports everything present
    app.verify_custody()
    assert pump(app, lambda: 'CUSTODY VERIFIED' in app.global_status.cget('text'))
    assert pump(app, lambda: '2/2' in app.global_status.cget('text'))


def test_export_audit_writes_html(sandbox, tmp_path, monkeypatch):
    import audit as audit_module
    app = sandbox['app']
    assert pump(app, lambda: len(app.cleanup_items) == 2)
    app.apply_cleanup()
    assert pump(app, lambda: sandbox['log_path'].exists())

    out = tmp_path / 'proof.html'
    monkeypatch.setattr(app, 'export_audit', lambda: None)  # avoid os.startfile in test

    import ledger as ledger_module
    import proof as proof_module
    entries = app._load_log_dicts()
    feed = ledger_module.build_activity_feed(
        __import__('restore').load_log(str(sandbox['log_path'])))
    custody = proof_module.verify_entries(entries)
    summary = ledger_module.summarize_feed(feed)
    trust = ledger_module.trust_score(custody['verified'], custody['total'])
    audit_module.export_html_audit(feed, custody, summary, trust, out)
    html = out.read_text(encoding='utf-8')
    assert 'CUSTODY VERIFIED' in html
    assert 'Trust score' in html
    assert 'old_installer.zip' in html or 'empty.tmp' in html


def test_restore_returns_file_to_original_location(sandbox):
    app = sandbox['app']
    assert pump(app, lambda: len(app.cleanup_items) == 2)
    app.apply_cleanup()
    assert pump(app, lambda: len(app.restore_entries) == 2)
    assert not sandbox['old_zip'].exists()

    # Select the archived zip in the restore tree and restore it.
    target_row = None
    for row in app.restore_tree.get_children():
        if app.restore_tree.set(row, 'src') == str(sandbox['old_zip']):
            target_row = row
            break
    assert target_row is not None
    app.restore_tree.selection_set(target_row)
    app.update()
    app.restore_selected_entry(apply=True)
    assert pump(app, lambda: sandbox['old_zip'].exists())
    assert sandbox['old_zip'].read_text(encoding='utf-8') == 'fake installer payload'


def test_file_preview_renders_jpeg_and_text(sandbox, tmp_path):
    pil = pytest.importorskip('PIL.Image')
    app = sandbox['app']
    app.update()

    jpg = tmp_path / 'photo.jpg'
    pil.new('RGB', (640, 480), (40, 90, 200)).save(jpg, 'JPEG')
    app._update_file_preview(str(jpg))
    app.update()
    assert app._preview_photo is not None, 'JPEG preview should produce a rendered photo'

    txt = tmp_path / 'readme.txt'
    txt.write_text('hello preview', encoding='utf-8')
    app._update_file_preview(str(txt))
    app.update()
    assert 'hello preview' in app.preview_text.get('1.0', 'end')


def test_disabled_category_lists_backups_and_offers_reenable(sandbox):
    app = sandbox['app']
    assert pump(app, lambda: len(app.data.get('disabled', [])) == 1)

    app._set_category('Disabled')
    app.update()
    rows = app.tree.get_children()
    assert len(rows) == 1
    vals = app.tree.item(rows[0])['values']
    assert vals[0] == 'SeededApp'
    assert vals[1] == 'Disabled backup'
    assert vals[2] == 'disabled'
    assert 'restorable' in str(vals[3]).lower()

    # Selecting a disabled entry flips the action button to re-enable mode
    app.tree.selection_set(rows[0])
    app.update()
    assert app.enable_btn.cget('text') == 'Re-enable Selected'
    assert str(app.enable_btn.cget('state')) == 'normal'
    assert str(app.disable_btn.cget('state')) == 'disabled'
    assert app.disabled_label.cget('text') == '1'


def test_settings_tab_roundtrips_config(sandbox):
    import yaml as yaml_mod
    app = sandbox['app']
    app.update()

    # Form is pre-populated from the sandbox config
    assert list(app.set_paths_list.get(0, 'end')) == [str(sandbox['scan_dir'])]
    assert app.set_size_mb.get() == 200

    # Change values and save
    app.set_size_mb.set(50)
    app.set_temp_age.set(14)
    app.set_exclude_text.insert('end', '\n*.keepme')
    app.save_settings()
    assert pump(app, lambda: 'saved' in app.settings_status_lbl.cget('text').lower())

    saved = yaml_mod.safe_load(Path(app.cleanup_config_path).read_text(encoding='utf-8'))
    assert saved['size_threshold_mb'] == 50
    assert saved['age_days']['temp'] == 14
    assert '*.keepme' in saved['exclude_patterns']
    assert saved['paths'] == [str(sandbox['scan_dir'])]
    # unknown keys preserved
    assert 'log_file' in saved


def test_restore_preview_pane_shows_details(sandbox):
    app = sandbox['app']
    assert pump(app, lambda: len(app.cleanup_items) == 2)
    app.apply_cleanup()
    assert pump(app, lambda: len(app.restore_entries) == 2)

    first = app.restore_tree.get_children()[0]
    app.restore_tree.selection_set(first)
    app._on_restore_select()
    app.update()
    assert app.restore_detail_src.cget('text') != 'Original: —'
    assert 'Yes' in app.restore_detail_exists.cget('text')


def test_uninstaller_tab_lists_programs_and_filters(sandbox):
    app = sandbox['app']
    app.tab_control.select(app.uninstall_tab)
    app.update()
    # The live registry scan should find at least one installed program.
    assert pump(app, lambda: len(app.uninstall_entries) > 0), \
        'expected installed programs from the registry'
    assert len(app.uninstall_tree.get_children()) == len(app.uninstall_entries)
    assert 'programs' in app.uninst_count_lbl.cget('text')

    # Filter narrows the tree to matching names/publishers.
    target = app.uninstall_entries[0]['name'][:6]
    app.uninst_filter_var.set(target)
    app._populate_uninstall_tree()
    shown = len(app.uninstall_tree.get_children())
    expected = sum(1 for e in app.uninstall_entries
                   if target.lower() in e['name'].lower()
                   or target.lower() in e['publisher'].lower())
    assert shown == expected
    assert shown >= 1

    # Clearing the filter restores all rows.
    app.uninst_filter_var.set('')
    app._populate_uninstall_tree()
    assert len(app.uninstall_tree.get_children()) == len(app.uninstall_entries)


def test_time_machine_rolls_back_a_day(sandbox):
    import timeline as timeline_module
    import restore as restore_module
    app = sandbox['app']
    assert pump(app, lambda: len(app.cleanup_items) == 2)
    app.apply_cleanup()
    assert pump(app, lambda: sandbox['log_path'].exists())
    assert pump(app, lambda: len(app.restore_entries) == 2)
    assert not sandbox['old_zip'].exists()

    actions = restore_module.load_log(str(sandbox['log_path']))
    buckets = timeline_module.build_timeline(actions)
    assert len(buckets) == 1
    today = buckets[0]
    assert today['count'] == 2
    assert today['restorable'] == 2

    restored, skipped, failed, msgs = timeline_module.rollback_day(
        today, lambda s, d: restore_module.restore_one(s, d, apply=True))
    assert (restored, skipped, failed) == (2, 0, 0), msgs
    assert sandbox['old_zip'].exists()
    assert sandbox['empty_tmp'].exists()


def test_uninstaller_checkboxes_and_chips(sandbox):
    from datetime import datetime, timedelta
    app = sandbox['app']
    # Let the startup program scan settle (result or error) so a late rescan
    # can't overwrite the deterministic list injected below.
    pump(app, lambda: app.uninst_status_lbl.cget('text') != 'Scanning installed programs…',
         timeout=30)

    def day(days_ago):
        return (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')

    def prog(name, size_kb, install_date):
        return {'name': name, 'publisher': 'MegaCorp', 'version': '1.0',
                'size_kb': size_kb, 'install_date': install_date,
                'uninstall_string': 'x', 'quiet_uninstall_string': '',
                'hive': 'HKEY_CURRENT_USER', 'key': 'K', 'subkey': name}

    app.uninstall_entries = [
        prog('BigOldApp', 2 * 1024 * 1024, day(400)),
        prog('FreshApp', 512, day(5)),
        prog('NoDateApp', 256, ''),
    ]
    app.uninst_checked.clear()
    app._set_uninstall_mode('all')
    assert len(app.uninstall_tree.get_children()) == 3

    # Checking two programs makes them the batch target
    app._toggle_uninstall_check(0)
    second = int(app.uninstall_tree.get_children()[1])
    app._toggle_uninstall_check(second)
    assert app.uninst_checked == {0, second}
    assert len(app._selected_programs()) == 2
    assert 'checked' in app.uninst_count_lbl.cget('text')
    first_iid = app.uninstall_tree.get_children()[0]
    assert app.uninstall_tree.set(first_iid, 'sel') in ('☑', '☐')

    # Header toggle: check all visible, then uncheck all
    app._toggle_all_uninstall_checks()
    visible = len(app.uninstall_tree.get_children())
    assert len(app.uninst_checked) == visible
    app._toggle_all_uninstall_checks()
    assert app.uninst_checked == set()

    # Smart filter chips narrow the list per filter_programs
    expected_names = {'large': ['BigOldApp'], 'recent': ['FreshApp'],
                      'old': ['BigOldApp'], 'all': ['BigOldApp', 'FreshApp', 'NoDateApp']}
    for mode, names in expected_names.items():
        app._set_uninstall_mode(mode)
        shown = [app.uninstall_tree.set(iid, 'name')
                 for iid in app.uninstall_tree.get_children()]
        assert shown == names, mode
    assert app.uninst_mode == 'all'


def test_registry_health_dialog_repairs_checked_issues(sandbox, monkeypatch):
    import registry_health as rh_mod
    app = sandbox['app']
    issues = [
        {'type': 'startup-ref', 'fix': 'delete-value', 'hive': 'HKEY_CURRENT_USER',
         'key': r'Software\Run', 'value_name': 'Dead', 'display': 'Dead',
         'detail': 'startup command points to missing file: C:\\gone\\a.exe'},
        {'type': 'uninstall-entry', 'fix': 'delete-key', 'hive': 'HKEY_CURRENT_USER',
         'key': r'Software\Uninstall\Gone', 'value_name': None, 'display': 'Gone',
         'detail': 'uninstaller missing'},
    ]
    captured = {}

    def fake_archive(chosen, archive_dir, log_file, **kw):
        captured['chosen'] = chosen
        return [{'src': 'REGISTRY::x', 'dest': 'y', 'reason': 'broken-registry',
                 'size': 1, 'when': '2026-06-10T00:00:00'}]

    monkeypatch.setattr(rh_mod, 'archive_registry_issues', fake_archive)
    app._show_registry_health_dialog(issues)
    app.update()
    app._reg_health_repair()
    assert pump(app, lambda: 'chosen' in captured)
    # uninstall-entry issues default to unchecked; only the startup ref is repaired
    assert [i['display'] for i in captured['chosen']] == ['Dead']


def test_smart_restore_routes_registry_entries(sandbox, tmp_path):
    import uninstaller as uninst_mod
    app = sandbox['app']

    reg_file = tmp_path / 'export.reg'
    reg_file.write_text('Windows Registry Editor Version 5.00\n')
    src = uninst_mod.REG_PREFIX + r'HKEY_CURRENT_USER\SOFTWARE\FooPlayer'

    # Dry-run on an existing export says it would import; missing export fails.
    ok, msg = app._smart_restore(src, str(reg_file), apply=False)
    assert ok and 'import' in msg
    ok, msg = app._smart_restore(src, str(tmp_path / 'gone.reg'), apply=False)
    assert not ok and 'missing' in msg

    # Plain file entries still go through restore.restore_one
    archived = tmp_path / 'plain.txt'
    archived.write_text('x')
    target = tmp_path / 'home' / 'plain.txt'
    ok, msg = app._smart_restore(str(target), str(archived), apply=False)
    assert ok and 'would move' in msg


def test_uninstaller_leftover_archive_shows_in_restore(sandbox, tmp_path):
    import uninstaller as uninst_mod
    app = sandbox['app']

    leftover = tmp_path / 'roots' / 'FooPlayer'
    leftover.mkdir(parents=True)
    (leftover / 'cache.bin').write_bytes(b'x' * 10)

    found = uninst_mod.find_leftovers('FooPlayer 2.0', roots=[tmp_path / 'roots'])
    assert found == [str(leftover)]

    moved = uninst_mod.archive_leftovers(found, sandbox['archive_dir'],
                                         str(sandbox['log_path']))
    assert len(moved) == 1
    assert not leftover.exists()

    app.refresh_restore()
    assert pump(app, lambda: len(app.restore_entries) >= 1)
    # entries are (src, dest, ts, raw) tuples
    srcs = {src for src, _, _, _ in app.restore_entries}
    assert str(leftover) in srcs
    raws = [raw for _, _, _, raw in app.restore_entries if isinstance(raw, dict)]
    assert any(r.get('reason') == 'uninstall-leftover' for r in raws)
