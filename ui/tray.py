"""Windows notification-area tray for Cleanroom — optional, failure-safe."""
from __future__ import annotations

import atexit
import logging
import os
import sys
import threading
import time
from pathlib import Path

import brand

logger = logging.getLogger(__name__)

_active_tray: 'TrayController | None' = None
_keepalive: list = []
_start_lock = threading.Lock()
_TRAY_ICON_NAME = 'Cleanroom'


def get_active_tray() -> 'TrayController | None':
    return _active_tray


def shutdown_all_trays() -> None:
    """Stop any live tray controller — used by app/test teardown."""
    global _active_tray
    tray = _active_tray
    if tray is not None:
        try:
            tray.stop()
        except Exception:
            logger.exception('shutdown_all_trays failed')
    _active_tray = None


atexit.register(shutdown_all_trays)


def _resource_path(name):
    here = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    candidate = here / name
    if candidate.exists():
        return candidate
    return Path(getattr(sys, '_MEIPASS', str(Path(__file__).resolve().parent.parent))) / name


def _tray_target_size() -> int:
    if sys.platform.startswith('win'):
        try:
            import ctypes
            dpi = int(ctypes.windll.user32.GetDpiForSystem())
            return 32 if dpi >= 120 else 16
        except Exception:
            pass
    return 32


def _flatten_tray_image(img):
    """Windows notification area renders transparent margins as a white box."""
    from PIL import Image

    bg = (15, 20, 25, 255)
    flat = Image.new('RGBA', img.size, bg)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return Image.alpha_composite(flat, img)


