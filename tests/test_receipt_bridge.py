"""Unit tests for receipt_bridge — RECEIPT availability + out-of-process launch.

Pure logic, no tk. subprocess.Popen is always monkeypatched; no real process
is started and no GUI is opened.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import receipt_bridge

# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    def test_true_when_standalone_exe_present(self, monkeypatch, tmp_path):
        exe = tmp_path / 'RECEIPT.exe'
        exe.write_text('stub', encoding='utf-8')
        monkeypatch.setattr(receipt_bridge, '_standalone_exe', lambda: exe)
        # Even if frozen with no module, the exe wins.
        monkeypatch.setattr(receipt_bridge, '_frozen', lambda: True)
        monkeypatch.setattr(receipt_bridge, '_module_available', lambda: False)
        assert receipt_bridge.is_available() is True

    def test_true_in_dev_when_module_importable(self, monkeypatch):
        monkeypatch.setattr(receipt_bridge, '_standalone_exe', lambda: None)
        monkeypatch.setattr(receipt_bridge, '_frozen', lambda: False)
        monkeypatch.setattr(receipt_bridge, '_module_available', lambda: True)
        assert receipt_bridge.is_available() is True

    def test_false_when_frozen_without_sibling_exe(self, monkeypatch):
        # Frozen build, no exe beside it: module-import path must NOT count.
        monkeypatch.setattr(receipt_bridge, '_standalone_exe', lambda: None)
        monkeypatch.setattr(receipt_bridge, '_frozen', lambda: True)
        monkeypatch.setattr(receipt_bridge, '_module_available', lambda: True)
        assert receipt_bridge.is_available() is False

    def test_false_when_nothing_available(self, monkeypatch):
        monkeypatch.setattr(receipt_bridge, '_standalone_exe', lambda: None)
        monkeypatch.setattr(receipt_bridge, '_frozen', lambda: False)
        monkeypatch.setattr(receipt_bridge, '_module_available', lambda: False)
        assert receipt_bridge.is_available() is False

    def test_module_importable_in_this_repo(self):
        # Sanity: in the source tree, receipt_desktop.app really is importable.
        assert receipt_bridge._module_available() is True


# ---------------------------------------------------------------------------
# open_receipt
# ---------------------------------------------------------------------------


def _capture_popen(monkeypatch):
    """Replace subprocess.Popen with a capturing stub; return the captured dict."""
    captured = {}

    def fake_popen(cmd, cwd=None, close_fds=None, **kw):
        captured['cmd'] = cmd
        captured['cwd'] = cwd
        captured['close_fds'] = close_fds
        return object()

    monkeypatch.setattr(receipt_bridge.subprocess, 'Popen', fake_popen)
    return captured


class TestOpenReceipt:
    def test_missing_file_returns_error(self, tmp_path):
        ok, err = receipt_bridge.open_receipt(str(tmp_path / 'nope.cleanroom-receipt'))
        assert ok is False
        assert 'not found' in err.lower()

    def test_unavailable_returns_error(self, monkeypatch, tmp_path):
        f = tmp_path / 'receipt.cleanroom-receipt'
        f.write_text('body', encoding='utf-8')
        monkeypatch.setattr(receipt_bridge, '_launch_plan', lambda p: None)
        ok, err = receipt_bridge.open_receipt(str(f))
        assert ok is False
        assert 'not available' in err.lower()

    def test_launch_via_standalone_exe(self, monkeypatch, tmp_path):
        f = tmp_path / 'receipt.cleanroom-receipt'
        f.write_text('body', encoding='utf-8')
        exe = tmp_path / 'RECEIPT.exe'
        exe.write_text('stub', encoding='utf-8')
        monkeypatch.setattr(receipt_bridge, '_standalone_exe', lambda: exe)
        captured = _capture_popen(monkeypatch)

        ok, err = receipt_bridge.open_receipt(str(f))
        assert ok is True
        assert err == ''
        assert captured['cmd'] == [str(exe), '--open', str(f)]
        assert captured['cwd'] == str(exe.parent)

    def test_launch_via_module_in_dev(self, monkeypatch, tmp_path):
        f = tmp_path / 'receipt.cleanroom-receipt'
        f.write_text('body', encoding='utf-8')
        monkeypatch.setattr(receipt_bridge, '_standalone_exe', lambda: None)
        monkeypatch.setattr(receipt_bridge, '_frozen', lambda: False)
        monkeypatch.setattr(receipt_bridge, '_module_available', lambda: True)
        captured = _capture_popen(monkeypatch)

        ok, err = receipt_bridge.open_receipt(str(f))
        assert ok is True
        assert captured['cmd'] == [
            sys.executable, '-m', 'receipt_desktop.app', '--open', str(f)]
        # cwd must be the repo root so `-m receipt_desktop.app` resolves.
        assert captured['cwd'] == str(Path(receipt_bridge.__file__).resolve().parent)

    def test_popen_failure_is_caught(self, monkeypatch, tmp_path):
        f = tmp_path / 'receipt.cleanroom-receipt'
        f.write_text('body', encoding='utf-8')
        exe = tmp_path / 'RECEIPT.exe'
        exe.write_text('stub', encoding='utf-8')
        monkeypatch.setattr(receipt_bridge, '_standalone_exe', lambda: exe)

        def boom(*a, **k):
            raise OSError('launch denied')

        monkeypatch.setattr(receipt_bridge.subprocess, 'Popen', boom)
        ok, err = receipt_bridge.open_receipt(str(f))
        assert ok is False
        assert 'could not start receipt' in err.lower()
