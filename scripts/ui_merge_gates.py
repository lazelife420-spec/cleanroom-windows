#!/usr/bin/env python3
"""Pre-merge UI gates: scaling/layout checks for CustomTkinter shell.

Run on ui/local-only-polish before merging PR #6:
  python scripts/ui_merge_gates.py
  python scripts/ui_merge_gates.py --packaged dist/Cleanroom/Cleanroom.exe
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GEOMETRIES = (
    (1080, 700, '1080x700-default'),
    (1050, 680, '1050x680'),
    (920, 580, '920x580-min'),
    (1920, 1080, '1920x1080-ultrawide'),
)

TAB_ACTION_CHECKS = (
    (0, 'review', (
        ('health_canvas', 'Review health'),
    )),
    (1, 'activity', (
        ('act_refresh_btn', 'Refresh'),
    )),
    (2, 'startup', (
        ('cat_all', 'All'),
        ('refresh_btn', 'Refresh'),
    )),
    (3, 'cleaner', (
        ('scan_btn', 'Scan Now'),
        ('apply_clean_btn', 'Archive & Clean'),
    )),
    (4, 'uninstaller', (
        ('uninst_uninstall_btn', 'Uninstall'),
    )),
    (5, 'restore', (
        ('reload_restore_btn', 'Reload Log'),
        ('restore_selected_btn', 'Restore Selected'),
    )),
    (6, 'archive', (
        ('delete_archive_btn', 'Delete from Archive'),
    )),
    (7, 'settings', (
        ('_settings_shell_btn', 'Context Menu Editor'),
        ('save_settings_btn', 'Save Settings'),
    )),
)

SIDEBAR_CHECKS = (
    ('_sidebar_explorer_btn', 'Explorer Context Menus'),
)

TOOLBAR_LABELS = (
    ('tb_scan', 'Scan'),
    ('tb_preview', 'Preview'),
    ('tb_apply', 'Archive'),
    ('tb_restore', 'Restore'),
)


def _fail(msg: str) -> None:
    print(f'FAIL: {msg}', file=sys.stderr)


def _ok(msg: str) -> None:
    print(f'OK: {msg}')


def _widget_ok(widget, name: str, min_w: int = 24, min_h: int = 14) -> list[str]:
    issues = []
    try:
        widget.update_idletasks()
        if not widget.winfo_ismapped():
            issues.append(f'{name} not mapped')
            return issues
        w, h = widget.winfo_width(), widget.winfo_height()
        if w < min_w or h < min_h:
            issues.append(f'{name} too small ({w}x{h})')
    except Exception as exc:
        issues.append(f'{name} check error: {exc}')
    return issues


def _widget_in_viewport(widget, root, name: str, margin: int = 6) -> list[str]:
    issues = []
    try:
        widget.update_idletasks()
        root.update_idletasks()
        if not widget.winfo_ismapped():
            return issues
        wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
        ww, wh = widget.winfo_width(), widget.winfo_height()
        rx, ry = root.winfo_rootx(), root.winfo_rooty()
        rw, rh = root.winfo_width(), root.winfo_height()
        if ww < 8 or wh < 8:
            issues.append(f'{name} not laid out ({ww}x{wh})')
            return issues
        if wx + ww < rx + margin or wy + wh < ry + margin:
            issues.append(f'{name} clipped off-screen (pos {wx},{wy})')
        if wx > rx + rw - margin or wy > ry + rh - margin:
            issues.append(f'{name} outside window bounds')
    except Exception as exc:
        issues.append(f'{name} viewport check error: {exc}')
    return issues


def _find_text_in_tree(widget, needle: str) -> bool:
    try:
        if hasattr(widget, 'cget'):
            text = str(widget.cget('text'))
            if needle in text:
                return True
    except Exception:
        pass
    for child in widget.winfo_children():
        if _find_text_in_tree(child, needle):
            return True
    return False


def check_layout(app, width: int, height: int, label: str, *, check_settings: bool = False) -> list[str]:
    """Return list of layout failures at the given window size."""
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    app.geometry(f'{width}x{height}+{x}+{y}')
    app.update_idletasks()
    app.update()
    if hasattr(app, '_update_responsive_layout'):
        app._update_responsive_layout()
    time.sleep(0.15)

    issues: list[str] = []
    for attr, name in TOOLBAR_LABELS:
        widget = getattr(app, attr)
        issues.extend(_widget_ok(widget, f'{label}/{name}'))
        issues.extend(_widget_in_viewport(widget, app, f'{label}/{name}'))

    issues.extend(_widget_ok(app.hdr_trust_value, f'{label}/Custody Trust value', 20, 16))
    issues.extend(_widget_ok(app.hdr_trust_lbl, f'{label}/Custody Trust label', 40, 12))
    issues.extend(_widget_in_viewport(app.tb_apply, app, f'{label}/Archive toolbar'))

    for attr, name in SIDEBAR_CHECKS:
        widget = getattr(app, attr, None)
        if widget is None:
            issues.append(f'{label}/sidebar missing {attr}')
            continue
        issues.extend(_widget_ok(widget, f'{label}/sidebar/{name}', 80, 20))
        issues.extend(_widget_in_viewport(widget, app, f'{label}/sidebar/{name}'))

    if not _find_text_in_tree(app, 'Preview'):
        issues.append(f'{label}/proof-flow or Preview Receipt text missing')
    if not _find_text_in_tree(app, 'Archive-first mode is ON'):
        issues.append(f'{label}/archive-first banner missing')

    for tab_idx, tab_name, buttons in TAB_ACTION_CHECKS:
        try:
            app.tab_control.select(tab_idx)
            app.update_idletasks()
            app.update()
            time.sleep(0.08)
            for attr, btn_name in buttons:
                widget = getattr(app, attr, None)
                if widget is None:
                    issues.append(f'{label}/{tab_name} missing {attr}')
                    continue
                issues.extend(_widget_ok(widget, f'{label}/{tab_name}/{btn_name}'))
                issues.extend(_widget_in_viewport(widget, app, f'{label}/{tab_name}/{btn_name}'))
        except Exception as exc:
            issues.append(f'{label}/{tab_name} tab check error: {exc}')

    try:
        app.tab_control.select(0)
        app.update_idletasks()
    except Exception:
        pass

    if check_settings:
        try:
            app.tab_control.select(7)
            app.update_idletasks()
            app.update()
            time.sleep(0.1)
            if not _find_text_in_tree(app, 'local-only'):
                issues.append(f'{label}/Settings local-only text missing')
            shell_btn = getattr(app, '_settings_shell_btn', None)
            if shell_btn is None:
                issues.append(f'{label}/Settings missing context menu editor button')
            else:
                issues.extend(_widget_ok(shell_btn, f'{label}/Settings/Context Menu Editor', 80, 20))
                issues.extend(_widget_in_viewport(shell_btn, app, f'{label}/Settings/Context Menu Editor'))
            save_btn = getattr(app, 'save_settings_btn', None)
            if save_btn is not None:
                issues.extend(_widget_in_viewport(save_btn, app, f'{label}/Settings/Save Settings'))
        except Exception as exc:
            issues.append(f'{label}/Settings tab check error: {exc}')

    return issues


def run_scaling_gates(tk_scaling: float = 1.0) -> int:
    from tkinter import messagebox
    import startup_manager_gui as gui_module

    os.environ['CLEANROOM_DISABLE_ANIMATIONS'] = '1'
    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
        setattr(messagebox, fn, lambda *a, **k: True if fn == 'askyesno' else None)

    app = gui_module.StartupManagerGUI()
    app.update_idletasks()
    app._finish_launch_sequence()
    if tk_scaling != 1.0:
        app.tk.call('tk', 'scaling', tk_scaling)
    all_issues: list[str] = []
    try:
        for w, h, label in GEOMETRIES:
            issues = check_layout(app, w, h, label, check_settings=True)
            if issues:
                all_issues.extend(issues)
                for i in issues:
                    _fail(i)
            else:
                _ok(f'Layout gate passed at {label}')

        if tk_scaling != 1.0:
            label = f'150pct-tk-scaling-{tk_scaling}'
            issues = check_layout(app, 1080, 700, label, check_settings=True)
            if issues:
                all_issues.extend(issues)
                for i in issues:
                    _fail(i)
            else:
                _ok(f'150% tk scaling layout gate passed at 1080x700 (scaling={tk_scaling})')
    finally:
        app.destroy()

    if all_issues:
        print(f'\nScaling gate FAILED ({len(all_issues)} issue(s))', file=sys.stderr)
        return 1
    scale_note = f', tk scaling={tk_scaling}' if tk_scaling != 1.0 else ''
    print(f'\nScaling gate PASSED (1080x700 default, 1050x680, 920x580-min, 1920x1080-ultrawide{scale_note})')
    return 0


def run_packaged_smoke(exe: Path, seconds: float = 8.0) -> int:
    if not exe.is_file():
        _fail(f'Packaged EXE not found: {exe}')
        return 1

    profile = Path(tempfile.mkdtemp(prefix='cleanroom-gate-'))
    local = profile / 'LocalAppData'
    local.mkdir()
    cleanroom = local / 'Cleanroom'
    env = os.environ.copy()
    env['LOCALAPPDATA'] = str(local)

    _ok(f'Fresh profile LOCALAPPDATA={local}')
    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(exe.parent),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(seconds)
    code = proc.poll()
    if code is not None:
        _fail(f'Packaged EXE exited early with code {code}')
        return 1
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    if cleanroom.exists():
        _ok(f'Cleanroom data dir created: {cleanroom}')
    else:
        _ok('No data dir yet (OK if first launch made no writes)')

    internal = exe.parent / '_internal' / 'customtkinter'
    if internal.is_dir():
        _ok('customtkinter assets present in _internal')
    else:
        _fail('customtkinter _internal folder missing')
        return 1

    print('\nPackaged smoke PASSED (fresh LOCALAPPDATA, CTk assets present)')
    print('NOTE: Full clean-machine installer test still required manually.')
    return 0


def run_headless_proof(exe: Path, profile_local: Path) -> int:
    """Run --headless-clean from installed EXE (no Python on PATH)."""
    sandbox = profile_local / 'sandbox_run'
    scan = sandbox / 'scan'
    archive = sandbox / 'archive'
    log_path = sandbox / 'cleanup_log.json'
    scan.mkdir(parents=True, exist_ok=True)
    old = scan / 'gate_test.zip'
    old.write_text('sandbox payload', encoding='utf-8')
    import time as _time
    old_ts = _time.time() - 45 * 86400
    os.utime(old, (old_ts, old_ts))

    cfg = sandbox / 'config.yaml'
    cfg.write_text(
        f'paths:\n  - {scan}\n'
        'age_days:\n  temp: 7\n  installers: 30\n'
        'size_threshold_mb: 200\n'
        "extensions_archive: ['.zip']\n"
        'exclude_patterns: []\nwhitelist: []\n'
        f'archive_dir: {archive}\n'
        f'log_file: {log_path}\n'
        'confirm_threshold_bytes: 99999999999999\n',
        encoding='utf-8',
    )

    env = os.environ.copy()
    env['LOCALAPPDATA'] = str(profile_local)
    env['PATH'] = os.environ.get('SystemRoot', r'C:\Windows') + r'\System32'

    proc = subprocess.run(
        [str(exe), '--headless-clean', '--config', str(cfg)],
        cwd=str(exe.parent),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        _fail(f'headless-clean exit {proc.returncode}: {proc.stderr[-500:] if proc.stderr else proc.stdout[-500:]}')
        return 1
    _ok('Installed EXE --headless-clean completed')

    if not log_path.is_file():
        _fail('cleanup_log.json not created after headless clean')
        return 1
    _ok('Archive log written (Archive & Clean path)')

    receipts = profile_local / 'Cleanroom' / 'receipts'
    if receipts.is_dir() and any(receipts.glob('*.txt')):
        _ok('Cleanroom Receipt generated')
    else:
        _fail('No receipt in Cleanroom/receipts after headless clean')
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packaged', metavar='EXE', default='',
                        help='Also run packaged EXE smoke test')
    parser.add_argument('--installed-exe', metavar='EXE', default='',
                        help='Run headless proof loop on installed EXE')
    parser.add_argument('--profile-local', metavar='PATH', default='',
                        help='LOCALAPPDATA for installed headless proof')
    parser.add_argument('--tk-scaling', type=float, default=1.0,
                        help='Simulate display scaling via tk scaling (1.5 = 150%%)')
    parser.add_argument('--headless-only', action='store_true',
                        help='Only run --installed-exe headless proof (skip layout gates)')
    parser.add_argument('--include-150', action='store_true',
                        help='Run additional layout pass at tk scaling 1.5')
    args = parser.parse_args()

    rc = 0
    if not args.headless_only:
        rc = run_scaling_gates(args.tk_scaling if args.tk_scaling != 1.0 else 1.0)
        if args.include_150 and args.tk_scaling == 1.0:
            rc = max(rc, run_scaling_gates(1.5))
    if args.installed_exe:
        local = Path(args.profile_local) if args.profile_local else Path(tempfile.mkdtemp()) / 'LocalAppData'
        local.mkdir(parents=True, exist_ok=True)
        rc = max(rc, run_headless_proof(Path(args.installed_exe), local))
    elif not args.headless_only:
        if args.packaged:
            rc = max(rc, run_packaged_smoke(Path(args.packaged)))
        elif Path('dist/Cleanroom/Cleanroom.exe').is_file():
            rc = max(rc, run_packaged_smoke(Path('dist/Cleanroom/Cleanroom.exe')))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
