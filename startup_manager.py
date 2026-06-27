#!/usr/bin/env python3
"""Startup manager: list startup entries from startup folders and registry.

This module is read-only by default and safe to run on non-Windows platforms.
"""
import json
import os
from pathlib import Path


def _get_startup_folders():
    folders = []
    # per-user Startup
    appdata = os.environ.get('APPDATA')
    if appdata:
        folders.append(Path(appdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup')
    # common Startup
    programdata = os.environ.get('PROGRAMDATA')
    if programdata:
        folders.append(Path(programdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'StartUp')
    return folders

def _list_folder_entries(folders):
    out = []
    for f in folders:
        try:
            p = Path(f)
            if not p.exists():
                continue
            for child in p.iterdir():
                if child.is_file():
                    out.append({'source': 'folder', 'location': str(p), 'name': child.name, 'path': str(child.resolve())})
        except Exception:
            continue
    return out

def _list_registry_entries():
    # Attempt to read registry Run keys on Windows; otherwise return empty list
    entries = []
    try:
        import winreg
    except Exception:
        return entries

    keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        # 64-bit/32-bit view
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
    ]

    for hive, subkey in keys:
        try:
            with winreg.OpenKey(hive, subkey) as k:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(k, i)
                        entries.append({'source': 'registry', 'hive': str(hive), 'key': subkey, 'name': name, 'command': value})
                        i += 1
                    except OSError:
                        break
        except Exception:
            continue
    return entries

def _parse_schtasks_csv(text):
    """Parse `schtasks /Query /FO CSV /V` output, returning logon-triggered tasks.

    schtasks repeats the header row for every task folder; those rows are
    skipped by checking for the literal 'TaskName' value.
    """
    import csv
    import io
    entries = []
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            name = (row.get('TaskName') or '').strip()
            if not name or name == 'TaskName':
                continue
            sched = (row.get('Schedule Type') or '').lower()
            if 'logon' not in sched:
                continue
            entries.append({
                'source': 'task',
                'location': name,
                'name': name.rsplit('\\', 1)[-1],
                'command': (row.get('Task To Run') or '').strip(),
                'status': (row.get('Status') or '').strip(),
            })
    except Exception:
        return []
    return entries


def _list_logon_tasks():
    """List Task Scheduler tasks that run at logon (read-only). Windows only."""
    import subprocess
    try:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        out = subprocess.run(['schtasks', '/Query', '/FO', 'CSV', '/V'],
                             capture_output=True, text=True, timeout=60,
                             creationflags=flags)
        if out.returncode != 0:
            return []
        return _parse_schtasks_csv(out.stdout)
    except Exception:
        return []


def list_startup_entries():
    folders = _get_startup_folders()
    folder_entries = _list_folder_entries(folders)
    reg_entries = _list_registry_entries()
    task_entries = _list_logon_tasks()
    return {'folders': folder_entries, 'registry': reg_entries, 'tasks': task_entries}


def main():
    import argparse
    ap = argparse.ArgumentParser(description='List startup entries (read-only)')
    ap.add_argument('--json', action='store_true', help='Print JSON')
    args = ap.parse_args()
    data = list_startup_entries()
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print('Startup folder items:')
        for e in data['folders']:
            print(f" - {e['name']} ({e['path']}) from {e['location']}")
        print('\nRegistry Run entries:')
        for r in data['registry']:
            print(f" - {r['name']}: {r['command']}")


if __name__ == '__main__':
    main()
