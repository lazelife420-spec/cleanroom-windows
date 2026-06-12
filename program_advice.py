"""Local-only installed-program guidance — no web lookups, no telemetry.

Heuristics inspired by common uninstaller UX (publisher/name/category rules).
"""
from __future__ import annotations

import re
from pathlib import Path

# Verdict keys used by the GUI for coloring.
KEEP = 'keep'
USUALLY_KEEP = 'usually_keep'
OPTIONAL = 'optional'
SAFE_IF_UNUSED = 'safe_if_unused'
CAUTION = 'caution'
UNKNOWN = 'unknown'

VERDICT_LABELS = {
    KEEP: 'Keep — likely required for Windows or hardware',
    USUALLY_KEEP: 'Usually keep — shared runtime or driver support',
    OPTIONAL: 'Optional — remove only if you do not use this app',
    SAFE_IF_UNUSED: 'Safe if unused — remove if you do not recognize or need it',
    CAUTION: 'Caution — use the official uninstaller; do not force-remove blindly',
    UNKNOWN: 'Review — not enough local signals; decide based on whether you use it',
}

SYSTEM_PUBLISHERS = (
    'microsoft corporation', 'microsoft', 'windows', 'microsoft windows',
)
DRIVER_PUBLISHERS = (
    'intel', 'intel corporation', 'nvidia', 'nvidia corporation', 'advanced micro devices',
    'amd', 'realtek', 'realtek semiconductor', 'qualcomm', 'broadcom', 'dell inc', 'dell',
    'hp inc', 'hewlett-packard', 'lenovo', 'asus', 'acer', 'samsung',
)
SECURITY_PUBLISHERS = (
    'norton', 'symantec', 'mcafee', 'kaspersky', 'avast', 'avg', 'bitdefender',
    'malwarebytes', 'eset', 'trend micro', 'sophos', 'crowdstrike',
)

RUNTIME_NAME_HINTS = (
    'visual c++', 'redistributable', 'microsoft .net', '.net framework', '.net desktop',
    'directx', 'runtime', 'windows sdk', 'edge webview', 'webview2',
)
SYSTEM_NAME_HINTS = (
    'windows', 'microsoft edge', 'defender', 'update assistant', 'windows kit',
    'powershell', 'terminal', 'oneDrive', 'microsoft store',
)
DRIVER_NAME_HINTS = (
    'driver', 'bluetooth', 'wireless', 'wifi', 'audio', 'graphics', 'chipset',
    'touchpad', 'lan ', 'ethernet',
)
BLOAT_NAME_HINTS = (
    'toolbar', 'optimizer', 'registry cleaner', 'pc cleaner', 'speed up',
    'browser helper', 'coupon', 'search protect', 'ask toolbar', 'bloat',
    'trial', 'adware',
)
DEV_TOOL_HINTS = (
    'python', 'node.js', 'git', 'visual studio', 'inno setup', 'cmake',
    'docker', 'java', 'jdk', 'android studio', 'cursor', 'vscode',
)


def _norm(s: str) -> str:
    return (s or '').strip().lower()


def _category(name: str, publisher: str) -> str:
    n, p = _norm(name), _norm(publisher)
    combined = f'{n} {p}'
    if any(h in combined for h in RUNTIME_NAME_HINTS):
        return 'runtime'
    if any(h in combined for h in SYSTEM_NAME_HINTS) or any(x in p for x in SYSTEM_PUBLISHERS):
        return 'system'
    if any(h in combined for h in DRIVER_NAME_HINTS) or any(x in p for x in DRIVER_PUBLISHERS):
        return 'driver'
    if any(x in p for x in SECURITY_PUBLISHERS) or 'security' in combined or 'antivirus' in combined:
        return 'security'
    if any(h in combined for h in DEV_TOOL_HINTS):
        return 'dev_tool'
    if any(h in combined for h in BLOAT_NAME_HINTS):
        return 'bloat'
    if 'game' in combined or 'steam' in combined or 'epic games' in combined:
        return 'game'
    return 'application'


def _what_is(name: str, publisher: str, category: str) -> str:
    pub = (publisher or 'Unknown publisher').strip()
    if category == 'system':
        return f'Windows or Microsoft component published by {pub}.'
    if category == 'driver':
        return f'Hardware/driver software from {pub} for this PC.'
    if category == 'runtime':
        return f'Shared library/runtime from {pub} used by other programs.'
    if category == 'security':
        return f'Security or antivirus product from {pub}.'
    if category == 'dev_tool':
        return f'Development tool: {name} ({pub}).'
    if category == 'game':
        return f'Game or game platform: {name} ({pub}).'
    if category == 'bloat':
        return f'Optional utility or add-on: {name} ({pub}).'
    return f'Installed application: {name} ({pub}).'


