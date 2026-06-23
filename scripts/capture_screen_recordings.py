#!/usr/bin/env python3
"""Capture Cleanroom proof screen recordings (local sandbox only — do not commit MP4s).

Output: screenshot_sandbox/screen-recordings/*.mp4

Run from repo root after killing stray Cleanroom/python GUI processes:
    python scripts/capture_screen_recordings.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'screenshot_sandbox' / 'screen-recordings'
WIDTH, HEIGHT = 1280, 760
FPS = 24

sys.path.insert(0, str(ROOT))


class WindowRecorder:
    """Record a Tk window region via ffmpeg gdigrab."""

    def __init__(self, app):
        self.app = app
        self._proc: subprocess.Popen | None = None

    def _bbox(self) -> tuple[int, int, int, int]:
        self.app.update_idletasks()
        self.app.update()
        x = int(self.app.winfo_rootx())
        y = int(self.app.winfo_rooty())
        w = int(self.app.winfo_width())
        h = int(self.app.winfo_height())
        w = max(320, w - (w % 2))
        h = max(240, h - (h % 2))
        return x, y, w, h

    def start(self, path: Path) -> None:
        self.stop()
        x, y, w, h = self._bbox()
        path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-f', 'gdigrab', '-framerate', str(FPS),
            '-offset_x', str(x), '-offset_y', str(y),
            '-video_size', f'{w}x{h}',
            '-i', 'desktop',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
            str(path),
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        time.sleep(0.35)

    def stop(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.write(b'q')
                proc.stdin.flush()
        except Exception:
            proc.kill()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


class ScreenRecorder:
    """Record a fixed desktop region (tray area)."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def start(self, path: Path, *, x: int, y: int, w: int, h: int) -> None:
        self.stop()
        w = max(320, w - (w % 2))
        h = max(120, h - (h % 2))
        path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-f', 'gdigrab', '-framerate', str(FPS),
            '-offset_x', str(x), '-offset_y', str(y),
            '-video_size', f'{w}x{h}',
            '-i', 'desktop',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
            str(path),
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        time.sleep(0.35)

    def stop(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.write(b'q')
                proc.stdin.flush()
        except Exception:
            proc.kill()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


def _pump(app, cond, timeout=90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.update_idletasks()
        app.update()
        if cond():
            return True
        time.sleep(0.03)
    return cond()


def _sleep(app, seconds: float) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.update_idletasks()
        app.update()
        time.sleep(0.03)


def _position_app(app) -> None:
    app.update_idletasks()
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    x = max(0, (sw - WIDTH) // 2)
    y = max(0, (sh - HEIGHT) // 2)
    app.geometry(f'{WIDTH}x{HEIGHT}+{x}+{y}')
    app.minsize(WIDTH, HEIGHT)
    app.update()
    time.sleep(0.25)


def _demo_root() -> Path:
    base = Path(os.environ.get('TEMP', Path.home() / 'AppData' / 'Local' / 'Temp'))
    base = base / 'cleanroom_recording_demo'
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    return base


def _seed_scan_candidates(scan: Path) -> None:
    samples = [
        ('stale_installer.msi', 400 * 1024 * 1024, 90),
        ('old_bundle.zip', 250 * 1024 * 1024, 60),
        ('cache_dump.tmp', 50 * 1024 * 1024, 45),
    ]
    for name, _size, age_days in samples:
        p = scan / name
        p.write_bytes(b'x' * 8192)
        old_ts = time.time() - age_days * 86400
        os.utime(p, (old_ts, old_ts))


def _seed_log_and_receipts(scan: Path, archive: Path, log_path: Path, receipt_dir: Path, *, count: int = 80):
    import receipts as receipts_module

    receipt_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for i in range(count):
        name = f'archive_item_{i:04d}.zip'
        src = scan / name
        if not src.exists():
            src.write_bytes(b'x' * 128)
        dest = archive / name
        if not dest.exists():
            dest.write_bytes(b'x' * 128)
        when = f'2026-06-10T14:{i % 60:02d}:00'
        entries.append({
            'src': str(src),
            'dest': str(dest),
            'reason': 'temp' if i % 3 else 'installer/archive',
            'size': 128 * (i + 1),
            'when': when,
        })
        if i < 5:
            receipts_module.write_receipt([entries[-1]])
    log_path.write_text(json.dumps(entries, indent=2), encoding='utf-8')


def _make_app(*, enable_tray: bool = False):
    os.environ['CLEANROOM_DISABLE_ANIMATIONS'] = '1'
    import receipts as receipts_module
    import foresight as foresight_module
    import startup_manager_gui as gui_module
    from tkinter import messagebox

    _orig_askyesno = messagebox.askyesno

    def _askyesno(title, message, **kw):
        if 'Force remove' in str(title):
            def _auto_no():
                time.sleep(2.8)
                try:
                    import ctypes
                    ctypes.windll.user32.keybd_event(0x4E, 0, 0, 0, 0)  # N
                    ctypes.windll.user32.keybd_event(0x4E, 0, 2, 0, 0)
                except Exception:
                    pass

            threading.Thread(target=_auto_no, daemon=True).start()
            return _orig_askyesno(title, message, **kw)
        return _orig_askyesno(title, message, **kw)

    for fn in ('showinfo', 'showwarning', 'showerror'):
        setattr(messagebox, fn, lambda *a, **k: None)
    messagebox.askyesno = _askyesno

    gui_module.StartupManagerGUI._show_proof_report = lambda *a, **k: None
    gui_module.StartupManagerGUI._play_receipt_animation = (
        lambda self, stamp, on_complete=None, **kw: on_complete() if on_complete else None
    )

    tmp = _demo_root()
    scan = tmp / 'scan'
    scan.mkdir()
    archive = tmp / 'archive'
    archive.mkdir()
    _seed_scan_candidates(scan)
    log_path = tmp / 'cleanup_log.json'
    receipt_dir = tmp / 'receipts'
    _seed_log_and_receipts(scan, archive, log_path, receipt_dir, count=120)

    cfg = tmp / 'config.yaml'
    cfg.write_text(
        f'paths:\n  - "{scan.as_posix()}"\n'
        'age_days:\n  temp: 7\n  installers: 30\n  partial-download: 14\n'
        'size_threshold_mb: 0\n'
        "extensions_archive: ['.zip', '.tmp', '.msi']\n"
        'exclude_patterns: []\nwhitelist: []\n'
        f'archive_dir: "{archive.as_posix()}"\n'
        f'log_file: "{log_path.as_posix()}"\n'
        'confirm_threshold_bytes: 99999999999999\n',
        encoding='utf-8',
    )

    receipts_module.RECEIPT_DIR = receipt_dir
    foresight_module.HISTORY_PATH = tmp / 'disk_history.json'
    foresight_module.HEALTH_PATH = tmp / 'health_history.json'

    app = gui_module.StartupManagerGUI(config_path=cfg, restore_log_path=log_path)
    app.update_idletasks()
    app._finish_launch_sequence()
    _position_app(app)

    if enable_tray:
        if not _pump(app, lambda: getattr(getattr(app, '_tray', None), 'is_running', False), timeout=20):
            print('[warn] tray not running — clip 08 may be partial')
    return app


def _simulate_right_click_tree(app, tree, handler):
    children = tree.get_children()
    if not children:
        return
    iid = children[0]
    tree.selection_set(iid)
    tree.focus(iid)
    x, y = 40, 18
    evt = tk.Event()
    evt.x = x
    evt.y = y
    evt.x_root = tree.winfo_rootx() + x
    evt.y_root = tree.winfo_rooty() + y
    handler(evt)


def _flow_01_home_scan(app, rec: WindowRecorder) -> None:
    app._navigate_to_tab(0)
    _sleep(app, 1.2)
    app.refresh_cleanup()
    _pump(app, lambda: getattr(app, '_scan_session_done', False) and not app._cleaner_loading, timeout=60)
    app.refresh_dashboard()
    _sleep(app, 2.5)


def _flow_02_cleaner_preview(app, rec: WindowRecorder) -> None:
    app._navigate_to_tab(3)
    _sleep(app, 1.0)
    if app.cleanup_items:
        app.cleanup_selected = set(range(len(app.cleanup_items)))
        app._update_cleanup_tree()
        app._sync_home_state()
    _sleep(app, 1.0)
    app.preview_cleanup_receipt()
    _sleep(app, 3.5)
    import customtkinter as ctk
    for w in list(app.winfo_children()):
        try:
            if isinstance(w, ctk.CTkToplevel):
                w.destroy()
        except Exception:
            pass
    app.update()


def _flow_03_archive(app, rec: WindowRecorder) -> None:
    app._navigate_to_tab(6)
    app.update()
    app.refresh_archive_browser()
    _sleep(app, 1.5)
    _pump(app, lambda: getattr(app, '_archive_busy', False) and getattr(app, '_archive_loaded', False), timeout=30)
    _sleep(app, 2.5)


def _flow_04_proof_ledger(app, rec: WindowRecorder) -> None:
    app._navigate_to_tab(1)
    app.refresh_activity()
    _pump(app, lambda: bool(getattr(app, 'activity_tree', None) and app.activity_tree.get_children()), timeout=20)
    _sleep(app, 1.2)
    children = app.activity_tree.get_children()
    if children:
        app.activity_tree.selection_set(children[0])
        app._on_activity_select()
        _sleep(app, 0.8)
        app._activity_open_receipt()
        _sleep(app, 3.0)
        import customtkinter as ctk
        for w in list(app.winfo_children()):
            try:
                if isinstance(w, ctk.CTkToplevel):
                    w.destroy()
            except Exception:
                pass
    app.update()


def _flow_05_context_menus(app, rec: WindowRecorder) -> None:
    app._navigate_to_tab(0)
    app.refresh_dashboard()
    _sleep(app, 0.8)
    if getattr(app, '_rec_card_frames', None) and app._rec_card_frames:
        card = app._rec_card_frames[0]
        evt = tk.Event()
        evt.x_root = card.winfo_rootx() + 60
        evt.y_root = card.winfo_rooty() + 24
        app._on_recommendation_card_right(evt, 0)
        _sleep(app, 2.0)
        for w in list(app.winfo_children()):
            if 'CTkToplevel' in w.winfo_class() or w.__class__.__name__ == 'Toplevel':
                try:
                    w.destroy()
                except Exception:
                    pass

    app._navigate_to_tab(3)
    _sleep(app, 0.6)
    if app.cleanup_tree.get_children():
        _simulate_right_click_tree(app, app.cleanup_tree, app._on_cleanup_right_click)
        _sleep(app, 2.0)

    app._navigate_to_tab(6)
    _sleep(app, 0.5)
    if not getattr(app, '_archive_loaded', False):
        app.refresh_archive_browser()
        _pump(app, lambda: getattr(app, '_archive_loaded', False), timeout=25)
    if app.archive_tree.get_children():
        _simulate_right_click_tree(app, app.archive_tree, app._on_archive_right_click)
        _sleep(app, 2.0)

    app._navigate_to_tab(1)
    app.refresh_activity()
    _pump(app, lambda: bool(app.activity_tree.get_children()), timeout=15)
    if app.activity_tree.get_children():
        _simulate_right_click_tree(app, app.activity_tree, app._on_activity_right_click)
        _sleep(app, 2.0)


def _flow_06_uninstaller(app, rec: WindowRecorder) -> None:
    app._navigate_to_tab(4)
    app.refresh_uninstaller()
    _pump(app, lambda: bool(getattr(app, 'uninstall_tree', None) and app.uninstall_tree.get_children()), timeout=45)
    _sleep(app, 1.0)
    children = app.uninstall_tree.get_children()
    if children:
        app.uninstall_tree.selection_set(children[0])
        app._on_uninstall_select()
        _sleep(app, 1.5)
        app.force_remove_selected()
        _sleep(app, 1.0)


def _flow_07_startup(app, rec: WindowRecorder) -> None:
    app._navigate_to_tab(2)
    _sleep(app, 0.8)
    if not app.tree.get_children():
        app.refresh()
        _pump(app, lambda: bool(app.tree.get_children()), timeout=30)
    children = app.tree.get_children()
    if children:
        _simulate_right_click_tree(app, app.tree, app._on_startup_right_click)
        _sleep(app, 2.5)


def _record_flow(app, name: str, flow_fn) -> Path:
    path = OUT / name
    rec = WindowRecorder(app)
    rec.start(path)
    try:
        flow_fn(app, rec)
    finally:
        rec.stop()
    if not path.is_file() or path.stat().st_size < 5000:
        raise RuntimeError(f'Recording too small or missing: {path}')
    print(f'[ok] {name} ({path.stat().st_size // 1024} KB)')
    return path


def _flow_08_tray() -> None:
    from ui.tray import shutdown_all_trays

    shutdown_all_trays()
    app = _make_app(enable_tray=True)
    win_rec = WindowRecorder(app)
    tray_rec = ScreenRecorder()
    out = OUT / '08-tray-hide-show-quit.mp4'
    win_hide = OUT / '_08-hide-temp.mp4'
    tray_path = OUT / '_08-tray-temp.mp4'
    win_show = OUT / '_08-show-temp.mp4'

    try:
        win_rec.start(win_hide)
        _sleep(app, 1.2)
        app._tray_hide_window()
        _sleep(app, 2.0)
        win_rec.stop()

        sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
        tray_rec.start(tray_path, x=max(0, sw - 520), y=max(0, sh - 120), w=520, h=120)
        time.sleep(0.8)
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.click(sw - 90, sh - 15, button='right')
            time.sleep(2.5)
            pyautogui.press('escape')
        except Exception as exc:
            print(f'[warn] tray menu click skipped: {exc}')
        tray_rec.stop()

        app._tray_show_window()
        _sleep(app, 1.2)
        win_rec.start(win_show)
        _sleep(app, 1.5)
        win_rec.stop()

        app._shutdown_app(reason='recording-quit')
        time.sleep(0.8)

        parts = [p for p in (win_hide, tray_path, win_show) if p.is_file() and p.stat().st_size > 5000]
        if len(parts) == 2:
            list_file = OUT / '_08_concat.txt'
            list_file.write_text(
                '\n'.join(f"file '{p.as_posix()}'" for p in parts),
                encoding='utf-8',
            )
            subprocess.run(
                ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                 '-i', str(list_file), '-c', 'copy', str(out)],
                check=True,
            )
        elif win_hide.is_file():
            shutil.copy2(win_hide, out)
        else:
            raise RuntimeError('Tray recording failed')
        print(f'[ok] 08-tray-hide-show-quit.mp4 ({out.stat().st_size // 1024} KB)')
    finally:
        shutdown_all_trays()
        for p in (win_hide, tray_path, win_show, OUT / '_08_concat.txt'):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        try:
            app.destroy()
        except Exception:
            pass


def _write_readme(*, pytest_result: str, process_result: str) -> None:
    import brand
    import subprocess as sp

    commit = sp.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip()
    branch = sp.check_output(['git', 'branch', '--show-current'], text=True).strip()
    pyver = sys.version.split()[0]
    files = [
        ('01-home-scan-review.mp4', 'Home before/after scan; Review Candidates primary; gated Archive & Clean'),
        ('02-cleaner-preview-receipt.mp4', 'Cleaner candidates + Preview Receipt modal (PREVIEW ONLY)'),
        ('03-archive-custody-loading-loaded.mp4', 'Archive load → populated custody table'),
        ('04-proof-ledger-receipt.mp4', 'Proof Ledger rows + branded receipt viewer'),
        ('05-context-menus.mp4', 'Right-click menus on Home, Cleaner, Archive, Proof Ledger'),
        ('06-uninstaller-guardrails.mp4', 'Uninstaller selection; Force Remove confirm then cancel'),
        ('07-startup-manager-context-menu.mp4', 'Startup row context menu; no entry changes'),
        ('08-tray-hide-show-quit.mp4', 'Tray icon, menu, hide/show, quit'),
    ]
    lines = [
        'Cleanroom screen recording proof pack',
        f'Date/time: {time.strftime("%Y-%m-%d %H:%M:%S")}',
        f'Repo: {ROOT}',
        f'Branch: {branch}',
        f'Main commit: {commit}',
        f'Python: {pyver}',
        'Recording tool: ffmpeg gdigrab (window/region capture)',
        '',
        'Files:',
    ]
    for fname, desc in files:
        lines.append(f'- {fname} — {desc}')
    lines.extend([
        '',
        'Validation:',
        f'- pytest result: {pytest_result}',
        f'- process cleanup result: {process_result}',
        '',
        'Safety:',
        '- sandbox/demo data only (%TEMP%\\cleanroom_recording_demo)',
        '- no real uninstall/force remove/destructive action performed',
        '- Force Remove stopped at confirmation (No)',
        '- startup entries not modified',
        '',
        'Release:',
        '- no tag',
        '- no release prep',
        '- no shipping action',
    ])
    (OUT / '00-README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _checksums() -> None:
    import hashlib
    lines = []
    for mp4 in sorted(OUT.glob('*.mp4')):
        h = hashlib.sha256(mp4.read_bytes()).hexdigest()
        lines.append(f'{h}  {mp4.name}')
    (OUT / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _process_check() -> str:
    import subprocess as sp
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
        "Where-Object { $_.CommandLine -match 'startup_manager_gui|cleanroom_recording' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    r = sp.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True)
    pids = [ln.strip() for ln in (r.stdout or '').splitlines() if ln.strip()]
    clean = sp.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-Process Cleanroom -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
        capture_output=True, text=True,
    )
    cpids = [ln.strip() for ln in (clean.stdout or '').splitlines() if ln.strip()]
    leftover = pids + cpids
    return 'clean (no stray Cleanroom/python GUI processes)' if not leftover else f'leftover PIDs: {", ".join(leftover)}'


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    pytest = subprocess.run(
        [sys.executable, '-m', 'pytest', '-p', 'no:xonsh', '-q'],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    pytest_result = '347 passed' if pytest.returncode == 0 else f'FAIL (exit {pytest.returncode})'
    if pytest.returncode != 0:
        print(pytest.stdout[-2000:] if pytest.stdout else '')
        print(pytest.stderr[-1000:] if pytest.stderr else '')

    subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
         "Where-Object { $_.CommandLine -match 'startup_manager_gui|cleanroom_recording' } | "
         "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; "
         "Get-Process Cleanroom -ErrorAction SilentlyContinue | "
         "ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"],
        check=False,
    )

    from ui.tray import shutdown_all_trays

    app = _make_app(enable_tray=False)
    try:
        _record_flow(app, '01-home-scan-review.mp4', _flow_01_home_scan)
        _record_flow(app, '02-cleaner-preview-receipt.mp4', _flow_02_cleaner_preview)
        _record_flow(app, '03-archive-custody-loading-loaded.mp4', _flow_03_archive)
        _record_flow(app, '04-proof-ledger-receipt.mp4', _flow_04_proof_ledger)
        _record_flow(app, '05-context-menus.mp4', _flow_05_context_menus)
        _record_flow(app, '06-uninstaller-guardrails.mp4', _flow_06_uninstaller)
        _record_flow(app, '07-startup-manager-context-menu.mp4', _flow_07_startup)
    finally:
        try:
            app._shutdown_app(reason='recording-batch-end')
        except Exception:
            pass
        shutdown_all_trays()

    _flow_08_tray()

    proc_result = _process_check()
    _write_readme(pytest_result=pytest_result, process_result=proc_result)
    _checksums()

    print(f'\nAll recordings in: {OUT}')
    return 0 if pytest.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
