"""Windows notification-area tray for Cleanroom — optional, failure-safe."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import brand


def _resource_path(name):
    here = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    candidate = here / name
    if candidate.exists():
        return candidate
    return Path(getattr(sys, '_MEIPASS', str(Path(__file__).resolve().parent.parent))) / name


def _load_tray_image():
    from PIL import Image

    for rel in (
        'assets/brand/cleanroom-icon.png',
        'cleanroom-icon.png',
    ):
        path = _resource_path(rel)
        if not path.is_file():
            path = brand.ICON_PNG_PATH if rel.endswith('.png') else brand.ICON_ICO_PATH
        if path.is_file():
            img = Image.open(path)
            return img.convert('RGBA') if img.mode != 'RGBA' else img
    return Image.new('RGBA', (64, 64), (59, 130, 246, 255))


class TrayController:
    """System tray icon with explicit Open/Hide/Show/Receipt/Proof Pack/Quit."""

    MENU_LABELS = (
        'Open Cleanroom',
        'Hide to tray',
        'Show',
        'Latest Receipt',
        'Proof Pack',
        'Quit',
    )

    def __init__(self, app):
        self._app = app
        self._icon = None
        self._thread = None

    def start(self):
        try:
            import pystray
        except ImportError:
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._thread = threading.Thread(target=self._run, name='cleanroom-tray', daemon=True)
        self._thread.start()
        return True

    def stop(self):
        icon = self._icon
        if icon is None:
            return
        try:
            icon.stop()
        except Exception:
            pass

    def _run(self):
        try:
            import pystray
            from pystray import Menu, MenuItem as item

            image = _load_tray_image()
            menu = Menu(
                item('Open Cleanroom', self._on_open),
                item('Hide to tray', self._on_hide),
                item('Show', self._on_show),
                item('Latest Receipt', self._on_latest_receipt),
                item('Proof Pack', self._on_proof_pack),
                Menu.SEPARATOR,
                item('Quit', self._on_quit),
            )
            self._icon = pystray.Icon('Cleanroom', image, brand.APP_DISPLAY, menu)
            self._icon.run()
        except Exception:
            self._icon = None

    def _schedule(self, fn):
        try:
            self._app.after(0, fn)
        except Exception:
            pass

    def _on_open(self, icon, item):
        self._schedule(self._app._tray_show_window)

    def _on_hide(self, icon, item):
        self._schedule(self._app._tray_hide_window)

    def _on_show(self, icon, item):
        self._schedule(self._app._tray_show_window)

    def _on_latest_receipt(self, icon, item):
        self._schedule(self._app.open_last_receipt)

    def _on_proof_pack(self, icon, item):
        self._schedule(self._app.export_audit)

    def _on_quit(self, icon, item):
        self._schedule(self._app._tray_quit)