def _what_does(category: str, name: str) -> str:
    n = _norm(name)
    if category == 'system':
        return 'Supports Windows updates, built-in features, or OS services.'
    if category == 'driver':
        return 'Lets Windows talk to Wi‑Fi, Bluetooth, audio, graphics, or other hardware.'
    if category == 'runtime':
        return 'Other apps may depend on this; removing it can break programs until reinstalled.'
    if category == 'security':
        return 'Provides malware protection, firewall, or endpoint security services.'
    if category == 'dev_tool':
        return 'Used to build, run, or package software — not needed for everyday PC use.'
    if category == 'game':
        return 'Entertainment software — safe to remove if you no longer play it.'
    if category == 'bloat':
        return 'Often bundled extras, optimizers, or toolbars — rarely essential.'
    if 'download manager' in n or 'idm' in n:
        return 'Accelerates or manages file downloads in your browser.'
    if '7-zip' in n or 'winrar' in n:
        return 'Opens and creates compressed archives (.zip, .7z, etc.).'
    if 'appgate' in n:
        return 'Enterprise VPN / zero-trust network access client (work access).'
    return 'Runs when you open it or in the background depending on how it was installed.'


def _verdict(category: str, name: str, publisher: str, *,
             uninstaller_missing: bool, size_kb: int, install_age_days: int | None) -> str:
    if category == 'system':
        return KEEP
    if category in ('driver', 'security'):
        return CAUTION
    if category == 'runtime':
        return USUALLY_KEEP
    if category == 'dev_tool':
        return OPTIONAL
    if category == 'bloat':
        return SAFE_IF_UNUSED
    if category == 'game':
        return SAFE_IF_UNUSED
    if uninstaller_missing:
        return SAFE_IF_UNUSED
    if size_kb >= 1024 * 1024:  # >= 1 GB
        return SAFE_IF_UNUSED
    if install_age_days is not None and install_age_days > 365:
        return SAFE_IF_UNUSED
    return OPTIONAL


def _need_line(verdict: str, category: str, uninstaller_missing: bool) -> str:
    label = VERDICT_LABELS.get(verdict, VERDICT_LABELS[UNKNOWN])
    if uninstaller_missing and verdict not in (KEEP, USUALLY_KEEP, CAUTION):
        return f'{label} Uninstaller appears missing — Force Remove is appropriate after backup.'
    if category == 'security':
        return f'{label} Prefer the vendor\'s official removal tool if uninstall fails.'
    return label


def parse_uninstall_exe(cmd: str) -> str | None:
    """First executable path from an UninstallString, or None for MSI/shell-only."""
    cmd = (cmd or '').strip()
    if not cmd or cmd.lower().startswith('msiexec'):
        return None
    m = re.match(r'^"([^"]+)"', cmd)
    if m:
        return m.group(1)
    m = re.match(r'^(\S+\.exe\b)', cmd, re.IGNORECASE)
    return m.group(1) if m else None


def uninstaller_exe_exists(entry: dict) -> bool:
    cmd = entry.get('uninstall_string') or entry.get('quiet_uninstall_string') or ''
    if _norm(cmd).startswith('msiexec'):
        return True
    path = parse_uninstall_exe(cmd)
    if not path:
        return False
    try:
        return Path(path).is_file()
    except Exception:
        return False


def analyze_program(entry: dict, *, now=None) -> dict:
    """Return local guidance for one installed program entry."""
    name = entry.get('name') or 'Unknown program'
    publisher = entry.get('publisher') or ''
    category = _category(name, publisher)
    missing = not uninstaller_exe_exists(entry)

    install_age_days = None
    inst = entry.get('install_date') or ''
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', inst):
        try:
            from datetime import datetime
            now = now or datetime.now()
            delta = now - datetime.strptime(inst, '%Y-%m-%d')
            install_age_days = delta.days
        except Exception:
            pass

    verdict = _verdict(
        category, name, publisher,
        uninstaller_missing=missing,
        size_kb=int(entry.get('size_kb') or 0),
        install_age_days=install_age_days,
    )
    uninstall_note = (
        'Uninstaller executable not found — normal uninstall may fail; Force Remove available.'
        if missing else 'Uninstaller path looks present — try Uninstall first.'
    )
    if _norm(entry.get('uninstall_string') or '').startswith('msiexec'):
        uninstall_note = 'Windows Installer (MSI) package — uninstall via msiexec /x.'

    return {
        'category': category,
        'what_is': _what_is(name, publisher, category),
        'what_does': _what_does(category, name),
        'verdict': verdict,
        'need': _need_line(verdict, category, missing),
        'uninstaller_status': 'missing' if missing else 'ok',
        'uninstaller_note': uninstall_note,
    }
