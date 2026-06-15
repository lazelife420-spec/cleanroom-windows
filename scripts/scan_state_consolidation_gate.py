#!/usr/bin/env python3
"""Gate: single scan surface — no legacy spinner path; skip-folder wired."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUI = (ROOT / 'startup_manager_gui.py').read_text(encoding='utf-8')
MAIN = (ROOT / 'main.py').read_text(encoding='utf-8')


def main() -> int:
    failed = []
    if 'cleanup_progress.pack(side=' in GUI:
        failed.append('legacy cleanup_progress still packed in toolbar')
    if 'skip_scan_folder' not in GUI or 'skip_folder_check' not in MAIN:
        failed.append('skip folder not wired in GUI/main scan')
    if 'FOLDER_FILE_BUDGET' not in MAIN:
        failed.append('main.py missing folder file budget')
    if '_sync_home_state' not in GUI or '_sync_cleaner_state' not in GUI:
        failed.append('missing unified page state sync')
    if 'to archive' in GUI.split('def refresh_dashboard', 1)[-1].split('def ', 1)[0]:
        failed.append('refresh_dashboard still uses "to archive" gauge copy')
    if 'Review Candidates' not in GUI:
        failed.append('Home primary CTA not Review Candidates')
    if 'dashboard_preview_btn' not in GUI or 'preview_receipt_btn = self.dashboard_preview_btn' not in GUI:
        failed.append('preview_receipt_btn not aliased to dashboard_preview_btn')
    if failed:
        print('scan_state_consolidation_gate: FAIL')
        for line in failed:
            print(f'  - {line}')
        return 1
    print('scan_state_consolidation_gate: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
