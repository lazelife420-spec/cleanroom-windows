#!/usr/bin/env python3
"""Installed-program listing, uninstall and leftover cleanup (IObit-style).

Registry reading is Windows-only; the parsing/matching helpers are pure and
unit-testable on any platform. Leftover cleanup is archive-first: folders are
moved into the archive and logged to cleanup_log.json so the Restore tab can
bring them back.
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

UNINSTALL_KEY_PATHS = [
    ('HKEY_LOCAL_MACHINE', r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
    ('HKEY_LOCAL_MACHINE', r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
    ('HKEY_CURRENT_USER', r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
]


def normalize_entry(raw, hive_name='', key_path='', subkey=''):
    """Turn a raw registry value dict into a program entry, or None if it
    should be hidden (updates, system components, nameless keys)."""
    name = (raw.get('DisplayName') or '').strip()
    if not name:
        return None
    if raw.get('SystemComponent') in (1, '1'):
        return None
    if raw.get('ParentKeyName'):  # patches/updates attach to a parent product
        return None
    if (raw.get('ReleaseType') or '').lower() in ('security update', 'update rollup', 'hotfix'):
        return None
    if not raw.get('UninstallString') and not raw.get('QuietUninstallString'):
        return None

    install_date = ''
    rd = str(raw.get('InstallDate') or '')
    if re.fullmatch(r'\d{8}', rd):
        install_date = f'{rd[0:4]}-{rd[4:6]}-{rd[6:8]}'

    size_kb = 0
    try:
        size_kb = int(raw.get('EstimatedSize') or 0)
    except (TypeError, ValueError):
        size_kb = 0

    install_location = str(raw.get('InstallLocation') or raw.get('InstallSource') or '').strip()
    if install_location:
        install_location = str(Path(install_location))

    return {
        'name': name,
        'version': str(raw.get('DisplayVersion') or ''),
        'publisher': str(raw.get('Publisher') or ''),
        'install_date': install_date,
        'size_kb': size_kb,
        'install_location': install_location,
        'comments': str(raw.get('Comments') or raw.get('DisplayIcon') or '').strip(),
        'uninstall_string': str(raw.get('UninstallString') or ''),
        'quiet_uninstall_string': str(raw.get('QuietUninstallString') or ''),
        'hive': hive_name,
        'key': key_path,
        'subkey': subkey,
    }


def list_installed_programs():
    """Enumerate installed programs from the Uninstall registry keys."""
    try:
        import winreg
    except Exception:
        return []
    seen = set()
    programs = []
    for hive_name, key_path in UNINSTALL_KEY_PATHS:
        hive = getattr(winreg, hive_name, None)
        if hive is None:
            continue
        try:
            root = winreg.OpenKey(hive, key_path)
        except Exception:
            continue
        with root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                raw = {}
                try:
                    with winreg.OpenKey(root, sub) as k:
                        j = 0
                        while True:
                            try:
                                vname, value, _ = winreg.EnumValue(k, j)
                                raw[vname] = value
                                j += 1
                            except OSError:
                                break
                except Exception:
                    continue
                entry = normalize_entry(raw, hive_name, key_path, sub)
                if entry is None:
                    continue
                dedup = (entry['name'].lower(), entry['version'])
                if dedup in seen:
                    continue
                seen.add(dedup)
                programs.append(entry)
    programs.sort(key=lambda e: e['name'].lower())
    return programs


FILTER_MODES = ('all', 'large', 'recent', 'old')


def filter_programs(entries, mode, now=None):
    """IObit-style smart filters over installed programs.

    all    everything
    large  EstimatedSize >= 1 GB
    recent installed within the last 30 days
    old    installed more than a year ago (unknown dates excluded)
    """
    from datetime import datetime, timedelta
    now = now or datetime.now()

    def installed(e):
        try:
            return datetime.strptime(e['install_date'], '%Y-%m-%d')
        except (KeyError, ValueError, TypeError):
            return None

    if mode == 'large':
        return [e for e in entries if e.get('size_kb', 0) >= 1024 * 1024]
    if mode == 'recent':
        cutoff = now - timedelta(days=30)
        return [e for e in entries if (d := installed(e)) and d >= cutoff]
    if mode == 'old':
        cutoff = now - timedelta(days=365)
        return [e for e in entries if (d := installed(e)) and d < cutoff]
    return list(entries)


def build_uninstall_command(entry, quiet=False):
    """Return the command line to launch the program's uninstaller."""
    if quiet and entry.get('quiet_uninstall_string'):
        return entry['quiet_uninstall_string']
    cmd = entry.get('uninstall_string') or entry.get('quiet_uninstall_string') or ''
    if quiet and cmd.lower().startswith('msiexec'):
        # msiexec accepts /qn for silent; /I (modify) must become /X (remove)
        cmd = re.sub(r'/I', '/X', cmd, count=1, flags=re.IGNORECASE)
        if '/qn' not in cmd.lower():
            cmd += ' /qn'
    return cmd


