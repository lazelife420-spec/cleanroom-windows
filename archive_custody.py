#!/usr/bin/env python3
"""Archive custody browser and local-only prune recommendations.

Reads evidence from cleanup_log.json and receipt files on disk.
Prune affects archived copies only — never original live paths.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import brand

PRUNE_SAFE = 'Safe to delete'
PRUNE_REVIEW = 'Review first'
PRUNE_KEEP = 'Keep in custody'

PRUNE_RANK_ORDER = (PRUNE_SAFE, PRUNE_REVIEW, PRUNE_KEEP)

INSTALLER_EXTENSIONS = {'.msi', '.exe', '.zip', '.7z', '.rar', '.msix', '.cab'}
INSTALLER_REASONS = {'installer', 'installer/archive', 'old-installer', 'duplicate'}
TEMP_REASONS = {'zero-byte', 'temp', 'cache', 'log', 'tmp'}

PROTECTED_PARTS = (
    'documents', 'program files', 'program files (x86)', 'windows',
    'appdata\\local\\cleanroom', 'appdata\\roaming\\cleanroom',
)


def _parse_ts(ts):
    if not ts:
        return None
    s = str(ts).replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def _entry_fields(raw):
    src = (raw.get('src') or raw.get('src_path') or raw.get('source')
           or raw.get('original') or '')
    dest = (raw.get('dest') or raw.get('dest_path') or raw.get('target')
            or raw.get('archive') or raw.get('archived_path') or '')
    ts = raw.get('timestamp') or raw.get('time') or raw.get('when')
    try:
        size = int(raw.get('size') or 0)
    except (TypeError, ValueError):
        size = 0
    reason = raw.get('reason') or 'other'
    return str(src), str(dest), ts, size, reason


def _is_protected_path(path_str):
    if not path_str or path_str.startswith('REGISTRY::'):
        return True
    lower = path_str.replace('/', '\\').lower()
    return any(part in lower for part in PROTECTED_PARTS)


def _receipt_dir(receipt_dir=None):
    return Path(receipt_dir or brand.user_data_dir() / 'receipts')


def _find_receipt_path(entry_ts, receipt_dir=None):
    """Best-effort link: closest receipt file at or before entry time."""
    rdir = _receipt_dir(receipt_dir)
    if not rdir.is_dir():
        return None
    entry_dt = _parse_ts(entry_ts)
    import receipts as receipts_module
    receipts = receipts_module.list_receipt_files(rdir, prefix='receipt')
    if not receipts:
        return None
    if entry_dt is None:
        return receipts[-1]
    best = None
    best_delta = None
    for rp in receipts:
        stem = rp.stem.replace('receipt_', '')
        try:
            rdt = datetime.strptime(stem, '%Y%m%d_%H%M%S')
        except ValueError:
            continue
        if rdt <= entry_dt:
            delta = (entry_dt - rdt).total_seconds()
            if best is None or delta < best_delta:
                best = rp
                best_delta = delta
    return best or receipts[-1]


def _restore_context(actions):
    """Sets of paths involved in successful restores."""
    restored_archive_dests = set()
    restored_original_srcs = set()
    for raw in actions:
        if not isinstance(raw, dict) or raw.get('action') != 'restore':
            continue
        if raw.get('ok') is False:
            continue
        src = raw.get('src') or ''
        dest = raw.get('dest') or ''
        if dest:
            restored_archive_dests.add(str(dest))
        if src:
            restored_original_srcs.add(str(src))
    return restored_archive_dests, restored_original_srcs


def _pruned_dests(actions):
    out = set()
    for raw in actions:
        if isinstance(raw, dict) and raw.get('action') == 'prune':
            dest = raw.get('dest') or ''
            if dest:
                out.add(str(dest))
    return out


def _duplicate_basenames(records):
    from collections import Counter
    names = Counter()
    for r in records:
        try:
            names[Path(r['dest']).name.lower()] += 1
        except Exception:
            pass
    return {n for n, c in names.items() if c > 1}


def rank_prune(record, config=None, now=None, duplicate_names=None,
               restored_archive_dests=None, restored_original_srcs=None):
    """Local-only tier for archive custody — not a health score."""
    config = config or {}
    now = now or datetime.now()
    duplicate_names = duplicate_names or set()
    restored_archive_dests = restored_archive_dests or set()
    restored_original_srcs = restored_original_srcs or set()

    src = record.get('src') or ''
    dest = record.get('dest') or ''
    if not src or not dest:
        return PRUNE_KEEP

    dest_path = Path(dest)
    if not dest_path.exists():
        return PRUNE_SAFE

    ts = _parse_ts(record.get('when'))
    age_days = (now - ts).days if ts else 9999
    recent_days = int(config.get('prune_recent_days', 7))
    if age_days < recent_days:
        return PRUNE_KEEP

    reason = (record.get('reason') or 'other').lower()
    size = int(record.get('size') or 0)
    try:
        if dest_path.is_file():
            size = max(size, dest_path.stat().st_size)
    except OSError:
        pass

    if str(dest) in restored_archive_dests:
        return PRUNE_KEEP

    if src in restored_original_srcs and dest_path.exists():
        return PRUNE_SAFE

    if _is_protected_path(src):
        return PRUNE_KEEP

    if size == 0:
        return PRUNE_SAFE

    age_cfg = config.get('age_days') or {}
    temp_days = int(age_cfg.get('temp', 7))
    installer_days = int(age_cfg.get('installers', 30))

    if reason in TEMP_REASONS or reason == 'zero-byte':
        return PRUNE_SAFE if age_days >= temp_days else PRUNE_KEEP

    ext = dest_path.suffix.lower()
    basename = dest_path.name.lower()

    if basename in duplicate_names and age_days >= installer_days:
        return PRUNE_SAFE

    if reason in INSTALLER_REASONS or ext in INSTALLER_EXTENSIONS:
        if age_days >= installer_days and size < 200 * 1024 * 1024:
            return PRUNE_SAFE
        return PRUNE_REVIEW

    if ext in {'.zip', '.7z', '.rar', '.tar', '.gz'}:
        return PRUNE_REVIEW

    if size >= int(config.get('size_threshold_mb', 200)) * 1024 * 1024:
        return PRUNE_REVIEW

    if 'download' in src.replace('/', '\\').lower():
        return PRUNE_REVIEW

    return PRUNE_REVIEW


def build_archive_records(actions, receipt_dir=None, config=None, now=None):
    """Evidence-backed archive rows for the in-app browser."""
    config = config or {}
    now = now or datetime.now()
    pruned = _pruned_dests(actions)
    restored_dests, restored_srcs = _restore_context(actions)

    raw_records = []
    for raw in actions:
        if not isinstance(raw, dict):
            continue
        action = raw.get('action')
        if action in ('restore', 'prune'):
            continue
        src, dest, ts, size, reason = _entry_fields(raw)
        if not src or not dest:
            continue
        if dest in pruned:
            continue
        present = Path(dest).exists()
        raw_records.append({
            'when': ts,
            'src': src,
            'dest': dest,
            'reason': reason,
            'size': size,
            'restorable': present,
            'receipt_path': _find_receipt_path(ts, receipt_dir),
            'raw': raw,
        })

    dup_names = _duplicate_basenames(raw_records)
    records = []
    for i, rec in enumerate(raw_records):
        rank = rank_prune(
            rec, config=config, now=now, duplicate_names=dup_names,
            restored_archive_dests=restored_dests,
            restored_original_srcs=restored_srcs,
        )
        records.append({**rec, 'index': i, 'prune_rank': rank})
    records.sort(key=lambda r: r.get('when') or '', reverse=True)
    return records


def filter_by_prune_rank(records, rank=None):
    if not rank:
        return list(records)
    return [r for r in records if r.get('prune_rank') == rank]


def filter_by_search(records, query):
    q = (query or '').strip().lower()
    if not q:
        return list(records)
    out = []
    for r in records:
        hay = ' '.join(str(r.get(k, '')) for k in ('src', 'dest', 'reason', 'prune_rank'))
        if q in hay.lower():
            out.append(r)
    return out


def filter_older_than_days(records, days, now=None):
    """Records whose archive timestamp is at least `days` old and still on disk."""
    now = now or datetime.now()
    cutoff = now - timedelta(days=max(0, int(days)))
    out = []
    for r in records:
        ts = _parse_ts(r.get('when'))
        if ts is not None and ts > cutoff:
            continue
        dest = r.get('dest') or ''
        if dest and Path(dest).exists():
            out.append(r)
    return out


def summarize_archive_records(records):
    safe = [r for r in records if r.get('prune_rank') == PRUNE_SAFE]
    bytes_total = 0
    for r in records:
        try:
            bytes_total += int(r.get('size') or 0)
        except (TypeError, ValueError):
            pass
    safe_bytes = sum(int(r.get('size') or 0) for r in safe)
    return {
        'total': len(records),
        'present': sum(1 for r in records if r.get('restorable')),
        'bytes_total': bytes_total,
        'safe_count': len(safe),
        'safe_bytes': safe_bytes,
    }


def _bytes_on_disk(dest_path):
    try:
        if dest_path.is_file():
            return dest_path.stat().st_size
        if dest_path.is_dir():
            return sum(f.stat().st_size for f in dest_path.rglob('*') if f.is_file())
    except OSError:
        pass
    return 0


def _remove_archive_path(dest_path):
    if dest_path.is_file():
        dest_path.unlink()
        return True
    if dest_path.is_dir():
        shutil.rmtree(dest_path)
        return True
    return False


def append_log_entries(log_path, new_entries):
    path = Path(log_path)
    actions = []
    if path.is_file():
        try:
            import restore as restore_module
            actions = restore_module.load_log(str(path))
        except Exception:
            actions = []
    if isinstance(actions, dict):
        actions = actions.get('actions', [])
    if not isinstance(actions, list):
        actions = []
    actions.extend(new_entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(actions, indent=2), encoding='utf-8')
    return path


def apply_prune(records, log_path, receipt_dir=None, dry_run=False, now=None):
    """Permanently remove archived copies only. Never touches original live paths."""
    now = now or datetime.now()
    pruned_entries = []
    bytes_pruned = 0
    skipped = []

    for rec in records:
        src = rec.get('src') or ''
        dest = rec.get('dest') or ''
        if not dest:
            skipped.append({'dest': dest, 'reason': 'missing dest evidence'})
            continue
        dest_path = Path(dest)
        if not dest_path.exists():
            skipped.append({'dest': dest, 'reason': 'not in archive'})
            continue
        if src and Path(src).exists():
            try:
                if dest_path.resolve() == Path(src).resolve():
                    skipped.append({'dest': dest, 'reason': 'refuses live path'})
                    continue
            except OSError:
                pass
        try:
            size = _bytes_on_disk(dest_path) or int(rec.get('size') or 0)
        except (TypeError, ValueError):
            size = _bytes_on_disk(dest_path)
        if dry_run:
            pruned_entries.append({
                'src': src, 'dest': dest, 'size': size,
                'reason': rec.get('reason') or 'archive-custody',
            })
            bytes_pruned += size
            continue
        try:
            if not _remove_archive_path(dest_path):
                skipped.append({'dest': dest, 'reason': 'not in archive'})
                continue
        except OSError as e:
            skipped.append({'dest': dest, 'reason': str(e)})
            continue
        pruned_entries.append({
            'src': src, 'dest': dest, 'size': size,
            'reason': rec.get('reason') or 'archive-custody',
        })
        bytes_pruned += size

    receipt_path = None
    if not dry_run and pruned_entries:
        log_rows = [{
            'action': 'prune',
            'src': e['src'],
            'dest': e['dest'],
            'size': e['size'],
            'reason': 'prune-archive',
            'when': now.isoformat(timespec='seconds'),
        } for e in pruned_entries]
        append_log_entries(log_path, log_rows)
        try:
            import receipts as receipts_module
            receipt_path = receipts_module.write_prune_receipt(
                pruned_entries, bytes_pruned=bytes_pruned,
                receipt_dir=receipt_dir, now=now)
        except Exception:
            pass

    return {
        'pruned': pruned_entries,
        'bytes_pruned': bytes_pruned,
        'skipped': skipped,
        'receipt_path': receipt_path,
        'dry_run': dry_run,
    }


def summarize_prune_events(actions):
    """Bytes pruned from ledger actions (separate from bytes archived)."""
    total = 0
    count = 0
    for raw in actions:
        if not isinstance(raw, dict) or raw.get('action') != 'prune':
            continue
        count += 1
        try:
            total += int(raw.get('size') or 0)
        except (TypeError, ValueError):
            pass
    return {'prune_events': count, 'bytes_pruned': total}
