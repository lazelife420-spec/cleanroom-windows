#!/usr/bin/env python3
"""Activity ledger — every Cleanroom action, provably restorable.

Turns the cleanup log into a chronological feed with per-item custody
status (artifact still on disk?) and a suite-wide trust score.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path


def _present(dest):
    try:
        return Path(dest).exists()
    except Exception:
        return False


def build_activity_feed(actions):
    """Chronological activity feed, newest first.

    Each event: when, src, dest, reason, size, present, kind
    (file | registry | restore).
    """
    events = []
    for raw in actions:
        if not isinstance(raw, dict):
            continue
        if raw.get('action') == 'restore':
            ts = raw.get('timestamp') or raw.get('time') or raw.get('when')
            events.append({
                'when': ts,
                'src': raw.get('src') or '',
                'dest': raw.get('dest') or '',
                'reason': 'restore',
                'size': 0,
                'present': True,
                'kind': 'restore',
            })
            continue
        if raw.get('action') == 'prune':
            ts = raw.get('timestamp') or raw.get('time') or raw.get('when')
            try:
                size = int(raw.get('size') or 0)
            except (TypeError, ValueError):
                size = 0
            events.append({
                'when': ts,
                'src': raw.get('src') or '',
                'dest': raw.get('dest') or '',
                'reason': 'prune-archive',
                'size': size,
                'present': False,
                'kind': 'prune',
            })
            continue
        src = (raw.get('src') or raw.get('src_path') or raw.get('source')
               or raw.get('original') or '')
        dest = (raw.get('dest') or raw.get('dest_path') or raw.get('target')
                or raw.get('archive') or raw.get('archived_path') or '')
        if not src or not dest:
            continue
        ts = raw.get('timestamp') or raw.get('time') or raw.get('when')
        try:
            size = int(raw.get('size') or 0)
        except (TypeError, ValueError):
            size = 0
        kind = 'registry' if str(src).startswith('REGISTRY::') else 'file'
        events.append({
            'when': ts,
            'src': str(src),
            'dest': str(dest),
            'reason': raw.get('reason') or 'other',
            'size': size,
            'present': _present(dest),
            'kind': kind,
        })
    events.sort(key=lambda e: e.get('when') or '', reverse=True)
    return events


def summarize_feed(events):
    """Roll-up stats for the Activity dashboard."""
    restorable = [e for e in events if e.get('kind') != 'restore']
    present = sum(1 for e in restorable if e.get('present'))
    missing = len(restorable) - present
    bytes_moved = sum(e.get('size', 0) for e in restorable)
    reasons = Counter(e.get('reason', 'other') for e in restorable)
    prune_events = [e for e in events if e.get('kind') == 'prune']
    return {
        'total_actions': len(restorable),
        'present': present,
        'missing': missing,
        'bytes_moved': bytes_moved,
        'reasons': reasons,
        'restore_events': sum(1 for e in events if e.get('kind') == 'restore'),
        'prune_events': len(prune_events),
        'bytes_pruned': sum(e.get('size', 0) for e in prune_events),
    }


def trust_score(present, total):
    """0–100 custody trust score. Empty log → 100 (nothing broken yet)."""
    if total <= 0:
        return 100
    return int(round(100 * present / total))


def format_trust_score_display(verified_count, total_count, missing_count):
    """Proof/UI trust string — never perfect when any archive item is missing."""
    if total_count <= 0:
        return '100/100'
    raw_score = (verified_count / total_count) * 100
    if missing_count > 0:
        score = min(int(raw_score), 99)
    else:
        score = int(round(raw_score))
    return f'{score}/100'
