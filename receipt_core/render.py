"""Receipt body rendering (RECEIPT Core)."""
from collections import Counter
from datetime import datetime

from receipt_core._human import human_bytes
from receipt_core.custody import format_proof


def format_receipt(moved_entries, days_bought=None, now=None, proof=None, motto=''):
    """Render the receipt text for a list of cleanup-log entries.
    `proof` is an optional build_proof() record with OS-measured
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
        f'  {motto}',
        '=' * 46,
        f'  Date:        {now.strftime("%Y-%m-%d %H:%M:%S")}',
        f'  Items moved: {len(moved_entries)}',
        f'  Space moved: {human_bytes(total)}',
    ]
    if days_bought and days_bought >= 1:
        lines.append(f'  Disk life:   ~{days_bought:.0f} extra days at your usage rate')
    lines.append('-' * 46)
    lines.append('  By reason:')
    for reason, count in reasons.most_common():
        lines.append(f'    {reason:<24} {count}')
    if proof:
        try:
            lines.append('-' * 46)
            lines.extend(format_proof(proof))
        except Exception:
            pass
    lines.append('-' * 46)
    lines.append('  Nothing was deleted. Everything was moved to')
    lines.append('  the archive and can be restored from the')
    lines.append('  Restore tab (or rolled back via Cleanroom Rewind).')
    lines.append('=' * 46)
    return '\n'.join(lines) + '\n'


def format_prune_receipt(pruned_entries, bytes_pruned=None, now=None, motto=''):
    """Human-readable proof for archive-only permanent removal."""
    now = now or datetime.now()
    if bytes_pruned is None:
        bytes_pruned = sum(int(e.get('size') or 0) for e in pruned_entries)
    lines = [
        '=' * 46,
        '      CLEANROOM — PRUNE RECEIPT',
        f'  {motto}',
        '=' * 46,
        f'  Date:         {now.strftime("%Y-%m-%d %H:%M:%S")}',
        f'  Items pruned: {len(pruned_entries)}',
        f'  Bytes pruned: {human_bytes(bytes_pruned)}',
        '-' * 46,
        '  Archive-only removal. Original live files were not touched.',
        '  Restoring these archived copies is no longer possible.',
        '-' * 46,
        '  Pruned from archive custody:',
    ]
    for e in pruned_entries[:100]:
        dest = e.get('dest') or ''
        lines.append(f'    {human_bytes(int(e.get("size") or 0)):>8}  {dest}')
    if len(pruned_entries) > 100:
        lines.append(f'    … and {len(pruned_entries) - 100} more')
    lines.extend(['=' * 46, ''])
    return '\n'.join(lines)
