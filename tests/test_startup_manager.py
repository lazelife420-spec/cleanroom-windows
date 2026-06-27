import sys
from pathlib import Path


def _import_sm():
    p = Path(__file__).resolve().parent.parent
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    import startup_manager as sm
    return sm


def test_list_folder_entries(tmp_path, monkeypatch):
    sm = _import_sm()
    # create fake startup folder path that matches the code's expected structure
    fake = tmp_path / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
    fake.mkdir(parents=True)
    f = fake / 'dummy.lnk'
    f.write_text('shortcut', encoding='utf-8')
    # monkeypatch environment so _get_startup_folders finds our fake folder
    monkeypatch.setenv('APPDATA', str(tmp_path))
    entries = sm.list_startup_entries()
    # should include the dummy file
    found = any(e.get('name') == 'dummy.lnk' for e in entries['folders'])
    assert found


def test_registry_entries_no_crash():
    sm = _import_sm()
    entries = sm._list_registry_entries()
    # entries may be empty on non-Windows or restricted env, but function should return list
    assert isinstance(entries, list)
