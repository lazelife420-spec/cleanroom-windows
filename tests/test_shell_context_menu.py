"""Tests for shell_context_menu helpers (no registry writes)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import shell_context_menu as scm


def test_resolve_args_uses_v_for_folder_background():
    args = scm.resolve_args('archive', 'folder_background')
    assert '%V' in args
    assert '%1' not in args


def test_resolve_args_uses_one_for_files():
    args = scm.resolve_args('archive', 'all_files')
    assert '%1' in args


def test_iter_enabled_menu_items_respects_presets():
    cfg = scm.default_config()
    cfg['presets']['archive_file'] = True
    cfg['presets']['delete_archive_file'] = False
    items = list(scm.iter_enabled_menu_items(cfg))
    ids = {i['id'] for i in items}
    assert 'archive_file' in ids
    assert 'delete_archive_file' not in ids


def test_build_command_quotes_exe():
    cmd = scm.build_command(r'C:\Apps\Cleanroom.exe', '--open-tab archive')
    assert cmd.startswith('"C:\\Apps\\Cleanroom.exe"')


def test_uninstall_all_sweeps_cleanroom_keys(monkeypatch):
    if sys.platform != 'win32':
        return
    seen = []

    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    fake_winreg = type('WR', (), {
        'HKEY_CURRENT_USER': 1,
        'REG_SZ': 2,
        'CreateKey': lambda *a, **k: FakeKey(),
        'SetValueEx': lambda *a, **k: None,
        'DeleteKey': lambda *a, **k: seen.append(a[1]),
        'OpenKey': lambda *a, **k: (_ for _ in ()).throw(OSError()),
    })
    monkeypatch.setattr(scm, '_open_registry', lambda: fake_winreg)
    monkeypatch.setattr(scm, 'list_installed_cleanroom_keys',
                        lambda: [('Software\\Classes\\*', 'Cleanroom.test')])
    scm.uninstall_cleanroom_shell_keys()
    assert any('Cleanroom.test' in k for k in seen)