def _load_tray_image():
    """Return (PIL image copy, asset path or '', used_fallback)."""
    from PIL import Image

    target = _tray_target_size()
    candidates = (
        brand.ICON_TRAY_PNG_PATH,
        brand.ICON_PNG_PATH,
        brand.ICON_ICO_PATH,
        _resource_path('assets/brand/cleanroom-icon-tray.png'),
        _resource_path('assets/brand/cleanroom-icon.png'),
        _resource_path('cleanroom-icon-tray.png'),
        _resource_path('cleanroom-icon.png'),
        _resource_path('cleanroom-icon.ico'),
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            with Image.open(path) as img:
                img = img.convert('RGBA') if img.mode != 'RGBA' else img
                if max(img.size) != target or min(img.size) != target:
                    img = img.resize((target, target), Image.LANCZOS)
                img = _flatten_tray_image(img)
                return img.copy(), str(path), False
        except Exception as exc:
            logger.debug('Tray icon load failed for %s: %s', path, exc)
            continue
    fallback = Image.new('RGBA', (target, target), (34, 197, 94, 255))
    return fallback, '', True


def _ensure_icon_running_attr(icon) -> None:
    if icon is not None and not hasattr(icon, '_running'):
        icon._running = False


def _patch_pystray_icon_lifecycle() -> None:
    try:
        import pystray
        from pystray import _win32
    except Exception:
        return

    targets = []
    for cls in (getattr(pystray, 'Icon', None), getattr(_win32, 'Icon', None)):
        if cls is not None and cls not in targets:
            targets.append(cls)

    for cls in targets:
        if getattr(cls, '_cleanroom_lifecycle_patched', False):
            continue
        orig_init = cls.__init__
        orig_del = cls.__del__

        def _init(self, *args, _orig=orig_init, **kwargs):
            _orig(self, *args, **kwargs)
            _ensure_icon_running_attr(self)

        def _del(self, _orig=orig_del):
            _ensure_icon_running_attr(self)
            try:
                _orig(self)
            except Exception:
                pass

        cls.__init__ = _init
        cls.__del__ = _del
        cls._cleanroom_lifecycle_patched = True


_patch_pystray_icon_lifecycle()


class TrayController:
    """System tray with product menu hierarchy and live proof-status tooltip."""

    MENU_LABELS = (
        'Open Cleanroom',
        'Run Scan',
        'Stop Scan',
        'Preview Latest Receipt',
        'Open Latest Receipt',
        'Open Proof Pack',
        'Open Archive Folder',
        'Tools',
        'Explorer Context Menus',
        'Registry Snapshot',
        'Cleanroom Rewind',
        'Custody Check',
        'Window',
        'Hide to tray',
        'Show',
        'Restore',
        'Quit Cleanroom',
    )

    def __init__(self, app):
        self._app = app
        self._icon = None
        self._tray_image = None
        self._tray_menu = None
        self._tray_thread = None
        self._monitor_thread = None
        self._ready = threading.Event()
        self._stopping = False
        self._started = False
        self.last_error = ''
        self.diagnostics: dict = {}
        self._icon_asset_path = ''
        self._used_fallback_image = False

    @property
    def is_running(self) -> bool:
        return self.check_health()

    def check_health(self) -> bool:
        if self._stopping:
            return False
        icon = self._icon
        if icon is None or not self._started:
            return False
        thread = self._tray_thread
        if thread is not None and not thread.is_alive():
            self.last_error = self.last_error or 'Tray thread exited unexpectedly'
            return False
        return bool(getattr(icon, '_running', False))

    def diagnostics_text(self) -> str:
        self._refresh_diagnostics()
        lines = ['CLEANROOM TRAY DIAGNOSTICS']
        for key, value in self.diagnostics.items():
            lines.append(f'{key}: {value}')
        if self.last_error:
            lines.append(f'last_error: {self.last_error}')
        return '\n'.join(lines)

    def _refresh_diagnostics(self) -> None:
        icon = self._icon
        thread = self._tray_thread
        self.diagnostics = {
            'tray_enabled': True,
            'pystray_import': 'ok',
            'pid': os.getpid(),
            'icon_asset_path': self._icon_asset_path or '(fallback)',
            'fallback_icon': self._used_fallback_image,
            'tray_object_id': id(self),
            'icon_object_id': id(icon) if icon else None,
            'active_tray_stored': _active_tray is self,
            'started': self._started,
            'stopping': self._stopping,
            'thread_name': thread.name if thread else None,
            'thread_id': thread.ident if thread else None,
            'thread_alive': thread.is_alive() if thread else False,
            'icon_running': bool(getattr(icon, '_running', False)) if icon else False,
            'icon_visible': bool(getattr(icon, 'visible', False)) if icon else False,
        }

    def _log_diagnostics(self, note: str = '') -> None:
        self._refresh_diagnostics()
        if note:
            self.diagnostics['note'] = note
        logger.info('Tray diagnostics (%s): %s', note or 'snapshot', self.diagnostics)

    def start(self) -> bool:
        global _active_tray
        with _start_lock:
            return self._start_locked()

    def _start_locked(self) -> bool:
        global _active_tray
        self.last_error = ''
        logger.info('Tray start requested (controller=%s pid=%s)', id(self), os.getpid())

        try:
            import pystray  # noqa: F401
        except ImportError as exc:
            self.last_error = f'pystray is not installed ({exc})'
            logger.warning('Tray unavailable: %s', self.last_error)
            self.diagnostics['pystray_import'] = f'failed: {exc}'
            return False

        if _active_tray is not None and _active_tray is not self:
            if _active_tray.check_health():
                logger.info('Tray already running on controller=%s — reusing', id(_active_tray))
                if hasattr(self._app, '_tray'):
                    self._app._tray = _active_tray
                return True
            logger.info('Stopping stale tray controller=%s', id(_active_tray))
            try:
                _active_tray.stop()
            except Exception:
                logger.debug('Stale tray stop raised', exc_info=True)
            _active_tray = None

        if self._started and self.check_health():
            logger.info('Tray already running on this controller=%s', id(self))
            _active_tray = self
            return True

        if self._icon is not None:
            logger.info('Stopping prior icon on controller=%s before restart', id(self))
            self.stop()
            time.sleep(0.35)

        self._stopping = False
        self._started = False
        self._ready.clear()
        try:
            self._start_icon()
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception('Tray failed to start')
            self.stop()
            return False

        if not self._ready.wait(timeout=10.0):
            self.last_error = self.last_error or 'Tray icon did not become ready in time'
            logger.error('Tray start timeout: %s', self.last_error)
            self.stop()
            return False

        self._started = True
        if not self.check_health():
            self.last_error = self.last_error or 'Tray icon not healthy after start'
            logger.error('Tray unhealthy immediately after start: %s', self.last_error)
            self._started = False
            self.stop()
            return False

        _active_tray = self
        self._pin_keepalive()
        self._log_diagnostics('started')
        return True

    def _pin_keepalive(self) -> None:
        global _keepalive
        for obj in (self, self._icon, self._tray_image, self._tray_menu):
            if obj is not None and obj not in _keepalive:
                _keepalive.append(obj)

    def _unpin_keepalive(self) -> None:
        global _keepalive
        for obj in (self._tray_menu, self._tray_image, self._icon, self):
            try:
                _keepalive.remove(obj)
            except ValueError:
                pass

    def _start_icon(self):
        import pystray

        image, asset_path, used_fallback = _load_tray_image()
        self._tray_image = image
        self._icon_asset_path = asset_path
        self._used_fallback_image = used_fallback

        menu = self._build_menu()
        self._tray_menu = menu

        icon_name = _TRAY_ICON_NAME
        icon = pystray.Icon(
            icon_name,
            image,
            self._safe_tooltip_text(),
            menu=menu,
        )
        _ensure_icon_running_attr(icon)
        self._icon = icon
        logger.info(
            'Tray icon creating name=%s icon_id=%s asset=%s fallback=%s',
            icon_name, id(icon), asset_path or 'none', used_fallback,
        )

        def _setup(ic):
            logger.info('Tray setup callback (icon_id=%s)', id(ic))
            try:
                ic.visible = True
            except Exception as exc:
                self.last_error = str(exc)
                logger.exception('Tray setup failed to show icon')

        logger.info('Tray calling run_detached (icon_id=%s)', id(icon))
        icon.run_detached(setup=_setup)

        deadline = time.time() + 10.0
        while time.time() < deadline:
            if getattr(icon, '_running', False):
                break
            time.sleep(0.05)
        else:
            self.last_error = 'Tray icon thread did not reach running state'
            raise RuntimeError(self.last_error)

        self._tray_thread = getattr(icon, '_thread', None)
        if self._tray_thread is not None:
            logger.info(
                'Tray thread alive name=%s id=%s',
                self._tray_thread.name, self._tray_thread.ident,
            )
        self._start_thread_monitor()
        self._ready.set()

        def _nudge():
            if self._icon is not None and not self._stopping:
                try:
                    self._icon.visible = True
                except Exception:
                    logger.debug('Tray visibility nudge failed', exc_info=True)

        threading.Timer(0.6, _nudge).start()
        threading.Timer(2.0, _nudge).start()

    def _start_thread_monitor(self) -> None:
        """Log unexpected tray thread exit and notify the app on the Tk thread."""
        thread = self._tray_thread
        if thread is None:
            return

        controller = self

        def _watch():
            try:
                thread.join()
            except Exception:
                logger.debug('Tray monitor join failed', exc_info=True)
            if controller._stopping:
                logger.info('Tray thread exited after stop (controller=%s)', id(controller))
                return
            controller.last_error = 'Tray thread exited unexpectedly'
            logger.error(
                'Tray thread exited while still active (controller=%s): %s',
                id(controller), controller.last_error,
            )
            controller._started = False
            try:
                controller._schedule_app(lambda: controller._notify_thread_exit())
            except Exception:
                pass

        self._monitor_thread = threading.Thread(
            target=_watch, name='cleanroom-tray-monitor', daemon=True)
        self._monitor_thread.start()

    def _schedule_app(self, fn):
        try:
            self._app.after(0, fn)
        except Exception:
            logger.debug('Tray app schedule failed (app may be shutting down)', exc_info=True)

    def _notify_thread_exit(self):
        if getattr(self._app, '_shutting_down', False):
            return
        if hasattr(self._app, '_on_tray_thread_exit'):
            self._app._on_tray_thread_exit(self)

    def stop(self):
        global _active_tray
        if self._stopping and self._icon is None and not self._started:
            return

        logger.info('Tray stop requested (controller=%s pid=%s)', id(self), os.getpid())
        self._stopping = True
        self._started = False
        icon = self._icon
        thread = self._tray_thread or (getattr(icon, '_thread', None) if icon else None)
        self._icon = None
        self._ready.clear()

        if icon is not None:
            _ensure_icon_running_attr(icon)
            try:
                icon.visible = False
            except Exception:
                pass
            try:
                logger.info('Tray icon.stop() (icon_id=%s)', id(icon))
                icon.stop()
            except AttributeError:
                logger.debug('Tray icon stop — missing _running (patched)', exc_info=True)
            except Exception:
                logger.exception('Tray icon stop raised')
            finally:
                try:
                    icon._running = False
                except Exception:
                    pass

        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            logger.info('Tray joining thread id=%s', thread.ident)
            thread.join(timeout=5.0)
            if thread.is_alive():
                self.last_error = 'Tray thread did not exit within 5s'
                logger.error('Tray thread join timeout (id=%s)', thread.ident)

        self._tray_thread = None
        if _active_tray is self:
            _active_tray = None
        self._unpin_keepalive()
        self._log_diagnostics('stopped')

    def refresh_tooltip(self):
        icon = self._icon
        if icon is None:
            return
        try:
            if hasattr(self._app, 'get_tray_tooltip'):
                icon.title = self._app.get_tray_tooltip()
            else:
                icon.title = self._safe_tooltip_text()
        except Exception:
            try:
                icon.title = self._safe_tooltip_text()
            except Exception:
                logger.debug('Tray tooltip refresh failed', exc_info=True)

    def _safe_tooltip_text(self) -> str:
        return f'{brand.APP_DISPLAY} — Archive-first ON'

    def refresh_menu(self):
        icon = self._icon
        if icon is None or self._stopping:
            return
        try:
            menu = self._build_menu()
            self._tray_menu = menu
            icon.menu = menu
            if hasattr(icon, 'update_menu'):
                icon.update_menu()
        except Exception:
            logger.debug('Tray menu refresh failed', exc_info=True)

    def _scan_running(self) -> bool:
        return bool(getattr(self._app, '_cleaner_loading', False))

    def _run_scan_label(self, _item=None) -> str:
        return 'Scanning…' if self._scan_running() else 'Run Scan'

    def _run_scan_enabled(self, _item) -> bool:
        return not self._scan_running()

    def _stop_scan_visible(self, _item) -> bool:
        return self._scan_running()

    def _stop_scan_enabled(self, _item) -> bool:
        return self._scan_running()

    def _build_menu(self):
        from pystray import Menu, MenuItem as item

        return Menu(
            item(f'{brand.APP_DISPLAY} — archive-first', None, enabled=False),
            Menu.SEPARATOR,
            item('Open Cleanroom', self._on_open),
            item(self._run_scan_label, self._on_run_scan, enabled=self._run_scan_enabled),
            item('Stop Scan', self._on_stop_scan,
                 visible=self._stop_scan_visible, enabled=self._stop_scan_enabled),
            item('Preview Latest Receipt', self._on_preview_receipt),
            item('Open Latest Receipt', self._on_latest_receipt),
            item('Open Proof Pack', self._on_proof_pack),
            item('Open Archive Folder', self._on_archive_folder),
            Menu.SEPARATOR,
            item('Tools', Menu(
                item('Explorer Context Menus', self._on_explorer_menus),
                item('Registry Snapshot', self._on_registry_snapshot),
                item('Cleanroom Rewind', self._on_rewind),
                item('Custody Check', self._on_custody_check),
            )),
            item('Window', Menu(
                item('Hide to tray', self._on_hide),
                item('Show', self._on_show),
                item('Restore', self._on_restore_tab),
            )),
            Menu.SEPARATOR,
            item('Quit Cleanroom', self._on_quit),
        )

    def _schedule(self, fn):
        if self._stopping:
            return
        self._schedule_app(fn)

    def _on_open(self, icon, item):
        self._schedule(self._app._tray_show_window)

    def _on_hide(self, icon, item):
        self._schedule(self._app._tray_hide_window)

    def _on_show(self, icon, item):
        self._schedule(self._app._tray_show_window)

    def _on_run_scan(self, icon, item):
        def _go():
            if getattr(self._app, '_cleaner_loading', False):
                return
            self._app.refresh_cleanup()

        self._schedule(_go)

    def _on_stop_scan(self, icon, item):
        def _go():
            if hasattr(self._app, 'stop_scan'):
                self._app.stop_scan()

        self._schedule(_go)

    def _on_quit(self, icon, item):
        def _go():
            if getattr(self._app, '_cleaner_loading', False):
                if hasattr(self._app, 'stop_scan'):
                    self._app.stop_scan()
                self._app._pending_shutdown = True
                return
            self._app._shutdown_app(reason='tray-quit')

        self._schedule(_go)

    def _on_preview_receipt(self, icon, item):
        def _go():
            items = getattr(self._app, 'cleanup_items', None) or []
            selected = getattr(self._app, 'cleanup_selected', None) or set()
            if not items or not selected:
                return
            self._app.preview_cleanup_receipt()

        self._schedule(_go)

    def _on_latest_receipt(self, icon, item):
        self._schedule(self._app.open_last_receipt)

    def _on_proof_pack(self, icon, item):
        self._schedule(self._app.export_audit)

    def _on_archive_folder(self, icon, item):
        self._schedule(self._app.open_archive_folder)

    def _on_explorer_menus(self, icon, item):
        self._schedule(self._app.open_shell_context_menu_tool)

    def _on_registry_snapshot(self, icon, item):
        self._schedule(self._app.open_registry_health)

    def _on_rewind(self, icon, item):
        self._schedule(self._app.open_time_machine)

    def _on_custody_check(self, icon, item):
        self._schedule(self._app.verify_custody)

    def _on_restore_tab(self, icon, item):
        def _go():
            try:
                self._app.tab_control.select(self._app.restore_tab)
                self._app.refresh_restore()
                self._app._tray_show_window()
            except Exception:
                self._app._tray_show_window()

        self._schedule(_go)
