#!/usr/bin/env python3
"""Capture launch screenshots for README (Review tab, Activity tab, Proof Pack demo)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'screenshots'
# Release screenshots: fixed window size (not maximized ultra-wide)
RELEASE_WIDTH = 1280
RELEASE_HEIGHT = 760
sys.path.insert(0, str(ROOT))

from PIL import ImageGrab  # noqa: E402


def _demo_root():
    """Sandbox under LocalAppData\\Cleanroom — never smart_clean_tool in visible paths."""
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'Cleanroom' / 'demo_capture'
    if base.exists():
        import shutil
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    return base


def _grab_window(app, path: Path):
    app.update_idletasks()
    app.update()
    time.sleep(0.5)
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    if img.size != (RELEASE_WIDTH, RELEASE_HEIGHT):
        from PIL import Image as PILImage
        img = img.resize((RELEASE_WIDTH, RELEASE_HEIGHT), PILImage.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f'Wrote {path} ({img.size[0]}x{img.size[1]})')


def _seed_demo_log(scan: Path, archive: Path, log_path: Path):
    """Activity ledger with verified custody (all dest files exist)."""
    entries = []
    samples = [
        ('large-file', 'reviewed_installer.msi', 512 * 1024 * 1024),
        ('temp', 'cache_bundle.zip', 128 * 1024 * 1024),
        ('partial-download', 'video.crdownload', 256 * 1024 * 1024),
    ]
    for reason, name, size in samples:
        src = scan / name
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(b'x' * min(size, 4096))
        dest = archive / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'x' * min(size, 4096))
        entries.append({
            'src': str(src),
            'dest': str(dest),
            'reason': reason,
            'size': size,
            'when': '2026-06-10T14:00:00',
        })
    log_path.write_text(json.dumps(entries, indent=2), encoding='utf-8')
    return log_path


def capture_gui_screenshots():
    os.environ['CLEANROOM_DISABLE_ANIMATIONS'] = '1'
    import receipts as receipts_module
    import foresight as foresight_module
    import startup_manager_gui as gui_module
    from tkinter import messagebox

    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
        setattr(messagebox, fn, lambda *a, **k: True if fn == 'askyesno' else None)
    gui_module.StartupManagerGUI._show_proof_report = lambda *a, **k: None

    tmp = _demo_root()
    scan = tmp / 'scan'
    scan.mkdir()
    archive = tmp / 'archive'
    archive.mkdir()
    old = scan / 'reviewed_candidate.zip'
    old.write_text('demo payload', encoding='utf-8')
    old_ts = time.time() - 45 * 86400
    os.utime(old, (old_ts, old_ts))
    log_path = tmp / 'cleanup_log.json'
    _seed_demo_log(scan, archive, log_path)

    cfg = tmp / 'config.yaml'
    cfg.write_text(
        f'paths:\n  - {scan}\n'
        'age_days:\n  temp: 7\n  installers: 30\n'
        'size_threshold_mb: 200\n'
        "extensions_archive: ['.zip']\n"
        'exclude_patterns: []\nwhitelist: []\n'
        f'archive_dir: {archive}\n'
        f'log_file: {log_path}\n'
        'confirm_threshold_bytes: 99999999999999\n',
        encoding='utf-8')

    receipts_module.RECEIPT_DIR = tmp / 'receipts'
    foresight_module.HISTORY_PATH = tmp / 'disk_history.json'
    foresight_module.HEALTH_PATH = tmp / 'health_history.json'

    app = gui_module.StartupManagerGUI(config_path=cfg, restore_log_path=log_path)
    app.update_idletasks()
    app._finish_launch_sequence()
    app.geometry(f'{RELEASE_WIDTH}x{RELEASE_HEIGHT}')
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    x = max(0, (sw - RELEASE_WIDTH) // 2)
    y = max(0, (sh - RELEASE_HEIGHT) // 2)
    app.geometry(f'{RELEASE_WIDTH}x{RELEASE_HEIGHT}+{x}+{y}')
    app.update()

    # Review tab — must include toolbar: Scan / Preview Receipt / Archive & Clean / Restore
    app.tab_control.select(0)
    app.refresh_cleanup()
    deadline = time.time() + 20
    while time.time() < deadline:
        app.update()
        if app.cleanup_items:
            break
        time.sleep(0.05)
    app.refresh_optimizer()
    app.update()
    time.sleep(0.4)
    for btn, label in ((app.tb_scan, 'Scan'), (app.tb_preview, 'Preview Receipt'),
                       (app.tb_apply, 'Archive & Clean'), (app.tb_restore, 'Restore')):
        text = btn.cget('text')
        if label not in text:
            raise SystemExit(f'Toolbar missing {label!r}: got {text!r}')
    _grab_window(app, OUT / 'cleanroom-review.png')

    # Activity tab — verified custody
    app.tab_control.select(1)
    app.refresh_activity()
    app.update()
    time.sleep(0.4)
    _grab_window(app, OUT / 'cleanroom-activity-ledger.png')

    app.destroy()


def capture_proof_pack_html():
    html = (ROOT / 'docs' / 'demo' / 'cleanroom-proof-pack-demo.html').resolve()
    out = OUT / 'cleanroom-proof-pack-demo.png'
    candidates = [
        Path(os.environ.get('PROGRAMFILES', '')) / 'Microsoft/Edge/Application/msedge.exe',
        Path(os.environ.get('PROGRAMFILES(X86)', '')) / 'Microsoft/Edge/Application/msedge.exe',
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/Application/chrome.exe',
    ]
    browser = next((p for p in candidates if p.is_file()), None)
    if browser is None:
        raise SystemExit('No Edge/Chrome found for headless HTML screenshot')
    url = html.as_uri()
    cmd = [
        str(browser),
        '--headless=new',
        '--disable-gpu',
        '--hide-scrollbars',
        '--window-size=1280,920',
        f'--screenshot={out}',
        url,
    ]
    subprocess.run(cmd, check=True, timeout=60)
    print(f'Wrote {out}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    capture_gui_screenshots()
    capture_proof_pack_html()
    for name in ('cleanroom-review.png', 'cleanroom-activity-ledger.png', 'cleanroom-proof-pack-demo.png'):
        p = OUT / name
        if not p.is_file():
            raise SystemExit(f'Missing screenshot: {p}')
    print('All launch screenshots captured.')


if __name__ == '__main__':
    main()
