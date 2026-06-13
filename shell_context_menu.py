#!/usr/bin/env python3
"""Windows Explorer context menu registration for Cleanroom (HKCU, per-user)."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

try:
    import brand
except ImportError:
    brand = None

TARGETS = {
    'all_files': ('All files', r'Software\Classes\*\shell'),
    'folders': ('Folders', r'Software\Classes\Directory\shell'),
    'folder_background': ('Folder background', r'Software\Classes\Directory\Background\shell'),
    'drives': ('Drives', r'Software\Classes\Drive\shell'),
}

ACTION_TEMPLATES = {
    'archive': ('Archive with Cleanroom', '--shell-archive "%1"'),
    'delete_archive': ('Delete from Cleanroom Archive', '--shell-delete-archive "%1"'),
    'open_archive_tab': ('Open Cleanroom Archive tab', '--open-tab archive'),
    'open_restore_tab': ('Open Cleanroom Restore tab', '--open-tab restore'),
    'open_receipt': ('Open Cleanroom Receipt', '--open-receipt "%1"'),
}

PRESETS = (
    {
        'id': 'archive_file',
        'label': 'Archive with Cleanroom',
        'target': 'all_files',
        'action': 'archive',
        'enabled_default': True,
    },
    {
        'id': 'delete_archive_file',
        'label': 'Delete from Cleanroom Archive',
        'target': 'all_files',
        'action': 'delete_archive',
        'enabled_default': False,
    },
    {
        'id': 'open_archive_folder_bg',
        'label': 'Open Cleanroom Archive',
        'target': 'folder_background',
        'action': 'open_archive_tab',
        'enabled_default': True,
    },
    {
        'id': 'archive_folder',
        'label': 'Archive folder with Cleanroom',
        'target': 'folders',
        'action': 'archive',
        'enabled_default': False,
    },
)


def menus_config_path():
    if brand:
        return brand.user_data_dir() / 'shell_context_menus.json'
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Cleanroom'
    return base / 'shell_context_menus.json'


def default_config():
    return {
        'presets': {p['id']: p['enabled_default'] for p in PRESETS},
        'custom': [],
    }


def load_config():
    path = menus_config_path()
    if not path.is_file():
        return default_config()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default_config()
    base = default_config()
    base['presets'].update(data.get('presets') or {})
    base['custom'] = list(data.get('custom') or [])
    return base


def save_config(cfg):
    path = menus_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    return path


def _registry_key_name(menu_id):
    safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in menu_id)
    return f'Cleanroom.{safe}'


def _param_placeholder(target):
    return '%V' if target == 'folder_background' else '%1'


def resolve_args(action_key, target, custom_args=None):
    if custom_args:
        template = custom_args
    else:
        template = ACTION_TEMPLATES.get(action_key, ('', ''))[1]
    if not template:
        return ''
    param = _param_placeholder(target)
    return template.replace('%1', param).replace('%V', param)


def build_command(exe_path, args):
    exe = str(Path(exe_path))
    return f'"{exe}" {args}'.strip()


def menu_item_from_preset(preset_id, enabled_map):
    preset = next((p for p in PRESETS if p['id'] == preset_id), None)
    if not preset or not enabled_map.get(preset_id):
        return None
    return {
        'id': preset_id,
        'label': preset['label'],
        'target': preset['target'],
        'args': resolve_args(preset['action'], preset['target']),
    }


def iter_enabled_menu_items(cfg=None):
    cfg = cfg or load_config()
    for preset in PRESETS:
        item = menu_item_from_preset(preset['id'], cfg.get('presets') or {})
        if item:
            yield item
    for custom in cfg.get('custom') or []:
        if not custom.get('enabled', True):
            continue
        target = custom.get('target') or 'all_files'
        args = custom.get('args') or resolve_args(
            custom.get('action', ''), target, custom.get('custom_args'))
        if not args and custom.get('action') not in ACTION_TEMPLATES:
            continue
        yield {
            'id': custom.get('id') or str(uuid.uuid4()),
            'label': custom.get('label') or 'Cleanroom',
            'target': target,
            'args': args,
        }


def _open_registry():
    if sys.platform != 'win32':
        raise OSError('Windows registry menus require win32')
    import winreg
    return winreg


HKCU_ROOT = 'Software\\Classes'


def _shell_parent_roots():
    for _label, rel in TARGETS.values():
        yield rel.rsplit('\\shell', 1)[0]


def list_installed_cleanroom_keys():
    """Return HKCU shell keys named Cleanroom.* that are currently registered."""
    winreg = _open_registry()
    found = []
    for root in _shell_parent_roots():
        shell_path = f'{root}\\shell'
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, shell_path) as shell_key:
                idx = 0
                while True:
                    try:
                        name = winreg.EnumKey(shell_key, idx)
                    except OSError:
                        break
                    if name.startswith('Cleanroom.'):
                        found.append((root, name))
                    idx += 1
        except OSError:
            continue
    return found


def uninstall_cleanroom_shell_keys():
    """Remove every HKCU Cleanroom.* shell key under known Explorer targets."""
    winreg = _open_registry()
    for root, name in list(list_installed_cleanroom_keys()):
        shell_key = f'{root}\\shell\\{name}'
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f'{shell_key}\\command')
        except OSError:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, shell_key)
        except OSError:
            pass
    return list_installed_cleanroom_keys()


def install_menu_item(exe_path, menu_id, label, target, args, icon=None):
    winreg = _open_registry()
    root, _sub = TARGETS[target][1].rsplit('\\shell', 1)
    shell_key = f'{root}\\shell\\{_registry_key_name(menu_id)}'
    cmd_key = f'{shell_key}\\command'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, shell_key) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, label)
        if icon:
            winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, icon)
    command = build_command(exe_path, args)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cmd_key) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, command)
    return command


def uninstall_menu_item(menu_id, target):
    winreg = _open_registry()
    root, _sub = TARGETS[target][1].rsplit('\\shell', 1)
    shell_key = f'{root}\\shell\\{_registry_key_name(menu_id)}'
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f'{shell_key}\\command')
    except OSError:
        pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, shell_key)
    except OSError:
        pass


def install_all(exe_path, cfg=None):
    cfg = cfg or load_config()
    installed = []
    for item in iter_enabled_menu_items(cfg):
        cmd = install_menu_item(
            exe_path, item['id'], item['label'], item['target'], item['args'],
            icon=f'{exe_path},0',
        )
        installed.append({**item, 'command': cmd})
    return installed


def uninstall_all(cfg=None):
    cfg = cfg or load_config()
    for preset in PRESETS:
        uninstall_menu_item(preset['id'], preset['target'])
    for custom in cfg.get('custom') or []:
        uninstall_menu_item(custom.get('id', ''), custom.get('target', 'all_files'))
    uninstall_cleanroom_shell_keys()


def add_custom_menu(label, target, action=None, custom_args=None, enabled=True):
    cfg = load_config()
    entry = {
        'id': f'custom_{uuid.uuid4().hex[:8]}',
        'label': label,
        'target': target,
        'action': action or '',
        'custom_args': custom_args or '',
        'enabled': enabled,
    }
    cfg.setdefault('custom', []).append(entry)
    save_config(cfg)
    return entry
