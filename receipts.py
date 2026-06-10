#!/usr/bin/env python3
"""Cleanup receipts: a human-readable record written after every clean —
what moved, space freed, and how many days of disk life it bought
(via Disk Foresight). Stored in %LOCALAPPDATA%\\Cleanroom\\receipts."""
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import brand

RECEIPT_DIR = brand.user_data_dir() / 'receipts'
MAX_RECEIPTS = 100


def _human(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1024:
            return f'{n:.1f}{unit}'
        n /= 1024
    return f'{n:.1f}PB'


def format_receipt(moved_entries, days_bought=None, now=None, proof=None):
    """Render the receipt text for a list of cleanup-log entries.
    `proof` is an optional proof.build_proof() record with OS-measured
    free-space numbers and a custody check."""
    now = now or datetime.now()
    total = 0
    reasons = Counter()
    for e in moved_entries:
        try:
            total += int(e.get('size') or 0)
        except (TypeError, ValueError):
            pass
        reasons[e.get('reason') or 'other'] += 1

    lines = [
        '=' * 46,
        '         CLEANROOM — RECEIPT',
        f'  {brand.APP_MOTTO}',
        '=' * 46,
        f'  Date:        {now.strftime("%Y-%m-%d %H:%M:%S")}',
        f'  Items moved: {len(moved_entries)}',
        f'  Space moved: {_human(total)}',
    ]
    if days_bought and days_bought >= 1:
        lines.append(f'  Disk life:   ~{days_bought:.0f} extra days at your usage rate')
    lines.append('-' * 46)
    lines.append('  By reason:')
    for reason, count in reasons.most_common():
        lines.append(f'    {reason:<24} {count}')
    if proof:
        try:
            import proof as proof_module
            lines.append('-' * 46)
            lines.extend(proof_module.format_proof(proof))
        except Exception:
            pass
    lines.append('-' * 46)
    lines.append('  Nothing was deleted. Everything was moved to')
    lines.append('  the archive and can be restored from the')
    lines.append('  Restore tab (or rolled back via Cleanroom Rewind).')
    lines.append('=' * 46)
    return '\n'.join(lines) + '\n'


def write_receipt(moved_entries, days_bought=None, receipt_dir=None, now=None, proof=None):
    """Write a receipt file; prunes old receipts beyond MAX_RECEIPTS.
    Returns the path, or None when there is nothing to record."""
    if not moved_entries:
        return None
    now = now or datetime.now()
    rdir = Path(receipt_dir or RECEIPT_DIR)
    rdir.mkdir(parents=True, exist_ok=True)
    path = rdir / f'receipt_{now.strftime("%Y%m%d_%H%M%S")}.txt'
    path.write_text(format_receipt(moved_entries, days_bought, now, proof=proof),
                    encoding='utf-8')

    receipts = sorted(rdir.glob('receipt_*.txt'))
    for old in receipts[:-MAX_RECEIPTS]:
        try:
            old.unlink()
        except Exception:
            pass
    return path


def latest_receipt(receipt_dir=None):
    rdir = Path(receipt_dir or RECEIPT_DIR)
    receipts = sorted(rdir.glob('receipt_*.txt')) if rdir.exists() else []
    return receipts[-1] if receipts else None
