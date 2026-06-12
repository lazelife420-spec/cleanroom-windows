"""Tests for local program guidance heuristics."""
from program_advice import (
    KEEP, OPTIONAL, SAFE_IF_UNUSED, CAUTION, USUALLY_KEEP,
    analyze_program, parse_uninstall_exe, uninstaller_exe_exists,
)


def test_parse_uninstall_exe_quoted():
    assert parse_uninstall_exe(r'"C:\Apps\foo\unins000.exe" /SILENT') == r'C:\Apps\foo\unins000.exe'


def test_parse_uninstall_exe_msiexec_none():
    assert parse_uninstall_exe('MsiExec.exe /X{GUID}') is None


def test_analyze_microsoft_system():
    a = analyze_program({'name': 'Microsoft Edge Update', 'publisher': 'Microsoft Corporation',
                         'uninstall_string': 'msiexec /x {guid}'})
    assert a['category'] == 'system'
    assert a['verdict'] == KEEP


def test_analyze_runtime():
    a = analyze_program({'name': 'Microsoft Visual C++ 2015-2022 Redistributable (x64)',
                         'publisher': 'Microsoft Corporation',
                         'uninstall_string': 'msiexec /x {guid}'})
    assert a['category'] == 'runtime'
    assert a['verdict'] == USUALLY_KEEP


def test_analyze_unknown_app_old_large():
    a = analyze_program({
        'name': 'Old Game Demo',
        'publisher': 'Unknown',
        'size_kb': 2 * 1024 * 1024,
        'install_date': '2020-01-01',
        'uninstall_string': r'"C:\missing\unins.exe"',
    })
    assert a['verdict'] in (SAFE_IF_UNUSED, OPTIONAL)
    assert a['uninstaller_status'] == 'missing'


def test_analyze_security_caution():
    a = analyze_program({'name': 'Norton Security', 'publisher': 'NortonLifeLock',
                         'uninstall_string': 'setup.exe'})
    assert a['category'] == 'security'
    assert a['verdict'] == CAUTION


def test_uninstaller_exe_exists_missing():
    assert not uninstaller_exe_exists({'uninstall_string': r'"Z:\no\such\unins.exe"'})
