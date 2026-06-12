#!/usr/bin/env python3
"""Helper for PR #14 tray + receipt file type manual gates."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def tray_smoke_only():
    from ui.tray import TrayController

    class App:
        def __init__(self):
            self.calls = []

        def after(self, _ms, fn):
            fn()

        def _tray_show_window(self):
            self.calls.append('show')

        def _tray_hide_window(self):
            self.calls.append('hide')

        def _tray_quit(self):
            self.calls.append('quit')

        def open_last_receipt(self):
            self.calls.append('receipt')

        def export_audit(self):
            self.calls.append('proof')

    app = App()
    tray = TrayController(app)
    tray._on_open(None, None)
    tray._on_hide(None, None)
    tray._on_show(None, None)
    tray._on_latest_receipt(None, None)
    tray._on_proof_pack(None, None)
    tray._on_quit(None, None)
    expected = ['show', 'hide', 'show', 'receipt', 'proof', 'quit']
    if app.calls != expected:
        print('tray smoke failed:', app.calls, file=sys.stderr)
        return 1
    if not tray.start():
        print('tray start failed', file=sys.stderr)
        return 1
    tray.stop()
    return 0


def receipt_gate(profile_local: str, installed_exe: str):
    import os
    import receipts

    os.environ['LOCALAPPDATA'] = profile_local
    rdir = Path(profile_local) / 'Cleanroom' / 'receipts'
    rdir.mkdir(parents=True, exist_ok=True)

    moved = [{'src': 'a', 'dest': 'b', 'size': 100, 'reason': 'temp'}]
    cleanup_path = receipts.write_receipt(moved, receipt_dir=rdir, now=datetime(2026, 6, 12, 12, 0, 0))
    if cleanup_path.suffix != receipts.RECEIPT_EXT:
        print('cleanup receipt ext fail', cleanup_path, file=sys.stderr)
        return 1

    prune_path = receipts.write_prune_receipt(moved, receipt_dir=rdir, now=datetime(2026, 6, 12, 12, 1, 0))
    if prune_path.suffix != receipts.RECEIPT_EXT:
        print('prune receipt ext fail', prune_path, file=sys.stderr)
        return 1

    legacy = rdir / 'receipt_20260101_120000.txt'
    legacy.write_text('legacy receipt plain text', encoding='utf-8')
    if receipts.read_receipt(legacy) != 'legacy receipt plain text':
        print('legacy read fail', file=sys.stderr)
        return 1
    if receipts.latest_receipt(rdir) != cleanup_path:
        print('latest receipt fail', receipts.latest_receipt(rdir), cleanup_path, file=sys.stderr)
        return 1

    body = cleanup_path.read_text(encoding='utf-8')
    if 'CLEANROOM' not in body:
        print('plain text fail', file=sys.stderr)
        return 1

    exe = Path(installed_exe)
    if not exe.is_file():
        print('installed exe missing', file=sys.stderr)
        return 1

    proc = subprocess.Popen(
        [str(exe), '--open-receipt', str(cleanup_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(5)
    if proc.poll() is not None and proc.returncode not in (0, None):
        # viewer may keep process alive; non-zero immediate exit is failure
        if proc.returncode > 1:
            print('open-receipt exit', proc.returncode, file=sys.stderr)
            return 1
    # Should not write cleanup log from receipt open
    log_candidates = list(Path(profile_local).rglob('cleanup_log.json'))
    for log in log_candidates:
        if log.stat().st_mtime > time.time() - 10:
            print('unexpected cleanup log activity', log, file=sys.stderr)
            return 1
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tray-smoke-only', action='store_true')
    ap.add_argument('--receipt-gate', action='store_true')
    ap.add_argument('--profile-local')
    ap.add_argument('--installed-exe')
    args = ap.parse_args()
    if args.tray_smoke_only:
        raise SystemExit(tray_smoke_only())
    if args.receipt_gate:
        if not args.profile_local or not args.installed_exe:
            print('receipt gate needs --profile-local and --installed-exe', file=sys.stderr)
            raise SystemExit(2)
        raise SystemExit(receipt_gate(args.profile_local, args.installed_exe))
    ap.print_help()
    raise SystemExit(2)


if __name__ == '__main__':
    main()