def run_uninstall(entry, quiet=False, timeout=1800):
    """Run the uninstaller and wait. Returns (exit_code, message)."""
    cmd = build_uninstall_command(entry, quiet)
    if not cmd:
        return 1, 'No uninstall command available.'
    try:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if quiet else 0
        result = subprocess.run(cmd, shell=True, timeout=timeout, creationflags=flags)
        return result.returncode, f'Uninstaller exited with code {result.returncode}.'
    except subprocess.TimeoutExpired:
        return 1, 'Uninstaller timed out.'
    except Exception as e:
        return 1, f'Failed to run uninstaller: {e}'


# ---------------------------------------------------------------------------
# Leftover scanning (archive-first)
# ---------------------------------------------------------------------------
_STOPWORDS = {'the', 'for', 'and', 'inc', 'llc', 'ltd', 'corporation', 'corp',
              'software', 'technologies', 'version', 'edition', 'x64', 'x86',
              '64-bit', '32-bit', 'windows'}


def name_tokens(program_name):
    """Significant lowercase tokens of a program name (no versions/noise)."""
    tokens = re.split(r'[^A-Za-z0-9]+', program_name.lower())
    return [t for t in tokens
            if len(t) >= 3 and t not in _STOPWORDS and not t.replace('.', '').isdigit()]


def match_leftover_dirs(program_name, candidate_names):
    """Return candidate folder names that look like leftovers of the program.

    A folder matches when it contains the longest significant token of the
    program name (e.g. 'MegaCorp FooPlayer 3.1' -> 'fooplayer')."""
    tokens = sorted(name_tokens(program_name), key=len, reverse=True)
    if not tokens:
        return []
    primary = tokens[0]
    return [c for c in candidate_names if primary in c.lower()]


def leftover_roots():
    roots = []
    for var in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA', 'APPDATA', 'PROGRAMDATA'):
        v = os.environ.get(var)
        if v and Path(v).exists():
            roots.append(Path(v))
    return roots


def find_leftovers(program_name, roots=None):
    """Scan the top level of common install/data roots for leftover folders."""
    results = []
    for root in (roots or leftover_roots()):
        try:
            children = [c for c in root.iterdir() if c.is_dir()]
        except Exception:
            continue
        names = [c.name for c in children]
        for matched in match_leftover_dirs(program_name, names):
            results.append(str(root / matched))
    return results


# ---------------------------------------------------------------------------
# Registry leftovers (archive-first: keys are exported to .reg, then deleted;
# a restore re-imports the .reg file)
# ---------------------------------------------------------------------------
REG_PREFIX = 'REGISTRY::'

SOFTWARE_ROOTS = [
    ('HKEY_CURRENT_USER', 'SOFTWARE'),
    ('HKEY_LOCAL_MACHINE', 'SOFTWARE'),
    ('HKEY_LOCAL_MACHINE', r'SOFTWARE\WOW6432Node'),
]

