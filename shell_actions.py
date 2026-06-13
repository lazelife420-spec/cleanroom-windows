#!/usr/bin/env python3
"""Shell-invoked archive actions (Explorer context menus, CLI flags)."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def _load_config(config_path=None):
    try:
        import main as cleanup_main
    except ImportError:
        return {}
    path = Path(config_path) if config_path else cleanup_main.default_config_path()
    try:
        return cleanup_main.load_config(path) or {}
    except Exception:
        return {}


def _log_path(cfg):
    log_file = cfg.get('log_file')
    if log_file:
        return Path(log_file)
    try:
        import brand
        return brand.user_data_dir() / 'cleanup_log.json'
    except Exception:
        return Path('cleanup_log.json')


def _dir_size(path):
    try:
        return sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())
    except OSError:
        return 0


def _archive_dir(cfg):
    return Path(cfg.get('archive_dir') or Path.home() / 'Downloads' / 'cleanup_archive')


def _is_under_archive(path, archive_dir):
    try:
        Path(path).resolve().relative_to(Path(archive_dir).resolve())
        return True
    except (ValueError, OSError):
        return False


def archive_path(path, config_path=None, reason='shell-archive'):
    """Move a file or folder into the configured archive folder and log it."""
    src = Path(path)
    if not src.exists():
        return False, f'Path not found: {src}'
    cfg = _load_config(config_path)
    archive_dir = _archive_dir(cfg)
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / src.name
    if dest.exists():
        dest = archive_dir / f'{datetime.now().strftime("%Y%m%d%H%M%S_")}{src.name}'
    try:
        if src.is_dir():
            size = _dir_size(src)
        else:
            size = src.stat().st_size
        shutil.move(str(src), str(dest))
    except OSError as e:
        return False, str(e)
    entry = {
        'src': str(src),
        'dest': str(dest),
        'reason': reason,
        'size': size,
        'when': datetime.now().isoformat(timespec='seconds'),
    }
    try:
        import archive_custody as ac
        ac.append_log_entries(_log_path(cfg), [entry])
    except Exception:
        log_path = _log_path(cfg)
        actions = []
        if log_path.is_file():
            try:
                actions = json.loads(log_path.read_text(encoding='utf-8'))
            except Exception:
                actions = []
        if not isinstance(actions, list):
            actions = []
        actions.append(entry)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(actions, indent=2), encoding='utf-8')
    return True, f'Archived to {dest}'


def delete_archive_path(path, config_path=None):
    """Delete an archived copy when path matches custody dest (file or folder)."""
    target = str(Path(path))
    p = Path(target)
    if not p.exists():
        return False, f'Archive path not found: {target}'
    cfg = _load_config(config_path)
    archive_dir = _archive_dir(cfg)
    if not _is_under_archive(p, archive_dir):
        return False, 'Refusing delete: path is not under the Cleanroom archive folder.'
    log_path = _log_path(cfg)
    try:
        import restore as restore_module
        import archive_custody as ac
    except ImportError:
        return False, 'Archive modules unavailable'
    actions = []
    if log_path.is_file():
        try:
            actions = restore_module.load_log(str(log_path))
        except Exception:
            actions = []
    records = ac.build_archive_records(actions, config=cfg)
    matches = [r for r in records if str(r.get('dest') or '') == target]
    if not matches:
        return False, 'No Cleanroom custody record for this path.'
    result = ac.apply_prune(matches, log_path, dry_run=False)
    n = len(result.get('pruned') or [])
    if n == 0:
        skipped = result.get('skipped') or []
        reason = skipped[0].get('reason', 'unknown') if skipped else 'unknown'
        return False, f'Could not delete: {reason}'
    return True, f'Deleted {n} archived item(s) from custody.'


def shell_archive_cli(argv_paths, config_path=None):
    if not argv_paths:
        return 2
    code = 0
    for p in argv_paths:
        ok, msg = archive_path(p, config_path=config_path)
        print(msg)
        if not ok:
            code = 1
    return code


def shell_delete_archive_cli(argv_paths, config_path=None):
    if not argv_paths:
        return 2
    code = 0
    for p in argv_paths:
        ok, msg = delete_archive_path(p, config_path=config_path)
        print(msg)
        if not ok:
            code = 1
    return code
