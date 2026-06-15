"""Window geometry defaults for responsive layout."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ui import window_geometry


def test_default_and_minimum_window_sizes():
    assert window_geometry.DEFAULT_SIZE == (1150, 720)
    assert window_geometry.MAX_SIZE == (1280, 820)
    assert window_geometry.MIN_SIZE[0] >= 920
    assert window_geometry.MIN_SIZE[1] >= 580


def test_saved_geometry_clamps_tall_aspect():
    class _W:
        def update_idletasks(self):
            return None

        def winfo_screenwidth(self):
            return 1920

        def winfo_screenheight(self):
            return 1080

        def winfo_fpixels(self, _unit):
            return 96.0

    w, h, *_ = window_geometry.compute_geometry(_W(), {'window_geometry': {'w': 900, 'h': 900}})
    assert h <= int(w * window_geometry.MAX_HEIGHT_RATIO) + 1
    assert h < 900


def test_saved_geometry_clamps_excess_width():
    class _W:
        def update_idletasks(self):
            return None

        def winfo_screenwidth(self):
            return 2560

        def winfo_screenheight(self):
            return 1440

        def winfo_fpixels(self, _unit):
            return 96.0

    w, h, *_ = window_geometry.compute_geometry(_W(), {'window_geometry': {'w': 2200, 'h': 700}})
    assert w <= 2560 - window_geometry.MARGIN
    assert w < 2200
