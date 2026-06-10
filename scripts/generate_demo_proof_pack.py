#!/usr/bin/env python3
"""Generate a clean demo Proof Pack for README / launch screenshots.

Uses synthetic data with 100% custody verification — not a gaps-detected example.
"""
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import audit  # noqa: E402

DEMO_DIR = ROOT / 'docs' / 'demo'
OUT = DEMO_DIR / 'cleanroom-proof-pack-demo.html'

FEED = [
    {'when': '2026-06-10T14:22:11', 'reason': 'large-file', 'src': r'C:\Users\Demo\Downloads\installer_backup.msi',
     'size': 2_147_483_648, 'present': True, 'kind': 'file'},
    {'when': '2026-06-10T14:22:12', 'reason': 'temp', 'src': r'C:\Users\Demo\AppData\Local\Temp\setup_cache.zip',
     'size': 524_288_000, 'present': True, 'kind': 'file'},
    {'when': '2026-06-10T14:22:13', 'reason': 'partial-download', 'src': r'C:\Users\Demo\Downloads\video.crdownload',
     'size': 1_073_741_824, 'present': True, 'kind': 'file'},
    {'when': '2026-06-10T14:22:14', 'reason': 'installer/archive', 'src': r'C:\Users\Demo\Downloads\old_setup.exe',
     'size': 268_435_456, 'present': True, 'kind': 'file'},
    {'when': '2026-06-10T14:22:15', 'reason': 'broken-registry', 'src': 'REGISTRY::HKCU\\Software\\Demo\\DeadRun',
     'size': 4096, 'present': True, 'kind': 'registry'},
]

CUSTODY = {
    'verified': len(FEED),
    'total': len(FEED),
    'missing': 0,
    'bytes_in_custody': sum(e['size'] for e in FEED),
    'missing_items': [],
}

SUMMARY = {
    'total_actions': len(FEED),
    'present': len(FEED),
    'missing': 0,
    'bytes_moved': sum(e['size'] for e in FEED),
    'reasons': Counter(e['reason'] for e in FEED),
    'restore_events': 0,
}


def main():
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    audit.export_html_audit(FEED, CUSTODY, SUMMARY, 100, OUT, app_version='1.0.0')
    text = OUT.read_text(encoding='utf-8')
    assert 'CUSTODY VERIFIED' in text
    assert 'GAPS DETECTED' not in text
    assert 'Trust score: <strong>100/100</strong>' in text
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
