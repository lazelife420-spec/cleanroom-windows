#!/usr/bin/env python3
"""Cleanup receipts: a human-readable record written after every clean —
what moved, space freed, and how many days of disk life it bought
(via Disk Foresight). Stored in %LOCALAPPDATA%\\Cleanroom\\receipts.

Path helpers and render logic live in receipt_core; this module re-exports
for backward compatibility and owns file I/O (write, read, prune).
"""
from datetime import datetime
from pathlib import Path

import brand
from receipt_core import paths, render
from receipt_core.paths import (
    LEGACY_RECEIPT_EXT,
    RECEIPT_EXT,
    RECEIPT_EXTENSIONS,
)

RECEIPT_DIR = brand.user_data_dir() / 'receipts'
MAX_RECEIPTS = 100


def list_receipt_files(receipt_dir=None, prefix='receipt'):
    return paths.list_receipt_files(receipt_dir or RECEIPT_DIR, prefix=prefix)


def is_receipt_path(path):
    return paths.is_receipt_path(path)


def format_receipt(moved_entries, days_bought=None, now=None, proof=None, motto=None):
    return render.format_receipt(
        moved_entries,
        days_bought=days_bought,
        now=now,
        proof=proof,
        motto=motto or brand.APP_MOTTO,
    )


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
    return render.format_prune_receipt(
        pruned_entries,
        bytes_pruned=bytes_pruned,
        now=now,
        motto=brand.APP_MOTTO,
    )


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
