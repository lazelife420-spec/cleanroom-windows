"""Unit tests for registry_health (pure helpers + archive-first repair flow)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import registry_health as rh


def never(_path):
    return False


def no_which(_name, *a, **k):
    return None


# ---------------------------------------------------------------------------
# extract_exe_path
# ---------------------------------------------------------------------------
def test_extract_exe_path_quoted():
    assert rh.extract_exe_path(r'"C:\Tools\My App\app.exe" --tray',
                               exists=never) == r'C:\Tools\My App\app.exe'


def test_extract_exe_path_unquoted_with_spaces_prefers_existing_prefix():
    target = r'C:\Program Files\Foo\foo.exe'
    def exists(path):
        return path == target

    assert rh.extract_exe_path(r'C:\Program Files\Foo\foo.exe /silent',
                               exists=exists) == target


def test_extract_exe_path_falls_back_to_first_token():
    assert rh.extract_exe_path(r'C:\gone\app.exe --flag', exists=never) == r'C:\gone\app.exe'


def test_extract_exe_path_empty():
    assert rh.extract_exe_path('', exists=never) is None
    assert rh.extract_exe_path(None, exists=never) is None


# ---------------------------------------------------------------------------
# is_broken_command
# ---------------------------------------------------------------------------
def test_is_broken_command_missing_file_is_broken():
    assert rh.is_broken_command(r'"C:\gone\app.exe" /run', exists=never, which=no_which)


def test_is_broken_command_existing_file_is_healthy():
    def exists(path):
        return path == r'C:\ok\app.exe'

    assert not rh.is_broken_command(r'"C:\ok\app.exe" /run', exists=exists, which=no_which)


def test_is_broken_command_host_launchers_never_flagged():
    for host in (r'rundll32.exe C:\gone\thing.dll,Entry', 'cmd /c del x',
                 r'C:\Windows\System32\rundll32.exe shell32.dll,Foo'):
        assert not rh.is_broken_command(host, exists=never, which=no_which)


def test_is_broken_command_bare_name_resolved_via_path_is_healthy():
    def which(name):
        return r'C:\Windows\notepad.exe' if 'notepad' in name else None

    assert not rh.is_broken_command('notepad', exists=never, which=which)
    assert rh.is_broken_command('definitely-not-a-real-binary', exists=never, which=no_which)


# ---------------------------------------------------------------------------
# scanners (injected data)
# ---------------------------------------------------------------------------
def test_scan_dead_startup_refs_flags_only_broken():
    values = [
        ('HKEY_CURRENT_USER', r'Software\...\Run', 'Dead', r'"C:\gone\a.exe" -x'),
        ('HKEY_CURRENT_USER', r'Software\...\Run', 'Alive', r'"C:\ok\b.exe"'),
    ]
    def exists(path):
        return path == r'C:\ok\b.exe'

    issues = rh.scan_dead_startup_refs(values=values, exists=exists, which=no_which)
    assert [i['display'] for i in issues] == ['Dead']
    assert issues[0]['fix'] == 'delete-value'
    assert issues[0]['value_name'] == 'Dead'


def test_scan_broken_app_paths():
    entries = [
        ('HKEY_LOCAL_MACHINE', r'SOFTWARE\...\App Paths', 'gone.exe', r'"C:\gone\gone.exe"'),
        ('HKEY_LOCAL_MACHINE', r'SOFTWARE\...\App Paths', 'ok.exe', r'C:\ok\ok.exe'),
    ]
    def exists(path):
        return path == r'C:\ok\ok.exe'

    issues = rh.scan_broken_app_paths(entries=entries, exists=exists)
    assert [i['display'] for i in issues] == ['gone.exe']
    assert issues[0]['fix'] == 'delete-key'
    assert issues[0]['key'].endswith(r'App Paths\gone.exe')


def test_scan_orphaned_uninstall_entries_skips_msiexec():
    programs = [
        {'name': 'Gone', 'uninstall_string': r'"C:\gone\unins.exe"',
         'hive': 'HKEY_CURRENT_USER', 'key': r'...\Uninstall', 'subkey': 'Gone'},
        {'name': 'MSI', 'uninstall_string': 'MsiExec.exe /X{GUID}',
         'hive': 'HKEY_CURRENT_USER', 'key': r'...\Uninstall', 'subkey': 'MSI'},
        {'name': 'NoCmd', 'uninstall_string': '',
         'hive': 'HKEY_CURRENT_USER', 'key': r'...\Uninstall', 'subkey': 'NoCmd'},
    ]
    issues = rh.scan_orphaned_uninstall_entries(programs=programs, exists=never, which=no_which)
    assert [i['display'] for i in issues] == ['Gone']
    assert issues[0]['type'] == 'uninstall-entry'


# ---------------------------------------------------------------------------
# .reg formatting
# ---------------------------------------------------------------------------
def test_format_value_reg_escapes_backslashes_and_quotes():
    text = rh.format_value_reg('HKEY_CURRENT_USER', r'Software\X', 'My"App',
                               r'"C:\app\run.exe" -x')
    assert text.startswith('Windows Registry Editor Version 5.00')
    assert r'[HKEY_CURRENT_USER\Software\X]' in text
    assert '"My\\"App"="\\"C:\\\\app\\\\run.exe\\" -x"' in text


def test_format_value_reg_expand_sz_uses_hex2():
    text = rh.format_value_reg('HKEY_CURRENT_USER', r'Software\X', 'Path',
                               '%TEMP%\\x', expand=True)
    assert '=hex(2):' in text
    # utf-16-le of '%' is 25,00
    assert 'hex(2):25,00' in text


# ---------------------------------------------------------------------------
# archive-first repair
# ---------------------------------------------------------------------------
def _fake_fs_fns(tmp_path, fail_delete=False):
    calls = {'exported': [], 'deleted': []}

    def export_value(hive, key, name, out):
        calls['exported'].append(('value', hive, key, name))
        Path(out).write_text('REG VALUE BACKUP', encoding='utf-8')
        return True

    def delete_value(hive, key, name):
        if fail_delete:
            return False
        calls['deleted'].append(('value', hive, key, name))
        return True

    def export_key(full_key, out):
        calls['exported'].append(('key', full_key))
        Path(out).write_text('REG KEY BACKUP', encoding='utf-8')
        return True

    def delete_key(full_key):
        if fail_delete:
            return False
        calls['deleted'].append(('key', full_key))
        return True

    return calls, export_value, delete_value, export_key, delete_key


def test_archive_registry_issues_value_and_key(tmp_path):
    calls, ev, dv, ek, dk = _fake_fs_fns(tmp_path)
    issues = [
        {'type': 'startup-ref', 'fix': 'delete-value', 'hive': 'HKEY_CURRENT_USER',
         'key': r'Software\Run', 'value_name': 'Dead', 'display': 'Dead', 'detail': 'd'},
        {'type': 'app-path', 'fix': 'delete-key', 'hive': 'HKEY_LOCAL_MACHINE',
         'key': r'SOFTWARE\App Paths\gone.exe', 'value_name': None,
         'display': 'gone.exe', 'detail': 'd'},
    ]
    log_file = tmp_path / 'log.json'
    entries = rh.archive_registry_issues(issues, tmp_path / 'arc', log_file,
                                         export_key_fn=ek, delete_key_fn=dk,
                                         export_value_fn=ev, delete_value_fn=dv)
    assert len(entries) == 2
    assert all(e['reason'] == 'broken-registry' for e in entries)
    assert all(Path(e['dest']).exists() for e in entries)
    assert entries[0]['src'].startswith(rh.REG_PREFIX)
    assert ':: Dead' in entries[0]['src']
    assert entries[1]['src'] == rh.REG_PREFIX + r'HKEY_LOCAL_MACHINE\SOFTWARE\App Paths\gone.exe'
    logged = json.loads(log_file.read_text(encoding='utf-8'))
    assert len(logged) == 2
    assert ('value', 'HKEY_CURRENT_USER', r'Software\Run', 'Dead') in calls['deleted']


def test_archive_registry_issues_failed_delete_consumes_backup(tmp_path):
    _, ev, dv, ek, dk = _fake_fs_fns(tmp_path, fail_delete=True)
    issues = [{'type': 'startup-ref', 'fix': 'delete-value', 'hive': 'HKEY_CURRENT_USER',
               'key': r'Software\Run', 'value_name': 'Dead', 'display': 'Dead', 'detail': 'd'}]
    log_file = tmp_path / 'log.json'
    entries = rh.archive_registry_issues(issues, tmp_path / 'arc', log_file,
                                         export_key_fn=ek, delete_key_fn=dk,
                                         export_value_fn=ev, delete_value_fn=dv)
    assert entries == []
    assert not log_file.exists()
    # no stray .reg backups left behind for the failed item
    assert not list((tmp_path / 'arc' / 'registry_health').glob('*.reg'))