# Umbrella/vendor/system keys that must never be matched as "leftovers" —
# deleting them would take out far more than one program.
PROTECTED_KEY_NAMES = {
    'microsoft', 'windows', 'classes', 'policies', 'clients', 'wow6432node',
    'google', 'intel', 'amd', 'nvidia', 'apple', 'adobe', 'oracle', 'mozilla',
    'realtek', 'asus', 'dell', 'hp', 'lenovo', 'samsung', 'logitech',
}


def match_registry_keys(program_name, key_names):
    """Leftover-style match over registry key names, minus protected keys."""
    return [k for k in match_leftover_dirs(program_name, key_names)
            if k.lower() not in PROTECTED_KEY_NAMES]


def find_registry_leftovers(program_name, roots=None):
    """Scan top-level Software keys for leftovers of the program.
    Returns full key paths like 'HKEY_CURRENT_USER\\SOFTWARE\\FooPlayer'."""
    try:
        import winreg
    except Exception:
        return []
    results = []
    for hive_name, base in (roots or SOFTWARE_ROOTS):
        hive = getattr(winreg, hive_name, None)
        if hive is None:
            continue
        names = []
        try:
            with winreg.OpenKey(hive, base) as root:
                i = 0
                while True:
                    try:
                        names.append(winreg.EnumKey(root, i))
                        i += 1
                    except OSError:
                        break
        except Exception:
            continue
        for matched in match_registry_keys(program_name, names):
            results.append(f'{hive_name}\\{base}\\{matched}')
    return results


def export_registry_key(full_key, out_file):
    """reg export the key to a .reg file. Returns True on success."""
    try:
        result = subprocess.run(['reg', 'export', full_key, str(out_file), '/y'],
                                capture_output=True, timeout=60)
        return result.returncode == 0 and Path(out_file).exists()
    except Exception:
        return False


