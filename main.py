#!/usr/bin/env python3
import argparse
import fnmatch
import json
import logging
import os
import shutil
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

SCAN_PROGRESS_EVERY_FILES = 50
SLOW_FOLDER_SECONDS = 30.0
FOLDER_FILE_BUDGET = 25000
SLOW_FOLDER_FILE_WARN = 10000

try:
    import yaml
except Exception:
    yaml = None
try:
    import telemetry
except Exception:
    telemetry = None
try:
    import enable_telemetry
except Exception:
    enable_telemetry = None

try:
    from send2trash import send2trash
except Exception:
    send2trash = None

try:
    import performance_engine as pe
except Exception:
    pe = None

APP_NAME = 'Cleanroom'


def _app_dir():
    """Directory of the running app: exe folder when frozen, source folder otherwise."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def user_config_dir():
    """Per-user writable data dir (%LOCALAPPDATA%\\Cleanroom; migrates legacy SmartClean once)."""
    try:
        import brand
        return brand.user_data_dir()
    except Exception:
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
        return Path(base) / APP_NAME


def generate_default_config(dest):
    """Write a sensible default config derived from the user profile.

    Returns the config dict that was written.
    """
    dest = Path(dest)
    home = Path(os.environ.get('USERPROFILE', str(Path.home())))
    temp = os.environ.get('TEMP') or str(home / 'AppData' / 'Local' / 'Temp')
    data_dir = dest.parent
    cfg = {
        'paths': [str(home / 'Downloads'), str(temp)],
        'dry_run': True,
        'age_days': {'temp': 7, 'installers': 30},
        'size_threshold_mb': 200,
        'extensions_archive': ['.msi', '.exe', '.zip', '.7z', '.rar'],
        'exclude_patterns': [],
        'whitelist': [],
        'archive_dir': str(home / 'Downloads' / 'cleanup_archive'),
        'log_file': str(data_dir / 'cleanup_log.json'),
        'plan_file': str(data_dir / 'cleanup_plan.json'),
        'confirm_threshold_bytes': 5 * 1024 * 1024 * 1024,
        'telemetry': {'enabled': False, 'usage_log': str(data_dir / 'usage_log.json')},
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    if yaml:
        dest.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8')
    else:
        dest.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    return cfg


def default_config_path():
    """Config discovery order.

    Installed (frozen): always use per-user %LOCALAPPDATA%\\Cleanroom config.
    Generate from %USERPROFILE% on first run — never dev hardcoded paths shipped
    next to the exe.

    Dev (source): cleanup_config.yaml next to main.py, then per-user fallback.
    """
    user_cfg = user_config_dir() / 'cleanup_config.yaml'

    if getattr(sys, 'frozen', False):
        if user_cfg.exists():
            return user_cfg
        try:
            generate_default_config(user_cfg)
            return user_cfg
        except Exception:
            bundled = Path(getattr(sys, '_MEIPASS', '')) / 'cleanup_config.yaml'
            if bundled.exists():
                return bundled
        return user_cfg

    candidate = _app_dir() / 'cleanup_config.yaml'
    if candidate.exists():
        return candidate
    if user_cfg.exists():
        return user_cfg
    return candidate


DEFAULT_CONFIG = default_config_path()

def load_config(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Config file not found: {path}")
    text = p.read_text(encoding='utf-8')
    if yaml:
        try:
            return yaml.safe_load(text)
        except Exception:
            pass
    # fallback to JSON-like parsing if YAML not available
    try:
        return json.loads(text)
    except Exception:
        raise SystemExit("Failed to parse config. Install PyYAML or provide JSON config.")

def is_older_than(p: Path, days: int):
    return datetime.fromtimestamp(p.stat().st_mtime) < (datetime.now() - timedelta(days=days))

def _path_is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _scan_roots(cfg):
    """Configured roots minus archive/custody dirs (not parent of log paths)."""
    paths = cfg.get('paths', []) or []
    exclude_patterns = cfg.get('exclude_patterns', []) or []
    skip_roots: list[Path] = []
    archive = cfg.get('archive_dir')
    if archive:
        skip_roots.append(Path(archive).expanduser())
    try:
        skip_roots.append(user_config_dir())
    except Exception:
        pass

    roots: list[Path] = []
    for root in paths:
        rootp = Path(root).expanduser()
        if not rootp.exists():
            continue
        if _matches_patterns(str(rootp), exclude_patterns):
            continue
        skip = False
        for skip_root in skip_roots:
            try:
                if rootp.resolve() == skip_root.resolve() or _path_is_under(rootp, skip_root):
                    skip = True
                    break
            except Exception:
                continue
        if not skip:
            roots.append(rootp)
    return roots


def _emit_scan_progress(on_progress, state: dict) -> None:
    if on_progress is None:
        return
    try:
        on_progress(dict(state))
    except Exception:
        logger.debug('scan progress callback failed', exc_info=True)


def scan_candidates(cfg, cancel_check=None, on_progress=None, skip_folder_check=None):
    """Scan configured folders; optional cooperative cancel, skip-folder, and progress."""
    candidates = []
    age_temp = cfg.get('age_days', {}).get('temp', 7)
    age_installers = cfg.get('age_days', {}).get('installers', 30)
    size_threshold = cfg.get('size_threshold_mb', 200) * 1024 * 1024
    ext_archive = set(x.lower() for x in cfg.get('extensions_archive', []))
    exclude_patterns = cfg.get('exclude_patterns', []) or []
    whitelist = cfg.get('whitelist', []) or []
    roots = _scan_roots(cfg)
    started = time.time()
    folders_scanned = 0
    files_checked = 0
    files_since_emit = 0
    cancelled = False
    skipped_folders: list[str] = []
    folder_file_counts: dict[str, int] = {}
    folder_started: dict[str, float] = {}
    summarized_folders: list[str] = []

    def is_under_skipped(folder: str) -> bool:
        fp = Path(folder)
        for sf in skipped_folders:
            try:
                sp = Path(sf)
                if fp == sp or _path_is_under(fp, sp):
                    return True
            except Exception:
                continue
        return False

    def snapshot(current_folder: str = '') -> dict:
        reclaimable = sum(c.get('size', 0) for c in candidates)
        folder_count = folder_file_counts.get(current_folder, 0) if current_folder else 0
        folder_elapsed = 0.0
        if current_folder and current_folder in folder_started:
            folder_elapsed = time.time() - folder_started[current_folder]
        slow = (
            bool(current_folder)
            and (
                folder_elapsed >= SLOW_FOLDER_SECONDS
                or folder_count >= SLOW_FOLDER_FILE_WARN
            )
        )
        return {
            'started_at': started,
            'elapsed_s': time.time() - started,
            'folders_scanned': folders_scanned,
            'files_checked': files_checked,
            'candidates_found': len(candidates),
            'reclaimable_bytes': reclaimable,
            'reclaimable_label': human_size(reclaimable),
            'current_folder': current_folder,
            'folder_file_count': folder_count,
            'folder_elapsed_s': folder_elapsed,
            'slow_folder': slow,
            'skipped_folders': list(skipped_folders),
            'summarized_folders': list(summarized_folders),
            'configured_roots': [str(p) for p in roots],
            'exclude_patterns': list(exclude_patterns),
            'stop_requested': bool(cancel_check and cancel_check()),
            'cancelled': cancelled,
        }

    _emit_scan_progress(on_progress, snapshot())

    for rootp in roots:
        if cancel_check and cancel_check():
            cancelled = True
            break
        folders_scanned += 1
        folder_started[str(rootp)] = time.time()
        _emit_scan_progress(on_progress, snapshot(str(rootp)))
        for f in rootp.rglob('*'):
            if cancel_check and cancel_check():
                cancelled = True
                break
            if not f.is_file():
                continue
            parent = str(f.parent)
            if is_under_skipped(parent):
                continue
            if skip_folder_check and skip_folder_check(parent):
                skipped_folders.append(parent)
                prog = snapshot(parent)
                prog['folder_skipped'] = parent
                _emit_scan_progress(on_progress, prog)
                continue
            path_str = str(f)
            if _matches_patterns(path_str, exclude_patterns):
                continue
            if _matches_patterns(path_str, whitelist):
                continue
            try:
                ext = f.suffix.lower()
                size = f.stat().st_size
            except Exception:
                continue
            if parent not in folder_started:
                folder_started[parent] = time.time()
            folder_file_counts[parent] = folder_file_counts.get(parent, 0) + 1
            cnt = folder_file_counts[parent]
            if cnt > FOLDER_FILE_BUDGET:
                if parent not in summarized_folders:
                    summarized_folders.append(parent)
                    skipped_folders.append(parent)
                    logger.info(
                        'Summarized large folder (%d files): %s', cnt, parent)
                    prog = snapshot(parent)
                    prog['folder_summarized'] = parent
                    _emit_scan_progress(on_progress, prog)
                continue
            files_checked += 1
            files_since_emit += 1
            if files_since_emit >= SCAN_PROGRESS_EVERY_FILES:
                files_since_emit = 0
                _emit_scan_progress(on_progress, snapshot(parent))
            if size == 0 and is_older_than(f, age_temp):
                candidates.append({'path': path_str, 'reason': 'zero-byte', 'size': size})
                continue
            if f.name.endswith('.crdownload') and is_older_than(f, 7):
                candidates.append({'path': path_str, 'reason': 'partial-download', 'size': size})
                continue
            if ext in ext_archive and is_older_than(f, age_installers):
                candidates.append({'path': path_str, 'reason': 'installer/archive', 'size': size})
                continue
            if size >= size_threshold and is_older_than(f, 7):
                candidates.append({'path': path_str, 'reason': 'large-file', 'size': size})
        if cancelled:
            break
        elapsed_folder = time.time() - folder_started.get(str(rootp), started)
        if elapsed_folder >= SLOW_FOLDER_SECONDS:
            logger.info('Slow scan folder: %s (%.1fs)', rootp, elapsed_folder)

    final = snapshot()
    final['cancelled'] = cancelled or bool(cancel_check and cancel_check())
    final['completed'] = True
    _emit_scan_progress(on_progress, final)
    return candidates


def _is_older_than_mtime(mtime: float, days: int) -> bool:
    return datetime.fromtimestamp(mtime) < (datetime.now() - timedelta(days=days))


def scan_candidates_fast(cfg, cancel_check=None, on_progress=None, skip_folder_check=None):
    """Scan using the performance engine for large or repeated scans.

    Falls back to the standard scanner if the performance engine is unavailable.
    Applies the same age/extension/size rules as scan_candidates().

    Per-folder skipping is supported by evaluating the skip check against the
    parent folder of each discovered file. This is not as efficient as the
    folder-before-entry check in the standard scanner, but it lets the GUI use
    the fast path while still honoring the user-driven Stop-Scan folder feature.
    """
    if pe is None:
        logger.warning('Performance engine unavailable; falling back to standard scan')
        return scan_candidates(cfg, cancel_check, on_progress, skip_folder_check)

    perf_cfg = cfg.get('performance', {})
    options = pe.ScanOptions(
        max_workers=perf_cfg.get('max_workers', 0),
        memory_limit_mb=perf_cfg.get('memory_limit_mb', 512),
        incremental=perf_cfg.get('incremental', True),
        force_rescan=perf_cfg.get('force_rescan', False),
    )

    cache_dir = user_config_dir() / 'performance_cache'
    engine = pe.PerformanceEngine(cache_dir=cache_dir, options=options)

    age_temp = cfg.get('age_days', {}).get('temp', 7)
    age_installers = cfg.get('age_days', {}).get('installers', 30)
    size_threshold = cfg.get('size_threshold_mb', 200) * 1024 * 1024
    ext_archive = set(x.lower() for x in cfg.get('extensions_archive', []))
    exclude_patterns = cfg.get('exclude_patterns', []) or []
    whitelist = cfg.get('whitelist', []) or []
    roots = [str(r) for r in _scan_roots(cfg)]

    candidates = []
    started = time.time()
    files_checked = 0
    cancelled = False
    skipped_folders: list[str] = []
    skipped_lock = threading.Lock()

    def file_filter(info: dict) -> bool:
        path = info['path']
        if skip_folder_check is not None:
            parent = str(Path(path).parent)
            with skipped_lock:
                if parent not in skipped_folders and skip_folder_check(parent):
                    skipped_folders.append(parent)
                    return False
        if _matches_patterns(path, exclude_patterns):
            return False
        if _matches_patterns(path, whitelist):
            return False
        return True

    def emit_progress(count: int, elapsed: float):
        if on_progress is None:
            return
        try:
            on_progress({
                'started_at': started,
                'elapsed_s': elapsed,
                'folders_scanned': 0,
                'files_checked': count,
                'candidates_found': len(candidates),
                'reclaimable_bytes': sum(c.get('size', 0) for c in candidates),
                'reclaimable_label': human_size(sum(c.get('size', 0) for c in candidates)),
                'current_folder': 'performance-scan',
                'folder_file_count': count,
                'folder_elapsed_s': elapsed,
                'slow_folder': False,
                'skipped_folders': list(skipped_folders),
                'summarized_folders': [],
                'configured_roots': roots,
                'exclude_patterns': list(exclude_patterns),
                'stop_requested': bool(cancel_check and cancel_check()),
                'cancelled': cancelled,
            })
        except Exception:
            logger.debug('fast scan progress callback failed', exc_info=True)

    scan_fn = engine.incremental_scan if options.incremental else engine.parallel_scan_directories

    for info in scan_fn(roots, file_filter=file_filter, progress_callback=emit_progress):
        if cancel_check and cancel_check():
            cancelled = True
            break

        files_checked += 1
        path = info['path']
        ext = info['extension']
        size = info['size']
        mtime = info['modified']

        if size == 0 and _is_older_than_mtime(mtime, age_temp):
            candidates.append({'path': path, 'reason': 'zero-byte', 'size': size})
        elif Path(path).name.endswith('.crdownload') and _is_older_than_mtime(mtime, 7):
            candidates.append({'path': path, 'reason': 'partial-download', 'size': size})
        elif ext in ext_archive and _is_older_than_mtime(mtime, age_installers):
            candidates.append({'path': path, 'reason': 'installer/archive', 'size': size})
        elif size >= size_threshold and _is_older_than_mtime(mtime, 7):
            candidates.append({'path': path, 'reason': 'large-file', 'size': size})

    if on_progress is not None:
        final = {
            'started_at': started,
            'elapsed_s': time.time() - started,
            'folders_scanned': 0,
            'files_checked': files_checked,
            'candidates_found': len(candidates),
            'reclaimable_bytes': sum(c.get('size', 0) for c in candidates),
            'reclaimable_label': human_size(sum(c.get('size', 0) for c in candidates)),
            'current_folder': '',
            'folder_file_count': 0,
            'folder_elapsed_s': 0.0,
            'slow_folder': False,
            'skipped_folders': list(skipped_folders),
            'summarized_folders': [],
            'configured_roots': roots,
            'exclude_patterns': list(exclude_patterns),
            'stop_requested': bool(cancel_check and cancel_check()),
            'cancelled': cancelled,
            'completed': True,
        }
        _emit_scan_progress(on_progress, final)

    return candidates


def human_size(n):
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024:
            return f"{n:.2f}{unit}"
        n /= 1024
    return f"{n:.2f}PB"

def apply_actions(candidates, cfg, archive_dir, permanent_delete=False):
    log = []
    for c in candidates:
        src = Path(c['path'])
        if not src.exists():
            continue
        try:
            if permanent_delete:
                # Delete file directly instead of archiving
                if send2trash and not cfg.get('force_permanent_delete', False):
                    send2trash(str(src))
                    action = "trashed"
                    dest = "Recycle Bin"
                else:
                    src.unlink()
                    action = "deleted"
                    dest = "permanently deleted"
                entry = {'src': str(src), 'dest': dest, 'reason': c['reason'], 'size': c['size'], 'when': datetime.now().isoformat(), 'action': action}
                print(f"{action.capitalize()}: {src}")
            else:
                # Original archive behavior
                archive_dir = Path(archive_dir)
                archive_dir.mkdir(parents=True, exist_ok=True)
                dest = archive_dir / src.name
                if dest.exists():
                    dest = archive_dir / (datetime.now().strftime('%Y%m%d%H%M%S_') + src.name)
                shutil.move(str(src), str(dest))
                entry = {'src': str(src), 'dest': str(dest), 'reason': c['reason'], 'size': c['size'], 'when': datetime.now().isoformat(), 'action': 'archived'}
                print(f"Moved: {src} -> {dest}")
            log.append(entry)
        except Exception as e:
            print(f"Failed to process {src}: {e}")
    # write log
    log_file = cfg.get('log_file') or (Path(__file__).parent / 'cleanup_log.json')
    try:
        existing = []
        if Path(log_file).exists():
            existing = json.loads(Path(log_file).read_text(encoding='utf-8'))
    except Exception:
        existing = []
    existing.extend(log)
    Path(log_file).write_text(json.dumps(existing, indent=2), encoding='utf-8')
    return log


def file_hash(path: Path, chunk_size: int = 4 * 1024 * 1024):
    import hashlib
    h = hashlib.sha256()
    try:
        with path.open('rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _matches_patterns(path: str, patterns):
    if not patterns:
        return False
    normalized = path.replace('\\', '/').lower()
    for pattern in patterns:
        if not isinstance(pattern, str):
            continue
        pat = pattern.replace('\\', '/').lower()
        if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(os.path.basename(normalized), pat) or pat in normalized:
            return True
    return False


def dedupe_candidates(candidates):
    # Group by size first to reduce hashing
    size_map = {}
    for c in candidates:
        size_map.setdefault(c['size'], []).append(c)

    to_keep = []
    to_remove = []
    engine = None
    if pe is not None:
        try:
            engine = pe.PerformanceEngine(cache_dir=user_config_dir() / 'dedupe_cache')
        except Exception:
            engine = None

    for size, group in size_map.items():
        if len(group) == 1:
            to_keep.extend(group)
            continue

        if engine is not None:
            paths = [c['path'] for c in group]
            try:
                hashes = dict(engine.batch_hash_files(paths))
            except Exception:
                hashes = {}
            hash_map = {}
            for c in group:
                h = hashes.get(c['path'])
                if not h:
                    to_keep.append(c)
                    continue
                key = (size, h)
                if key in hash_map:
                    to_remove.append(c)
                else:
                    hash_map[key] = c
                    to_keep.append(c)
        else:
            # Fallback to sequential hashing
            hash_map = {}
            for c in group:
                h = file_hash(Path(c['path']))
                if h is None:
                    to_keep.append(c)
                    continue
                key = (size, h)
                if key in hash_map:
                    to_remove.append(c)
                else:
                    hash_map[key] = c
                    to_keep.append(c)

    # Return candidates where duplicates removed (we'll still archive duplicates separately)
    return to_keep, to_remove

def move_duplicates(duplicates, archive_dir):
    """Move duplicate files into <archive_dir>/duplicates for review."""
    moved = 0
    dup_dir = Path(archive_dir) / 'duplicates'
    dup_dir.mkdir(parents=True, exist_ok=True)
    for d in duplicates:
        try:
            src = Path(d['path'])
            if not src.exists():
                continue
            dest = dup_dir / src.name
            if dest.exists():
                dest = dup_dir / (datetime.now().strftime('%Y%m%d%H%M%S_') + src.name)
            shutil.move(str(src), str(dest))
            moved += 1
        except Exception:
            pass
    return moved


def run_headless(config_path=None, dedupe=False, log_to=None):
    """Non-interactive cleanup for scheduled runs (no console, no prompts).

    Appends a one-run summary to log_to (default: headless_run.log in the
    per-user data dir). Returns a process exit code (0 ok, 1 failure).
    """
    lines = [f'[{datetime.now().isoformat()}] headless clean starting']
    rc = 0
    try:
        cfg = load_config(config_path or DEFAULT_CONFIG)
        if cfg.get('performance_scan'):
            candidates = scan_candidates_fast(cfg)
        else:
            candidates = scan_candidates(cfg)
        total = sum(c['size'] for c in candidates)
        lines.append(f'found {len(candidates)} candidate(s), reclaimable {human_size(total)}')
        duplicates = []
        if dedupe:
            candidates, duplicates = dedupe_candidates(candidates)
        archive_dir = cfg.get('archive_dir') or str(_app_dir() / ('archive_' + datetime.now().strftime('%Y%m%d%H%M%S')))
        prf = None
        try:
            import proof as proof_module
            volume = proof_module.volume_of(archive_dir)
            before_free = proof_module.disk_free(volume)
        except Exception:
            proof_module = None
        log = apply_actions(candidates, cfg, archive_dir)
        if proof_module:
            try:
                prf = proof_module.build_proof(before_free, proof_module.disk_free(volume), log)
                c = prf['custody']
                lines.append(f"custody check: {c['verified']}/{c['total']} archived item(s) verified")
            except Exception:
                prf = None
        lines.append(f'archived {len(log)} item(s) to {archive_dir}')
        if duplicates:
            moved = move_duplicates(duplicates, archive_dir)
            lines.append(f'separated {moved} duplicate(s)')
        if log:
            try:
                import receipts as receipts_module
                bought = None
                try:
                    import foresight
                    fc = foresight.forecast(foresight.load_history())
                    freed = sum(int(e.get('size') or 0) for e in log)
                    bought = foresight.days_bought(freed, fc['slope_per_day'])
                except Exception:
                    bought = None
                receipt = receipts_module.write_receipt(log, days_bought=bought, proof=prf)
                if receipt:
                    lines.append(f'receipt: {receipt}')
            except Exception:
                pass
    except BaseException as e:  # SystemExit from load_config included
        lines.append(f'ERROR: {e}')
        rc = 1
    log_file = Path(log_to) if log_to else user_config_dir() / 'headless_run.log'
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open('a', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception:
        pass
    return rc


def main():
    ap = argparse.ArgumentParser(description='Cleanroom — archive-first Windows cleaner')
    ap.add_argument('--config', '-c', default=str(DEFAULT_CONFIG), help='Path to config file')
    ap.add_argument('--apply', action='store_true', help='Apply changes (moves files to archive)')
    ap.add_argument('--delete', '--permanent-delete', action='store_true', help='Delete files permanently instead of archiving')
    ap.add_argument('--dedupe', action='store_true', help='Detect and separate duplicates by hash')
    ap.add_argument('--no-prompt', action='store_true', help='Do not prompt for confirmation when applying')
    ap.add_argument('--confirm-threshold-gb', type=float, default=None, help='If set, prompt when total reclaimable size exceeds this many GB')
    ap.add_argument('--json', action='store_true', help='Output JSON report for dry-run')
    ap.add_argument('--telemetry', choices=['on', 'off', 'status'], help='Enable/disable telemetry or show status')
    ap.add_argument('--startup', choices=['list', 'json'], help='Show startup items (list or json)')
    ap.add_argument('--startup-enable', type=str, metavar='NAME=COMMAND', help='Enable startup entry (requires admin; format: name=C:\\path\\to\\exe.exe)')
    ap.add_argument('--startup-disable', type=str, metavar='NAME', help='Disable startup entry (requires admin)')
    ap.add_argument('--archive', choices=['summary', 'browse', 'manage'], help='Archive management: show summary, browse files, or interactive cleanup')
    ap.add_argument('--fast-scan', action='store_true', help='Use the high-performance parallel/incremental scanner')
    ap.add_argument('--profile', help='Use smart cleanup profile (conservative, aggressive, gaming)')
    args = ap.parse_args()

    # Handle telemetry toggle requests early and exit
    if getattr(args, 'telemetry', None):
        choice = args.telemetry
        if choice == 'status':
            # show current configured value
            try:
                cfg = load_config(args.config)
                tele = cfg.get('telemetry', {})
                enabled = bool(tele.get('enabled'))
                print('Telemetry enabled' if enabled else 'Telemetry disabled')
                return
            except SystemExit as e:
                print(e)
                return
        # enable/disable
        if enable_telemetry is None:
            # fallback to subprocess call
            import subprocess
            rc = subprocess.run([sys.executable, str(Path(__file__).parent / 'enable_telemetry.py'), 'on' if choice == 'on' else 'off'], capture_output=True, text=True)
            sys.exit(rc.returncode)
        else:
            # ensure module updates the same config path
            try:
                enable_telemetry.CFG = Path(args.config)
            except Exception:
                pass
            rc = enable_telemetry.main(enable=(choice == 'on'))
            sys.exit(rc)

    cfg = load_config(args.config)

    # Handle profile-based cleanup requests
    if getattr(args, 'profile', None):
        try:
            import cleanup_profiles
            smart_cfg = cleanup_profiles.SmartConfig()
            profile = smart_cfg.get_profile(args.profile)

            if not profile:
                print(f"❌ Profile not found: {args.profile}")
                return

            if not profile.enabled:
                print(f"❌ Profile disabled: {args.profile}")
                return

            print(f"📋 Using profile: {profile.name}")
            print(f"📝 Description: {profile.description}")
            print(f"📁 Paths: {', '.join(profile.paths)}")

            # Override config with profile settings
            cfg['paths'] = profile.paths

            # Get active rules for this profile
            rules = smart_cfg.get_active_rules(args.profile)
            print(f"📜 Active rules: {len(rules)}")

            # Apply rule-based filtering to candidates
            if args.fast_scan or cfg.get('performance_scan'):
                candidates = scan_candidates_fast(cfg)
            else:
                candidates = scan_candidates(cfg)
            filtered_candidates = []

            for candidate in candidates:
                matching_rule = smart_cfg.evaluate_file(candidate['path'], rules)
                if matching_rule:
                    candidate['rule'] = matching_rule.name
                    candidate['action'] = matching_rule.actions.get('operation', 'archive')
                    filtered_candidates.append(candidate)

            candidates = filtered_candidates
            print(f"🎯 Filtered candidates: {len(candidates)} (based on profile rules)")

        except ImportError:
            print("❌ Smart configuration not available - install smart_config.py")
            return
        except Exception as e:
            print(f"❌ Profile error: {e}")
            return

    # Handle archive management requests
    if getattr(args, 'archive', None):
        try:
            import archive_runtime
            archive_dir = cfg.get('archive_dir') or str(Path(__file__).parent / 'cleanup_archive')
            log_file = cfg.get('log_file') or 'cleanup_log.json'

            if args.archive == 'summary':
                summary = archive_runtime.get_archive_summary(archive_dir, log_file)
                archive_runtime.display_archive_summary(summary)
            elif args.archive == 'browse':
                files = archive_runtime.browse_archive(archive_dir, limit=50)
                archive_runtime.display_archive_files(files)
            elif args.archive == 'manage':
                archive_runtime.interactive_archive_cleanup(archive_dir, log_file)
            return
        except ImportError:
            print("Archive management not available - missing archive_manager.py")
            return
        except Exception as e:
            print(f"Archive management error: {e}")
            return

    # Handle startup enable/disable requests
    if getattr(args, 'startup_enable', None):
        try:
            import startup_manager_admin
            if '=' not in args.startup_enable:
                print('Invalid format. Use: name=C:\\path\\to\\exe.exe')
                return
            name, command = args.startup_enable.split('=', 1)
            success, msg = startup_manager_admin.enable_registry_run(name, command)
            print(msg)
            sys.exit(0 if success else 1)
        except Exception as e:
            print('Failed to enable startup entry:', e)
            sys.exit(1)
    if getattr(args, 'startup_disable', None):
        try:
            import startup_manager_admin
            success, msg = startup_manager_admin.disable_registry_run(args.startup_disable)
            print(msg)
            sys.exit(0 if success else 1)
        except Exception as e:
            print('Failed to disable startup entry:', e)
            sys.exit(1)

    # Handle startup listing requests
    if getattr(args, 'startup', None):
        try:
            import startup_manager
            data = startup_manager.list_startup_entries()
            if args.startup == 'json':
                print(json.dumps(data, indent=2))
            else:
                print('Startup folder items:')
                for e in data['folders']:
                    print(f" - {e['name']} ({e['path']}) from {e['location']}")
                print('\nRegistry Run entries:')
                for r in data['registry']:
                    print(f" - {r['name']}: {r['command']}")
        except Exception as e:
            print('Failed to list startup entries:', e)
        return
    # log run if telemetry enabled (non-blocking)
    try:
        if telemetry:
            telemetry.log_event(cfg, 'run', {'mode': 'apply' if args.apply else 'dry-run', 'dedupe': bool(args.dedupe)})
    except Exception:
        pass
    if args.fast_scan or cfg.get('performance_scan'):
        candidates = scan_candidates_fast(cfg)
    else:
        candidates = scan_candidates(cfg)
    total = sum(c['size'] for c in candidates)

    if args.json:
        out = {'count': len(candidates), 'total_bytes': total, 'candidates': candidates}
        print(json.dumps(out, indent=2))
        # Also write a planned-actions file mapping src -> planned archive dest (dry-run plan)
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        archive_dir = cfg.get('archive_dir') or str(Path(__file__).parent / f'cleanup_archive_{ts}')
        plan = []
        seen_names = {}
        for c in candidates:
            src = Path(c['path'])
            name = src.name
            # avoid name collisions deterministically
            count = seen_names.get(name, 0)
            seen_names[name] = count + 1
            if count == 0:
                dest_name = name
            else:
                dest_name = f"{ts}_{count}_{name}"
            dest = str(Path(archive_dir) / dest_name)
            plan.append({'src': str(src), 'dest': dest, 'reason': c['reason'], 'size': c['size']})
        plan_file = cfg.get('plan_file') or (Path(__file__).parent / 'cleanup_plan.json')
        try:
            Path(plan_file).write_text(json.dumps({'plan_time': ts, 'archive_dir': archive_dir, 'actions': plan}, indent=2), encoding='utf-8')
            # keep machine-readable JSON on stdout; write human messages to stderr
            print(f"Planned actions written to: {plan_file}", file=sys.stderr)
        except Exception:
            pass
    else:
        print(f"Found {len(candidates)} candidates, reclaimable: {human_size(total)}")
        for c in candidates[:200]:
            print(f" - {c['reason']}: {c['path']} ({human_size(c['size'])})")

    if args.apply or getattr(args, 'delete', False):
        if not candidates:
            print("No candidates to apply.")
            return

        permanent_delete = getattr(args, 'delete', False)

        # Handle rule-based actions from smart profiles
        if getattr(args, 'profile', None):
            # Group candidates by action type
            archive_candidates = [c for c in candidates if c.get('action') == 'archive']
            delete_candidates = [c for c in candidates if c.get('action') == 'delete']
            review_candidates = [c for c in candidates if c.get('action') == 'review']

            print("📊 Rule-based actions:")
            print(f"   📦 Archive: {len(archive_candidates)} files")
            print(f"   🗑️  Delete: {len(delete_candidates)} files")
            print(f"   👁️  Review: {len(review_candidates)} files")

            if review_candidates:
                print("\n⚠️  Files requiring review:")
                for c in review_candidates[:10]:
                    print(f"   • {c['path']} ({c['rule']})")
                if len(review_candidates) > 10:
                    print(f"   ... and {len(review_candidates) - 10} more")

            # Process each action type
            total_processed = 0

            if delete_candidates and (permanent_delete or input(f"\n🗑️  Delete {len(delete_candidates)} files? (y/N): ").lower() == 'y'):
                log = apply_actions(delete_candidates, cfg, cfg.get('archive_dir'), permanent_delete=True)
                total_processed += len(log)
                print(f"✅ Deleted {len(log)} files")

            if archive_candidates and input(f"\n📦 Archive {len(archive_candidates)} files? (y/N): ").lower() == 'y':
                archive_dir = cfg.get('archive_dir') or str(Path(__file__).parent / 'archive_' + datetime.now().strftime('%Y%m%d%H%M%S'))
                log = apply_actions(archive_candidates, cfg, archive_dir, permanent_delete=False)
                total_processed += len(log)
                print(f"✅ Archived {len(log)} files")

            print(f"\n🎉 Total processed: {total_processed} files")
            return

        action_type = "permanently delete" if permanent_delete else "move to archive"

        # interactive confirmation when reclaim size large
        total_bytes = sum(c['size'] for c in candidates)
        confirm_threshold = None
        if args.confirm_threshold_gb is not None:
            confirm_threshold = int(args.confirm_threshold_gb * 1024 * 1024 * 1024)
        else:
            # default threshold from config (in bytes) or 5GB
            confirm_threshold = cfg.get('confirm_threshold_bytes') or (5 * 1024 * 1024 * 1024)

        if (not args.no_prompt) and total_bytes >= confirm_threshold:
            # human-readable summary printed to stderr (keep stdout for machine use)
            print(f"About to {action_type} {len(candidates)} files, reclaimable: {human_size(total_bytes)}", file=sys.stderr)
            if permanent_delete:
                print("WARNING: This will permanently delete files! They cannot be recovered.", file=sys.stderr)
            ans = input("Proceed? (y/N): ")
            if ans.strip().lower() not in ('y', 'yes'):
                print("Aborting apply.", file=sys.stderr)
                return

        # handle duplicates if requested
        duplicates = []
        if getattr(args, 'dedupe', False):
            keep, duplicates = dedupe_candidates(candidates)
            print(f"Deduplication: {len(candidates) - len(keep)} duplicates detected")
            candidates = keep

        archive_dir = cfg.get('archive_dir') or (str(Path(__file__).parent / 'archive_' + datetime.now().strftime('%Y%m%d%H%M%S')))
        log = apply_actions(candidates, cfg, archive_dir, permanent_delete=permanent_delete)

        # optionally move duplicates into a subfolder for review (only if not deleting)
        if duplicates and not permanent_delete:
            dup_dir = Path(archive_dir) / 'duplicates'
            dup_dir.mkdir(parents=True, exist_ok=True)
            for d in duplicates:
                try:
                    src = Path(d['path'])
                    if not src.exists():
                        continue
                    dest = dup_dir / src.name
                    if dest.exists():
                        dest = dup_dir / (datetime.now().strftime('%Y%m%d%H%M%S_') + src.name)
                    shutil.move(str(src), str(dest))
                    print(f"Moved duplicate: {src} -> {dest}")
                except Exception as e:
                    print(f"Failed to move duplicate {src}: {e}")
        elif duplicates and permanent_delete:
            # Handle duplicates when deleting permanently
            for d in duplicates:
                try:
                    src = Path(d['path'])
                    if not src.exists():
                        continue
                    if send2trash and not cfg.get('force_permanent_delete', False):
                        send2trash(str(src))
                        print(f"Trashed duplicate: {src}")
                    else:
                        src.unlink()
                        print(f"Deleted duplicate: {src}")
                except Exception as e:
                    print(f"Failed to delete duplicate {src}: {e}")

        print(f"Actions logged to: {cfg.get('log_file')}")
    else:
        action_msg = "delete" if getattr(args, 'delete', False) else "move to archive"
        print(f'\nDry-run: no files were {action_msg}. Use --apply to move to archive or --delete to permanently delete.', file=sys.stderr)

if __name__ == '__main__':
    main()
