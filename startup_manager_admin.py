#!/usr/bin/env python3
"""Startup manager admin: enable/disable startup entries (requires admin).

This module requires administrator privileges for registry writes.
"""
import ctypes
import json
import sys
from datetime import datetime

# Backup store for disabled startup entries: disabling is reversible, in line
# with the app's archive-first philosophy. Per-user and writable without admin.
import brand

DISABLED_STORE = brand.user_data_dir() / 'disabled_startup.json'


def _load_disabled():
    try:
        if DISABLED_STORE.exists():
            data = json.loads(DISABLED_STORE.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_disabled(entries):
    DISABLED_STORE.parent.mkdir(parents=True, exist_ok=True)
    DISABLED_STORE.write_text(json.dumps(entries, indent=2), encoding='utf-8')


def list_disabled():
    """Return backed-up (disabled) startup entries."""
    return _load_disabled()


def backup_disabled_entry(name, command, hive_name, key_path):
    """Save a startup entry before it is removed; replaces an older backup of the same name/hive."""
    entries = [e for e in _load_disabled()
               if not (e.get('name') == name and e.get('hive') == hive_name)]
    entries.append({
        'name': name,
        'command': command,
        'hive': hive_name,
        'key': key_path,
        'disabled_at': datetime.now().isoformat(),
    })
    _save_disabled(entries)


def remove_disabled(name, hive_name=None):
    """Drop a backup entry (after a successful re-enable). Returns removed count."""
    entries = _load_disabled()
    kept = [e for e in entries
            if not (e.get('name') == name and (hive_name is None or e.get('hive') == hive_name))]
    if len(kept) != len(entries):
        _save_disabled(kept)
    return len(entries) - len(kept)


def restore_disabled(name, hive_name=None):
    """Re-create a disabled startup entry from its backup.

    Returns (success: bool, message: str).
    """
    match = next((e for e in _load_disabled()
                  if e.get('name') == name and (hive_name is None or e.get('hive') == hive_name)), None)
    if match is None:
        return False, f'No backup found for {name}'
    ok, msg = enable_registry_run(match['name'], match.get('command') or '', match.get('hive') or 'HKEY_CURRENT_USER')
    if ok:
        remove_disabled(name, match.get('hive'))
        return True, f'Restored {name} to startup'
    return ok, msg


def is_admin():
    """Check if running as administrator."""
    try:
        result = ctypes.windll.shell32.IsUserAnAdmin()
        return bool(result)
    except Exception:
        return False


def enable_registry_run(name: str, command: str, hive_name: str = 'HKEY_CURRENT_USER'):
    """Enable a startup entry in the Windows Run registry key.
    
    Args:
        name: Entry name (e.g., 'MyApp').
        command: Command to run (e.g., 'C:\\Path\\To\\App.exe').
        hive_name: Registry hive ('HKEY_CURRENT_USER' or 'HKEY_LOCAL_MACHINE').
    
    Returns:
        (success: bool, message: str)
    """
    try:
        import winreg
    except Exception:
        return False, 'winreg module not available (Windows only)'

    if not is_admin():
        return False, 'Administrator privileges required'

    hive = getattr(winreg, hive_name, None)
    if hive is None:
        return False, f'Unknown hive: {hive_name}'

    try:
        key_path = r'Software\Microsoft\Windows\CurrentVersion\Run'
        with winreg.OpenKey(hive, key_path, access=winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
        try:
            remove_disabled(name, hive_name)  # entry is live again; drop stale backup
        except Exception:
            pass
        return True, f'Enabled {name} in registry'
    except PermissionError:
        return False, 'Permission denied (admin required)'
    except Exception as e:
        return False, f'Registry error: {e}'


def disable_registry_run(name: str, hive_name: str = 'HKEY_CURRENT_USER'):
    """Remove a startup entry from the Windows Run registry key.
    
    Args:
        name: Entry name to disable.
        hive_name: Registry hive.
    
    Returns:
        (success: bool, message: str)
    """
    try:
        import winreg
    except Exception:
        return False, 'winreg module not available (Windows only)'

    if not is_admin():
        return False, 'Administrator privileges required'

    hive = getattr(winreg, hive_name, None)
    if hive is None:
        return False, f'Unknown hive: {hive_name}'

    try:
        key_path = r'Software\Microsoft\Windows\CurrentVersion\Run'
        # Read the current command first so disabling stays reversible
        with winreg.OpenKey(hive, key_path, access=winreg.KEY_READ) as key:
            command, _ = winreg.QueryValueEx(key, name)
        with winreg.OpenKey(hive, key_path, access=winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, name)
        try:
            backup_disabled_entry(name, command, hive_name, key_path)
            return True, f'Disabled {name} (backed up — can be restored from the Disabled list)'
        except Exception:
            return True, f'Disabled {name} in registry (warning: backup failed)'
    except FileNotFoundError:
        return False, f'Entry {name} not found'
    except PermissionError:
        return False, 'Permission denied (admin required)'
    except Exception as e:
        return False, f'Registry error: {e}'


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Enable/disable startup entries (requires admin)')
    ap.add_argument('--enable', type=str, metavar='NAME=COMMAND', help='Enable startup entry (format: name=C:\\path\\to\\exe.exe)')
    ap.add_argument('--disable', type=str, metavar='NAME', help='Disable startup entry by name (backed up for restore)')
    ap.add_argument('--restore', type=str, metavar='NAME', help='Restore a previously disabled entry from backup')
    ap.add_argument('--list-disabled', action='store_true', help='List backed-up (disabled) startup entries')
    ap.add_argument('--hive', choices=['HKEY_CURRENT_USER', 'HKEY_LOCAL_MACHINE'], default='HKEY_CURRENT_USER', help='Registry hive (default: HKEY_CURRENT_USER)')
    ap.add_argument('--json', action='store_true', help='Output JSON result')
    args = ap.parse_args()

    if args.list_disabled:
        entries = list_disabled()
        if args.json:
            print(json.dumps(entries, indent=2))
        else:
            for e in entries:
                print(f" - {e.get('name')}: {e.get('command')} ({e.get('hive')}, disabled {e.get('disabled_at')})")
            if not entries:
                print('No disabled entries backed up.')
        return

    result = None
    if args.restore:
        result = restore_disabled(args.restore)
    elif args.enable:
        if '=' not in args.enable:
            result = (False, 'Invalid format. Use: name=C:\\path\\to\\exe.exe')
        else:
            name, command = args.enable.split('=', 1)
            success, msg = enable_registry_run(name, command, args.hive)
            result = (success, msg)
    elif args.disable:
        success, msg = disable_registry_run(args.disable, args.hive)
        result = (success, msg)
    else:
        ap.print_help()
        return

    if result:
        success, msg = result
        if args.json:
            print(json.dumps({'success': success, 'message': msg}))
        else:
            print(msg)
            sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
