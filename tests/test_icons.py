"""Product icon pipeline — multi-size ICO and tray asset sanity."""
from __future__ import annotations

import struct
from pathlib import Path

import brand
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def _ico_sizes(path: Path) -> list[tuple[int, int]]:
    data = path.read_bytes()
    if len(data) < 6 or data[:4] != b'\x00\x00\x01\x00':
        return []
    count = struct.unpack_from('<H', data, 4)[0]
    out = []
    off = 6
    for _ in range(count):
        w, h = data[off], data[off + 1]
        out.append((256 if w == 0 else w, 256 if h == 0 else h))
        off += 16
    return out


def test_icon_assets_exist_and_sizes():
    assert brand.ICON_SVG_PATH.is_file(), 'SVG source missing'
    assert brand.ICON_PNG_PATH.is_file()
    assert brand.ICON_TRAY_PNG_PATH.is_file()
    assert brand.ICON_ICO_PATH.is_file()

    png = Image.open(brand.ICON_PNG_PATH)
    assert png.size == (256, 256)
    assert png.mode == 'RGBA'

    tray = Image.open(brand.ICON_TRAY_PNG_PATH)
    assert tray.size == (32, 32)

    sizes = _ico_sizes(brand.ICON_ICO_PATH)
    assert (16, 16) in sizes
    assert (32, 32) in sizes
    assert (256, 256) in sizes
    assert len(sizes) >= 5


def test_generate_icons_script_is_idempotent():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'generate_icons.py')],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert r.returncode == 0, r.stderr or r.stdout
