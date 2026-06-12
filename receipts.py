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
RECEIPT_EXT = '.cleanroom-receipt'
LEGACY_RECEIPT_EXT = '.txt'
RECEIPT_EXTENSIONS = (RECEIPT_EXT, LEGACY_RECEIPT_EXT)


def _human(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1024:
            return f'{n:.1f}{unit}'
        n /= 1024
    return f'{n:.1f}PB'


def _receipt_sort_key(path):
    stem = path.stem
    for prefix in ('receipt_', 'prune_receipt_'):
        if stem.startswith(prefix):
            ts = stem[len(prefix):]
            try:
                return datetime.strptime(ts, '%Y%m%d_%H%M%S')
            except ValueError:
                break
    return datetime.fromtimestamp(path.stat().st_mtime)


def list_receipt_files(receipt_dir=None, prefix='receipt'):
    """Sorted receipt paths for a prefix (receipt or prune_receipt)."""
    rdir = Path(receipt_dir or RECEIPT_DIR)
    if not rdir.is_dir():
        return []
    files = []
    for ext in RECEIPT_EXTENSIONS:
        files.extend(rdir.glob(f'{prefix}_*{ext}'))
    return sorted(files, key=_receipt_sort_key)


def is_receipt_path(path):
    """True when path looks like a Cleanroom receipt file."""
    p = Path(path)
    if not p.is_file():
        return False
    suffix = p.suffix.lower()
    if suffix == RECEIPT_EXT:
        return True
    if suffix == LEGACY_RECEIPT_EXT:
        name = p.name.lower()
        return name.startswith('receipt_') or name.startswith('prune_receipt_')
    return False


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
    path = rdir / f'receipt_{now.strftime("%Y%m%d_%H%M%S")}{RECEIPT_EXT}'
    path.write_text(format_receipt(moved_entries, days_bought, now, proof=proof),
                    encoding='utf-8')

    receipts = list_receipt_files(rdir, prefix='receipt')
    for old in receipts[:-MAX_RECEIPTS]:
        try:
            old.unlink()
        except Exception:
            pass
    return path


def latest_receipt(receipt_dir=None):
    receipts = list_receipt_files(receipt_dir, prefix='receipt')
    return receipts[-1] if receipts else None


def read_receipt(path):
    """Load receipt text from disk."""
    return Path(path).read_text(encoding='utf-8')


def format_prune_receipt(pruned_entries, bytes_pruned=None, now=None):
    """Human-readable proof for archive-only permanent removal."""
    now = now or datetime.now()
    if bytes_pruned is None:
        bytes_pruned = sum(int(e.get('size') or 0) for e in pruned_entries)
    lines = [
        '=' * 46,
        '      CLEANROOM — PRUNE RECEIPT',
        f'  {brand.APP_MOTTO}',
        '=' * 46,
        f'  Date:         {now.strftime("%Y-%m-%d %H:%M:%S")}',
        f'  Items pruned: {len(pruned_entries)}',
        f'  Bytes pruned: {_human(bytes_pruned)}',
        '-' * 46,
        '  Archive-only removal. Original live files were not touched.',
        '  Restoring these archived copies is no longer possible.',
        '-' * 46,
        '  Pruned from archive custody:',
    ]
    for e in pruned_entries[:100]:
        dest = e.get('dest') or ''
        lines.append(f'    {_human(int(e.get("size") or 0)):>8}  {dest}')
    if len(pruned_entries) > 100:
        lines.append(f'    … and {len(pruned_entries) - 100} more')
    lines.extend(['=' * 46, ''])
    return '\n'.join(lines)


def write_prune_receipt(pruned_entries, bytes_pruned=None, receipt_dir=None, now=None):
    if not pruned_entries:
        return None
    now = now or datetime.now()
    rdir = Path(receipt_dir or RECEIPT_DIR)
    rdir.mkdir(parents=True, exist_ok=True)
    path = rdir / f'prune_receipt_{now.strftime("%Y%m%d_%H%M%S")}{RECEIPT_EXT}'
    path.write_text(
        format_prune_receipt(pruned_entries, bytes_pruned=bytes_pruned, now=now),
        encoding='utf-8',
    )
    return path
