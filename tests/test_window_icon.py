"""Window icon helper — beat CustomTkinter default taskbar icon."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import brand
from ui.window_icon import apply_window_icon


def test_apply_window_icon_sets_ctk_flag(monkeypatch):
    if sys.platform.startswith('win'):
        monkeypatch.setattr(
            'ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID', lambda _: None)

    window = MagicMock()
    window._iconbitmap_method_called = False
    assert brand.ICON_ICO_PATH.is_file()
    assert apply_window_icon(window) is True
    window.iconbitmap.assert_called()
    assert window._iconbitmap_method_called is True
