#!/usr/bin/env python3
import argparse
import fnmatch
import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

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

def scan_candidates(cfg):
    candidates = []
    paths = cfg.get('paths', [])
    age_temp = cfg.get('age_days', {}).get('temp', 7)
    age_installers = cfg.get('age_days', {}).get('installers', 30)
    size_threshold = cfg.get('size_threshold_mb', 200) * 1024 * 1024
    ext_archive = set(x.lower() for x in cfg.get('extensions_archive', []))

    exclude_patterns = cfg.get('exclude_patterns', []) or []
    whitelist = cfg.get('whitelist', []) or []
    for root in paths:
        rootp = Path(root).expanduser()
        if not rootp.exists():
            continue
        if _matches_patterns(str(rootp), exclude_patterns):
            continue
        for f in rootp.rglob('*'):
            if not f.is_file():
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
            # zero-byte
            if size == 0 and is_older_than(f, age_temp):
                candidates.append({'path': path_str, 'reason': 'zero-byte', 'size': size})
                continue
            # partial downloads
            if f.name.endswith('.crdownload') and is_older_than(f, 7):
                candidates.append({'path': str(f), 'reason': 'partial-download', 'size': size})
                continue
            # installers/archives older than installers age
            if ext in ext_archive and is_older_than(f, age_installers):
                candidates.append({'path': str(f), 'reason': 'installer/archive', 'size': size})
                continue
            # large files older than 7 days
            if size >= size_threshold and is_older_than(f, 7):
                candidates.append({'path': str(f), 'reason': 'large-file', 'size': size})
    return candidates

def human_size(n):
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024:
            return f"{n:.2f}{unit}"
        n /= 1024
    return f"{n:.2f}PB"

def apply_actions(candidates, cfg, archive_dir):
    archive_dir = Path(archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)
    log = []
    for c in candidates:
        src = Path(c['path'])
        if not src.exists():
            continue
        try:
            dest = archive_dir / src.name
            if dest.exists():
                dest = archive_dir / (datetime.now().strftime('%Y%m%d%H%M%S_') + src.name)
            shutil.move(str(src), str(dest))
            entry = {'src': str(src), 'dest': str(dest), 'reason': c['reason'], 'size': c['size'], 'when': datetime.now().isoformat()}
            log.append(entry)
            print(f"Moved: {src} -> {dest}")
        except Exception as e:
            print(f"Failed to move {src}: {e}")
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
    for size, group in size_map.items():
        if len(group) == 1:
            to_keep.extend(group)
            continue
        # compute hashes for group
        hash_map = {}
        for c in group:
            p = Path(c['path'])
            h = file_hash(p)
            key = (size, h)
            if h is None:
                # can't hash, keep
                to_keep.append(c)
                continue
            if key in hash_map:
                # duplicate -> mark for duplicate handling
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
    ap.add_argument('--dedupe', action='store_true', help='Detect and separate duplicates by hash')
    ap.add_argument('--no-prompt', action='store_true', help='Do not prompt for confirmation when applying')
    ap.add_argument('--confirm-threshold-gb', type=float, default=None, help='If set, prompt when total reclaimable size exceeds this many GB')
    ap.add_argument('--json', action='store_true', help='Output JSON report for dry-run')
    ap.add_argument('--telemetry', choices=['on', 'off', 'status'], help='Enable/disable telemetry or show status')
    ap.add_argument('--startup', choices=['list', 'json'], help='Show startup items (list or json)')
    ap.add_argument('--startup-enable', type=str, metavar='NAME=COMMAND', help='Enable startup entry (requires admin; format: name=C:\\path\\to\\exe.exe)')
    ap.add_argument('--startup-disable', type=str, metavar='NAME', help='Disable startup entry (requires admin)')
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

    if args.apply:
        if not candidates:
            print("No candidates to apply.")
            return
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
            print(f"About to move {len(candidates)} files, reclaimable: {human_size(total_bytes)}", file=sys.stderr)
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
        log = apply_actions(candidates, cfg, archive_dir)
        # optionally move duplicates into a subfolder for review
        if duplicates:
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
        print(f"Actions logged to: {cfg.get('log_file')}")
    else:
        print('\nDry-run: no files were moved. Use --apply to move candidates to archive.', file=sys.stderr)

if __name__ == '__main__':
    main()
