"""Receipt path discovery and legacy extension compatibility (RECEIPT Core)."""
from datetime import datetime
from pathlib import Path

RECEIPT_EXT = '.cleanroom-receipt'
LEGACY_RECEIPT_EXT = '.txt'
RECEIPT_EXTENSIONS = (RECEIPT_EXT, LEGACY_RECEIPT_EXT)


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


def list_receipt_files(receipt_dir, prefix='receipt'):
    """Sorted receipt paths for a prefix (receipt or prune_receipt)."""
    rdir = Path(receipt_dir)
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
