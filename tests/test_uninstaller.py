"""Tests for the uninstaller module (parsing, matching, leftover archiving)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uninstaller


# ---------------------------------------------------------------------------
# normalize_entry
# ---------------------------------------------------------------------------
def test_normalize_basic_entry():
    raw = {
        'DisplayName': 'Foo Player',
        'DisplayVersion': '3.1.4',
        'Publisher': 'MegaCorp',
        'InstallDate': '20240115',
        'EstimatedSize': 2048,
        'UninstallString': r'"C:\Program Files\FooPlayer\unins000.exe"',
    }
    e = uninstaller.normalize_entry(raw, 'HKEY_LOCAL_MACHINE', 'SOFTWARE\\...', 'FooPlayer')
    assert e['name'] == 'Foo Player'
    assert e['version'] == '3.1.4'
    assert e['publisher'] == 'MegaCorp'
    assert e['install_date'] == '2024-01-15'
    assert e['size_kb'] == 2048
    assert 'unins000.exe' in e['uninstall_string']


def test_normalize_skips_nameless_and_system_components():
    assert uninstaller.normalize_entry({'UninstallString': 'x'}) is None
    assert uninstaller.normalize_entry(
        {'DisplayName': 'Thing', 'SystemComponent': 1, 'UninstallString': 'x'}) is None
    assert uninstaller.normalize_entry(
        {'DisplayName': 'KB12345', 'ParentKeyName': 'Office', 'UninstallString': 'x'}) is None
    assert uninstaller.normalize_entry(
        {'DisplayName': 'Patch', 'ReleaseType': 'Security Update', 'UninstallString': 'x'}) is None


def test_normalize_skips_entries_without_uninstall_string():
    assert uninstaller.normalize_entry({'DisplayName': 'Ghost App'}) is None


def test_normalize_tolerates_bad_date_and_size():
    raw = {'DisplayName': 'Odd', 'UninstallString': 'x',
           'InstallDate': 'not-a-date', 'EstimatedSize': 'huge'}
    e = uninstaller.normalize_entry(raw)
    assert e['install_date'] == ''
    assert e['size_kb'] == 0


# ---------------------------------------------------------------------------
# build_uninstall_command
# ---------------------------------------------------------------------------
def test_build_command_prefers_quiet_string_when_quiet():
    entry = {'uninstall_string': 'unins.exe', 'quiet_uninstall_string': 'unins.exe /SILENT'}
    assert uninstaller.build_uninstall_command(entry, quiet=True) == 'unins.exe /SILENT'
    assert uninstaller.build_uninstall_command(entry, quiet=False) == 'unins.exe'


def test_build_command_msiexec_quiet_converts_to_silent_remove():
    entry = {'uninstall_string': 'MsiExec.exe /I{GUID-123}', 'quiet_uninstall_string': ''}
    cmd = uninstaller.build_uninstall_command(entry, quiet=True)
    assert '/X' in cmd
    assert '/qn' in cmd


def test_build_command_empty_entry():
    assert uninstaller.build_uninstall_command({}, quiet=True) == ''


# ---------------------------------------------------------------------------
# leftover matching
# ---------------------------------------------------------------------------
def test_name_tokens_strips_noise():
    tokens = uninstaller.name_tokens('MegaCorp FooPlayer 3.1 (x64 Edition)')
    assert 'fooplayer' in tokens
    assert 'x64' not in tokens
    assert '3' not in tokens


def test_match_leftover_dirs_uses_longest_token():
    candidates = ['FooPlayer', 'fooplayer-cache', 'BarTool', 'Mega']
    matched = uninstaller.match_leftover_dirs('MegaCorp FooPlayer 3.1', candidates)
    assert 'FooPlayer' in matched
    assert 'fooplayer-cache' in matched
    assert 'BarTool' not in matched


def test_match_leftover_dirs_no_tokens():
    assert uninstaller.match_leftover_dirs('7+ 1.0', ['anything']) == []


def test_find_leftovers_scans_roots(tmp_path):
    root = tmp_path / 'Program Files'
    (root / 'FooPlayer').mkdir(parents=True)
    (root / 'Other').mkdir()
    found = uninstaller.find_leftovers('FooPlayer 2.0', roots=[root])
    assert [Path(p).name for p in found] == ['FooPlayer']


# ---------------------------------------------------------------------------
# archive_leftovers (archive-first, restorable)
# ---------------------------------------------------------------------------
def test_archive_leftovers_moves_and_logs(tmp_path):
    src = tmp_path / 'apps' / 'FooPlayer'
    src.mkdir(parents=True)
    (src / 'data.txt').write_text('hello')
    archive = tmp_path / 'archive'
    log = tmp_path / 'cleanup_log.json'

    moved = uninstaller.archive_leftovers([str(src)], archive, str(log))

    assert len(moved) == 1
    assert not src.exists()
    dest = Path(moved[0]['dest'])
    assert dest.exists()
    assert (dest / 'data.txt').read_text() == 'hello'

    entries = json.loads(log.read_text())
    assert entries[0]['src'] == str(src)
    assert entries[0]['reason'] == 'uninstall-leftover'
    assert entries[0]['size'] == 5


def test_archive_leftovers_appends_to_existing_log(tmp_path):
    log = tmp_path / 'cleanup_log.json'
    log.write_text(json.dumps([{'src': 'old', 'dest': 'olddest'}]))
    src = tmp_path / 'LeftoverDir'
    src.mkdir()
    uninstaller.archive_leftovers([str(src)], tmp_path / 'arch', str(log))
    entries = json.loads(log.read_text())
    assert len(entries) == 2
    assert entries[0]['src'] == 'old'


def test_archive_leftovers_skips_missing_paths(tmp_path):
    log = tmp_path / 'log.json'
    moved = uninstaller.archive_leftovers([str(tmp_path / 'nope')], tmp_path / 'arch', str(log))
    assert moved == []
    assert not log.exists()


def test_archive_leftovers_collision_gets_unique_name(tmp_path):
    archive = tmp_path / 'arch'
    (archive / 'uninstall_leftovers' / 'Dup').mkdir(parents=True)
    src = tmp_path / 'Dup'
    src.mkdir()
    moved = uninstaller.archive_leftovers([str(src)], archive, str(tmp_path / 'log.json'))
    assert len(moved) == 1
    assert Path(moved[0]['dest']).name != 'Dup'
    assert Path(moved[0]['dest']).name.endswith('Dup')


# ---------------------------------------------------------------------------
# smart filters
# ---------------------------------------------------------------------------
def test_filter_programs_modes():
    from datetime import datetime
    now = datetime(2026, 6, 10)
    entries = [
        {'name': 'Big', 'size_kb': 2 * 1024 * 1024, 'install_date': '2024-01-01'},
        {'name': 'Fresh', 'size_kb': 100, 'install_date': '2026-06-01'},
        {'name': 'Ancient', 'size_kb': 100, 'install_date': '2020-05-01'},
        {'name': 'NoDate', 'size_kb': 100, 'install_date': ''},
    ]
    assert len(uninstaller.filter_programs(entries, 'all', now=now)) == 4
    assert [e['name'] for e in uninstaller.filter_programs(entries, 'large', now=now)] == ['Big']
    assert [e['name'] for e in uninstaller.filter_programs(entries, 'recent', now=now)] == ['Fresh']
    assert [e['name'] for e in uninstaller.filter_programs(entries, 'old', now=now)] == ['Big', 'Ancient']
    # unknown mode behaves like 'all'
    assert len(uninstaller.filter_programs(entries, 'bogus', now=now)) == 4


# ---------------------------------------------------------------------------
# registry leftovers
# ---------------------------------------------------------------------------
def test_match_registry_keys_filters_protected_umbrella_keys():
    candidates = ['FooPlayer', 'Microsoft', 'Google', 'fooplayer-sync']
    matched = uninstaller.match_registry_keys('FooPlayer 2.0', candidates)
    assert matched == ['FooPlayer', 'fooplayer-sync']
    # a program literally named e.g. "Google Updater" must not match the
    # umbrella 'Google' vendor key
    assert uninstaller.match_registry_keys('Google Updater', ['Google']) == []


def test_archive_registry_leftovers_exports_deletes_and_logs(tmp_path):
    log = tmp_path / 'log.json'
    deleted = []

    def fake_export(full_key, out_file):
        Path(out_file).write_text('Windows Registry Editor Version 5.00\n')
        return True

    def fake_delete(full_key):
        deleted.append(full_key)
        return True

    key = r'HKEY_CURRENT_USER\SOFTWARE\FooPlayer'
    entries = uninstaller.archive_registry_leftovers(
        [key], tmp_path / 'arch', str(log),
        export_fn=fake_export, delete_fn=fake_delete)

    assert deleted == [key]
    assert len(entries) == 1
    assert entries[0]['src'] == uninstaller.REG_PREFIX + key
    assert entries[0]['reason'] == 'registry-leftover'
    assert Path(entries[0]['dest']).exists()
    assert Path(entries[0]['dest']).suffix == '.reg'

    logged = json.loads(log.read_text())
    assert logged[0]['src'].startswith(uninstaller.REG_PREFIX)


def test_archive_registry_leftovers_skips_failed_export_and_delete(tmp_path):
    log = tmp_path / 'log.json'

    # export fails -> nothing logged
    entries = uninstaller.archive_registry_leftovers(
        ['HKCU\\SOFTWARE\\X'], tmp_path / 'arch', str(log),
        export_fn=lambda k, o: False, delete_fn=lambda k: True)
    assert entries == []

    # delete fails -> exported file is removed again, nothing logged
    def fake_export(full_key, out_file):
        Path(out_file).write_text('x')
        return True

    entries = uninstaller.archive_registry_leftovers(
        ['HKCU\\SOFTWARE\\Y'], tmp_path / 'arch', str(log),
        export_fn=fake_export, delete_fn=lambda k: False)
    assert entries == []
    assert not list((tmp_path / 'arch' / 'uninstall_leftovers' / 'registry').glob('*.reg'))
    assert not log.exists()


def test_remove_uninstall_entry_archives_the_orphan_key(tmp_path):
    log = tmp_path / 'log.json'
    deleted = []

    def fake_export(full_key, out_file):
        Path(out_file).write_text('Windows Registry Editor Version 5.00\n')
        return True

    entry = {'name': 'Broken App', 'hive': 'HKEY_CURRENT_USER',
             'key': r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
             'subkey': 'BrokenApp_is1'}
    result = uninstaller.remove_uninstall_entry(
        entry, tmp_path / 'arch', str(log),
        export_fn=fake_export, delete_fn=lambda k: deleted.append(k) or True)

    expected_key = ('HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Windows'
                    '\\CurrentVersion\\Uninstall\\BrokenApp_is1')
    assert deleted == [expected_key]
    assert result is not None
    assert result['src'] == uninstaller.REG_PREFIX + expected_key
    assert Path(result['dest']).exists()
    logged = json.loads(log.read_text())
    assert len(logged) == 1


def test_remove_uninstall_entry_requires_registry_fields(tmp_path):
    assert uninstaller.remove_uninstall_entry(
        {'name': 'No Key Info', 'hive': '', 'subkey': ''},
        tmp_path, str(tmp_path / 'log.json')) is None


def test_remove_uninstall_entry_failed_export_returns_none(tmp_path):
    entry = {'name': 'X', 'hive': 'HKEY_LOCAL_MACHINE',
             'key': r'SOFTWARE\...\Uninstall', 'subkey': 'X'}
    result = uninstaller.remove_uninstall_entry(
        entry, tmp_path / 'arch', str(tmp_path / 'log.json'),
        export_fn=lambda k, o: False, delete_fn=lambda k: True)
    assert result is None
    assert not (tmp_path / 'log.json').exists()


def test_collect_force_remove_targets_includes_install_location(tmp_path):
    app = tmp_path / 'OldApp'
    app.mkdir()
    entry = {
        'name': 'OldApp Suite',
        'install_location': str(app),
        'hive': 'HKEY_CURRENT_USER',
        'key': r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'subkey': 'OldApp',
    }
    dirs, keys = uninstaller.collect_force_remove_targets(entry)
    assert str(app) in dirs
    assert isinstance(keys, list)


def test_force_remove_archives_and_removes_entry(tmp_path):
    log = tmp_path / 'log.json'
    src = tmp_path / 'leftover'
    src.mkdir()
    (src / 'data.txt').write_text('x', encoding='utf-8')
    deleted = []

    def fake_export(full_key, out_file):
        Path(out_file).write_text('Windows Registry Editor Version 5.00\n')
        return True

    entry = {'name': 'Broken App', 'hive': 'HKEY_CURRENT_USER',
             'key': r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
             'subkey': 'BrokenApp_is1'}
    result = uninstaller.force_remove(
        entry, tmp_path / 'arch', str(log),
        chosen_dirs=[str(src)], chosen_keys=[],
        export_fn=fake_export, delete_fn=lambda k: deleted.append(k) or True)
    assert len(result['folders']) == 1
    assert result['list_entry'] is not None
    assert not src.exists()
    assert deleted


def test_entry_requires_admin_hklm():
    assert uninstaller.entry_requires_admin({'hive': 'HKEY_LOCAL_MACHINE'})
    assert not uninstaller.entry_requires_admin({'hive': 'HKEY_CURRENT_USER'})


def test_restore_registry_export_missing_file(tmp_path):
    ok, msg = uninstaller.restore_registry_export(tmp_path / 'nope.reg')
    assert not ok
    assert 'missing' in msg


def test_find_registry_leftovers_returns_list():
    # Structural: live registry scan must not raise and returns full key paths.
    results = uninstaller.find_registry_leftovers('Zz Improbable Program Qq 9.9')
    assert isinstance(results, list)
    assert results == [] or all('\\SOFTWARE' in r.upper() for r in results)


# ---------------------------------------------------------------------------
# live registry listing (Windows only, structural)
# ---------------------------------------------------------------------------
def test_list_installed_programs_structure():
    programs = uninstaller.list_installed_programs()
    assert isinstance(programs, list)
    for p in programs[:5]:
        assert p['name']
        assert p['uninstall_string'] or p['quiet_uninstall_string']
