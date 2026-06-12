"""CLI --open-receipt entry for shell file association."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_open_receipt_standalone_missing_file():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import startup_manager_gui as gui

    assert gui.open_receipt_standalone(str(ROOT / 'does-not-exist.cleanroom-receipt')) == 1


def test_open_receipt_standalone_rejects_non_receipt_txt(tmp_path):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import startup_manager_gui as gui

    random_txt = tmp_path / 'notes.txt'
    random_txt.write_text('hello', encoding='utf-8')
    assert gui.open_receipt_standalone(str(random_txt)) == 2


def test_open_receipt_standalone_accepts_legacy_receipt_txt(tmp_path):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import startup_manager_gui as gui

    legacy = tmp_path / 'receipt_20260101_120000.txt'
    legacy.write_text('CLEANROOM — RECEIPT\n', encoding='utf-8')
    # Viewer opens a Tk window — skip mainloop in headless CI
    if not gui.show_receipt:
        pytest.skip('receipt viewer unavailable')
    pytest.importorskip('tkinter')
    # Smoke: validate path gate only (return 2 on read failure, not 2 on valid path before UI)
    import receipts
    assert receipts.is_receipt_path(legacy)
