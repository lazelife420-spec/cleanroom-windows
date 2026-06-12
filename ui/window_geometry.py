"""Fit Cleanroom to the current display and remember window placement."""
from __future__ import annotations

import re
from typing import Callable

DEFAULT_SIZE = (1280, 760)
MIN_SIZE = (1000, 600)
MARGIN = 28
TASKBAR_RESERVE = 52

_GEO_RE = re.compile(r'^(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?$')


def animations_disabled() -> bool:
    import os
    v = os.environ.get('CLEANROOM_DISABLE_ANIMATIONS', '').strip().lower()
    return v in ('1', 'true', 'yes', 'on')


def dpi_scale(widget) -> float:
    try:
        widget.update_idletasks()
        return max(1.0, min(widget.winfo_fpixels('1i') / 96.0, 2.0))
    except Exception:
        return 1.0


def _screen_box(widget):
    widget.update_idletasks()
    sw = widget.winfo_screenwidth()
    sh = widget.winfo_screenheight()
    scale = dpi_scale(widget)
    margin = int(MARGIN * scale)
    taskbar = int(TASKBAR_RESERVE * scale)
    return sw, sh - taskbar, margin, scale


def compute_geometry(widget, prefs: dict | None = None):
    """Return (width, height, x, y) sized for this monitor."""
    sw, avail_h, margin, scale = _screen_box(widget)
    pref_w = int(DEFAULT_SIZE[0] * scale)
    pref_h = int(DEFAULT_SIZE[1] * scale)
    min_w, min_h = MIN_SIZE

    saved = (prefs or {}).get('window_geometry') or {}
    if saved.get('w') and saved.get('h'):
        w = int(saved['w'])
        h = int(saved['h'])
        x = int(saved.get('x', (sw - w) // 2))
        y = int(saved.get('y', (avail_h - h) // 2))
        w = max(min_w, min(w, sw - margin))
        h = max(min_h, min(h, avail_h - margin))
        x = max(0, min(x, sw - w))
        y = max(0, min(y, avail_h - h))
        return w, h, x, y, bool(saved.get('maximized'))

    w = max(min_w, min(pref_w, sw - margin))
    h = max(min_h, min(pref_h, avail_h - margin))
    x = max(0, (sw - w) // 2)
    y = max(0, (avail_h - h) // 2)
    return w, h, x, y, False


def apply_window_geometry(widget, prefs: dict | None = None) -> None:
    w, h, x, y, maximized = compute_geometry(widget, prefs)
    widget.minsize(*MIN_SIZE)
    try:
        sw, avail_h, margin, _ = _screen_box(widget)
        widget.maxsize(sw, avail_h)
    except Exception:
        pass
    widget.geometry(f'{w}x{h}+{x}+{y}')
    if maximized:
        try:
            widget.state('zoomed')
        except Exception:
            pass


def parse_geometry_string(geo: str):
    m = _GEO_RE.match(geo or '')
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    x = int(m.group(3)) if m.group(3) is not None else None
    y = int(m.group(4)) if m.group(4) is not None else None
    return w, h, x, y


def bind_window_tracking(widget, *, on_save: Callable[[dict], None]) -> None:
    """Debounced save of size/position; responsive wraplength via callback."""
    state = {'job': None}

    def _emit_save():
        state['job'] = None
        payload = {}
        try:
            if widget.state() == 'zoomed':
                payload['maximized'] = True
                parsed = parse_geometry_string(widget.wm_geometry())
                if parsed:
                    payload['w'], payload['h'] = parsed[0], parsed[1]
            else:
                parsed = parse_geometry_string(widget.geometry())
                if parsed:
                    payload['w'], payload['h'], payload['x'], payload['y'] = parsed
                payload['maximized'] = False
        except Exception:
            return
        if payload:
            on_save(payload)

    def _schedule_save(_event=None):
        if state['job'] is not None:
            try:
                widget.after_cancel(state['job'])
            except Exception:
                pass
        state['job'] = widget.after(450, _emit_save)

    widget.bind('<Configure>', _schedule_save, add='+')
