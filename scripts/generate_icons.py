#!/usr/bin/env python3
"""Generate Cleanroom product icons from the vector design spec.

Source of truth: assets/brand/cleanroom-icon.svg
Outputs (same paths used by brand.py, tray, titlebar, PyInstaller, Inno Setup):
  - assets/brand/cleanroom-icon.png      (256×256, app/titlebar)
  - assets/brand/cleanroom-icon-tray.png (32×32, notification area)
  - assets/brand/cleanroom-icon.ico      (16–256 multi-size)

Uses Pillow only (no Cairo). Re-run after editing the SVG geometry constants below.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / 'assets' / 'brand'
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

# Palette — matches Cleanroom proof / custody chrome
BG = (15, 20, 25)
BG_EDGE = (36, 48, 68)
SHIELD_TOP = (52, 211, 153)
SHIELD_BOT = (5, 150, 105)
SHIELD_EDGE = (110, 231, 183)
INK = (236, 253, 245)
ACCENT = (52, 211, 153)


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _shield_points(w: int, h: int) -> list[tuple[float, float]]:
    cx, cy = w / 2, h / 2
    s = min(w, h)
    return [
        (cx, cy - s * 0.36),
        (cx + s * 0.30, cy - s * 0.22),
        (cx + s * 0.30, cy + s * 0.08),
        (cx, cy + s * 0.38),
        (cx - s * 0.30, cy + s * 0.08),
        (cx - s * 0.30, cy - s * 0.22),
    ]


def render_icon(size: int) -> Image.Image:
    """Rasterize the custody-shield icon; simplify detail below 48px."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(1, size // 32)
    radius = max(2, size // 5)
    draw.rounded_rectangle(
        (pad, pad, size - pad - 1, size - pad - 1),
        radius=radius, fill=BG, outline=BG_EDGE, width=max(1, size // 42),
    )

    shield = _shield_points(size, size)
    for i, (x, y) in enumerate(shield):
        shield[i] = (x, y)
    # Vertical gradient fill via horizontal strips
    ys = [p[1] for p in shield]
    y_min, y_max = min(ys), max(ys)
    for y in range(int(y_min), int(y_max) + 1):
        t = 0 if y_max == y_min else (y - y_min) / (y_max - y_min)
        color = (
            _lerp(SHIELD_TOP[0], SHIELD_BOT[0], t),
            _lerp(SHIELD_TOP[1], SHIELD_BOT[1], t),
            _lerp(SHIELD_TOP[2], SHIELD_BOT[2], t),
        )
        draw.line([(0, y), (size, y)], fill=color)
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).polygon(shield, fill=255)
    grad = img.copy()
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    img.paste(grad, mask=mask)
    draw = ImageDraw.Draw(img)
    draw.polygon(shield, outline=SHIELD_EDGE, width=max(1, size // 64))

    if size >= 48:
        box_w = max(6, int(size * 0.31))
        box_h = max(5, int(size * 0.23))
        bx = (size - box_w) // 2
        by = int(size * 0.38)
        br = max(1, size // 32)
        draw.rounded_rectangle(
            (bx, by, bx + box_w, by + box_h), radius=br,
            fill=BG, outline=INK, width=max(1, size // 51),
        )
        lid_y = by + max(2, box_h // 4)
        draw.line(
            [(bx, lid_y), (bx + box_w, lid_y)], fill=INK,
            width=max(1, size // 51),
        )
        cr = max(2, size // 12)
        ccx, ccy = bx + box_w - cr // 3, by + box_h + cr // 2
        draw.ellipse(
            (ccx - cr, ccy - cr, ccx + cr, ccy + cr),
            fill=BG, outline=INK, width=max(1, size // 64),
        )
        tick = max(2, size // 18)
        draw.line(
            [(ccx - tick, ccy), (ccx - tick // 3, ccy + tick // 2), (ccx + tick, ccy - tick // 2)],
            fill=ACCENT, width=max(1, size // 42), joint='curve',
        )
    elif size >= 24:
        # Archive lid bar only
        bar_w = max(4, int(size * 0.42))
        bar_h = max(1, size // 16)
        bx = (size - bar_w) // 2
        by = int(size * 0.46)
        draw.rounded_rectangle(
            (bx, by, bx + bar_w, by + bar_h * 3), radius=1, fill=INK,
        )
    else:
        # 16px: bold center dot = custody mark
        r = max(1, size // 10)
        draw.ellipse(
            (size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r), fill=INK,
        )

    return img


def write_ico(path: Path, frames: list[Image.Image]) -> None:
    """Write multi-size ICO with PNG-compressed entries (Windows Vista+)."""
    from io import BytesIO

    png_chunks: list[bytes] = []
    for im in frames:
        bio = BytesIO()
        im.save(bio, format='PNG', optimize=True)
        png_chunks.append(bio.getvalue())

    count = len(png_chunks)
    header = struct.pack('<HHH', 0, 1, count)
    entries = bytearray()
    image_data = bytearray()
    offset = 6 + 16 * count
    for im, png in zip(frames, png_chunks):
        w, h = im.size
        bw = 0 if w >= 256 else w
        bh = 0 if h >= 256 else h
        entries.extend(struct.pack('<BBBBHHII', bw, bh, 0, 0, 1, 32, len(png), offset))
        offset += len(png)
        image_data.extend(png)
    path.write_bytes(header + bytes(entries) + bytes(image_data))


def verify_ico(path: Path) -> list[tuple[int, int]]:
    """Return embedded ICO dimensions for sanity checks."""
    data = path.read_bytes()
    if data[:4] != b'\x00\x00\x01\x00':
        return []
    count = struct.unpack_from('<H', data, 4)[0]
    out = []
    off = 6
    for _ in range(count):
        w, h = data[off], data[off + 1]
        out.append((256 if w == 0 else w, 256 if h == 0 else h))
        off += 16
    return out


def main() -> int:
    BRAND.mkdir(parents=True, exist_ok=True)
    frames = [render_icon(s) for s in ICO_SIZES]
    png_path = BRAND / 'cleanroom-icon.png'
    tray_path = BRAND / 'cleanroom-icon-tray.png'
    ico_path = BRAND / 'cleanroom-icon.ico'

    frames[-1].save(png_path, format='PNG', optimize=True)
    render_icon(32).save(tray_path, format='PNG', optimize=True)
    write_ico(ico_path, frames)

    embedded = verify_ico(ico_path)
    print(f'Wrote {png_path} ({png_path.stat().st_size} bytes)')
    print(f'Wrote {tray_path} ({tray_path.stat().st_size} bytes)')
    print(f'Wrote {ico_path} ({ico_path.stat().st_size} bytes) sizes={embedded}')
    if len(embedded) < 5:
        print('FAIL: ICO should contain multiple sizes', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
