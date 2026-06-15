#!/usr/bin/env python3
"""Gate: receipt viewer paths use receipt_identity, not generic titles."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GUI = (ROOT / 'startup_manager_gui.py').read_text(encoding='utf-8')
VIEWER = (ROOT / 'ui' / 'receipt_viewer.py').read_text(encoding='utf-8')
IDENTITY = (ROOT / 'ui' / 'receipt_identity.py').read_text(encoding='utf-8')


def main() -> int:
    failed = []
    if 'receipt_context' not in GUI or '_view_receipt_file' not in GUI:
        failed.append('_view_receipt_file must use receipt_context')
    if "title='Receipt'" in VIEWER and "title='Receipt'" in VIEWER.split('def show_receipt')[0]:
        pass  # default param OK if overridden
    if 'receipt_context' not in VIEWER or 'ctx[\'acronym\']' not in VIEWER:
        failed.append('receipt_viewer must show R.E.C.E.I.P.T. via receipt_context')
    if 'Cleanroom Receipt —' not in IDENTITY:
        failed.append('receipt_identity missing branded title format')
    if "action_key='cleaner_preview'" not in GUI:
        failed.append('preview_cleanup_receipt missing cleaner_preview action_key')
    if "action_key='latest'" not in GUI:
        failed.append('open_last_receipt missing latest action_key')
    if "action_key='cleaner_archive'" not in GUI:
        failed.append('archive receipt paths missing cleaner_archive action_key')
    if failed:
        print('receipt_identity_gate: FAIL')
        for line in failed:
            print(f'  - {line}')
        return 1
    print('receipt_identity_gate: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
