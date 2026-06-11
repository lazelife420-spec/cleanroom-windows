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
    (1240, 760, '1240x760'),
    (1366, 768, '1366x768'),
    (1920, 1080, '1920x1080'),
)

TOOLBAR_LABELS = (
    ('tb_scan', 'Scan'),
    ('tb_preview', 'Preview Receipt'),
    ('tb_apply', 'Archive & Clean'),
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
        w, h = widget.winfo_width(), widget.winfo_height()
        if w < min_w or h < min_h:
            issues.append(f'{name} too small ({w}x{h})')
        if not widget.winfo_viewable():
            issues.append(f'{name} not viewable')
    except Exception as exc:
        issues.append(f'{name} check error: {exc}')
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
    time.sleep(0.15)

    issues: list[str] = []
    for attr, name in TOOLBAR_LABELS:
        issues.extend(_widget_ok(getattr(app, attr), f'{label}/{name}'))

    issues.extend(_widget_ok(app.hdr_trust_value, f'{label}/Custody Trust value', 20, 16))
    issues.extend(_widget_ok(app.hdr_trust_lbl, f'{label}/Custody Trust label', 40, 12))

    if not _find_text_in_tree(app, 'Preview Receipt'):
        issues.append(f'{label}/proof-flow or Preview Receipt text missing')
    if not _find_text_in_tree(app, 'Archive-first mode is ON'):
        issues.append(f'{label}/archive-first banner missing')

    if check_settings:
        try:
            app.tab_control.select(6)
            app.update_idletasks()
            app.update()
            time.sleep(0.1)
            if not _find_text_in_tree(app, 'local-only'):
                issues.append(f'{label}/Settings local-only text missing')
        except Exception as exc:
            issues.append(f'{label}/Settings tab check error: {exc}')

    return issues


def run_scaling_gates(tk_scaling: float = 1.0) -> int:
    from tkinter import messagebox
    import startup_manager_gui as gui_module

    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
        setattr(messagebox, fn, lambda *a, **k: True if fn == 'askyesno' else None)

    app = gui_module.StartupManagerGUI()
    if tk_scaling != 1.0:
        app.tk.call('tk', 'scaling', tk_scaling)
    all_issues: list[str] = []
    try:
        for w, h, label in GEOMETRIES:
            issues = check_layout(app, w, h, label, check_settings=False)
            if issues:
                all_issues.extend(issues)
                for i in issues:
                    _fail(i)
            else:
                _ok(f'Layout gate passed at {label}')

        if tk_scaling != 1.0:
            label = f'150pct-tk-scaling-{tk_scaling}'
            issues = check_layout(app, 1240, 760, label, check_settings=True)
            if issues:
                all_issues.extend(issues)
                for i in issues:
                    _fail(i)
            else:
                _ok(f'150% tk scaling layout gate passed at 1240x760 (scaling={tk_scaling})')
    finally:
        app.destroy()

    if all_issues:
        print(f'\nScaling gate FAILED ({len(all_issues)} issue(s))', file=sys.stderr)
        return 1
    scale_note = f', tk scaling={tk_scaling}' if tk_scaling != 1.0 else ''
    print(f'\nScaling gate PASSED (1240x760, 1366x768, 1920x1080{scale_note})')
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
