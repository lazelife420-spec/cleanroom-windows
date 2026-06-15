"""Apply Cleanroom window/taskbar icon — overrides CustomTkinter default on Windows."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import brand

logger = logging.getLogger(__name__)

_APP_USER_MODEL_ID = 'Cleanroom.ArchiveFirst.1'


def _resource_path(name: str) -> Path:
    if getattr(sys, 'frozen', False):
        here = Path(sys.executable).parent
    else:
        here = Path(__file__).resolve().parent.parent
    candidate = here / name
    if candidate.exists():
        return candidate
    return Path(getattr(sys, '_MEIPASS', str(here))) / name


def _resolve_ico_path() -> Path | None:
    for name in ('cleanroom-icon.ico', 'icon.ico'):
        candidate = _resource_path(name)
        if candidate.is_file():
            return candidate
    if brand.ICON_ICO_PATH.is_file():
        return brand.ICON_ICO_PATH
    return None


def _set_app_user_model_id() -> None:
    if not sys.platform.startswith('win'):
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_USER_MODEL_ID)
    except Exception:
        logger.debug('AppUserModelID not set', exc_info=True)


def apply_window_icon(window) -> bool:
    """Set titlebar + taskbar icon; keep CTk from restoring its default cube."""
    _set_app_user_model_id()
    ico = _resolve_ico_path()
    applied = False
    if ico is not None:
        try:
            window.iconbitmap(default=str(ico))
            applied = True
        except Exception:
            logger.debug('iconbitmap failed for %s', ico, exc_info=True)

    try:
        from PIL import Image, ImageTk
        png = brand.ICON_PNG_PATH if brand.ICON_PNG_PATH.is_file() else None
        if png is None:
            for name in ('cleanroom-icon.png', 'icon.png'):
                candidate = _resource_path(name)
                if candidate.is_file():
                    png = candidate
                    break
        if png is not None:
            with Image.open(png) as img:
                img = img.convert('RGBA')
                img.thumbnail((64, 64), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img, master=window)
            window.iconphoto(True, photo)
            window._cleanroom_icon_photo = photo  # prevent GC
            applied = True
    except Exception:
        logger.debug('iconphoto fallback failed', exc_info=True)

    try:
        window._iconbitmap_method_called = True
    except Exception:
        pass
    return applied


def schedule_window_icon(window, *, delays=(250, 800)) -> None:
    """Re-apply after CTk titlebar/icon hooks so the product icon sticks."""
    for ms in delays:
        try:
            window.after(ms, lambda w=window: apply_window_icon(w))
        except Exception:
            pass