def delete_registry_key(full_key):
    try:
        result = subprocess.run(['reg', 'delete', full_key, '/f'],
                                capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False


def restore_registry_export(reg_file):
    """Re-import a .reg export and consume the file. Returns (ok, msg)."""
    if not Path(reg_file).exists():
        return False, f'missing registry export: {reg_file}'
    try:
        result = subprocess.run(['reg', 'import', str(reg_file)],
                                capture_output=True, timeout=60)
        if result.returncode != 0:
            err = (result.stderr or b'').decode(errors='replace').strip()
            return False, f'reg import failed: {err or result.returncode}'
        try:
            Path(reg_file).unlink()
        except Exception:
            pass
        return True, f'imported {reg_file} back into the registry'
    except Exception as e:
        return False, f'reg import failed: {e}'


def archive_registry_leftovers(keys, archive_dir, log_file,
                               export_fn=export_registry_key,
                               delete_fn=delete_registry_key):
    """Export each key into <archive>/uninstall_leftovers/registry, delete it,
    and log a restorable entry (src='REGISTRY::<key>', dest=<.reg file>)."""
    dest_root = Path(archive_dir) / 'uninstall_leftovers' / 'registry'
    dest_root.mkdir(parents=True, exist_ok=True)
    log_entries = []
    for full_key in keys:
        safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', full_key)
        out = dest_root / f'{datetime.now().strftime("%Y%m%d%H%M%S")}_{safe}.reg'
        if not export_fn(full_key, out):
            continue
        if not delete_fn(full_key):
            try:
                out.unlink()
            except Exception:
                pass
            continue
        try:
            size = out.stat().st_size
        except Exception:
            size = 0
        log_entries.append({
            'src': REG_PREFIX + full_key,
            'dest': str(out),
            'reason': 'registry-leftover',
            'size': size,
            'when': datetime.now().isoformat(),
        })
    if log_entries:
        _append_log(log_file, log_entries)
    return log_entries


def uninstall_key_path(entry):
    """Full registry path of the program's Uninstall key."""
    return f"{entry['hive']}\\{entry['key']}\\{entry['subkey']}"


def remove_uninstall_entry(entry, archive_dir, log_file,
                           export_fn=export_registry_key,
                           delete_fn=delete_registry_key):
    """Forced removal of an orphaned Programs-list entry (broken uninstaller):
    export the Uninstall key to .reg in the archive, then delete it. Returns
    the log entry, or None when the export/delete failed."""
    if not entry.get('hive') or not entry.get('subkey'):
        return None
    entries = archive_registry_leftovers(
        [uninstall_key_path(entry)], archive_dir, log_file,
        export_fn=export_fn, delete_fn=delete_fn)
    return entries[0] if entries else None


def collect_force_remove_targets(entry, program_name=None):
    """Folders and registry keys to offer during force remove."""
    program_name = program_name or entry.get('name') or ''
    dirs = find_leftovers(program_name)
    seen = {str(Path(d)).lower() for d in dirs}
    loc = (entry.get('install_location') or '').strip()
    if loc:
        p = Path(loc)
        if p.is_dir() and str(p).lower() not in seen:
            dirs.append(str(p))
            seen.add(str(p).lower())
    keys = find_registry_leftovers(program_name)
    return dirs, keys


def force_remove(entry, archive_dir, log_file, *,
                 chosen_dirs=None, chosen_keys=None,
                 remove_list_entry=True,
                 export_fn=export_registry_key,
                 delete_fn=delete_registry_key):
    """Archive selected leftovers, then remove the Programs-list entry.

    Returns dict with keys: folders, registry, list_entry (log entry or None).
    """
    name = entry.get('name') or ''
    if chosen_dirs is None or chosen_keys is None:
        default_dirs, default_keys = collect_force_remove_targets(entry, name)
        chosen_dirs = default_dirs if chosen_dirs is None else chosen_dirs
        chosen_keys = default_keys if chosen_keys is None else chosen_keys

    folders = archive_leftovers(chosen_dirs, archive_dir, log_file) if chosen_dirs else []
    registry = archive_registry_leftovers(
        chosen_keys, archive_dir, log_file, export_fn=export_fn, delete_fn=delete_fn,
    ) if chosen_keys else []
    list_entry = None
    if remove_list_entry:
        list_entry = remove_uninstall_entry(
            entry, archive_dir, log_file, export_fn=export_fn, delete_fn=delete_fn)
    return {'folders': folders, 'registry': registry, 'list_entry': list_entry}


def entry_requires_admin(entry):
    """True when registry changes likely need elevation (HKLM uninstall key)."""
    hive = (entry.get('hive') or '').upper()
    return 'LOCAL_MACHINE' in hive


def _append_log(log_file, new_entries):
    existing = []
    try:
        if Path(log_file).exists():
            existing = json.loads(Path(log_file).read_text(encoding='utf-8-sig'))
            if not isinstance(existing, list):
                existing = []
    except Exception:
        existing = []
    existing.extend(new_entries)
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    Path(log_file).write_text(json.dumps(existing, indent=2), encoding='utf-8')


def dir_size(path):
    total = 0
    try:
        for p in Path(path).rglob('*'):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total


def archive_leftovers(paths, archive_dir, log_file):
    """Move leftover folders into <archive>/uninstall_leftovers and log them
    to the cleanup log (same schema as the cleaner, so Restore works)."""
    dest_root = Path(archive_dir) / 'uninstall_leftovers'
    dest_root.mkdir(parents=True, exist_ok=True)
    log_entries = []
    for raw in paths:
        src = Path(raw)
        if not src.exists():
            continue
        dest = dest_root / src.name
        if dest.exists():
            dest = dest_root / (datetime.now().strftime('%Y%m%d%H%M%S_') + src.name)
        size = dir_size(src)
        try:
            shutil.move(str(src), str(dest))
        except Exception:
            continue
        log_entries.append({
            'src': str(src),
            'dest': str(dest),
            'reason': 'uninstall-leftover',
            'size': size,
            'when': datetime.now().isoformat(),
        })
    if log_entries:
        _append_log(log_file, log_entries)
    return log_entries
