#!/usr/bin/env python3
"""Cleanroom product identity — single source of truth for names and paths."""
import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path

APP_DISPLAY = 'Cleanroom'
APP_TAGLINE = ('A Windows cleaner that archives first, proves every action, '
               'and lets you roll back.')
APP_MOTTO = 'Clean safely. Prove everything. Undo anytime.'
REPO_NAME = 'cleanroom-windows'
DATA_DIR_NAME = 'Cleanroom'
LEGACY_DATA_DIR_NAME = 'SmartClean'  # Smart Clean → Cleanroom upgrade path
EXE_NAME = 'Cleanroom'
APP_VERSION = '1.0.1'
MIGRATION_RECEIPT_NAME = 'migration_receipt.txt'

_ROOT = Path(__file__).resolve().parent
BRAND_DIR = _ROOT / 'assets' / 'brand'
LOGO_ORIGINAL_PATH = BRAND_DIR / 'cleanroom-logo-original.png'
LOGO_PATH = BRAND_DIR / 'cleanroom-logo.png'
ICON_PNG_PATH = BRAND_DIR / 'cleanroom-icon.png'
ICON_ICO_PATH = BRAND_DIR / 'cleanroom-icon.ico'

_migrated = False


def local_appdata():
    return Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')


def _human(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1024:
            return f'{n:.1f}{unit}'
        n /= 1024
    return f'{n:.1f}PB'


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _write_migration_receipt(dest_dir, legacy_dir, files_copied, total_bytes, hashes):
    """Cleanroom Migration Receipt — proof the upgrade happened."""
    now = datetime.now()
    lines = [
        '=' * 46,
        '      CLEANROOM — MIGRATION RECEIPT',
        '=' * 46,
        f'  Date:          {now.strftime("%Y-%m-%d %H:%M:%S")}',
        f'  From (legacy): {legacy_dir}',
        f'  To:            {dest_dir}',
        f'  Files copied:  {files_copied}',
        f'  Total bytes:   {_human(total_bytes)}',
        '-' * 46,
        '  SmartClean was left untouched as a backup.',
        '  All future Cleanroom data lives in the new path.',
        '-' * 46,
    ]
    if hashes:
        lines.append('  File hashes (SHA256):')
        for rel, digest in hashes[:200]:
            lines.append(f'    {digest[:16]}…  {rel}')
        if len(hashes) > 200:
            lines.append(f'    … and {len(hashes) - 200} more files')
    lines.extend(['=' * 46, ''])
    receipt = dest_dir / MIGRATION_RECEIPT_NAME
    receipt.write_text('\n'.join(lines), encoding='utf-8')
    return receipt


def migrate_legacy_data(base=None):
    """Copy SmartClean → Cleanroom once; leave legacy dir as backup.

    Returns (migrated: bool, receipt_path|None).
    Idempotent: skips when migration receipt already exists.
    """
    base = base or local_appdata()
    dest = base / DATA_DIR_NAME
    legacy = base / LEGACY_DATA_DIR_NAME
    receipt = dest / MIGRATION_RECEIPT_NAME

    if receipt.exists():
        return False, receipt
    if not legacy.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        return False, None

    dest.mkdir(parents=True, exist_ok=True)
    files_copied = 0
    total_bytes = 0
    hashes = []

    for src in legacy.rglob('*'):
        if not src.is_file():
            continue
        rel = src.relative_to(legacy)
        out = dest / rel
        if out.exists():
            continue  # already present — do not overwrite
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        files_copied += 1
        try:
            size = out.stat().st_size
            total_bytes += size
            if files_copied <= 500:
                hashes.append((str(rel).replace('\\', '/'), _sha256_file(out)))
        except Exception:
            pass

    path = _write_migration_receipt(dest, legacy, files_copied, total_bytes, hashes)
    return True, path


def ensure_migrated():
    """Run legacy migration once per process."""
    global _migrated
    if not _migrated:
        migrate_legacy_data()
        _migrated = True


def user_data_dir():
    """Per-user data directory — always %LOCALAPPDATA%\\Cleanroom after migration."""
    ensure_migrated()
    dest = local_appdata() / DATA_DIR_NAME
    dest.mkdir(parents=True, exist_ok=True)
    return dest
