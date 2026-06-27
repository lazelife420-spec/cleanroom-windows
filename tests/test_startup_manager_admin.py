import sys
from pathlib import Path


def _import_admin():
    p = Path(__file__).resolve().parent.parent
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    import startup_manager_admin as sma
    return sma


def test_is_admin():
    sma = _import_admin()
    # is_admin should return a bool (True or False, not crash)
    result = sma.is_admin()
    assert isinstance(result, bool)


def test_enable_registry_run_non_admin():
    sma = _import_admin()
    # If not running as admin, should return False
    if not sma.is_admin():
        success, msg = sma.enable_registry_run('TestApp', 'C:\\test.exe')
        assert success is False


def test_disable_registry_run_non_admin():
    sma = _import_admin()
    # If not running as admin, should return False
    if not sma.is_admin():
        success, msg = sma.disable_registry_run('TestApp')
        assert success is False


def test_enable_returns_tuple():
    sma = _import_admin()
    result = sma.enable_registry_run('TestApp', 'C:\\test.exe')
    assert isinstance(result, tuple)
    assert len(result) == 2
    success, msg = result
    assert isinstance(success, bool)
    assert isinstance(msg, str)


def test_disable_returns_tuple():
    sma = _import_admin()
    result = sma.disable_registry_run('TestApp')
    assert isinstance(result, tuple)
    assert len(result) == 2
    success, msg = result
    assert isinstance(success, bool)
    assert isinstance(msg, str)
