"""Tests for the reversible startup-disable backup store."""
# ruff: noqa: E402
import sys
from pathlib import Path

import pytest

tests_dir = Path(__file__).resolve().parent
project_dir = tests_dir.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import startup_manager_admin as adm

HIVE = 'HKEY_CURRENT_USER'
KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(adm, 'DISABLED_STORE', tmp_path / 'disabled_startup.json')


def test_backup_and_list():
    assert adm.list_disabled() == []
    adm.backup_disabled_entry('MyApp', 'C:\\app.exe', HIVE, KEY)
    entries = adm.list_disabled()
    assert len(entries) == 1
    e = entries[0]
    assert e['name'] == 'MyApp'
    assert e['command'] == 'C:\\app.exe'
    assert e['hive'] == HIVE
    assert e['key'] == KEY
    assert e['disabled_at']


def test_backup_replaces_same_name_and_hive():
    adm.backup_disabled_entry('MyApp', 'C:\\old.exe', HIVE, KEY)
    adm.backup_disabled_entry('MyApp', 'C:\\new.exe', HIVE, KEY)
    entries = adm.list_disabled()
    assert len(entries) == 1
    assert entries[0]['command'] == 'C:\\new.exe'


def test_remove_disabled():
    adm.backup_disabled_entry('A', 'C:\\a.exe', HIVE, KEY)
    adm.backup_disabled_entry('B', 'C:\\b.exe', HIVE, KEY)
    assert adm.remove_disabled('A') == 1
    assert [e['name'] for e in adm.list_disabled()] == ['B']
    assert adm.remove_disabled('A') == 0


def test_restore_disabled_success(monkeypatch):
    adm.backup_disabled_entry('MyApp', 'C:\\app.exe', HIVE, KEY)
    calls = []

    def fake_enable(name, command, hive_name='HKEY_CURRENT_USER'):
        calls.append((name, command, hive_name))
        return True, 'ok'

    monkeypatch.setattr(adm, 'enable_registry_run', fake_enable)
    ok, msg = adm.restore_disabled('MyApp')
    assert ok
    assert calls == [('MyApp', 'C:\\app.exe', HIVE)]
    assert adm.list_disabled() == []  # backup consumed


def test_restore_disabled_keeps_backup_on_failure(monkeypatch):
    adm.backup_disabled_entry('MyApp', 'C:\\app.exe', HIVE, KEY)
    monkeypatch.setattr(adm, 'enable_registry_run', lambda *a, **k: (False, 'denied'))
    ok, msg = adm.restore_disabled('MyApp')
    assert not ok
    assert len(adm.list_disabled()) == 1  # still restorable later


def test_restore_disabled_without_backup():
    ok, msg = adm.restore_disabled('Ghost')
    assert not ok
    assert 'No backup' in msg
