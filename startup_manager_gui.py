import json
import logging
import os
import queue
import brand
import customtkinter as ctk
from ui import ctk_theme
from ui.launcher import run_launch_splash
from ui.page_layout import (
    bind_pane_persistence,
    classify_layout,
    create_horizontal_pane,
    ensure_pane_sash,
    sync_split_workspace,
    sync_table_empty_view,
)
from ui.window_geometry import (
    apply_window_geometry, bind_window_tracking, animations_disabled,
    MAX_SIZE, MIN_SIZE, apply_dialog_geometry,
)
from ui.receipt_animation import (
    DEFAULT_LINES,
    PREVIEW_LINES,
    PROOF_PACK_LINES,
    play_receipt_animation,
)
from ui.page_state import (
    EMPTY_DONE,
    ERROR,
    IDLE_READY,
    LOADING,
    RECEIPT_READY,
    RESULTS_READY,
    SCAN_STOPPED,
    cleaner_page_state,
    home_page_state,
)
from ui.proof_dashboard import (
    CommandBar,
    ProofSummaryCard,
    app_shell_header,
    brand_identity_block,
    collapsible_section,
    recent_proof_tile,
    recommendation_card,
    settings_card,
    settings_pill_nav,
    settings_sidebar_nav,
    sidebar_nav_button,
    trust_compact_strip,
)
from ui.product_dialogs import (
    CleanroomModal,
    show_action_popover,
    show_grouped_popover,
    show_report_modal,
    show_summary_modal,
)
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import sys
import shutil
import time
from datetime import datetime
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None

try:
    import prune_archive
except Exception:
    prune_archive = None

try:
    import archive_custody
except Exception:
    archive_custody = None

try:
    from ui.receipt_viewer import show_receipt
except Exception:
    show_receipt = None

try:
    import receipt_bridge
except Exception:
    receipt_bridge = None

try:
    import startup_manager
except Exception:
    startup_manager = None

try:
    import startup_manager_admin
except Exception:
    startup_manager_admin = None

try:
    import main as cleanup_main
except Exception:
    cleanup_main = None

try:
    import restore as restore_module
except Exception:
    restore_module = None

try:
    import enable_telemetry
except Exception:
    enable_telemetry = None

try:
    import recommendations as rec_engine
except Exception:
    rec_engine = None

try:
    from PIL import Image as PILImage, ImageTk as PILImageTk
except Exception:
    PILImage = PILImageTk = None

try:
    import uninstaller
except Exception:
    uninstaller = None

try:
    import program_advice
except Exception:
    program_advice = None

try:
    import foresight
except Exception:
    foresight = None

try:
    import timeline as timeline_module
except Exception:
    timeline_module = None

try:
    import receipts as receipts_module
except Exception:
    receipts_module = None

try:
    import registry_health
except Exception:
    registry_health = None

try:
    import proof as proof_module
except Exception:
    proof_module = None

try:
    import ledger as ledger_module
except Exception:
    ledger_module = None

try:
    import shell_context_menu as shell_menu_module
except Exception:
    shell_menu_module = None

try:
    import shell_actions as shell_actions_module
except Exception:
    shell_actions_module = None

try:
    import audit as audit_module
except Exception:
    audit_module = None


def _resource_path(name):
    """Locate a bundled resource: next to the exe/script first, then the
    PyInstaller extraction dir."""
    here = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
    candidate = here / name
    if candidate.exists():
        return candidate
    return Path(getattr(sys, '_MEIPASS', str(Path(__file__).parent))) / name


# ---------------------------------------------------------------------------
# Palettes — pick any theme, dark is the default. Each palette must define the
# full key set (see THEME_KEYS); ON_ACCENT is the text color drawn on top of
# accent-colored surfaces (buttons, selected rows).
# ---------------------------------------------------------------------------
PALETTES = {
    'dark': {
        'LABEL': 'Dark',
        'BG': '#1E232B', 'SIDEBAR_BG': '#171C23', 'CARD_BG': '#262C36',
        'ACCENT': '#3B82F6', 'ACCENT_DARK': '#2563EB', 'ACCENT_SOFT': '#1E3A5F',
        'PROOF': '#22C55E', 'PROOF_DARK': '#16A34A', 'PROOF_SOFT': '#143D26',
        'ON_ACCENT': '#FFFFFF',
        'TEXT': '#E5E7EB', 'MUTED': '#9AA4B2', 'BORDER': '#39414E',
        'ROW_ALT': '#2B323D', 'HEAD_BG': '#323A46', 'STATUS_BG': '#171C23',
        'RING_BG': '#39414E', 'PREVIEW_BG': '#1A1F26', 'PLACEHOLDER': '#6B7480',
        'TOOLTIP_BG': '#3A4250', 'TOOLTIP_FG': '#E5E7EB',
        'SEVERITY': {'high': '#F87171', 'medium': '#FBBF24', 'low': '#60A5FA', 'info': '#9AA4B2'},
        'REASONS': {'large-file': '#FBBF24', 'installer/archive': '#60A5FA',
                    'partial-download': '#C4B5FD', 'zero-byte': '#9AA4B2',
                    'uninstall-leftover': '#F87171', 'registry-leftover': '#F87171',
                    'broken-registry': '#FB923C'},
    },
    'light': {
        'LABEL': 'Light',
        'BG': '#EEF2F9', 'SIDEBAR_BG': '#F7FAFF', 'CARD_BG': '#FFFFFF',
        'ACCENT': '#2563EB', 'ACCENT_DARK': '#1D4ED8', 'ACCENT_SOFT': '#E8F0FE',
        'PROOF': '#16A34A', 'PROOF_DARK': '#15803D', 'PROOF_SOFT': '#DCFCE7',
        'ON_ACCENT': '#FFFFFF',
        'TEXT': '#1F2937', 'MUTED': '#6B7280', 'BORDER': '#D9E2EC',
        'ROW_ALT': '#F4F8FE', 'HEAD_BG': '#E4E9F3', 'STATUS_BG': '#E4E9F3',
        'RING_BG': '#E5EAF3', 'PREVIEW_BG': '#FAFBFD', 'PLACEHOLDER': '#8A8A8A',
        'TOOLTIP_BG': '#FFFFE0', 'TOOLTIP_FG': '#1F2937',
        'SEVERITY': {'high': '#D62828', 'medium': '#F0A500', 'low': '#2563EB', 'info': '#6B7280'},
        'REASONS': {'large-file': '#C2620A', 'installer/archive': '#1D4ED8',
                    'partial-download': '#7C3AED', 'zero-byte': '#6B7280',
                    'uninstall-leftover': '#D62828', 'registry-leftover': '#D62828',
                    'broken-registry': '#C2410C'},
    },
    'midnight': {
        'LABEL': 'Midnight (OLED)',
        'BG': '#000000', 'SIDEBAR_BG': '#050709', 'CARD_BG': '#0D1117',
        'ACCENT': '#00E5FF', 'ACCENT_DARK': '#00B8D4', 'ACCENT_SOFT': '#003A44',
        'PROOF': '#34D399', 'PROOF_DARK': '#10B981', 'PROOF_SOFT': '#064E3B',
        'ON_ACCENT': '#00222A',
        'TEXT': '#D7E0E8', 'MUTED': '#7A8794', 'BORDER': '#1F2933',
        'ROW_ALT': '#11161C', 'HEAD_BG': '#161D24', 'STATUS_BG': '#050709',
        'RING_BG': '#1F2933', 'PREVIEW_BG': '#05080B', 'PLACEHOLDER': '#5A6671',
        'TOOLTIP_BG': '#14202A', 'TOOLTIP_FG': '#D7E0E8',
        'SEVERITY': {'high': '#FF5370', 'medium': '#FFCB6B', 'low': '#00E5FF', 'info': '#7A8794'},
        'REASONS': {'large-file': '#FFCB6B', 'installer/archive': '#00E5FF',
                    'partial-download': '#C792EA', 'zero-byte': '#7A8794',
                    'uninstall-leftover': '#FF5370', 'registry-leftover': '#FF5370',
                    'broken-registry': '#F78C6C'},
    },
    'nord': {
        'LABEL': 'Nord',
        'BG': '#2E3440', 'SIDEBAR_BG': '#272C36', 'CARD_BG': '#3B4252',
        'ACCENT': '#88C0D0', 'ACCENT_DARK': '#81A1C1', 'ACCENT_SOFT': '#434C5E',
        'PROOF': '#A3BE8C', 'PROOF_DARK': '#8FBCBB', 'PROOF_SOFT': '#3B4252',
        'ON_ACCENT': '#2E3440',
        'TEXT': '#ECEFF4', 'MUTED': '#A0AABE', 'BORDER': '#4C566A',
        'ROW_ALT': '#404859', 'HEAD_BG': '#434C5E', 'STATUS_BG': '#272C36',
        'RING_BG': '#4C566A', 'PREVIEW_BG': '#2B303B', 'PLACEHOLDER': '#7B86A0',
        'TOOLTIP_BG': '#4C566A', 'TOOLTIP_FG': '#ECEFF4',
        'SEVERITY': {'high': '#BF616A', 'medium': '#EBCB8B', 'low': '#88C0D0', 'info': '#A0AABE'},
        'REASONS': {'large-file': '#EBCB8B', 'installer/archive': '#88C0D0',
                    'partial-download': '#B48EAD', 'zero-byte': '#A0AABE',
                    'uninstall-leftover': '#BF616A', 'registry-leftover': '#BF616A',
                    'broken-registry': '#D08770'},
    },
    'emerald': {
        'LABEL': 'Emerald (Pro)',
        'BG': '#1F2428', 'SIDEBAR_BG': '#181C20', 'CARD_BG': '#272D33',
        'ACCENT': '#22C55E', 'ACCENT_DARK': '#16A34A', 'ACCENT_SOFT': '#143D26',
        'PROOF': '#22C55E', 'PROOF_DARK': '#16A34A', 'PROOF_SOFT': '#143D26',
        'ON_ACCENT': '#06270F',
        'TEXT': '#E7ECEF', 'MUTED': '#94A1AB', 'BORDER': '#3A434B',
        'ROW_ALT': '#2C333A', 'HEAD_BG': '#333B43', 'STATUS_BG': '#181C20',
        'RING_BG': '#3A434B', 'PREVIEW_BG': '#1A1F23', 'PLACEHOLDER': '#65737E',
        'TOOLTIP_BG': '#37404A', 'TOOLTIP_FG': '#E7ECEF',
        'SEVERITY': {'high': '#F87171', 'medium': '#FBBF24', 'low': '#22C55E', 'info': '#94A1AB'},
        'REASONS': {'large-file': '#FBBF24', 'installer/archive': '#4ADE80',
                    'partial-download': '#C4B5FD', 'zero-byte': '#94A1AB',
                    'uninstall-leftover': '#F87171', 'registry-leftover': '#F87171',
                    'broken-registry': '#FB923C'},
    },
    'cyberpunk': {
        'LABEL': 'Cyberpunk',
        'BG': '#170B22', 'SIDEBAR_BG': '#110718', 'CARD_BG': '#221033',
        'ACCENT': '#FF2ED1', 'ACCENT_DARK': '#D612AC', 'ACCENT_SOFT': '#3A1052',
        'PROOF': '#39FF14', 'PROOF_DARK': '#22C55E', 'PROOF_SOFT': '#1A3D1A',
        'ON_ACCENT': '#2A0030',
        'TEXT': '#F2E9FF', 'MUTED': '#A88FC9', 'BORDER': '#43245F',
        'ROW_ALT': '#2A1540', 'HEAD_BG': '#321A4A', 'STATUS_BG': '#110718',
        'RING_BG': '#43245F', 'PREVIEW_BG': '#130A1D', 'PLACEHOLDER': '#7E66A0',
        'TOOLTIP_BG': '#321A4A', 'TOOLTIP_FG': '#F2E9FF',
        'SEVERITY': {'high': '#FF5577', 'medium': '#FFD166', 'low': '#00F0FF', 'info': '#A88FC9'},
        'REASONS': {'large-file': '#FFD166', 'installer/archive': '#00F0FF',
                    'partial-download': '#B388FF', 'zero-byte': '#A88FC9',
                    'uninstall-leftover': '#FF5577', 'registry-leftover': '#FF5577',
                    'broken-registry': '#FF9E64'},
    },
}

THEME_ORDER = ['dark', 'light', 'emerald', 'midnight', 'nord', 'cyberpunk']
THEME_KEYS = ('BG', 'SIDEBAR_BG', 'CARD_BG', 'ACCENT', 'ACCENT_DARK', 'ACCENT_SOFT',
              'PROOF', 'PROOF_DARK', 'PROOF_SOFT',
              'ON_ACCENT', 'TEXT', 'MUTED', 'BORDER', 'ROW_ALT', 'HEAD_BG', 'STATUS_BG',
              'RING_BG', 'PREVIEW_BG', 'PLACEHOLDER', 'TOOLTIP_BG', 'TOOLTIP_FG')

UI_PREFS_PATH = brand.user_data_dir() / 'ui_prefs.json'


def load_ui_prefs():
    try:
        if UI_PREFS_PATH.exists():
            return json.loads(UI_PREFS_PATH.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}


def save_ui_prefs(prefs):
    try:
        UI_PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        UI_PREFS_PATH.write_text(json.dumps(prefs, indent=2), encoding='utf-8')
    except Exception:
        pass


# Module-level color names; set by apply_palette() before widgets are built.
BG = SIDEBAR_BG = CARD_BG = ACCENT = ACCENT_DARK = ACCENT_SOFT = ON_ACCENT = ''
PROOF = PROOF_DARK = PROOF_SOFT = ''
TEXT = MUTED = BORDER = ROW_ALT = HEAD_BG = STATUS_BG = ''
RING_BG = PREVIEW_BG = PLACEHOLDER = TOOLTIP_BG = TOOLTIP_FG = ''
SEVERITY_COLORS = {}
REASON_COLORS = {}
CURRENT_THEME = 'dark'


def apply_palette(name):
    p = PALETTES.get(name) or PALETTES['dark']
    g = globals()
    for key in THEME_KEYS:
        g[key] = p[key]
    g['SEVERITY_COLORS'] = p['SEVERITY']
    g['REASON_COLORS'] = p['REASONS']
    g['CURRENT_THEME'] = name if name in PALETTES else 'dark'


apply_palette(load_ui_prefs().get('theme', 'dark'))

logger = logging.getLogger(__name__)

APP_VERSION = brand.APP_VERSION
SEARCH_PLACEHOLDER = 'Search startup items...  (Ctrl+F)'

ACTIVITY_EVENT_LABELS = {
    'file': 'Archived',
    'registry': 'Archived',
    'prune': 'Pruned',
    'restore': 'Restored',
}

CLEANUP_REASON_GROUPS = (
    ('Installers & archives', frozenset({
        'installer/archive', 'installer', 'old-installer', 'duplicate', 'partial-download',
    })),
    ('Zero-byte files', frozenset({'zero-byte'})),
    ('Large files', frozenset({'large-file'})),
    ('Other', None),
)


class StartupManagerGUI(ctk.CTk):
    """Cleanroom GUI: Review, Activity, Startup, Cleaner, Uninstaller, Restore."""

    def __init__(self, config_path=None, restore_log_path=None, initial_tab=None):
        ctk_theme.sync_appearance(CURRENT_THEME)
        super().__init__()
        self.title(brand.APP_DISPLAY)
        self.withdraw()
        self.resizable(True, True)
        self.configure(fg_color=BG)
        try:
            ico = None
            for name in ('cleanroom-icon.ico', 'icon.ico'):
                candidate = _resource_path(name)
                if candidate.exists():
                    ico = candidate
                    break
            if ico is None and brand.ICON_ICO_PATH.exists():
                ico = brand.ICON_ICO_PATH
            if ico is not None:
                self.iconbitmap(default=str(ico))
        except Exception:
            pass
        self._init_style()

        self.data = {'folders': [], 'registry': []}
        self.current_category = 'All'
        self.search_text = ''
        self.current_sort = ('name', False)
        self.cleanup_items = []
        self.cleanup_selected = set()
        self.cleanup_total_size = 0
        if config_path:
            self.cleanup_config_path = Path(config_path)
        else:
            self.cleanup_config_path = cleanup_main.DEFAULT_CONFIG if cleanup_main else Path(__file__).parent / 'cleanup_config.yaml'
        self.dedupe_enabled = tk.BooleanVar(value=False)
        self.restore_entries = []
        if restore_log_path:
            self.restore_log_path = Path(restore_log_path)
        else:
            # Follow the config's log_file so the installed app reads the
            # same log the cleaner writes (not a path next to the source).
            log_file = None
            try:
                if cleanup_main:
                    log_file = (cleanup_main.load_config(self.cleanup_config_path) or {}).get('log_file')
            except Exception:
                log_file = None
            self.restore_log_path = Path(log_file) if log_file else Path(__file__).parent / 'cleanup_log.json'
        self._bg_queue = queue.Queue()
        self.wants_restart = False
        self._launch_done = False
        self._launch_logo = None
        self._tray = None
        self._tray_watch_ids: list[str] = []
        self._shutting_down = False
        self._initial_tab = initial_tab
        self._tab_loaded = {0}
        self._scan_session_done = False
        self._cleaner_loading = False
        self._cleaner_error = ''
        self._scan_stopped = False
        self._scan_cancel_event = threading.Event()
        self._scan_skip_folders: set[str] = set()
        self._scan_progress: dict = {}
        self._scan_progress_job = None
        self._scan_diag: dict = {}
        self._pending_shutdown = False
        self._scan_worker_id = 0
        self._selected_rec_idx = None
        self._sidebar_collapsed = bool(load_ui_prefs().get('sidebar_collapsed', False))
        self._cached_scan_count = 0
        self._cached_scan_size = 0
        self._cached_scan_at = ''
        self._archive_context_menu = None
        self._restore_context_menu = None
        self._archive_busy = False
        self._chunk_tokens = {}
        self._page_is_dashboard = True
        self._brand_phase = None
        self._settings_dirty = False
        self.protocol('WM_DELETE_WINDOW', self._on_window_close)
        global _APP_INSTANCE
        _APP_INSTANCE = self
        self.after(50, self._poll_bg_queue)

        self.create_widgets()
        self._bind_shortcuts()
        self.bind('<Configure>', self._on_root_configure, add='+')
        self.after(30, self._run_launch_sequence)

    def _launcher_colors(self):
        return {
            'BG': BG, 'CARD_BG': CARD_BG, 'ACCENT': ACCENT,
            'TEXT': TEXT, 'MUTED': MUTED, 'BORDER': BORDER,
        }

    def _save_window_geometry(self, geo: dict):
        if not load_ui_prefs().get('remember_window_geometry', True):
            return
        prefs = load_ui_prefs()
        prefs['window_geometry'] = geo
        save_ui_prefs(prefs)

    def _run_launch_sequence(self):
        if animations_disabled():
            self._finish_launch_sequence()
            return
        self._launch_logo = self._load_logo_ctk(96)
        run_launch_splash(
            self,
            title=brand.APP_DISPLAY,
            tagline=brand.APP_MOTTO,
            colors=self._launcher_colors(),
            logo_photo=self._launch_logo,
            on_complete=self._finish_launch_sequence,
            min_ms=1100,
        )

    def _apply_initial_tab(self):
        tab = getattr(self, '_initial_tab', None)
        if tab == 'archive':
            self.open_archive_browser_tab()
        elif tab == 'restore':
            self.tab_control.select(self.restore_tab)
            self.refresh_restore()
        elif tab == 'settings':
            self.tab_control.select(self.settings_tab)
        elif load_ui_prefs().get('remember_last_tab', True):
            try:
                idx = int(load_ui_prefs().get('last_tab', 0))
                if 0 <= idx < self.tab_control.index('end'):
                    self.tab_control.select(idx)
            except Exception:
                pass
        else:
            default_map = {
                'Home': 0, 'Activity': 1, 'Startup': 2, 'Cleaner': 3,
                'Archive': 6, 'Settings': 7,
            }
            label = load_ui_prefs().get('default_tab', 'Home')
            idx = default_map.get(label, 0)
            if 0 <= idx < self.tab_control.index('end'):
                self.tab_control.select(idx)

    def _finish_launch_sequence(self):
        if self._launch_done:
            return
        self._launch_done = True
        prefs = load_ui_prefs()
        if not prefs.get('remember_window_geometry', True):
            prefs = dict(prefs)
            prefs.pop('window_geometry', None)
        apply_window_geometry(self, prefs)
        bind_window_tracking(self, on_save=self._save_window_geometry)
        self.deiconify()
        self.lift()
        self.focus_force()
        self._update_responsive_layout()
        self._load_scan_cache()
        self._refresh_header_proof_badges()
        self.refresh_dashboard()
        self._sync_cleaner_state()
        self._sync_home_state()
        self._update_context_panel()
        if not animations_disabled():
            self._fade_in_window()
            self.after(350, self._pulse_proof_flow)
        self.after(900, self._init_tray)
        self._apply_initial_tab()
        if hasattr(self, '_shell_pane'):
            self._bind_pane(self._shell_pane, 'shell_sidebar', default=248)
        self._apply_sidebar_collapsed()
        self._update_page_chrome()
        self._update_brand_identity()
        self.after(250, self._post_paint_launch_tasks)

    def _scan_on_startup(self) -> bool:
        return bool(load_ui_prefs().get('scan_on_startup', False))

    def _load_scan_cache(self):
        snap = load_ui_prefs().get('last_scan') or {}
        self._cached_scan_count = int(snap.get('count', 0) or 0)
        self._cached_scan_size = int(snap.get('total_size', 0) or 0)
        self._cached_scan_at = str(snap.get('at', '') or '')

    def _save_scan_cache(self):
        prefs = load_ui_prefs()
        prefs['last_scan'] = {
            'count': len(self.cleanup_items),
            'total_size': int(self.cleanup_total_size),
            'at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        save_ui_prefs(prefs)
        self._cached_scan_count = len(self.cleanup_items)
        self._cached_scan_size = int(self.cleanup_total_size)
        self._cached_scan_at = prefs['last_scan']['at']

    def _post_paint_launch_tasks(self):
        """Lightweight work after the window is visible — never block first paint."""
        if self._scan_on_startup():
            self.refresh_cleanup()
        elif foresight:
            self._run_bg(foresight.record_snapshot,
                         lambda result, err: self.refresh_foresight())

    def _lazy_load_tab(self, tab_idx: int):
        if tab_idx in self._tab_loaded:
            return
        self._tab_loaded.add(tab_idx)
        loaders = {
            1: self.refresh_activity,
            2: self.refresh,
            4: self.refresh_uninstaller,
            5: self.refresh_restore,
            6: self.refresh_archive_browser,
        }
        loader = loaders.get(tab_idx)
        if loader:
            loader()

    def _pane_pref(self, key, default=None):
        return (load_ui_prefs().get('pane_sizes') or {}).get(key, default)

    def _save_pane_pref(self, key, value):
        prefs = load_ui_prefs()
        sizes = dict(prefs.get('pane_sizes') or {})
        sizes[key] = int(value)
        prefs['pane_sizes'] = sizes
        save_ui_prefs(prefs)

    def _bind_pane(self, pane, key, default=None, **kw):
        bind_pane_persistence(
            pane, key,
            get_value=lambda k, d=default: self._pane_pref(k, d),
            set_value=self._save_pane_pref,
            default=default,
            **kw,
        )

    def _ensure_pane(self, pane, key, default=None, **kw):
        ensure_pane_sash(
            pane, key=key,
            get_value=lambda k, d=default: self._pane_pref(k, d),
            default=default,
            **kw,
        )

    def _show_tray_unavailable(self, reason: str = ''):
        host = getattr(self, '_hdr_top', None)
        if host is None or getattr(self, '_tray_warning', None):
            return
        msg = reason.strip() or 'Tray icon unavailable.'
        self._tray_warning = ctk_theme.frame(host, '#3F1D1D', corner_radius=8)
        self._tray_warning.pack(fill='x', pady=(0, 4))
        body = ctk_theme.frame(self._tray_warning, '#3F1D1D')
        body.pack(fill='x', padx=12, pady=8)
        ctk_theme.label(
            body,
            'Tray icon could not stay running. Cleanroom will keep running in the main window.',
            text_color='#FCA5A5', font_size=9, wraplength=900, justify='left',
        ).pack(anchor='w')
        if msg:
            ctk_theme.label(
                body, msg, text_color='#FCA5A5', font_size=9, wraplength=900, justify='left',
            ).pack(anchor='w', pady=(4, 0))

        def _copy_diag():
            tray = getattr(self, '_tray', None)
            text = tray.diagnostics_text() if tray and hasattr(tray, 'diagnostics_text') else msg
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
                self._set_status('Tray diagnostics copied.')
            except tk.TclError:
                pass

        ctk_theme.button(
            body, 'Copy diagnostics', _copy_diag,
            fg_color=HEAD_BG, hover_color=ACCENT_SOFT, text_color=TEXT,
            height=24, width=120, corner_radius=8,
        ).pack(anchor='w', pady=(8, 0))
        logger.warning('Tray unavailable: %s', msg)

    def _is_cleaner_scanning(self) -> bool:
        return bool(getattr(self, '_cleaner_loading', False))

    def _scan_display_metrics(self):
        """Counts for Home/Cleaner hero — never show stale cache while scanning."""
        if getattr(self, '_cleaner_loading', False) or getattr(self, '_scan_stopped', False):
            return 0, 0, False
        items = self.cleanup_items or []
        session = getattr(self, '_scan_session_done', False)
        if session:
            return len(items), len(self.cleanup_selected or set()), session
        cached = int(getattr(self, '_cached_scan_count', 0) or 0)
        if cached > 0:
            return cached, 0, False
        return 0, 0, session

    def _refresh_tray_menu(self):
        tray = getattr(self, '_tray', None)
        if tray is not None and hasattr(tray, 'refresh_menu'):
            try:
                tray.refresh_menu()
            except Exception:
                pass

    def _sync_cleaner_state(self):
        """Single source of truth for Cleaner hero, footer, and empty layout."""
        count, checked, scan_done = self._scan_display_metrics()
        cached = int(getattr(self, '_cached_scan_count', 0) or 0)
        state, hero, sub, footer = cleaner_page_state(
            loading=self._cleaner_loading,
            stopped=getattr(self, '_scan_stopped', False),
            error=self._cleaner_error,
            count=count if scan_done else 0,
            checked=checked,
            scan_done=scan_done,
            cached_count=0 if scan_done or self._cleaner_loading else cached,
            progress=getattr(self, '_scan_progress', None),
        )
        self._cleaner_page_state = state
        if hasattr(self, 'cleanup_status_hero'):
            if state == ERROR:
                tone = SEVERITY_COLORS.get('high', ACCENT)
            elif state in (LOADING, RECEIPT_READY, IDLE_READY):
                tone = ACCENT
            elif state == EMPTY_DONE:
                tone = PROOF
            else:
                tone = TEXT
            self.cleanup_status_hero.config(text=hero, fg=tone)
            self.cleanup_msg_hero.config(text=sub)
        if hasattr(self, 'cleanup_status_lbl'):
            self.cleanup_status_lbl.config(text=footer)
        try:
            on_cleaner = self.tab_control.index('current') == 3
        except Exception:
            on_cleaner = False
        if on_cleaner or self._cleaner_loading:
            self._set_status(footer)
        if hasattr(self, 'apply_clean_btn'):
            self.apply_clean_btn.configure(
                style='Primary.TButton' if state == RECEIPT_READY else 'Action.TButton')
        count = len(self.cleanup_items or [])
        show_actions = count > 0 and state not in (LOADING, SCAN_STOPPED)
        scanning = state == LOADING
        for attr in ('cleaner_preview_btn', 'apply_clean_btn'):
            if not hasattr(self, attr):
                continue
            btn = getattr(self, attr)
            if scanning:
                btn.pack_forget()
            else:
                btn.pack(side='left', padx=(8, 0))
                btn.config(state='normal' if show_actions else 'disabled')
        if hasattr(self, 'scan_btn'):
            self.scan_btn.config(
                state='disabled' if scanning else 'normal',
                text='Scanning…' if scanning else 'Scan Now',
            )
        if hasattr(self, 'stop_scan_btn'):
            if scanning:
                self.stop_scan_btn.pack(side='left', padx=(8, 0))
            else:
                self.stop_scan_btn.pack_forget()
        if hasattr(self, 'skip_scan_folder_btn'):
            slow = bool((getattr(self, '_scan_progress', None) or {}).get('slow_folder'))
            if scanning and slow:
                self.skip_scan_folder_btn.pack(side='left', padx=(8, 0))
            else:
                self.skip_scan_folder_btn.pack_forget()
        if hasattr(self, '_scan_loading_stop') and hasattr(self, 'skip_scan_folder_btn'):
            if scanning:
                self._scan_loading_stop.pack(side='left', padx=(0, 8))
                slow = bool((getattr(self, '_scan_progress', None) or {}).get('slow_folder'))
                if slow:
                    self.skip_scan_folder_btn.pack(side='left')
                else:
                    self.skip_scan_folder_btn.pack_forget()
            else:
                self._scan_loading_stop.pack_forget()
                self.skip_scan_folder_btn.pack_forget()
        for attr in ('scan_btn', 'dashboard_primary_btn'):
            if hasattr(self, attr) and attr != 'scan_btn':
                getattr(self, attr).config(state='disabled' if scanning else 'normal')
        if hasattr(self, 'tb_scan'):
            self.tb_scan.configure(state='disabled' if scanning else 'normal')
        if hasattr(self, '_update_cleanup_empty_state'):
            self._update_cleanup_empty_state()
        if scanning:
            self._sync_scan_progress_ui()
        self._sync_global_actions(state, checked, scan_done)
        self._update_brand_identity()
        self._refresh_tray_menu()

    def _sync_global_actions(self, home_state=None, checked=0, scan_done=False):
        """Keep hidden command-bar buttons aligned with Home/Cleaner state."""
        if home_state is None:
            home_state = getattr(self, '_home_page_state', IDLE_READY)
        scanning = home_state == LOADING or getattr(self, '_cleaner_loading', False)
        can_preview = (
            not scanning and scan_done and checked > 0
            and home_state in (RECEIPT_READY, RESULTS_READY)
        )
        can_archive = can_preview and home_state == RECEIPT_READY
        for attr, enabled in (
            ('tb_scan', not scanning),
            ('tb_preview', can_preview),
            ('tb_apply', can_archive),
        ):
            if hasattr(self, attr):
                try:
                    getattr(self, attr).configure(state='normal' if enabled else 'disabled')
                except Exception:
                    pass

    def _sync_home_state(self, *, custody_missing: int = 0):
        """Align Home hero with the same scan lifecycle as Cleaner."""
        count, checked, scan_done = self._scan_display_metrics()
        cached = int(getattr(self, '_cached_scan_count', 0) or 0)
        state, hero, sub, status = home_page_state(
            loading=self._cleaner_loading,
            stopped=getattr(self, '_scan_stopped', False),
            error=self._cleaner_error,
            count=count if scan_done else 0,
            checked=checked,
            scan_done=scan_done,
            custody_missing=custody_missing,
            cached_count=0 if scan_done or self._cleaner_loading else cached,
            phase=getattr(self, '_brand_phase', None),
            progress=getattr(self, '_scan_progress', None),
        )
        self._home_page_state = state
        if state == ERROR:
            tone = SEVERITY_COLORS.get('high', ACCENT)
        elif state in (LOADING, RECEIPT_READY):
            tone = ACCENT
        elif state == EMPTY_DONE:
            tone = PROOF
        elif custody_missing:
            tone = SEVERITY_COLORS.get('high', ACCENT)
        else:
            tone = ACCENT if state == IDLE_READY else TEXT
        if hasattr(self, 'dashboard_status_lbl'):
            self.dashboard_status_lbl.config(text=hero, fg=tone)
        if hasattr(self, 'dashboard_msg_lbl'):
            self.dashboard_msg_lbl.config(text=sub)
        try:
            on_home = self.tab_control.index('current') == 0
        except Exception:
            on_home = False
        if on_home or self._cleaner_loading:
            self._set_status(status)
        if not hasattr(self, 'dashboard_primary_btn'):
            return
        scanning = self._cleaner_loading
        checked_n = len(self.cleanup_selected or set()) if scan_done else 0
        if scanning:
            for attr in ('dashboard_primary_btn', 'dashboard_preview_btn', 'dashboard_archive_btn'):
                if hasattr(self, attr):
                    getattr(self, attr).config(state='disabled')
            self.dashboard_primary_btn.configure(text='Scanning…')
            self._sync_global_actions(LOADING, 0, False)
            return
        if state == RECEIPT_READY:
            self.dashboard_primary_btn.configure(
                text='Review Candidates', command=lambda: self._navigate_to_tab(3))
            self.dashboard_preview_btn.config(state='normal')
            self.dashboard_archive_btn.config(
                state='normal' if checked_n > 0 else 'disabled')
            self.dashboard_secondary_btn.configure(
                text='Proof Ledger', command=lambda: self._navigate_to_tab(1))
        elif state == RESULTS_READY:
            self.dashboard_primary_btn.configure(
                text='Review Candidates', command=lambda: self._navigate_to_tab(3))
            self.dashboard_preview_btn.config(state='disabled')
            self.dashboard_archive_btn.config(state='disabled')
            self.dashboard_secondary_btn.configure(
                text='Proof Ledger', command=lambda: self._navigate_to_tab(1))
        elif state == EMPTY_DONE:
            self.dashboard_primary_btn.configure(
                text='Scan Again', command=self.refresh_cleanup)
            self.dashboard_preview_btn.config(state='disabled')
            self.dashboard_archive_btn.config(state='disabled')
            self.dashboard_secondary_btn.configure(
                text='Proof Ledger', command=lambda: self._navigate_to_tab(1))
        elif custody_missing:
            self.dashboard_primary_btn.configure(
                text='Review custody', command=lambda: self._navigate_to_tab(1))
            self.dashboard_preview_btn.config(state='disabled')
            self.dashboard_archive_btn.config(state='disabled')
            self.dashboard_secondary_btn.configure(
                text='Open Archive', command=lambda: self._navigate_to_tab(6))
        else:
            self.dashboard_primary_btn.configure(
                text='Scan Now', command=self.refresh_cleanup)
            self.dashboard_preview_btn.config(state='disabled')
            self.dashboard_archive_btn.config(state='disabled')
            self.dashboard_secondary_btn.configure(
                text='Proof Ledger', command=lambda: self._navigate_to_tab(1))
        self.preview_receipt_btn = self.dashboard_preview_btn
        self._sync_global_actions(state, checked_n, scan_done)
        self._update_brand_identity()

    def _toggle_sidebar_collapsed(self):
        self._sidebar_collapsed = not self._sidebar_collapsed
        prefs = load_ui_prefs()
        prefs['sidebar_collapsed'] = self._sidebar_collapsed
        save_ui_prefs(prefs)
        self._apply_sidebar_collapsed()

    def _apply_sidebar_collapsed(self):
        collapsed = getattr(self, '_sidebar_collapsed', False)
        if hasattr(self, '_sidebar_identity'):
            self._sidebar_identity.grid() if not collapsed else self._sidebar_identity.grid_remove()
        if hasattr(self, '_sidebar_collapse_btn'):
            self._sidebar_collapse_btn.configure(text='»' if collapsed else '«')
        if hasattr(self, '_shell_pane'):
            try:
                if collapsed:
                    self._shell_pane.sashpos(0, 56)
                else:
                    saved = self._pane_pref('shell_sidebar', 248)
                    self._shell_pane.sashpos(0, int(saved or 248))
            except Exception:
                pass

    def _cancel_tray_watches(self):
        for jid in list(getattr(self, '_tray_watch_ids', []) or []):
            try:
                self.after_cancel(jid)
            except Exception:
                pass
        self._tray_watch_ids = []

    def _schedule_tray_health(self, seconds: int):
        jid = self.after(seconds * 1000, lambda s=seconds: self._watch_tray_health(s))
        self._tray_watch_ids.append(jid)

    def _init_tray(self, attempt: int = 0):
        if getattr(self, '_shutting_down', False):
            return
        from ui.tray import TrayController, get_active_tray

        existing = get_active_tray()
        if existing is not None and existing.check_health():
            self._tray = existing
            logger.info('Tray already active — reusing controller=%s', id(existing))
            return

        prior = getattr(self, '_tray', None)
        if prior is not None and prior is not existing:
            try:
                prior.stop()
            except Exception:
                logger.debug('Prior tray stop before re-init raised', exc_info=True)
            self._tray = None

        try:
            if self._tray is None:
                self._tray = TrayController(self)
            if not self._tray.start():
                err = self._tray.last_error or 'Tray icon could not start'
                diag = self._tray.diagnostics_text() if hasattr(self._tray, 'diagnostics_text') else err
                try:
                    self._tray.stop()
                except Exception:
                    pass
                self._tray = None
                if attempt < 2 and not getattr(self, '_shutting_down', False):
                    logger.warning('Tray start retry %s: %s', attempt + 1, err)
                    self.after(1500, lambda: self._init_tray(attempt + 1))
                    return
                self._show_tray_unavailable(diag)
                return
            logger.info('Tray icon active')
            self._schedule_tray_health(1)
            self._schedule_tray_health(3)
            self._schedule_tray_health(5)
        except Exception as exc:
            self._tray = None
            if attempt < 2 and not getattr(self, '_shutting_down', False):
                logger.warning('Tray init retry %s: %s', attempt + 1, exc)
                self.after(1500, lambda: self._init_tray(attempt + 1))
                return
            self._show_tray_unavailable(str(exc))
            logger.exception('Tray init failed')

    def _on_tray_thread_exit(self, tray):
        if getattr(self, '_shutting_down', False):
            return
        err = tray.diagnostics_text() if hasattr(tray, 'diagnostics_text') else tray.last_error
        logger.error('Tray thread exit surfaced to app: %s', err)
        self._tray = None
        self._show_tray_unavailable(err or 'Tray icon stopped unexpectedly.')

    def _watch_tray_health(self, seconds: int):
        if getattr(self, '_shutting_down', False):
            return
        tray = getattr(self, '_tray', None)
        if tray is None:
            return
        tray._log_diagnostics(f'health@{seconds}s')
        if tray.check_health():
            return
        err = tray.diagnostics_text()
        logger.error('Tray died within %ss: %s', seconds, err)
        try:
            tray.stop()
        except Exception:
            pass
        self._tray = None
        self._show_tray_unavailable(err)

    def _shutdown_app(self, *_args, reason: str = 'quit'):
        """Single shutdown path — tray menu Quit, window close, tests, theme prep."""
        if getattr(self, '_cleaner_loading', False):
            self.stop_scan()
            self._pending_shutdown = True
            return
        if getattr(self, '_shutting_down', False):
            return
        self._shutting_down = True
        logger.info('Cleanroom shutdown requested (%s)', reason)
        self._cancel_tray_watches()
        tray = getattr(self, '_tray', None)
        if tray is not None:
            try:
                tray.stop()
            except Exception:
                logger.exception('Tray stop during shutdown')
            self._tray = None
        from ui.tray import shutdown_all_trays
        shutdown_all_trays()
        global _APP_INSTANCE
        if _APP_INSTANCE is self:
            _APP_INSTANCE = None
        try:
            self.quit()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _on_window_close(self):
        if getattr(self, '_tray', None) and self._tray.check_health():
            self._shutdown_app(reason='window-close')
        else:
            self._shutdown_app(reason='window-close-no-tray')

    def _tray_show_window(self):
        self.deiconify()
        self.lift()
        try:
            self.focus_force()
        except Exception:
            pass

    def _tray_hide_window(self):
        tray = getattr(self, '_tray', None)
        if tray is not None and tray.check_health():
            self.withdraw()
        else:
            self._set_status('Tray unavailable — keeping main window visible.')

    def _tray_quit(self):
        self._shutdown_app(reason='tray-quit')

    def _fade_in_window(self, step=0, steps=12):
        try:
            self.attributes('-alpha', 0.0 if step == 0 else step / steps)
        except Exception:
            return
        if step < steps:
            self.after(24, lambda: self._fade_in_window(step + 1, steps))
        else:
            try:
                self.attributes('-alpha', 1.0)
            except Exception:
                pass

    def _pulse_proof_flow(self, step=0):
        if step >= 4 or not hasattr(self, 'ctx_next_lbl'):
            return
        colors = (ACCENT, TEXT, ACCENT, TEXT)
        try:
            self.ctx_next_lbl.configure(text_color=colors[step % len(colors)])
        except Exception:
            return
        self.after(120, lambda: self._pulse_proof_flow(step + 1))

    def _on_root_configure(self, event):
        if event.widget is not self:
            return
        if getattr(self, '_resize_job', None):
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(80, self._update_responsive_layout)

    def _update_responsive_layout(self):
        try:
            scale = float(self.tk.call('tk', 'scaling'))
        except Exception:
            scale = 1.0
        try:
            w = int(self.winfo_width() / scale)
            h = int(self.winfo_height() / scale)
        except Exception:
            return
        if w < 200:
            return
        mode = classify_layout(w, h, scale=scale)
        self._layout_mode = mode
        wrap = max(420, min(720, w - 300))
        if hasattr(self, 'ctx_desc_lbl') and self.ctx_desc_lbl is not None:
            self.ctx_desc_lbl.configure(wraplength=wrap)
        if hasattr(self, 'ctx_next_lbl'):
            self.ctx_next_lbl.configure(wraplength=max(280, min(720, w - 340)))
        if getattr(self, 'ctx_subtitle_lbl', None) is not None:
            if mode == 'compact':
                self.ctx_subtitle_lbl.pack_forget()
            else:
                self.ctx_subtitle_lbl.pack(side='left', padx=(8, 0))
        if hasattr(self, '_hdr_settings_btn'):
            self._hdr_settings_btn.configure(
                text='⚙' if w < 900 else '⚙ Settings',
                width=40 if w < 900 else 100,
            )
        if hasattr(self, '_proof_flow_lbl'):
            self._proof_flow_lbl.pack_forget()
        if hasattr(self, '_command_bar'):
            self._command_bar.set_compact_labels(w < 1000)
            try:
                tab_idx = self.tab_control.index('current')
            except Exception:
                tab_idx = 0
            self._command_bar.set_page_mode(
                dashboard=getattr(self, '_page_is_dashboard', tab_idx == 0),
                tab_idx=tab_idx,
            )
        tree_rows = max(5, min(12, (h - 420) // 28))
        if hasattr(self, 'cleanup_tree'):
            self.cleanup_tree.column('#0', width=max(160, min(520, w - 380)))
        if hasattr(self, 'archive_tree'):
            self.archive_tree.configure(height=tree_rows)
        detail_w = max(200, min(420, int(w * 0.30)))
        detail_wrap = max(180, detail_w - 28)
        for attr in (
            '_act_detail_src', '_act_detail_dest', '_act_detail_hint',
            '_act_detail_type', '_act_detail_when', '_act_detail_custody',
            'detail_name', 'detail_location', 'detail_hint', 'detail_status',
            '_archive_detail_src', '_archive_detail_dest',
            '_archive_detail_meta', '_archive_detail_rank',
            'restore_detail_src', 'restore_detail_dest',
        ):
            if hasattr(self, attr):
                getattr(self, attr).configure(wraplength=detail_wrap)
        if hasattr(self, 'detail_command_text'):
            cmd_h = 3 if h < 640 else 4 if h < 760 else 5
            try:
                self.detail_command_text.configure(height=cmd_h)
            except Exception:
                pass
        if hasattr(self, '_startup_stats_row'):
            if mode == 'compact' or w < 980:
                try:
                    self._startup_stats_row.pack_forget()
                except Exception:
                    pass
            elif not self._startup_stats_row.winfo_ismapped():
                try:
                    self._startup_stats_row.pack(fill='x', padx=10, pady=(0, 8))
                except Exception:
                    pass
        if hasattr(self, 'search_entry'):
            sw = 14 if w < 920 else 20 if w < 1100 else 28
            try:
                self.search_entry.configure(width=sw)
            except Exception:
                pass
        if hasattr(self, 'disable_btn') and hasattr(self, '_startup_actions'):
            try:
                if w < 920:
                    self.disable_btn.pack(side='top', anchor='w', padx=0, pady=(4, 0))
                else:
                    self.disable_btn.pack(side='left', padx=(6, 0))
            except Exception:
                pass
        if hasattr(self, '_proof_summary') and hasattr(self._proof_summary, '_title_lbl'):
            pw = max(180, min(320, detail_w))
            self._proof_summary._title_lbl.configure(wraplength=pw)
            self._proof_summary._summary_lbl.configure(wraplength=pw)
        if hasattr(self, '_archive_subheader'):
            self._archive_subheader.configure(wraplength=max(320, w - 180))
        if hasattr(self, '_uninst_quiet_cb'):
            compact_uninst = w < 980
            if compact_uninst:
                self._uninst_quiet_cb.pack_forget()
                self.uninst_leftover_btn.pack_forget()
            else:
                self._uninst_quiet_cb.pack(side='left', padx=6)
                self.uninst_leftover_btn.pack(side='right')
            if w < 920:
                self.uninst_force_btn.pack_forget()
            else:
                self.uninst_force_btn.pack(side='right', padx=6)
            self.uninst_uninstall_btn.pack(side='right', padx=6)
        if hasattr(self, '_activity_top') and hasattr(self, 'act_refresh_btn'):
            try:
                scale = float(self.tk.call('tk', 'scaling'))
            except Exception:
                scale = 1.0
            if h < 680 or scale >= 1.45:
                self._activity_top.grid_remove()
            else:
                self._activity_top.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 6))
        wrap = max(420, w - 340)
        for attr in ('uninst_detail_what', 'uninst_detail_does',
                     'uninst_detail_need', 'uninst_detail_uninst'):
            if hasattr(self, attr):
                getattr(self, attr).configure(wraplength=wrap)

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _init_style(self):
        self.power_user = bool(load_ui_prefs().get('power_user'))
        self.style = ttk.Style(self)
        try:
            self.style.theme_use('clam')
        except Exception:
            pass
        s = self.style
        s.configure('.', background=BG, foreground=TEXT, font=('Segoe UI', 10))
        s.configure('Sidebar.TFrame', background=SIDEBAR_BG)
        s.configure('Content.TFrame', background=BG)
        s.configure('Card.TFrame', background=CARD_BG, relief='flat')
        s.configure('Search.TEntry', font=('Segoe UI', 10), padding=6,
                    fieldbackground=CARD_BG, foreground=TEXT, insertcolor=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        s.map('Search.TEntry', fieldbackground=[('focus', CARD_BG)])
        s.configure('TEntry', fieldbackground=CARD_BG, foreground=TEXT, insertcolor=TEXT)
        s.configure('TSpinbox', fieldbackground=CARD_BG, foreground=TEXT, insertcolor=TEXT,
                    background=HEAD_BG, bordercolor=BORDER, arrowcolor=TEXT)
        s.configure('TCombobox', fieldbackground=CARD_BG, foreground=TEXT,
                    background=HEAD_BG, bordercolor=BORDER, arrowcolor=TEXT)
        s.map('TCombobox', fieldbackground=[('readonly', CARD_BG)])
        s.configure('TScrollbar', background=HEAD_BG, troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED)
        s.map('TScrollbar', background=[('active', BORDER)])
        s.configure('TButton', background=HEAD_BG, foreground=TEXT, bordercolor=BORDER)
        s.configure('Sidebar.TButton', font=('Segoe UI', 10), padding=(10, 8), anchor='w',
                    background=SIDEBAR_BG, foreground=TEXT, borderwidth=0)
        s.map('Sidebar.TButton', background=[('active', ACCENT_SOFT)])
        s.configure('Sidebar.Selected.TButton', font=('Segoe UI', 10, 'bold'), padding=(10, 8),
                    anchor='w', background=ACCENT_SOFT, foreground=ACCENT, borderwidth=0)
        s.map('Sidebar.Selected.TButton', background=[('active', ACCENT_SOFT)])
        s.configure('Action.TButton', font=('Segoe UI', 10), padding=(10, 6),
                    background=HEAD_BG, foreground=TEXT, bordercolor=BORDER)
        s.map('Action.TButton',
              background=[('active', ACCENT_SOFT), ('disabled', BG)],
              foreground=[('disabled', MUTED)])
        s.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'), padding=(12, 6),
                    background=PROOF, foreground=ON_ACCENT, bordercolor=PROOF_DARK)
        s.map('Primary.TButton',
              background=[('active', PROOF_DARK), ('disabled', PROOF_SOFT)],
              foreground=[('disabled', MUTED)])
        s.configure('Header.TLabel', font=('Segoe UI', 15, 'bold'), background=BG)
        s.configure('SubHeader.TLabel', font=('Segoe UI', 10), background=BG, foreground=MUTED)
        s.configure('Info.TLabel', font=('Segoe UI', 10), background=BG)
        s.configure('CardInfo.TLabel', font=('Segoe UI', 10), background=CARD_BG)
        s.configure('Detail.TLabelframe', background=CARD_BG, bordercolor=BORDER, borderwidth=0)
        s.configure('Detail.TLabelframe.Label', font=('Segoe UI', 10, 'bold'),
                    background=CARD_BG, foreground=TEXT)
        s.configure('Treeview.Heading', font=('Segoe UI Semibold', 10), background=HEAD_BG,
                    foreground=TEXT, relief='flat')
        s.map('Treeview.Heading', background=[('active', ACCENT_SOFT)])
        row_h, tree_font = (26, ('Segoe UI', 9)) if self.power_user else (32, ('Segoe UI', 10))
        s.configure('Treeview', font=tree_font, rowheight=row_h + 8, background=CARD_BG,
                    foreground=TEXT, fieldbackground=CARD_BG, borderwidth=0)
        s.map('Treeview',
              background=[('selected', ACCENT_SOFT)],
              foreground=[('selected', TEXT)])
        badge_fg = ACCENT_DARK if CURRENT_THEME == 'light' else ACCENT
        s.configure('Badge.TLabel', font=('Segoe UI', 10, 'bold'), background=ACCENT_SOFT,
                    foreground=badge_fg, padding=(8, 4))
        s.configure('Status.TLabel', font=('Segoe UI', 9), background=STATUS_BG, foreground=TEXT, padding=(8, 4))
        s.configure('TNotebook', background=BG, borderwidth=0)
        s.configure('TPanedwindow', background=BORDER)
        try:
            s.configure(
                'Sash', sashthickness=6, sashpad=2,
                background=ACCENT, lightchild=BORDER, darkchild=BORDER,
            )
        except Exception:
            pass
        s.configure('TCheckbutton', background=BG, foreground=TEXT)
        s.map('TCheckbutton', background=[('active', BG)])
        self._hide_notebook_tabs()

    def _hide_notebook_tabs(self):
        """Sidebar is primary nav — remove duplicate notebook tab strip."""
        try:
            s = self.style
            s.layout('TNotebook.Tab', [])
            s.layout('TNotebook', [('Notebook.client', {'sticky': 'nswe'})])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------
    def create_widgets(self):
        self._body_center = tk.Frame(self, bg=BG)
        self._body_center.pack(fill='both', expand=True)

        shell = self._body_center
        self._build_header(shell)
        main = ttk.Frame(shell)
        main.pack(fill='both', expand=True, padx=8, pady=(0, 0))
        self._shell_pane = ttk.PanedWindow(main, orient='horizontal')
        self._shell_pane.pack(fill='both', expand=True, pady=(0, 6))
        sidebar_host = ttk.Frame(self._shell_pane)
        content_host = ttk.Frame(self._shell_pane)
        self._shell_pane.add(sidebar_host, weight=0)
        self._shell_pane.add(content_host, weight=1)
        self._build_sidebar(sidebar_host)

        self.tab_control = ttk.Notebook(content_host)
        self.tab_control.pack(fill='both', expand=True)

        self.optimizer_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.activity_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.startup_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.cleanup_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.uninstall_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.restore_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.archive_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.settings_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.tab_control.add(self.optimizer_tab, text='  🏠 Home  ')
        self.tab_control.add(self.activity_tab, text='  📋 Activity  ')
        self.tab_control.add(self.startup_tab, text='  🚀 Startup  ')
        self.tab_control.add(self.cleanup_tab, text='  🧹 Cleaner  ')
        self.tab_control.add(self.uninstall_tab, text='  🗑 Uninstaller  ')
        self.tab_control.add(self.restore_tab, text='  ↩ Restore  ')
        self.tab_control.add(self.archive_tab, text='  🗂️ Archive  ')
        self.tab_control.add(self.settings_tab, text='  ⚙ Settings  ')

        self._build_optimizer_tab()
        self._build_activity_tab()
        self._build_startup_tab()
        self._build_cleaner_tab()
        self._build_uninstaller_tab()
        self._build_restore_tab()
        self._build_archive_tab()
        self._build_settings_tab()
        self._build_statusbar()
        self._hide_notebook_tabs()
        self.tab_control.bind('<<NotebookTabChanged>>', self._sync_nav_buttons)
        self._sync_nav_buttons()
        self._update_context_panel()
        self.after(50, self._update_responsive_layout)

    def _load_logo(self, px=36):
        """Load app icon scaled to roughly px pixels; None if unavailable."""
        try:
            path = None
            for name in ('cleanroom-icon.png', 'icon.png'):
                candidate = _resource_path(name)
                if candidate.exists():
                    path = candidate
                    break
            if path is None and brand.ICON_PNG_PATH.exists():
                path = brand.ICON_PNG_PATH
            if path is None:
                return None
            if PILImage:
                with PILImage.open(path) as img:
                    img = img.convert('RGBA')
                    img.thumbnail((px, px), PILImage.LANCZOS)
                    return PILImageTk.PhotoImage(img, master=self)
            photo = tk.PhotoImage(file=str(path), master=self)
            factor = max(1, photo.width() // px)
            return photo.subsample(factor, factor)
        except Exception:
            return None

    def _load_logo_ctk(self, px=96):
        """CTkImage for CustomTkinter widgets — avoids CTkImage/PIL warnings."""
        try:
            path = None
            for name in ('cleanroom-icon.png', 'icon.png'):
                candidate = _resource_path(name)
                if candidate.exists():
                    path = candidate
                    break
            if path is None and brand.ICON_PNG_PATH.exists():
                path = brand.ICON_PNG_PATH
            if path is None or not PILImage:
                return None
            with PILImage.open(path) as img:
                img = img.convert('RGBA')
                img.thumbnail((px, px), PILImage.LANCZOS)
                w, h = img.size
                return ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
        except Exception:
            return None

    def _dialog_colors(self):
        return dict(
            bg=BG, card=CARD_BG, head=HEAD_BG, accent=ACCENT,
            accent_soft=ACCENT_SOFT, text=TEXT, muted=MUTED,
            border=BORDER, on_accent=ON_ACCENT, danger='#ef4444',
        )

    def _show_row_popover(self, x, y, items, *, title: str = ''):
        """Unified dark row action menu."""
        show_action_popover(self, x, y, items, colors=self._dialog_colors(), title=title)

    def _build_header(self, parent=None):
        host = parent or self
        top = ctk_theme.frame(host, BG)
        top.pack(fill='x', padx=8, pady=(4, 2))
        self._hdr_top = top

        self._command_bar = CommandBar(
            top,
            bg=BG,
            card_bg=CARD_BG,
            head_bg=HEAD_BG,
            accent=ACCENT,
            accent_dark=ACCENT_DARK,
            accent_soft=ACCENT_SOFT,
            proof=PROOF,
            proof_dark=PROOF_DARK,
            text=TEXT,
            on_accent=ON_ACCENT,
            on_scan=self.refresh_cleanup,
            on_preview=self.preview_cleanup_receipt,
            on_apply=self.apply_cleanup,
            on_restore=lambda: (self.tab_control.select(5), self.refresh_restore()),
            more_groups=(
                ('Receipts', (
                    ('Latest Receipt', self.open_last_receipt),
                    ('Receipt Viewer', self.open_last_receipt),
                    ('Proof Pack', self.export_audit),
                )),
                ('Custody', (
                    ('Verify Custody', self.verify_custody),
                    ('Open Archive Folder', self.open_archive_folder),
                    ('Custody Check', self.verify_custody),
                )),
                ('Tools', (
                    ('Explorer Context Menus', self.open_shell_context_menu_tool),
                    ('Registry Snapshot', self.open_registry_health),
                    ('Cleanroom Rewind', self.open_time_machine),
                    ('Schedule Cleanup', self.schedule_optimization),
                )),
                ('Diagnostics', (
                    ('Local Logs', self._show_diagnostics_dialog),
                    ('App Diagnostics', self._show_diagnostics_dialog),
                )),
            ),
        )
        self._hdr_toolbar = self._command_bar.frame
        self.tb_scan = self._command_bar.tb_scan
        self.tb_preview = self._command_bar.tb_preview
        self.tb_apply = self._command_bar.tb_apply
        self.tb_restore = self._command_bar.tb_restore
        self._proof_flow_lbl = self._command_bar._proof_flow_lbl
        self._command_bar.set_page_mode(dashboard=True)

        self._hdr_summary = ctk_theme.frame(top, BG)
        self._hdr_badges = None
        self._hdr_hero = None

        header_logo = self._load_logo(22)
        if header_logo is not None:
            self._header_logo = header_logo
        shell_parts = app_shell_header(
            top,
            bg=BG,
            bar_bg=HEAD_BG,
            text=TEXT,
            muted=MUTED,
            proof=PROOF,
            proof_soft=PROOF_SOFT,
            head_bg=HEAD_BG,
            logo_photo=getattr(self, '_header_logo', None),
            on_why=self._show_custody_trust_why,
            on_settings=self._open_settings,
            on_more=self._show_more_menu,
        )
        self._hdr_shell = shell_parts['frame']
        self._hdr_compact = shell_parts['custody_frame']
        self.hdr_trust_value = shell_parts['trust_value']
        self.hdr_trust_lbl = shell_parts['trust_caption']
        self.hdr_trust_why = shell_parts['why_btn']
        self._archive_badge = shell_parts['archive_badge']
        self._hdr_settings_btn = shell_parts['settings_btn']
        self._hdr_more_btn = shell_parts['more_btn']

        self._archive_banner = ctk_theme.frame(top, PROOF_SOFT, corner_radius=8)
        ctk_theme.label(
            self._archive_banner, ctk_theme.ARCHIVE_BANNER_TEXT,
            text_color=PROOF, font_size=9, weight='bold',
        ).pack(anchor='w', padx=12, pady=6)
        self._archive_banner.pack_forget()
        self._archive_banner_collapsed = True

        self._add_tooltip(self.hdr_trust_value,
                          'Custody trust — % of archived artifacts verified on disk right now.')
        nxt = THEME_ORDER[(THEME_ORDER.index(CURRENT_THEME) + 1) % len(THEME_ORDER)]
        self._add_tooltip(self._hdr_settings_btn, 'Open Settings (Ctrl+,)')
        self._add_tooltip(self._hdr_more_btn,
                          f'More tools — theme ({PALETTES[CURRENT_THEME]["LABEL"]} → '
                          f'{PALETTES[nxt]["LABEL"]}), receipts, proof pack, schedule.')
        self._add_tooltip(self.tb_scan, 'Scan configured folders for cleanup candidates. (F5 refreshes everything)')
        self._add_tooltip(self.tb_preview, 'Preview what the Cleanroom Receipt will say before you archive anything.')
        self._add_tooltip(self.tb_apply, 'Move checked items to the archive — nothing is permanently deleted.')
        self._add_tooltip(self.tb_restore, 'Open Restore tab and reload archived entries.')

    def _open_settings(self):
        """Global Settings — header chrome, not sidebar workflow."""
        self.tab_control.select(7)
        self._sync_nav_buttons()

    def _show_more_menu(self):
        if hasattr(self, '_command_bar'):
            anchor = getattr(self, '_hdr_more_btn', None)
            if anchor is not None:
                self._command_bar.show_more_at(anchor)
            else:
                self._command_bar._show_more()

    def _update_cleanup_empty_state(self):
        if not hasattr(self, '_cleanup_empty_panel'):
            return
        sync_split_workspace(
            loading=getattr(self, '_cleaner_loading', False),
            has_rows=bool(self.cleanup_items),
            pane=getattr(self, '_cleanup_pane', None),
            empty_panel=self._cleanup_empty_panel,
            loading_panel=getattr(self, '_cleanup_loading_panel', None),
        )
        empty = not self.cleanup_items and not getattr(self, '_cleaner_loading', False)
        loading = getattr(self, '_cleaner_loading', False)
        if hasattr(self, '_cleanup_chips'):
            if empty or loading:
                self._cleanup_chips.grid_remove()
                self._cleanup_tools.grid_remove()
            else:
                self._cleanup_chips.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 6))
                self._cleanup_tools.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 4))

    def _build_context_bar(self, parent=None):
        """Workspace module header — title, purpose, and next action."""
        host = parent or self
        bar = ctk_theme.frame(host, CARD_BG, corner_radius=10)
        bar.pack(fill='x', padx=14, pady=(0, 8))
        self._context_bar = bar
        inner = ctk_theme.frame(bar, CARD_BG)
        inner.pack(fill='x', padx=14, pady=10)
        title_row = ctk_theme.frame(inner, CARD_BG)
        title_row.pack(fill='x')
        self.ctx_page_lbl = ctk_theme.label(
            title_row, 'Workspace', text_color=TEXT, font_size=13, weight='bold')
        self.ctx_page_lbl.pack(side='left')
        self.ctx_purpose_lbl = ctk_theme.label(
            title_row, '', text_color=MUTED, font_size=10)
        self.ctx_purpose_lbl.pack(side='left', padx=(10, 0))
        self.ctx_next_lbl = ctk_theme.label(
            inner, '', text_color=TEXT, font_size=10, wraplength=720, justify='left')
        self.ctx_next_lbl.pack(anchor='w', pady=(6, 0))
        self.ctx_title_lbl = None
        self.ctx_subtitle_lbl = None
        self.ctx_desc_lbl = None

    def _update_context_panel(self):
        if not hasattr(self, 'ctx_page_lbl'):
            try:
                tab_idx = self.tab_control.index('current')
            except Exception:
                tab_idx = 0
            if hasattr(self, '_command_bar'):
                self._command_bar.set_context(tab_idx)
            self._update_brand_identity(tab_idx)
            return
        try:
            tab_idx = self.tab_control.index('current')
        except Exception:
            tab_idx = 0
        ctx = (ctk_theme.TAB_CONTEXT[tab_idx] if tab_idx < len(ctk_theme.TAB_CONTEXT)
               else ctk_theme.TAB_CONTEXT[0])
        page_titles = (
            'Home', 'Proof Ledger', 'Startup Manager', 'Cleaner',
            'Uninstaller', 'Restore', 'Archive Custody', 'Control Room',
        )
        page_title = page_titles[tab_idx] if tab_idx < len(page_titles) else ctx['title']
        subtitle = ctx['description']
        nxt = ctx['next']

        if tab_idx == 2:
            cat = getattr(self, 'current_category', 'All')
            sub = ctk_theme.STARTUP_FILTER_CONTEXT.get(cat)
            if sub:
                subtitle = sub[1]
                nxt = sub[2]
            visible = len(self.tree.get_children()) if hasattr(self, 'tree') else 0
            subtitle = f'{subtitle} · {visible} shown' if subtitle else f'{visible} items shown'
            ent = self._selected_entry() if hasattr(self, 'tree') else None
            if ent and ent.get('name'):
                src = ent.get('source') or 'unknown'
                nxt = (f'Selected: {ent["name"]} ({src}) — '
                       'use Enable/Disable below or copy the command.')
        elif tab_idx == 3:
            count = len(getattr(self, 'cleanup_items', []) or [])
            checked = len(getattr(self, 'cleanup_selected', set()) or set())
            if self._cleaner_loading:
                subtitle = 'Scanning configured folders…'
                nxt = 'Wait for scan to finish before previewing or archiving.'
            elif count == 0 and getattr(self, '_scan_session_done', False):
                subtitle = 'Scan complete — no candidates found'
                nxt = 'Try Settings → Relaxed scan, then Scan Now.'
            elif count == 0:
                subtitle = 'Ready to scan'
                nxt = 'Run Scan Now to review configured folders.'
            else:
                subtitle = f'{count} candidates · {checked} checked'
                nxt = f'{checked} item(s) ready — Preview Receipt, then Archive & Clean.'
        elif tab_idx == 4:
            entry = self._selected_program() if hasattr(self, 'uninstall_tree') else None
            if entry and program_advice:
                advice = program_advice.analyze_program(entry)
                subtitle = advice['category'].replace('_', ' ')
                nxt = advice['need']
            else:
                nxt = 'Select a program — read the summary panel, then Uninstall or Force Remove.'
        elif tab_idx == 6:
            stats = getattr(self, '_archive_stats', {}) or {}
            sel = len(self.archive_tree.selection()) if hasattr(self, 'archive_tree') else 0
            subtitle = (f'{stats.get("total", 0)} in custody · '
                          f'{stats.get("safe_count", 0)} safe to delete · '
                          f'{sel} selected')
            if stats.get('safe_count', 0):
                nxt = (f'{stats["safe_count"]} item(s) marked Safe to delete — '
                       'use Select All Safe, then Delete from Archive.')
            else:
                nxt = 'Select rows or use Delete Older Than… to reclaim archive disk space.'
        elif tab_idx == 0:
            count = len(getattr(self, 'cleanup_items', []) or [])
            if count:
                subtitle = f'{count} cleanup candidate(s) awaiting review'

        self.ctx_page_lbl.configure(text=page_title)
        self.ctx_purpose_lbl.configure(text=subtitle)
        self.ctx_next_lbl.configure(text=nxt)
        if hasattr(self, '_command_bar'):
            self._command_bar.set_context(tab_idx)
        self._update_brand_identity(tab_idx)

    def _mark_settings_dirty(self, *_args):
        self._settings_dirty = True
        self._update_brand_identity()

    def _compute_brand_state(self, tab_idx=None):
        """Page-aware title, live status line, and custody pill for the brand block."""
        if tab_idx is None:
            try:
                tab_idx = self.tab_control.index('current')
            except Exception:
                tab_idx = 0

        entries = self._load_log_dicts()
        custody = {'verified': 0, 'total': 0, 'missing': 0, 'bytes_in_custody': 0}
        if proof_module and entries:
            try:
                custody = proof_module.verify_entries(entries)
            except Exception:
                pass
        trust = None
        if ledger_module and custody.get('total'):
            trust = ledger_module.trust_score(custody['verified'], custody['total'])

        pill = brand.APP_LOCKUP_PILL
        pill_fg = ACCENT_SOFT
        pill_text = ACCENT
        if trust is not None:
            pill = f'Custody {trust}% verified'
        if custody.get('missing', 0):
            pill = f'{custody["missing"]} custody gap(s)'
            pill_fg = SEVERITY_COLORS.get('high', ACCENT)
            pill_text = ON_ACCENT

        show_tagline = False
        title_accent = False

        count = len(getattr(self, 'cleanup_items', []) or [])
        checked = len(getattr(self, 'cleanup_selected', set()) or set())
        phase = getattr(self, '_brand_phase', None)
        scan_prog = getattr(self, '_scan_progress', None) or {}

        if self._cleaner_loading:
            files = int(scan_prog.get('files_checked', 0) or 0)
            cands = int(scan_prog.get('candidates_found', 0) or 0)
            scan_status = f'Scanning · {files:,} checked'
            if cands:
                scan_status += f' · {cands} candidate(s)'
        elif getattr(self, '_scan_stopped', False):
            scan_status = 'Scan stopped'
        else:
            scan_status = ''

        if tab_idx == 0:
            title = brand.APP_DISPLAY
            show_tagline = True
            title_accent = True
            if scan_status:
                status = scan_status
            elif count and checked:
                status = 'Receipt ready · archive-first cleanup unlocked'
            elif count:
                status = (f'{count:,} candidates found · '
                          'receipt required before cleanup')
            elif phase == 'archived':
                status = 'Cleanup archived · proof saved'
            elif custody.get('missing', 0):
                status = 'Custody needs review'
            elif getattr(self, '_scan_session_done', False):
                status = 'Scan complete · no candidates pending'
            else:
                status = ''
        elif tab_idx == 1:
            title = 'Proof Ledger'
            act_txt = ''
            if hasattr(self, 'act_status_lbl'):
                try:
                    act_txt = self.act_status_lbl.cget('text') or ''
                except Exception:
                    pass
            if 'Loading' in act_txt:
                status = 'Loading activity ledger…'
            elif custody.get('total'):
                status = f'Every action has a receipt · {custody["total"]:,} logged'
            else:
                status = 'Every action has a receipt'
        elif tab_idx == 2:
            title = 'Startup Manager'
            visible = len(self.tree.get_children()) if hasattr(self, 'tree') else 0
            status = (f'{visible} startup entries loaded'
                      if visible else 'Programs that launch with Windows')
        elif tab_idx == 3:
            title = 'Cleaner'
            if scan_status:
                status = scan_status
            elif count:
                status = f'{count:,} candidates · {checked} checked for archive'
            elif getattr(self, '_scan_session_done', False):
                status = 'Scan complete — no candidates found'
            else:
                status = 'Ready to scan'
        elif tab_idx == 4:
            title = 'Uninstaller'
            n = len(self.uninstall_tree.get_children()) if hasattr(self, 'uninstall_tree') else 0
            status = f'{n} installed programs loaded' if n else 'Select a program to review leftovers'
        elif tab_idx == 5:
            title = 'Restore'
            n = len(self.restore_tree.get_children()) if hasattr(self, 'restore_tree') else 0
            status = f'{n} restorable entries' if n else 'Roll back archived files safely'
        elif tab_idx == 6:
            title = 'Archive Custody'
            stats = getattr(self, '_archive_stats', {}) or {}
            total = stats.get('total', 0)
            sel = len(self.archive_tree.selection()) if hasattr(self, 'archive_tree') else 0
            busy = getattr(self, '_archive_busy', False)
            if busy:
                status = 'Loading archive custody…'
            elif trust is not None and total:
                status = f'{total:,} archived · {trust}% verified · {sel} selected'
            elif total:
                status = f'{total:,} archived · {sel} selected'
            else:
                status = 'Browse archived copies before deleting custody'
        elif tab_idx == 7:
            title = 'Settings'
            if getattr(self, '_settings_dirty', False):
                status = 'Unsaved changes — Save Settings to apply'
                pill = 'Unsaved'
                pill_fg = SEVERITY_COLORS.get('medium', ACCENT_SOFT)
                pill_text = TEXT
            else:
                status = 'Local-only settings and proof rules'
        else:
            title = brand.APP_DISPLAY
            status = ''

        return {
            'title': title,
            'status': status,
            'tagline': brand.APP_LOCKUP_TAGLINE if show_tagline else '',
            'show_tagline': show_tagline,
            'title_accent': title_accent,
            'pill': pill,
            'pill_fg': pill_fg,
            'pill_text': pill_text,
        }

    def _update_brand_identity(self, tab_idx=None):
        """Refresh tray tooltip from app state — page identity lives in content, not chrome."""
        self._refresh_tray_tooltip()
        self._refresh_tray_menu()

    def _navigate_to_tab(self, idx):
        self.tab_control.select(idx)
        self._sync_nav_buttons()

    def set_theme(self, name):
        if name not in PALETTES:
            return
        prefs = load_ui_prefs()
        prefs['theme'] = name
        save_ui_prefs(prefs)
        apply_palette(name)
        self._cancel_tray_watches()
        tray = getattr(self, '_tray', None)
        if tray is not None:
            try:
                tray.stop()
            except Exception:
                logger.debug('Tray stop before theme restart raised', exc_info=True)
            self._tray = None
        from ui.tray import shutdown_all_trays
        shutdown_all_trays()
        self.wants_restart = True
        self._shutting_down = True
        self.destroy()

    def cycle_theme(self):
        nxt = THEME_ORDER[(THEME_ORDER.index(CURRENT_THEME) + 1) % len(THEME_ORDER)]
        self.set_theme(nxt)

    def _build_sidebar(self, parent):
        sidebar = ctk_theme.frame(parent, SIDEBAR_BG, corner_radius=10)
        sidebar.pack(fill='both', expand=True)
        sidebar.grid_rowconfigure(0, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        nav_scroll = ctk.CTkScrollableFrame(
            sidebar, fg_color=SIDEBAR_BG, corner_radius=0, width=214,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=HEAD_BG,
        )
        nav_scroll.grid(row=0, column=0, sticky='nsew', padx=4, pady=(4, 2))
        self._sidebar_nav_scroll = nav_scroll
        self._nav_buttons = []
        nav_kw = dict(
            sidebar_bg=SIDEBAR_BG, accent_soft=ACCENT_SOFT, text_color=TEXT,
            hover_color=HEAD_BG, accent=ACCENT, on_accent=ON_ACCENT,
        )
        section_kw = dict(sidebar_bg=SIDEBAR_BG, muted=MUTED, text_color=TEXT, hover_bg=HEAD_BG)

        _, main_body = collapsible_section(
            nav_scroll, 'Main', start_open=True, **section_kw,
        )
        for idx, label, tip in (
            (0, 'Home', 'Proof home — custody status and next archive-first action.'),
            (3, 'Cleaner', 'Scan folders and archive reviewed files to custody.'),
            (6, 'Archive', 'Archive custody — browse, delete, reclaim disk space.'),
            (1, 'Proof Ledger', 'Every action has a receipt — verify custody and restore.'),
        ):
            btn = sidebar_nav_button(
                main_body, label, lambda i=idx: self._navigate_to_tab(i), **nav_kw)
            btn.pack(fill='x', pady=2, padx=6)
            self._nav_buttons.append((idx, btn))
            self._add_tooltip(btn, tip)

        sys_toggle, sys_body = collapsible_section(
            nav_scroll, 'System', start_open=False, **section_kw,
        )
        self._sidebar_sys_toggle = sys_toggle
        self._sidebar_sys_body = sys_body
        for idx, label, tip in (
            (2, 'Startup', 'Startup programs — filter by source, enable or disable.'),
            (4, 'Uninstaller', 'Uninstall programs and archive leftovers.'),
            (5, 'Restore', 'Restore archived files from the cleanup log.'),
        ):
            btn = sidebar_nav_button(
                sys_body, label, lambda i=idx: self._navigate_to_tab(i), **nav_kw)
            btn.pack(fill='x', pady=2, padx=6)
            self._nav_buttons.append((idx, btn))
            self._add_tooltip(btn, tip)

        tools_toggle, tools_body = collapsible_section(
            nav_scroll, 'Tools', start_open=False, **section_kw,
        )
        self._sidebar_tools_toggle = tools_toggle
        self._sidebar_tools_body = tools_body
        tools = [
            ('Explorer Menus', self.open_shell_context_menu_tool,
             'Build and install Windows Explorer right-click menus (HKCU, per-user).\n'
             'Add presets or custom menus, then Install to Explorer.'),
            ('Registry Snapshot', self.open_registry_health,
             'Find registry entries pointing at missing files.'),
            ('Rewind', self.open_time_machine,
             'Roll back whole days of Cleanroom actions.'),
            ('Receipt', self.open_last_receipt,
             'Open the most recent Cleanroom receipt from disk.'),
            ('Proof Pack', self.export_audit,
             'Generate a shareable HTML proof report.'),
            ('Custody Check', self.verify_custody,
             'Audit history — prove archived items are still on disk.'),
            ('Lights Out', self._open_lights_out,
             'Separate companion app — opens release page after confirmation (no auto-install).'),
        ]
        for i, (label, cmd, tip) in enumerate(tools):
            btn = sidebar_nav_button(tools_body, label, cmd, **nav_kw)
            btn.pack(fill='x', pady=2, padx=6)
            if i == 0:
                self._sidebar_explorer_btn = btn
            self._add_tooltip(btn, tip)

        footer = ctk_theme.frame(sidebar, SIDEBAR_BG)
        footer.grid(row=1, column=0, sticky='ew', padx=10, pady=(4, 10))
        foot_row = ctk_theme.frame(footer, SIDEBAR_BG)
        foot_row.pack(fill='x')
        self._sidebar_collapse_btn = ctk_theme.button(
            foot_row, '«', self._toggle_sidebar_collapsed,
            fg_color=HEAD_BG, hover_color=ACCENT_SOFT, text_color=TEXT,
            width=28, height=22,
        )
        self._sidebar_collapse_btn.pack(side='right')
        ctk_theme.label(foot_row, 'F5 · Ctrl+F · Ctrl+,',
                        text_color=MUTED, font_size=9).pack(side='left', anchor='w')

    def _sync_sidebar_sections(self, tab_idx: int):
        """Expand System when a system tab is active."""
        try:
            if tab_idx in (2, 4, 5) and hasattr(self, '_sidebar_sys_body'):
                if not self._sidebar_sys_body.winfo_ismapped() and self._sidebar_sys_toggle:
                    self._sidebar_sys_toggle.invoke()
        except Exception:
            pass

    def _expand_sidebar_tools(self):
        """Expand Tools group so advanced utilities are reachable (layout gates, deep links)."""
        btn = getattr(self, '_sidebar_tools_toggle', None)
        body = getattr(self, '_sidebar_tools_body', None)
        if btn is None or body is None:
            return
        try:
            if not body.winfo_ismapped():
                btn.invoke()
                self.update_idletasks()
        except Exception:
            pass

    def _sync_nav_buttons(self, event=None):
        try:
            current = self.tab_control.index('current')
        except Exception:
            current = 0
        for i, btn in self._nav_buttons:
            if i == current:
                btn.configure(
                    fg_color=ACCENT, text_color=ON_ACCENT, hover_color=ACCENT,
                    font=ctk_theme.font(ctk_theme.TYPE_BODY, 'bold'),
                )
            else:
                btn.configure(
                    fg_color='transparent', text_color=TEXT, hover_color=HEAD_BG,
                    font=ctk_theme.font(ctk_theme.TYPE_BODY, 'normal'),
                )
        prefs = load_ui_prefs()
        prefs['last_tab'] = current
        save_ui_prefs(prefs)
        self._update_context_panel()
        self._update_page_chrome(current)
        if current == 3 and hasattr(self, '_sync_cleaner_state'):
            self._sync_cleaner_state()
        if current == 1 and hasattr(self, '_activity_pane'):
            self.after(80, lambda: self._ensure_pane(
                self._activity_pane, 'activity_split', default=520,
                min_left=340, min_right=260, default_ratio=0.68))
        pane_tabs = (
            (2, '_startup_pane', 'startup_split', 480),
            (3, '_cleanup_pane', 'cleaner_split', 520),
            (4, '_uninst_pane', 'uninstaller_split', 520),
            (5, '_restore_pane', 'restore_split', 520),
            (6, '_archive_pane', 'archive_split', 520),
        )
        for tab_idx, attr, key, default in pane_tabs:
            if current == tab_idx and hasattr(self, attr):
                pane = getattr(self, attr)
                self.after(80, lambda p=pane, k=key, d=default: self._ensure_pane(
                    p, k, default=d, min_left=340, min_right=260, default_ratio=0.62))
        self._sync_sidebar_sections(current)
        self._lazy_load_tab(current)
        if hasattr(self, '_archive_badge'):
            try:
                if current in (0, 3):
                    self._archive_badge.pack(side='left', padx=(8, 0))
                else:
                    self._archive_badge.pack_forget()
            except Exception:
                pass

    def _collapse_archive_banner(self):
        self._archive_banner_collapsed = True
        prefs = load_ui_prefs()
        prefs['archive_banner_collapsed'] = True
        save_ui_prefs(prefs)
        self._update_page_chrome()

    def _set_activity_loading(self, loading: bool):
        self._sync_activity_view(loading=loading)
        if not loading and hasattr(self, '_activity_pane'):
            self._ensure_pane(
                self._activity_pane, 'activity_split', default=520,
                min_left=340, min_right=260, default_ratio=0.68)

    def _update_page_chrome(self, tab_idx=None):
        """Single app shell header — no stacked context/archive banners."""
        if tab_idx is None:
            try:
                tab_idx = self.tab_control.index('current')
            except Exception:
                tab_idx = 0
        self._page_is_dashboard = tab_idx == 0
        try:
            if hasattr(self, '_hdr_summary'):
                self._hdr_summary.pack_forget()
            if hasattr(self, '_archive_banner'):
                self._archive_banner.pack_forget()
            if hasattr(self, '_context_bar'):
                self._context_bar.pack_forget()
            if hasattr(self, '_command_bar'):
                self._command_bar.set_page_mode(dashboard=True, tab_idx=tab_idx)
        except Exception:
            pass
        self._update_brand_identity(tab_idx)
        if hasattr(self, '_update_responsive_layout'):
            self._update_responsive_layout()

    def _build_optimizer_tab(self):
        self.optimizer_tab.grid_rowconfigure(2, weight=1)
        self.optimizer_tab.grid_columnconfigure(0, weight=1)

        hero = ctk_theme.frame(self.optimizer_tab, CARD_BG, corner_radius=10)
        hero.grid(row=0, column=0, sticky='ew', padx=10, pady=(4, 4))
        hero_inner = ttk.Frame(hero, style='Card.TFrame')
        hero_inner.pack(fill='x', padx=12, pady=8)
        title_row = ttk.Frame(hero_inner, style='Card.TFrame')
        title_row.pack(fill='x')
        self.dashboard_status_lbl = tk.Label(
            title_row, text='Ready to scan', bg=CARD_BG, fg=PROOF,
            font=('Segoe UI', 13, 'bold'))
        self.dashboard_status_lbl.pack(side='left')
        self.dashboard_msg_lbl = ttk.Label(
            title_row, text='', style='Info.TLabel')
        self.dashboard_msg_lbl.pack(side='left', padx=(8, 0))
        cta_row = ttk.Frame(hero_inner, style='Card.TFrame')
        cta_row.pack(anchor='w', pady=(6, 0))
        self.dashboard_primary_btn = ttk.Button(
            cta_row, text='Scan Now', style='Primary.TButton', command=self.refresh_cleanup)
        self.dashboard_primary_btn.pack(side='left', ipadx=10, ipady=2)
        self.dashboard_preview_btn = ttk.Button(
            cta_row, text='Preview Receipt', style='Action.TButton',
            command=self.preview_cleanup_receipt, state='disabled')
        self.dashboard_preview_btn.pack(side='left', padx=(8, 0))
        self.dashboard_archive_btn = ttk.Button(
            cta_row, text='Archive & Clean', style='Action.TButton',
            command=self.apply_cleanup, state='disabled')
        self.dashboard_archive_btn.pack(side='left', padx=(8, 0))
        self.dashboard_secondary_btn = ttk.Button(
            cta_row, text='Proof Ledger', style='Action.TButton',
            command=lambda: self._navigate_to_tab(1))
        self.dashboard_secondary_btn.pack(side='left', padx=(8, 0))
        self._add_tooltip(self.dashboard_primary_btn, 'Scan configured folders for cleanup candidates.')
        self.preview_receipt_btn = self.dashboard_preview_btn

        cards = ttk.Frame(self.optimizer_tab, style='Content.TFrame')
        cards.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 4))
        self._home_cards = cards
        for col in range(4):
            cards.grid_columnconfigure(col, weight=1)

        health_card = tk.Frame(cards, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        health_card.grid(row=0, column=0, sticky='ew', padx=(0, 6))
        health_inner = tk.Frame(health_card, bg=CARD_BG)
        health_inner.pack(fill='x', padx=8, pady=6)
        self.health_canvas = tk.Canvas(health_inner, width=56, height=56, bg=CARD_BG, highlightthickness=0)
        self.health_canvas.pack(side='left', padx=(0, 6))
        health_text = tk.Frame(health_inner, bg=CARD_BG)
        health_text.pack(side='left', fill='x', expand=True)
        tk.Label(health_text, text='TO REVIEW', bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 7, 'bold')).pack(anchor='w')
        self.health_band_lbl = tk.Label(health_text, text='—', bg=CARD_BG, fg=TEXT,
                                        font=('Segoe UI', 12, 'bold'))
        self.health_band_lbl.pack(anchor='w')
        self.health_note_lbl = tk.Label(health_text, text='Evidence only',
                                        bg=CARD_BG, fg=MUTED, font=('Segoe UI', 7))
        self.health_note_lbl.pack(anchor='w')
        self._add_tooltip(health_card, 'Cleanup candidates awaiting your review.')

        self.stat_startup_value = self._stat_card_compact(cards, 1, 'Startup items')
        self.stat_cleanup_value = self._stat_card_compact(cards, 2, 'Cleanup candidates')
        self.stat_size_value = self._stat_card_compact(cards, 3, 'Reclaimable space')

        self._home_scroll = ctk.CTkScrollableFrame(
            self.optimizer_tab, fg_color=BG, corner_radius=0,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=HEAD_BG,
        )
        self._home_scroll.grid(row=2, column=0, sticky='nsew', padx=10, pady=(0, 8))
        self._home_recent = self._home_scroll
        scroll = self._home_scroll

        ttk.Label(scroll, text='Recent proof', font=('Segoe UI', 11, 'bold'),
                  background=BG).pack(anchor='w', pady=(0, 4))
        recent_row = ttk.Frame(scroll, style='Content.TFrame')
        recent_row.pack(fill='x', pady=(0, 10))
        for col in range(3):
            recent_row.grid_columnconfigure(col, weight=1)
        tile_kw = dict(card_bg=CARD_BG, text_color=TEXT, muted=MUTED, accent=PROOF)
        rc, self.recent_receipt_lbl = recent_proof_tile(
            recent_row, title='Latest receipt', command=self.open_last_receipt, **tile_kw)
        rc.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        ac, self.recent_archive_lbl = recent_proof_tile(
            recent_row, title='Latest archive action', command=self.open_archive_browser_tab, **tile_kw)
        ac.grid(row=0, column=1, sticky='ew', padx=(0, 8))
        pc, self.recent_proofpack_lbl = recent_proof_tile(
            recent_row, title='Latest proof pack', command=self.export_audit, **tile_kw)
        pc.grid(row=0, column=2, sticky='ew')

        fs_card = ctk_theme.frame(scroll, CARD_BG, corner_radius=10)
        fs_card.pack(fill='x', pady=(0, 10))
        self._home_fs = fs_card
        fs_inner = ttk.Frame(fs_card, style='Card.TFrame')
        fs_inner.pack(fill='x', padx=12, pady=8)
        ttk.Label(fs_inner, text='Disk foresight', font=('Segoe UI', 9, 'bold'),
                  background=CARD_BG).pack(side='left')
        self.foresight_lbl = tk.Label(fs_inner, text='Collecting…', bg=CARD_BG, fg=TEXT,
                                      font=('Segoe UI', 10, 'bold'))
        self.foresight_lbl.pack(side='left', padx=(10, 0))
        self.foresight_sub_lbl = tk.Label(fs_inner, text='', bg=CARD_BG, fg=MUTED,
                                          font=('Segoe UI', 9))
        self.foresight_sub_lbl.pack(side='left', padx=(8, 0))
        self._add_tooltip(fs_card, 'Free-space trend summary — text only, no chart.')

        rec_card = ttk.Frame(scroll, style='Card.TFrame')
        rec_card.pack(fill='both', expand=True)
        self._home_rec = rec_card
        rec_card.grid_rowconfigure(1, weight=1)
        rec_card.grid_columnconfigure(0, weight=1)
        ttk.Label(rec_card, text='Next recommended action', font=('Segoe UI', 11, 'bold'),
                  background=CARD_BG).grid(row=0, column=0, sticky='w', padx=10, pady=(6, 2))
        rec_body = ttk.Frame(rec_card, style='Card.TFrame')
        rec_body.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 8))
        rec_body.grid_rowconfigure(0, weight=1)
        rec_body.grid_columnconfigure(0, weight=1)

        self._home_rec_pane, rec_left, rec_right = create_horizontal_pane(rec_body)
        self._bind_pane(self._home_rec_pane, 'home_rec_split', default=480)

        self._rec_cards_scroll = ctk.CTkScrollableFrame(
            rec_left, fg_color=CARD_BG, corner_radius=8,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=HEAD_BG,
        )
        self._rec_cards_scroll.pack(fill='both', expand=True, padx=4, pady=4)

        self._proof_summary = ProofSummaryCard(
            rec_right,
            panel_bg=BG,
            card_bg=CARD_BG,
            accent=ACCENT,
            proof=PROOF,
            text_color=TEXT,
            muted=MUTED,
            on_open_receipt=self.open_last_receipt,
            on_copy_proof=self._recommendation_copy_details,
            on_view_details=self._recommendation_primary_action,
        )
        self._proof_summary.pack(fill='both', expand=True, padx=(4, 0))
        self._proof_summary.show_idle()

        self._rec_card_frames = []
        self._dashboard_recommendations = []
        self._rec_context_menu = None

        self._home_rec_empty_panel = ctk_theme.frame(rec_body, CARD_BG, corner_radius=12)
        empty_inner = ttk.Frame(self._home_rec_empty_panel, style='Card.TFrame')
        empty_inner.place(relx=0.5, rely=0.42, anchor='center')
        ttk.Label(
            empty_inner, text='No recommendations yet.',
            font=('Segoe UI', 14, 'bold'), background=CARD_BG,
        ).pack(anchor='center')
        ttk.Label(
            empty_inner,
            text='Run Scan to review configured folders.\nCleanroom surfaces archive-first guidance with receipts.',
            style='Info.TLabel', wraplength=420, justify='center',
        ).pack(anchor='center', pady=(8, 16))
        ttk.Button(
            empty_inner, text='Scan Now', style='Primary.TButton', command=self.refresh_cleanup,
        ).pack(anchor='center')
        self._home_rec_empty = self._home_rec_empty_panel
        self.schedule_btn = self.dashboard_secondary_btn
        self.open_archive_btn = self.dashboard_secondary_btn
        self.open_log_btn = self.dashboard_secondary_btn
        self.prune_btn = self.dashboard_secondary_btn
        self.receipt_btn = self.dashboard_primary_btn
        self.reg_health_btn = self.dashboard_secondary_btn
        self.diagnostics_btn = self.dashboard_secondary_btn

    def _build_activity_tab(self):
        """Proof ledger — every action Cleanroom ever took, with custody status."""
        self.activity_tab.grid_rowconfigure(2, weight=1)
        self.activity_tab.grid_columnconfigure(0, weight=1)

        head = ctk_theme.frame(self.activity_tab, CARD_BG, corner_radius=10)
        head.grid(row=0, column=0, sticky='ew', padx=10, pady=(4, 4))
        head_inner = ttk.Frame(head, style='Card.TFrame')
        head_inner.pack(fill='x', padx=12, pady=8)
        title_row = ttk.Frame(head_inner, style='Card.TFrame')
        title_row.pack(fill='x')
        ttk.Label(title_row, text='Proof Ledger', font=('Segoe UI', 15, 'bold'),
                  background=CARD_BG).pack(side='left')
        self.trust_band_lbl = tk.Label(title_row, text='—', bg=CARD_BG, fg=PROOF,
                                       font=('Segoe UI', 11, 'bold'))
        self.trust_band_lbl.pack(side='left', padx=(12, 0))
        self.trust_sub_lbl = tk.Label(title_row, text='', bg=CARD_BG, fg=MUTED,
                                      font=('Segoe UI', 9), wraplength=360, justify='left')
        self.trust_sub_lbl.pack(side='left', padx=(8, 0))
        self.trust_canvas = tk.Canvas(title_row, width=1, height=1, bg=CARD_BG, highlightthickness=0)
        self.act_status_lbl = ttk.Label(title_row, text='', style='Badge.TLabel')
        self.act_status_lbl.pack(side='left', padx=(8, 0))
        self.act_refresh_btn = ttk.Button(title_row, text='Refresh', style='Action.TButton',
                                          command=self.refresh_activity)
        self.act_refresh_btn.pack(side='right')

        top = ttk.Frame(self.activity_tab, style='Content.TFrame')
        top.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 6))
        self._activity_top = top

        stats_wrap = ttk.Frame(top, style='Content.TFrame')
        stats_wrap.pack(fill='x')
        for col in range(4):
            stats_wrap.grid_columnconfigure(col, weight=1)
        self.stat_act_total = self._stat_card_compact(stats_wrap, 0, 'Actions logged')
        self.stat_act_present = self._stat_card_compact(stats_wrap, 1, 'Restorable now')
        self.stat_act_bytes = self._stat_card_compact(stats_wrap, 2, 'Bytes in custody')
        self.stat_act_pruned = self._stat_card_compact(stats_wrap, 3, 'Bytes pruned')
        self._add_tooltip(self.stat_act_bytes,
                          'Bytes in custody = verified files still restorable in the archive.')
        self._add_tooltip(self.stat_act_pruned,
                          'Bytes pruned = archive custody permanently removed (original files untouched).')

        self._activity_hint = None

        self.act_sub_notebook = None
        self._activity_container = ttk.Frame(self.activity_tab, style='Card.TFrame')
        self._activity_container.grid(row=2, column=0, sticky='nsew', padx=10, pady=(0, 8))

        self._activity_pane, activity_left, activity_right = create_horizontal_pane(
            self._activity_container, use_pack=True, min_left=340, min_right=260)
        self._bind_pane(
            self._activity_pane, 'activity_split', default=520,
            min_left=340, min_right=260, default_ratio=0.68)

        self._activity_loading_lbl = ttk.Label(
            self._activity_container,
            text='Loading proof ledger…',
            style='Info.TLabel',
            font=('Segoe UI', 12),
            anchor='center',
        )

        tree_card = ttk.Frame(activity_left, style='Card.TFrame')
        self._activity_tree_card = tree_card
        tree_card.pack(fill='both', expand=True)
        tree_card.grid_rowconfigure(0, weight=1)
        tree_card.grid_columnconfigure(0, weight=1)
        cols = ('status', 'when', 'type', 'reason', 'item', 'size')
        self.activity_tree = ttk.Treeview(tree_card, columns=cols, show='headings', selectmode='browse')
        for c, label, w in (
            ('status', 'Proof', 56), ('when', 'When', 128), ('type', 'Event', 88),
            ('reason', 'Reason', 100), ('item', 'Item', 200), ('size', 'Size', 72),
        ):
            self.activity_tree.heading(c, text=label)
            anchor = 'center' if c in ('status', 'size', 'type') else 'w'
            self.activity_tree.column(c, width=w, anchor=anchor, stretch=False)
        vsb = ttk.Scrollbar(tree_card, orient='vertical', command=self.activity_tree.yview)
        hsb = ttk.Scrollbar(tree_card, orient='horizontal', command=self.activity_tree.xview)
        self.activity_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.activity_tree.grid(row=0, column=0, sticky='nsew', padx=8, pady=8)
        vsb.grid(row=0, column=1, sticky='ns', pady=8)
        hsb.grid(row=1, column=0, sticky='ew', padx=8)
        self.activity_tree.tag_configure('oddrow', background=CARD_BG)
        self.activity_tree.tag_configure('evenrow', background=ROW_ALT)
        self.activity_tree.tag_configure('present', foreground=TEXT)
        self.activity_tree.tag_configure('missing', foreground=MUTED)
        self.activity_empty = self._make_empty_hint(
            self.activity_tree, 'No Cleanroom actions logged yet.\n'
                                'Run a cleanup — every move will appear here with proof status.')
        self._activity_feed = []
        self._activity_split_mode = None

        self._activity_detail_panel = ttk.Frame(activity_right, style='Card.TFrame')
        self._activity_detail_panel.pack(fill='both', expand=True)
        act_detail = ttk.Frame(self._activity_detail_panel, style='Card.TFrame')
        act_detail.pack(fill='both', expand=True, padx=12, pady=12)
        ttk.Label(act_detail, text='Proof details', font=('Segoe UI', 11, 'bold'),
                  background=CARD_BG).pack(anchor='w', pady=(0, 8))
        self._act_detail_type = ttk.Label(act_detail, text='—', style='CardInfo.TLabel', wraplength=280)
        self._act_detail_when = ttk.Label(act_detail, text='—', style='CardInfo.TLabel', wraplength=280)
        self._act_detail_custody = ttk.Label(act_detail, text='—', style='CardInfo.TLabel', wraplength=280)
        self._act_detail_src = ttk.Label(act_detail, text='—', style='CardInfo.TLabel', wraplength=280, justify='left')
        self._act_detail_dest = ttk.Label(act_detail, text='—', style='CardInfo.TLabel', wraplength=280, justify='left')
        self._act_detail_hint = ttk.Label(act_detail, text='Select a ledger row to view proof details.',
                                            style='CardInfo.TLabel', wraplength=280, justify='left',
                                            foreground=ACCENT)
        for lbl in (self._act_detail_type, self._act_detail_when, self._act_detail_custody,
                    self._act_detail_src, self._act_detail_dest, self._act_detail_hint):
            lbl.pack(anchor='w', pady=(0, 6))

        ttk.Label(act_detail, text='Quick actions', font=('Segoe UI', 10, 'bold'),
                  background=CARD_BG).pack(anchor='w', pady=(4, 6))
        act_btns = ttk.Frame(act_detail, style='Card.TFrame')
        act_btns.pack(fill='x', pady=(8, 0))
        act_btns.columnconfigure(0, weight=1)
        act_btns.columnconfigure(1, weight=1)
        self._act_btn_receipt = ttk.Button(act_btns, text='Open Receipt', style='Action.TButton',
                                          command=self._activity_open_receipt)
        self._act_btn_archive = ttk.Button(act_btns, text='Open Archive', style='Action.TButton',
                                           command=self._activity_open_archive)
        self._act_btn_copy = ttk.Button(act_btns, text='Copy Path', style='Action.TButton',
                                        command=self._activity_copy_path)
        self._act_btn_proof = ttk.Button(act_btns, text='Copy Proof', style='Action.TButton',
                                         command=self._activity_copy_proof)
        self._act_btn_verify = ttk.Button(act_btns, text='Verify Custody', style='Action.TButton',
                                          command=self.verify_custody)
        self._act_btn_restore = ttk.Button(act_btns, text='Restore', style='Action.TButton',
                                           command=self._activity_restore_selected)
        for i, btn in enumerate((
            self._act_btn_receipt, self._act_btn_archive, self._act_btn_copy,
            self._act_btn_proof, self._act_btn_verify, self._act_btn_restore,
        )):
            btn.grid(row=i // 2, column=i % 2, sticky='ew', padx=2, pady=2)

        self._bind_selectable_table(
            self.activity_tree,
            on_select=self._on_activity_select,
            on_double=self._on_activity_double_click,
            on_right=self._on_activity_right_click,
            on_enter=self._on_activity_double_click,
        )
        self._activity_context_menu = None

        self._activity_empty_panel = self._build_workspace_empty_panel(
            self._activity_container,
            'No Cleanroom actions yet',
            'Run a cleanup — every archive-first move appears here with proof status.',
            'Open Cleaner', lambda: self._navigate_to_tab(3),
        )
        self._sync_activity_view(loading=False)

    def _build_archive_tab(self):
        """Dedicated archive custody manager — browse, restore, delete."""
        self.archive_tab.grid_rowconfigure(4, weight=1)
        self.archive_tab.grid_columnconfigure(0, weight=1)
        self._archive_split_mode = 'wide'
        self._archive_action_btns = []
        self._archive_loaded = False

        def _archive_btn(parent, text, command, *, refresh=False, **pack_kw):
            btn = ttk.Button(parent, text=text, style='Action.TButton', command=command, **pack_kw)
            if refresh:
                self._archive_refresh_btn = btn
            else:
                self._archive_action_btns.append(btn)
            return btn

        header = ctk_theme.frame(self.archive_tab, CARD_BG, corner_radius=10)
        header.grid(row=0, column=0, sticky='ew', padx=10, pady=(4, 4))
        header_inner = ttk.Frame(header, style='Card.TFrame')
        header_inner.pack(fill='x', padx=12, pady=8)
        title_row = ttk.Frame(header_inner, style='Card.TFrame')
        title_row.pack(fill='x')
        ttk.Label(title_row, text='Archive Custody', font=('Segoe UI', 15, 'bold'),
                  background=CARD_BG).pack(side='left')
        self._archive_subheader = ttk.Label(
            title_row,
            text='Browse custody · delete archived copies only · originals never touched.',
            style='Info.TLabel', wraplength=640,
        )
        self._archive_subheader.pack(side='left', padx=(10, 0), anchor='w')

        stats_row = ttk.Frame(self.archive_tab, style='Content.TFrame')
        stats_row.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 4))
        for col in range(4):
            stats_row.grid_columnconfigure(col, weight=1)
        self.stat_arch_total = self._stat_card_compact(stats_row, 0, 'In custody')
        self.stat_arch_safe = self._stat_card_compact(stats_row, 1, 'Safe to delete')
        self.stat_arch_bytes = self._stat_card_compact(stats_row, 2, 'Archive size')
        self.stat_arch_selected = self._stat_card_compact(stats_row, 3, 'Selected')

        qa = ctk_theme.frame(self.archive_tab, CARD_BG, corner_radius=10)
        self._archive_qa = qa
        qa.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 4))
        qa_inner = ttk.Frame(qa, style='Card.TFrame')
        qa_inner.pack(fill='x', padx=10, pady=8)

        qa_primary = ttk.Frame(qa_inner, style='Card.TFrame')
        qa_primary.pack(fill='x')
        ttk.Label(qa_primary, text='Review & restore', style='CardInfo.TLabel').pack(
            side='left', padx=(0, 10))
        ttk.Button(qa_primary, text='↩ Restore Selected', style='Primary.TButton',
                   command=self._archive_restore_selected).pack(side='left', padx=(0, 6))
        self._archive_restore_btn = qa_primary.winfo_children()[-1]
        _archive_btn(qa_primary, 'Open Archive Folder', self.open_archive_folder).pack(
            side='left', padx=(0, 6))
        _archive_btn(qa_primary, 'Refresh', self.refresh_archive_browser, refresh=True).pack(
            side='left')

        qa_bulk = ttk.Frame(qa_inner, style='Card.TFrame')
        qa_bulk.pack(fill='x', pady=(6, 0))
        ttk.Label(qa_bulk, text='Select', style='CardInfo.TLabel').pack(side='left', padx=(0, 10))
        for label, cmd in (
            ('Select All Safe', self._archive_select_all_safe),
            ('Select Visible', self._archive_select_visible),
            ('Clear Selection', self._archive_clear_selection),
        ):
            _archive_btn(qa_bulk, label, cmd).pack(side='left', padx=(0, 6))

        qa_delete = ttk.Frame(qa_inner, style='Card.TFrame')
        qa_delete.pack(fill='x', pady=(6, 0))
        ttk.Label(qa_delete, text='Delete from archive', style='CardInfo.TLabel').pack(
            side='left', padx=(0, 10))
        self.delete_archive_btn = _archive_btn(
            qa_delete, 'Delete Eligible…', self.confirm_prune_selected,
        )
        self.delete_archive_btn.pack(side='left', padx=(0, 6))
        self._add_tooltip(self.delete_archive_btn,
                          'Permanently delete selected archived copies. Original live files untouched.')
        for label, cmd in (
            ('Delete All Safe…', self.confirm_delete_all_safe),
            ('Delete Older Than…', self.confirm_delete_older_than),
        ):
            _archive_btn(qa_delete, label, cmd).pack(side='left', padx=(0, 6))

        qa_secondary = ttk.Frame(qa_inner, style='Card.TFrame')
        qa_secondary.pack(fill='x', pady=(6, 0))
        _archive_btn(qa_secondary, 'Archive Settings…', self._open_archive_settings).pack(side='left')

        filter_bar = ttk.Frame(self.archive_tab, style='Content.TFrame')
        self._archive_filter_bar = filter_bar
        filter_bar.grid(row=3, column=0, sticky='ew', padx=10, pady=(0, 4))
        self._archive_prune_filter = tk.StringVar(value='')
        chip_labels = (
            ('All', ''), ('Safe to delete', archive_custody.PRUNE_SAFE if archive_custody else ''),
            ('Review first', archive_custody.PRUNE_REVIEW if archive_custody else ''),
            ('Keep in custody', archive_custody.PRUNE_KEEP if archive_custody else ''),
        )
        self._archive_filter_widgets = []
        for label, value in chip_labels:
            rb = ttk.Radiobutton(filter_bar, text=label, value=value,
                                 variable=self._archive_prune_filter,
                                 command=self._apply_archive_view_filters)
            rb.pack(side='left', padx=(0, 8))
            self._archive_filter_widgets.append(rb)
        ttk.Label(filter_bar, text='Search:', style='Info.TLabel').pack(side='left', padx=(12, 4))
        self._archive_search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_bar, textvariable=self._archive_search_var,
                                 width=28, style='Search.TEntry')
        search_entry.pack(side='left')
        search_entry.bind('<Return>', lambda e: self._apply_archive_view_filters())
        self._archive_search_entry = search_entry
        self._archive_filter_widgets.append(search_entry)
        archive_search_btn = ttk.Button(filter_bar, text='Search', style='Action.TButton',
                                        command=self._apply_archive_view_filters)
        archive_search_btn.pack(side='left', padx=(6, 0))
        self._archive_filter_widgets.append(archive_search_btn)

        self._archive_body = ttk.Frame(self.archive_tab, style='Content.TFrame')
        self._archive_body.grid(row=4, column=0, sticky='nsew', padx=10, pady=(0, 4))
        self._archive_body.grid_rowconfigure(0, weight=1)
        self._archive_body.grid_columnconfigure(0, weight=1)

        self._archive_pane, archive_left, archive_right = create_horizontal_pane(self._archive_body)
        self._bind_pane(self._archive_pane, 'archive_split', default=520)

        self._archive_empty_panel = self._build_workspace_empty_panel(
            self._archive_body,
            'No archive custody records',
            'Run a cleanup — archived items will appear here with proof status.',
            'Refresh', self.refresh_archive_browser,
        )
        self._archive_loading_lbl = ttk.Label(
            self._archive_body, text='Loading archive custody…',
            style='Info.TLabel', anchor='center', font=('Segoe UI', 12))

        tree_card = ctk_theme.frame(archive_left, CARD_BG, corner_radius=10)
        self._archive_tree_card = tree_card
        tree_card.pack(fill='both', expand=True)
        ttk.Label(tree_card, text='Custody records', font=('Segoe UI', 10, 'bold'),
                  background=CARD_BG).pack(anchor='w', padx=10, pady=(8, 0))
        tree_wrap = ttk.Frame(tree_card)
        tree_wrap.pack(fill='both', expand=True, padx=6, pady=6)
        acols = ('when', 'item', 'reason', 'size', 'restorable', 'receipt', 'prune_rank')
        self.archive_tree = ttk.Treeview(tree_wrap, columns=acols, show='headings',
                                         selectmode='extended')
        headings = {
            'when': 'Archived', 'item': 'Item', 'reason': 'Reason', 'size': 'Size',
            'restorable': 'On disk', 'receipt': 'Receipt', 'prune_rank': 'Recommendation',
        }
        widths = {'when': 108, 'item': 200, 'reason': 90, 'size': 64,
                  'restorable': 56, 'receipt': 48, 'prune_rank': 110}
        for c in acols:
            self.archive_tree.heading(c, text=headings[c])
            anchor = 'center' if c in ('size', 'restorable', 'receipt', 'prune_rank') else 'w'
            self.archive_tree.column(c, width=widths[c], anchor=anchor,
                                     stretch=False)
        vsb = ttk.Scrollbar(tree_wrap, orient='vertical', command=self.archive_tree.yview)
        hsb = ttk.Scrollbar(tree_wrap, orient='horizontal', command=self.archive_tree.xview)
        self.archive_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.archive_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)
        self.archive_tree.tag_configure('safe', foreground=TEXT)
        self.archive_tree.tag_configure('review', foreground=TEXT)
        self.archive_tree.tag_configure('keep', foreground=MUTED)
        self.archive_tree.tag_configure('oddrow', background=CARD_BG)
        self.archive_tree.tag_configure('evenrow', background=ROW_ALT)
        self.archive_empty = self._make_empty_hint(
            self.archive_tree, 'No archive custody records yet.\n'
                                'Run Cleaner → Archive & Clean — evidence appears here.')
        self._bind_selectable_table(
            self.archive_tree,
            on_select=self._on_archive_select,
            on_double=self._on_archive_double_click,
            on_right=self._on_archive_right_click,
        )
        self._archive_records_all = []
        self._archive_records = []
        self._archive_stats = {}

        detail = ctk_theme.frame(archive_right, CARD_BG, corner_radius=10)
        detail.pack(fill='both', expand=True)
        self._archive_detail_panel = detail
        detail_inner = ttk.Frame(detail, style='Card.TFrame')
        detail_inner.pack(fill='both', expand=True, padx=12, pady=12)
        ttk.Label(detail_inner, text='Selected custody', font=('Segoe UI', 11, 'bold'),
                  background=CARD_BG).pack(anchor='w', pady=(0, 8))
        qa_grid = ttk.Frame(detail_inner, style='Card.TFrame')
        qa_grid.pack(fill='x', pady=(0, 8))

        restore_box = ttk.Frame(qa_grid, style='Card.TFrame')
        restore_box.pack(fill='x', pady=(0, 10))
        ttk.Label(restore_box, text='Restore / Inspect', font=('Segoe UI', 10, 'bold'),
                  background=CARD_BG).pack(anchor='w', pady=(0, 6))
        restore_row = ttk.Frame(restore_box, style='Card.TFrame')
        restore_row.pack(fill='x')
        for label, cmd in (
            ('Restore Selected', self._archive_restore_selected),
            ('Open Receipt', self._archive_open_receipt),
            ('Open Archive Folder', self._archive_open_archive),
            ('Open Original', self._archive_open_original),
            ('Copy paths', self._archive_copy_path),
        ):
            btn = ttk.Button(restore_row, text=label, style='Action.TButton', command=cmd)
            btn.pack(side='left', padx=(0, 6), pady=2)
            self._archive_action_btns.append(btn)

        delete_box = ttk.Frame(qa_grid, style='Card.TFrame')
        delete_box.pack(fill='x')
        ttk.Label(delete_box, text='Archive cleanup', font=('Segoe UI', 10, 'bold'),
                  background=CARD_BG).pack(anchor='w', pady=(0, 2))
        ttk.Label(
            delete_box,
            text='Permanently removes archived copies only — original live files are never touched.',
            style='CardInfo.TLabel', wraplength=260, justify='left',
        ).pack(anchor='w', pady=(0, 6))
        delete_row = ttk.Frame(delete_box, style='Card.TFrame')
        delete_row.pack(fill='x')
        detail_delete_btn = ttk.Button(
            delete_row, text='Delete eligible…', style='Action.TButton',
            command=self.confirm_prune_selected,
        )
        detail_delete_btn.pack(side='left', padx=(0, 6), pady=2)
        self._archive_action_btns.append(detail_delete_btn)

        meta = ttk.Frame(detail_inner, style='Card.TFrame')
        meta.pack(fill='both', expand=True)
        self._archive_detail_src = ttk.Label(meta, text='Original: —', style='CardInfo.TLabel',
                                             wraplength=260, justify='left')
        self._archive_detail_dest = ttk.Label(meta, text='Archive: —', style='CardInfo.TLabel',
                                              wraplength=260, justify='left')
        self._archive_detail_meta = ttk.Label(meta, text='Select a row to view custody proof.',
                                              style='CardInfo.TLabel', wraplength=260, justify='left')
        self._archive_detail_rank = ttk.Label(meta, text='Recommendation: —', style='CardInfo.TLabel',
                                              wraplength=260, justify='left')
        for lbl in (self._archive_detail_src, self._archive_detail_dest,
                    self._archive_detail_meta, self._archive_detail_rank):
            lbl.pack(anchor='w', pady=(4, 2))

        self.archive_status_lbl = ttk.Label(self.archive_tab, text='', style='Info.TLabel')
        self.archive_status_lbl.grid(row=5, column=0, sticky='w', padx=12, pady=(0, 6))

    def _stat_card(self, parent, caption):
        """White stat card with a big value label; returns the value label."""
        card = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        card.pack(side='left', padx=(0, 10), fill='y')
        value = tk.Label(card, text='—', bg=CARD_BG, fg=TEXT, font=('Segoe UI', 22, 'bold'))
        value.pack(anchor='w', padx=16, pady=(14, 0))
        tk.Label(card, text=caption, bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 9)).pack(anchor='w', padx=16, pady=(0, 14))
        return value

    def _stat_card_compact(self, parent, column, caption):
        """Compact horizontal stat chip for dense tabs (Archive)."""
        pad = (0, 6) if column < 3 else (0, 0)
        card = tk.Frame(parent, bg=CARD_BG, highlightthickness=0)
        card.grid(row=0, column=column, sticky='ew', padx=pad)
        inner = tk.Frame(card, bg=CARD_BG)
        inner.pack(fill='x', padx=10, pady=5)
        value = tk.Label(inner, text='—', bg=CARD_BG, fg=TEXT, font=('Segoe UI', 15, 'bold'))
        value.pack(side='left')
        tk.Label(inner, text=caption, bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 8)).pack(side='left', padx=(8, 0), pady=(3, 0))
        return value

    def _config_status_label(self):
        """Sanitized config label — never expose repo folder names in the UI."""
        try:
            p = Path(self.cleanup_config_path).resolve()
            data_root = brand.user_data_dir().resolve()
            if p.is_relative_to(data_root):
                return 'Editing Cleanroom configuration'
        except Exception:
            pass
        return f'Config: {Path(self.cleanup_config_path).name}'

    def _refresh_header_proof_badges(self):
        """Update proof-first header badges from current log/custody/receipt state."""
        entries = self._load_log_dicts()
        measured = len(entries)
        custody = {'verified': 0, 'total': 0, 'missing': 0, 'bytes_in_custody': 0}
        if proof_module and entries:
            try:
                custody = proof_module.verify_entries(entries)
            except Exception:
                pass
        trust = None
        if ledger_module and custody.get('total'):
            trust = ledger_module.trust_score(custody['verified'], custody['total'])
        if trust is not None:
            self.hdr_trust_value.configure(text=f'Custody trust {trust}%')
            self.hdr_trust_lbl.configure(
                text=f'· {self._format_size(custody.get("bytes_in_custody", 0))} in custody')
        else:
            self.hdr_trust_value.configure(text='Custody trust —')
            self.hdr_trust_lbl.configure(text='no archive custody yet')
        self._update_brand_identity()

    def _bind_settings_dirty_tracking(self):
        """Mark settings form dirty when the user edits values."""
        for var in (
            getattr(self, 'set_scan_on_startup', None),
            getattr(self, 'set_remember_geometry', None),
            getattr(self, 'set_remember_last_tab', None),
            getattr(self, 'set_power_var', None),
            getattr(self, 'set_scan_downloads', None),
            getattr(self, 'set_scan_temp', None),
            getattr(self, 'set_relaxed_scan', None),
            getattr(self, 'set_dedupe_default', None),
            getattr(self, 'set_temp_age', None),
            getattr(self, 'set_installer_age', None),
            getattr(self, 'set_size_mb', None),
            getattr(self, 'set_confirm_gb', None),
            getattr(self, 'set_prune_recent_days', None),
        ):
            if var is not None:
                try:
                    var.trace_add('write', self._mark_settings_dirty)
                except Exception:
                    pass
        for var_name in ('set_archive_var', 'set_ext_var', 'set_theme_var', 'set_default_tab_var'):
            var = getattr(self, var_name, None)
            if var is not None:
                try:
                    var.trace_add('write', self._mark_settings_dirty)
                except Exception:
                    pass
        for widget in (getattr(self, 'set_exclude_text', None),
                       getattr(self, 'set_whitelist_text', None)):
            if widget is not None:
                widget.bind('<KeyRelease>', self._mark_settings_dirty)
        paths = getattr(self, 'set_paths_list', None)
        if paths is not None:
            paths.bind('<<ListboxSelect>>', self._mark_settings_dirty)

    def _menu_entry_state(self, menu, index, enabled: bool):
        """Enable/disable a menu row without touching separators (avoids TclError)."""
        try:
            if menu.type(index) != 'command':
                return
            menu.entryconfig(index, state='normal' if enabled else 'disabled')
        except (tk.TclError, Exception):
            pass

    def _play_receipt_animation(self, stamp, on_complete=None, lines=None, duration_ms=900):
        """Short proof-output animation on the Review tab; non-blocking."""
        play_receipt_animation(
            getattr(self, 'receipt_printer', None),
            stamp,
            lines=lines or DEFAULT_LINES,
            on_complete=on_complete,
            duration_ms=duration_ms,
        )

    def _show_text_dialog(self, title, text, width=620, height=480):
        dlg = CleanroomModal(
            self, title, width=min(width, 680), height=min(height, 520),
            colors=self._dialog_colors(), resizable=True,
        )
        dlg.heading(title, size=14)
        dlg.scroll_text(text, height=height - 120, mono=True)
        dlg.add_button('Close', dlg.close, primary=True)
        return dlg

    def preview_cleanup_receipt(self):
        """Draft Cleanroom Receipt for checked candidates — before any archive."""
        if getattr(self, '_cleaner_loading', False):
            messagebox.showinfo(
                'Preview Receipt',
                'Scan is still running. Wait for scan to finish before previewing.',
            )
            return
        if receipts_module is None:
            messagebox.showerror('Preview Receipt', 'Receipts module unavailable.')
            return
        if not self.cleanup_items:
            messagebox.showinfo('Preview Receipt', 'Scan first — no candidates to preview.')
            return
        items = [self.cleanup_items[i] for i in sorted(self.cleanup_selected)
                 if 0 <= i < len(self.cleanup_items)]
        if not items:
            messagebox.showinfo('Preview Receipt',
                                'Check at least one item to preview what will be archived.')
            return
        cfg = self._load_cleanup_config() or {}
        archive_dir = cfg.get('archive_dir') or '(configured archive folder)'
        draft = [{
            'src': it['path'],
            'dest': f'{archive_dir}/…',
            'reason': it.get('reason', 'other'),
            'size': it.get('size', 0),
            'when': datetime.now().isoformat(),
        } for it in items]
        body = receipts_module.format_receipt(draft)
        preview = ('*** PREVIEW ONLY — nothing has been archived yet ***\n\n' + body)

        def _open_preview():
            try:
                if show_receipt:
                    show_receipt(
                        self, preview, title='Cleanroom Receipt — Cleaner Preview',
                        preview=True, module='Cleaner', action='Preview',
                        action_key='cleaner_preview',
                        bg=BG, card=CARD_BG, text_fg=TEXT,
                    )
                else:
                    raise RuntimeError('receipt viewer unavailable')
            except Exception:
                self._show_text_dialog('Cleanroom Receipt — Cleaner Preview', preview)

        self._play_receipt_animation(
            'RECEIPT GENERATED',
            lines=PREVIEW_LINES,
            on_complete=_open_preview,
        )

    def _show_custody_trust_why(self):
        """Drilldown for custody trust — evidence, not a fake score."""
        if proof_module is None or ledger_module is None:
            messagebox.showerror('Custody Trust', 'Proof modules unavailable.')
            return
        entries = self._load_log_dicts()
        if not entries:
            messagebox.showinfo('Custody Trust',
                                'No archived actions yet.\n\n'
                                'Custody trust measures how many logged artifacts are still '
                                'on disk in the archive — run a cleanup first.')
            return
        custody = proof_module.verify_entries(entries)
        trust = ledger_module.trust_score(custody['verified'], custody['total'])
        lines = [
            'CLEANROOM — CUSTODY TRUST',
            brand.APP_MOTTO,
            '',
            f'Custody Trust: {trust}%',
            f'Verified on disk: {custody["verified"]}/{custody["total"]}',
            f'Bytes in custody: {self._format_size(custody.get("bytes_in_custody", 0))}',
            '',
            'This is NOT a PC health score. It is an audit of whether every item '
            'Cleanroom logged is still present in the archive and restorable.',
            '',
        ]
        if custody.get('missing'):
            lines.append(f'Missing from archive ({custody["missing"]}):')
            for src in custody.get('missing_items', [])[:12]:
                lines.append(f'  • {src}')
            if custody['missing'] > 12:
                lines.append(f'  … and {custody["missing"] - 12} more')
            lines.append('')
            lines.append('Missing items may have been pruned or moved outside Cleanroom.')
        else:
            lines.append('All logged artifacts verified present. ✓')
        lines.extend(['', 'View the Activity tab for the full evidence ledger.'])
        answer = messagebox.askyesno('Custody Trust — Why?',
                                     '\n'.join(lines) + '\n\nOpen Activity tab now?')
        if answer:
            self.tab_control.select(1)
            self.refresh_activity()

    def _draw_review_gauge(self, count, tone):
        """Review-tab gauge — shows item count, not a fake health score."""
        c = self.health_canvas
        c.delete('all')
        size, pad, width = 92, 9, 9
        c.create_arc(pad, pad, size - pad, size - pad, start=0, extent=359.9,
                     style='arc', outline=RING_BG, width=width)
        fill = min(count, 50) / 50.0
        if fill > 0:
            c.create_arc(pad, pad, size - pad, size - pad, start=90,
                         extent=-fill * 359.9, style='arc', outline=tone, width=width)
        c.create_text(size / 2, size / 2, text=str(count), fill=TEXT,
                      font=('Segoe UI', 18, 'bold'))

    def _draw_health_gauge(self, score, tone):
        c = self.health_canvas
        c.delete('all')
        size, pad, width = 92, 9, 9
        c.create_arc(pad, pad, size - pad, size - pad, start=0, extent=359.9,
                     style='arc', outline=RING_BG, width=width)
        if score > 0:
            c.create_arc(pad, pad, size - pad, size - pad, start=90,
                         extent=-(min(score, 100) / 100) * 359.9,
                         style='arc', outline=tone, width=width)
        c.create_text(size / 2, size / 2, text=str(score), fill=TEXT,
                      font=('Segoe UI', 18, 'bold'))

    def _draw_trust_ring(self, score, tone):
        c = self.trust_canvas
        c.delete('all')
        size, pad, width = 100, 10, 10
        c.create_arc(pad, pad, size - pad, size - pad, start=0, extent=359.9,
                     style='arc', outline=RING_BG, width=width)
        if score > 0:
            c.create_arc(pad, pad, size - pad, size - pad, start=90,
                         extent=-(min(score, 100) / 100) * 359.9,
                         style='arc', outline=tone, width=width)
        c.create_text(size / 2, size / 2, text=str(score), fill=TEXT,
                      font=('Segoe UI', 20, 'bold'))

    def _draw_health_sparkline(self, history, tone):
        return  # retired — Cleanroom does not show fake health-score trends

    # ------------------------------------------------------------------
    # Disk Foresight (free-space trend + disk-full prediction)
    # ------------------------------------------------------------------
    def refresh_foresight(self):
        if foresight is None:
            return
        try:
            history = foresight.load_history()
            fc = foresight.forecast(history)
        except Exception:
            return
        if fc['free'] is None:
            self.foresight_lbl.config(text='Collecting data…', fg=TEXT)
            self.foresight_sub_lbl.config(text='Run Cleanroom a few days in a row.')
            return
        free_txt = self._format_size(fc['free'])
        if fc['days_until_full'] is not None:
            days = fc['days_until_full']
            date_txt = fc['full_date'].strftime('%b %d, %Y')
            urgency = (SEVERITY_COLORS['high'] if days < 30
                       else SEVERITY_COLORS['medium'] if days < 90 else TEXT)
            self.foresight_lbl.config(text=f'Full in ~{days:.0f} days', fg=urgency)
            sub = f'{free_txt} free · empty around {date_txt}'
            bought = foresight.days_bought(self.cleanup_total_size, fc['slope_per_day'])
            if bought and bought >= 1:
                sub += f'\nCleaning now buys ~{bought:.0f} more days'
            self.foresight_sub_lbl.config(text=sub)
        elif fc['slope_per_day'] is None:
            self.foresight_lbl.config(text=f'{free_txt} free', fg=TEXT)
            self.foresight_sub_lbl.config(text='Trend appears after a few snapshots.')
        else:
            self.foresight_lbl.config(text='Disk usage stable', fg=TEXT)
            self.foresight_sub_lbl.config(text=f'{free_txt} free and not shrinking.')

    def _draw_foresight_sparkline(self, history):
        return  # sparkline removed — foresight is text-only on the dashboard

    def _build_startup_tab(self):
        head = ttk.Frame(self.startup_tab, style='Content.TFrame')
        head.pack(fill='x', padx=10, pady=(10, 4))
        ttk.Label(head, text='Startup Manager', font=('Segoe UI', 13, 'bold'),
                  background=BG).pack(side='left')
        self.status_lbl = ttk.Label(head, text='', style='Info.TLabel')
        self.status_lbl.pack(side='right')

        stats_row = ttk.Frame(self.startup_tab, style='Content.TFrame')
        stats_row.pack(fill='x', padx=10, pady=(0, 8))
        self._startup_stats_row = stats_row
        for col in range(5):
            stats_row.grid_columnconfigure(col, weight=1)
        self.total_label = self._stat_card_compact(stats_row, 0, 'Total')
        self.folder_label = self._stat_card_compact(stats_row, 1, 'Folders')
        self.registry_label = self._stat_card_compact(stats_row, 2, 'Registry')
        self.tasks_label = self._stat_card_compact(stats_row, 3, 'Tasks')
        self.disabled_label = self._stat_card_compact(stats_row, 4, 'Disabled')

        chips = ttk.Frame(self.startup_tab, style='Content.TFrame')
        chips.pack(fill='x', padx=10, pady=(0, 6))
        self._startup_chips = chips
        self.cat_all = ttk.Button(chips, text='All', style='Sidebar.TButton',
                                  command=lambda: self._set_category('All'))
        self.cat_folders = ttk.Button(chips, text='Folders', style='Sidebar.TButton',
                                      command=lambda: self._set_category('Folders'))
        self.cat_registry = ttk.Button(chips, text='Registry', style='Sidebar.TButton',
                                       command=lambda: self._set_category('Registry'))
        self.cat_tasks = ttk.Button(chips, text='Tasks', style='Sidebar.TButton',
                                    command=lambda: self._set_category('Tasks'))
        self.cat_disabled = ttk.Button(chips, text='Disabled', style='Sidebar.TButton',
                                       command=lambda: self._set_category('Disabled'))
        for btn in (self.cat_all, self.cat_folders, self.cat_registry,
                    self.cat_tasks, self.cat_disabled):
            btn.pack(side='left', padx=(0, 4))
        self._add_tooltip(self.cat_all, ctk_theme.STARTUP_FILTER_CONTEXT['All'][1])
        self._add_tooltip(self.cat_folders, ctk_theme.STARTUP_FILTER_CONTEXT['Folders'][1])
        self._add_tooltip(self.cat_registry, ctk_theme.STARTUP_FILTER_CONTEXT['Registry'][1])
        self._add_tooltip(self.cat_tasks, ctk_theme.STARTUP_FILTER_CONTEXT['Tasks'][1])
        self._add_tooltip(self.cat_disabled, ctk_theme.STARTUP_FILTER_CONTEXT['Disabled'][1])
        self._refresh_category_buttons()

        self.search_var = tk.StringVar()
        search = ttk.Entry(chips, textvariable=self.search_var, width=28, style='Search.TEntry')
        search.pack(side='right')
        search.insert(0, SEARCH_PLACEHOLDER)
        search.config(foreground=PLACEHOLDER)
        search.bind('<FocusIn>', self._clear_search_placeholder)
        search.bind('<FocusOut>', self._restore_search_placeholder)
        search.bind('<KeyRelease>', lambda e: self._on_search(self.search_var.get()))
        search.bind('<Return>', lambda e: self._on_search(self.search_var.get()))
        self.search_entry = search
        self._add_tooltip(search, 'Search by name, location, or command text. (Ctrl+F)')

        startup_actions = ttk.Frame(self.startup_tab, style='Content.TFrame')
        startup_actions.pack(fill='x', padx=10, pady=(0, 6))
        self._startup_actions = startup_actions
        self.refresh_btn = ttk.Button(startup_actions, text='Refresh', style='Primary.TButton',
                                      command=self.refresh)
        self.refresh_btn.pack(side='left')
        self.enable_btn = ttk.Button(startup_actions, text='Enable', style='Action.TButton',
                                     command=self.enable_selected)
        self.enable_btn.pack(side='left', padx=(8, 0))
        self.disable_btn = ttk.Button(startup_actions, text='Disable', style='Action.TButton',
                                      command=self.disable_selected)
        self.disable_btn.pack(side='left', padx=(6, 0))

        self._startup_container = ttk.Frame(self.startup_tab)
        self._startup_container.pack(fill='both', expand=True, padx=10, pady=(0, 4))

        self._startup_pane, startup_left, startup_right = create_horizontal_pane(
            self._startup_container, use_pack=True, min_left=300, min_right=260)
        self._bind_pane(self._startup_pane, 'startup_split', default=480)

        self._startup_tree_card = ttk.Frame(startup_left, style='Card.TFrame')
        self._startup_tree_card.pack(fill='both', expand=True)
        self._startup_tree_card.grid_rowconfigure(0, weight=1)
        self._startup_tree_card.grid_columnconfigure(0, weight=1)

        tree_frame = ttk.Frame(self._startup_tree_card, style='Card.TFrame')
        tree_frame.pack(fill='both', expand=True, padx=8, pady=8)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        cols = ('name', 'type', 'source', 'status')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        for col, label in (
            ('name', 'Name'), ('type', 'Type'), ('source', 'Source'), ('status', 'Status / Note'),
        ):
            self.tree.heading(col, text=label, command=lambda c=col: self._sort_column(c))
        self.tree.column('name', width=190, anchor='w', stretch=True)
        self.tree.column('type', width=110, anchor='w', stretch=False)
        self.tree.column('source', width=90, anchor='center', stretch=False)
        self.tree.column('status', width=160, anchor='w', stretch=True)
        self.tree.tag_configure('oddrow', background=CARD_BG)
        self.tree.tag_configure('evenrow', background=ROW_ALT)
        self._startup_rows = []
        self._startup_context_menu = None
        self._bind_selectable_table(
            self.tree,
            on_select=lambda: (self._update_detail(), self._update_actions()),
            on_double=self._on_startup_double_click,
            on_right=self._on_startup_right_click,
        )
        self.startup_empty_hint = self._make_empty_hint(
            self.tree, 'No startup items to show.\nTry clearing the search or switching category.')

        vscroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        hscroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vscroll.grid(row=0, column=1, sticky='ns')
        hscroll.grid(row=1, column=0, sticky='ew')

        self._startup_detail_panel = ttk.Frame(startup_right, style='Card.TFrame')
        self._startup_detail_panel.pack(fill='both', expand=True)
        detail_inner = ttk.Frame(self._startup_detail_panel, style='Card.TFrame')
        detail_inner.pack(fill='both', expand=True, padx=12, pady=12)
        ttk.Label(detail_inner, text='Details', font=('Segoe UI', 11, 'bold'),
                  background=CARD_BG).pack(anchor='w', pady=(0, 8))

        def _detail_row(label_text, attr_name):
            block = ttk.Frame(detail_inner, style='Card.TFrame')
            block.pack(fill='x', pady=(0, 8))
            ttk.Label(block, text=label_text, style='CardInfo.TLabel',
                      font=('Segoe UI', 9, 'bold')).pack(anchor='w')
            lbl = ttk.Label(block, text='—', style='CardInfo.TLabel', wraplength=280, justify='left')
            lbl.pack(anchor='w', pady=(2, 0))
            setattr(self, attr_name, lbl)
            return lbl

        self.detail_name = _detail_row('Name', 'detail_name')
        self.detail_type = _detail_row('Type', 'detail_type')
        self.detail_status = _detail_row('Status', 'detail_status')
        self.detail_location = _detail_row('Location', 'detail_location')
        self.detail_source = self.detail_type

        cmd_block = ttk.Frame(detail_inner, style='Card.TFrame')
        cmd_block.pack(fill='x', pady=(0, 8))
        ttk.Label(cmd_block, text='Command', style='CardInfo.TLabel',
                  font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.detail_command_text = tk.Text(
            cmd_block, height=4, wrap='word', font=('Consolas', 9), relief='flat',
            bg=PREVIEW_BG, fg=TEXT, insertbackground=TEXT, highlightthickness=0)
        self.detail_command_text.pack(fill='x', pady=(2, 0))
        self.detail_command_text.configure(state='disabled')

        self.detail_hint = ttk.Label(detail_inner, text='', style='CardInfo.TLabel',
                                     foreground=ACCENT, wraplength=280, justify='left')
        self.detail_hint.pack(anchor='w', pady=(4, 8))

        detail_btns = ttk.Frame(detail_inner, style='Card.TFrame')
        detail_btns.pack(fill='x')
        self.copy_command_detail = ttk.Button(detail_btns, text='Copy Command',
                                              style='Action.TButton', command=self.copy_command)
        self.copy_command_detail.pack(side='left')
        self.startup_open_loc_btn = ttk.Button(
            detail_btns, text='Open Location', style='Action.TButton',
            command=self._startup_open_file_location)
        self.startup_open_loc_btn.pack(side='left', padx=(8, 0))

        self._startup_split_mode = None
        self._startup_detail_frame = self._startup_detail_panel

        self._startup_empty_panel = self._build_workspace_empty_panel(
            self._startup_container,
            'No startup items',
            'Try Refresh, clear the search box, or switch category.',
            'Refresh', self.refresh,
        )
        self._startup_loading_lbl = ttk.Label(
            self._startup_container, text='Loading startup items…',
            style='Info.TLabel', anchor='center', font=('Segoe UI', 12))
        self._sync_startup_view(loading=False)

        self._add_tooltip(self.refresh_btn, 'Refresh the startup list from registry and startup folders.')
        self._add_tooltip(self.enable_btn, 'Enable the selected registry startup item.')
        self._add_tooltip(self.disable_btn, 'Disable the selected startup item (backed up, restorable).')
        self._add_tooltip(self.copy_command_detail, 'Copy the full command line to the clipboard.')

    def _build_cleaner_tab(self):
        self.cleanup_tab.grid_rowconfigure(3, weight=1)
        self.cleanup_tab.grid_columnconfigure(0, weight=1)

        hero = ctk_theme.frame(self.cleanup_tab, CARD_BG, corner_radius=10)
        hero.grid(row=0, column=0, sticky='ew', padx=10, pady=(4, 4))
        hero_inner = ttk.Frame(hero, style='Card.TFrame')
        hero_inner.pack(fill='x', padx=12, pady=8)
        title_row = ttk.Frame(hero_inner, style='Card.TFrame')
        title_row.pack(fill='x')
        ttk.Label(title_row, text='Cleaner', font=('Segoe UI', 15, 'bold'),
                  background=CARD_BG).pack(side='left')
        self.cleanup_status_hero = tk.Label(
            title_row, text='Ready to scan', bg=CARD_BG, fg=PROOF,
            font=('Segoe UI', 11, 'bold'))
        self.cleanup_status_hero.pack(side='left', padx=(12, 0))
        self.cleanup_msg_hero = ttk.Label(
            title_row, text='', style='Info.TLabel', wraplength=480)
        self.cleanup_msg_hero.pack(side='left', padx=(8, 0))
        cta_row = ttk.Frame(hero_inner, style='Card.TFrame')
        cta_row.pack(anchor='w', pady=(6, 0))
        self.scan_btn = ttk.Button(
            cta_row, text='Scan Now', style='Primary.TButton', command=self.refresh_cleanup)
        self.scan_btn.pack(side='left', ipadx=8, ipady=2)
        self.stop_scan_btn = ttk.Button(
            cta_row, text='Stop Scan', style='Action.TButton', command=self.stop_scan)
        self.cleaner_preview_btn = ttk.Button(
            cta_row, text='Preview Receipt', style='Action.TButton',
            command=self.preview_cleanup_receipt)
        self.cleaner_preview_btn.pack(side='left', padx=(8, 0))
        self.apply_clean_btn = ttk.Button(
            cta_row, text='Archive & Clean', style='Action.TButton', command=self.apply_cleanup)
        self.apply_clean_btn.pack(side='left', padx=(8, 0))

        chips = ttk.Frame(self.cleanup_tab, style='Content.TFrame')
        chips.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 6))
        self._cleanup_chips = chips
        for col in range(4):
            chips.grid_columnconfigure(col, weight=1)
        self.cleanup_count_label = ttk.Label(chips, text='0 candidates', style='Badge.TLabel')
        self.cleanup_count_label.grid(row=0, column=0, sticky='w', padx=(0, 8))
        self.cleanup_size_label = ttk.Label(chips, text='0B reclaimable', style='Badge.TLabel')
        self.cleanup_size_label.grid(row=0, column=1, sticky='w', padx=(0, 8))
        self.cleanup_archive_label = ttk.Label(chips, text='Archive: —', style='Badge.TLabel')
        self.cleanup_archive_label.grid(row=0, column=2, sticky='w', padx=(0, 8))
        self.cleanup_cat_lbl = ttk.Label(chips, text='', style='Badge.TLabel')
        self.cleanup_cat_lbl.grid(row=0, column=3, sticky='w')

        tools = ttk.Frame(self.cleanup_tab, style='Content.TFrame')
        tools.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 4))
        self._cleanup_tools = tools
        self.dedupe_check = ttk.Checkbutton(tools, text='Deduplicate', variable=self.dedupe_enabled)
        self.dedupe_check.pack(side='left')
        self.select_all_btn = ttk.Button(
            tools, text='Select All', style='Action.TButton',
            command=lambda: self._set_cleanup_selection(True))
        self.select_all_btn.pack(side='left', padx=(12, 0))
        self.select_none_btn = ttk.Button(
            tools, text='Select None', style='Action.TButton',
            command=lambda: self._set_cleanup_selection(False))
        self.select_none_btn.pack(side='left', padx=6)
        self.cleanup_progress = ttk.Progressbar(tools, mode='indeterminate', length=160)
        # Legacy spinner — hidden; premium scan panel is the sole scan surface.
        self.cleanup_progress.pack_forget()

        body = ttk.Frame(self.cleanup_tab, style='Content.TFrame')
        body.grid(row=3, column=0, sticky='nsew', padx=10, pady=(0, 4))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._cleanup_pane, cleanup_left, cleanup_right = create_horizontal_pane(body)
        self._bind_pane(self._cleanup_pane, 'cleaner_split', default=520)

        tree_card = ctk_theme.frame(cleanup_left, CARD_BG, corner_radius=10)
        tree_card.pack(fill='both', expand=True)
        tree_wrap = ttk.Frame(tree_card, style='Card.TFrame')
        tree_wrap.pack(fill='both', expand=True, padx=8, pady=8)
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)
        cleanup_cols = ('sel', 'size', 'reason')
        self.cleanup_tree = ttk.Treeview(
            tree_wrap, columns=cleanup_cols, show='tree headings', selectmode='browse')
        self.cleanup_tree.heading('#0', text='Item')
        self.cleanup_tree.heading('sel', text='✓', command=self._toggle_all_cleanup_selection)
        self.cleanup_tree.heading('size', text='Size')
        self.cleanup_tree.heading('reason', text='Category')
        self.cleanup_tree.column('#0', width=240, anchor='w', stretch=True, minwidth=120)
        self.cleanup_tree.column('sel', width=36, anchor='center', stretch=False, minwidth=36)
        self.cleanup_tree.column('size', width=80, anchor='center', stretch=False, minwidth=60)
        self.cleanup_tree.column('reason', width=120, anchor='w', stretch=False, minwidth=80)
        self.cleanup_tree.tag_configure('oddrow', background=CARD_BG)
        self.cleanup_tree.tag_configure('evenrow', background=ROW_ALT)
        self.cleanup_tree.tag_configure('group', foreground=MUTED)
        self.cleanup_tree.tag_configure('checked', background=PROOF_SOFT)
        self.cleanup_tree.bind('<Button-1>', self._on_cleanup_click)
        self.cleanup_tree.bind('<Double-Button-1>', self._on_cleanup_double_click)
        self.cleanup_tree.bind('<Button-3>', self._on_cleanup_right_click)
        self.cleanup_tree.bind('<Return>', lambda e: self._cleanup_open_location())
        self.cleanup_tree.bind('<space>', self._on_cleanup_space)
        self.cleanup_tree.bind('<<TreeviewSelect>>', lambda e: self._on_cleanup_select())
        for key in ('<Up>', '<Down>', '<Prior>', '<Next>'):
            self.cleanup_tree.bind(key, lambda e: self.after_idle(self._on_cleanup_select))
        for reason, color in REASON_COLORS.items():
            self.cleanup_tree.tag_configure(f'reason:{reason}', foreground=color)
        cleanup_vscroll = ttk.Scrollbar(tree_wrap, orient='vertical', command=self.cleanup_tree.yview)
        self.cleanup_tree.configure(yscrollcommand=cleanup_vscroll.set)
        self.cleanup_tree.grid(row=0, column=0, sticky='nsew')
        cleanup_vscroll.grid(row=0, column=1, sticky='ns')

        detail = ctk_theme.frame(cleanup_right, CARD_BG, corner_radius=10)
        detail.pack(fill='both', expand=True)
        detail_inner = ttk.Frame(detail, style='Card.TFrame')
        detail_inner.pack(fill='both', expand=True, padx=12, pady=12)
        ttk.Label(detail_inner, text='Candidate details', font=('Segoe UI', 11, 'bold'),
                  background=CARD_BG).pack(anchor='w', pady=(0, 8))
        self._cleanup_detail_name = ttk.Label(
            detail_inner, text='No candidate selected', style='CardInfo.TLabel', wraplength=260,
            font=('Segoe UI', 11, 'bold'))
        self._cleanup_detail_name.pack(anchor='w', pady=(0, 8))
        self._cleanup_detail_path = ttk.Label(
            detail_inner, text='', style='CardInfo.TLabel', wraplength=260, justify='left')
        self._cleanup_detail_reason = ttk.Label(
            detail_inner, text='', style='CardInfo.TLabel', wraplength=260, justify='left')
        self._cleanup_detail_size = ttk.Label(
            detail_inner, text='', style='CardInfo.TLabel', wraplength=260)
        self._cleanup_detail_archive = ttk.Label(
            detail_inner, text='', style='CardInfo.TLabel', wraplength=260, justify='left')
        self._cleanup_detail_receipt = ttk.Label(
            detail_inner, text='', style='CardInfo.TLabel', wraplength=260, justify='left')
        self._cleanup_detail_why = ttk.Label(
            detail_inner,
            text='Run Scan to populate candidates, then click a row to review path, archive destination, and safety notes.',
            style='CardInfo.TLabel', wraplength=260, justify='left', foreground=PROOF)
        for lbl in (
            self._cleanup_detail_path, self._cleanup_detail_reason, self._cleanup_detail_size,
            self._cleanup_detail_archive, self._cleanup_detail_receipt, self._cleanup_detail_why,
        ):
            lbl.pack(anchor='w', pady=(0, 8))
        cleaner_detail_btns = ttk.Frame(detail_inner, style='Card.TFrame')
        cleaner_detail_btns.pack(fill='x', pady=(4, 0))
        self._cleanup_btn_open = ttk.Button(
            cleaner_detail_btns, text='Open location', style='Action.TButton',
            command=self._cleanup_open_location)
        self._cleanup_btn_open.pack(side='left')
        self._cleanup_btn_copy = ttk.Button(
            cleaner_detail_btns, text='Copy path', style='Action.TButton',
            command=self._cleanup_copy_path)
        self._cleanup_btn_copy.pack(side='left', padx=(6, 0))
        self._cleanup_btn_exclude = ttk.Button(
            cleaner_detail_btns, text='Exclude', style='Action.TButton',
            command=self._cleanup_exclude_selected)
        self._cleanup_btn_exclude.pack(side='left', padx=(6, 0))
        self._cleanup_btn_preview = ttk.Button(
            cleaner_detail_btns, text='Preview receipt', style='Action.TButton',
            command=self._cleanup_preview_single)
        self._cleanup_btn_preview.pack(side='left', padx=(6, 0))

        self._cleanup_tree_card = tree_card
        self._cleanup_detail_panel = detail
        self._cleanup_empty_panel = ctk_theme.frame(body, CARD_BG, corner_radius=12)
        empty_inner = ttk.Frame(self._cleanup_empty_panel, style='Card.TFrame')
        empty_inner.place(relx=0.5, rely=0.42, anchor='center')
        ttk.Label(
            empty_inner, text='No cleanup candidates yet.',
            font=('Segoe UI', 16, 'bold'), background=CARD_BG,
        ).pack(anchor='center')
        ttk.Label(
            empty_inner,
            text='Run Scan to review configured folders.',
            style='Info.TLabel', wraplength=420, justify='center',
        ).pack(anchor='center', pady=(8, 16))
        ttk.Button(
            empty_inner, text='Scan Now', style='Primary.TButton', command=self.refresh_cleanup,
        ).pack(anchor='center')
        self._cleanup_loading_panel = ctk_theme.frame(body, CARD_BG, corner_radius=12)
        scan_inner = ttk.Frame(self._cleanup_loading_panel, style='Card.TFrame')
        scan_inner.place(relx=0.5, rely=0.44, anchor='center')
        self._scan_loading_title = ttk.Label(
            scan_inner, text='Scanning…', font=('Segoe UI', 16, 'bold'), background=CARD_BG)
        self._scan_loading_title.pack(anchor='center')
        self._scan_loading_sub = ttk.Label(
            scan_inner, text='Reviewing configured folders for candidates.',
            style='Info.TLabel', wraplength=520, justify='center')
        self._scan_loading_sub.pack(anchor='center', pady=(8, 12))
        self._scan_loading_bar = ttk.Progressbar(scan_inner, mode='indeterminate', length=360)
        self._scan_loading_bar.pack(anchor='center', pady=(0, 12))
        counters = ttk.Frame(scan_inner, style='Card.TFrame')
        counters.pack(anchor='center', pady=(0, 8))
        self._scan_counter_folders = ttk.Label(counters, text='Folders: 0', style='Badge.TLabel')
        self._scan_counter_folders.grid(row=0, column=0, padx=8)
        self._scan_counter_files = ttk.Label(counters, text='Files checked: 0', style='Badge.TLabel')
        self._scan_counter_files.grid(row=0, column=1, padx=8)
        self._scan_counter_candidates = ttk.Label(counters, text='Candidates: 0', style='Badge.TLabel')
        self._scan_counter_candidates.grid(row=0, column=2, padx=8)
        self._scan_counter_size = ttk.Label(counters, text='Reclaimable: 0B', style='Badge.TLabel')
        self._scan_counter_size.grid(row=1, column=0, padx=8, pady=(6, 0))
        self._scan_counter_elapsed = ttk.Label(counters, text='Elapsed: 0s', style='Badge.TLabel')
        self._scan_counter_elapsed.grid(row=1, column=1, padx=8, pady=(6, 0))
        scan_btn_row = ttk.Frame(scan_inner, style='Card.TFrame')
        scan_btn_row.pack(anchor='center', pady=(12, 0))
        self._scan_loading_stop = ttk.Button(
            scan_btn_row, text='Stop Scan', style='Action.TButton', command=self.stop_scan)
        self._scan_loading_stop.pack(side='left', padx=(0, 8))
        self.skip_scan_folder_btn = ttk.Button(
            scan_btn_row, text='Skip Folder', style='Action.TButton', command=self.skip_scan_folder)
        self.skip_scan_folder_btn.pack(side='left')
        self._update_cleanup_empty_state()

        status = ttk.Frame(self.cleanup_tab)
        status.grid(row=4, column=0, sticky='ew', padx=10, pady=(0, 8))
        self.cleanup_status_lbl = ttk.Label(status, text='Ready to scan.', style='Info.TLabel')
        self.cleanup_status_lbl.pack(side='left')
        self._add_tooltip(self.scan_btn, 'Scan configured folders for cleanup candidates.')
        self._add_tooltip(self.apply_clean_btn, 'Archive the checked candidate files.')
        self._add_tooltip(self.cleaner_preview_btn, 'Preview the Cleanroom Receipt before archiving.')
        self._add_tooltip(self.dedupe_check, 'Enable duplicate detection before archiving.')
        self._add_tooltip(self.select_all_btn, 'Check every candidate for cleanup.')
        self._add_tooltip(self.select_none_btn, 'Uncheck every candidate.')

    def _on_cleanup_select(self):
        sel = self.cleanup_tree.selection()
        if not sel or not self.cleanup_items:
            if not self.cleanup_items:
                self._cleanup_detail_name.config(text='No candidates yet')
                self._cleanup_detail_path.config(text='')
                self._cleanup_detail_reason.config(text='')
                self._cleanup_detail_size.config(text='')
                self._cleanup_detail_archive.config(text='')
                self._cleanup_detail_receipt.config(text='')
                self._cleanup_detail_why.config(
                    text='Run Scan to review configured folders, then select a row here.')
            else:
                checked = len(self.cleanup_selected or set())
                total = len(self.cleanup_items or [])
                self._cleanup_detail_name.config(text='No row selected')
                self._cleanup_detail_path.config(text='')
                self._cleanup_detail_reason.config(text='')
                self._cleanup_detail_size.config(text='')
                self._cleanup_detail_archive.config(text='')
                self._cleanup_detail_receipt.config(text='')
                if checked:
                    self._cleanup_detail_why.config(
                        text=(f'{checked} of {total} candidate(s) are checked for archive. '
                              'Click a row to inspect its path, reason, and archive destination.'))
                else:
                    self._cleanup_detail_why.config(
                        text=(f'{total} candidate(s) found. Check rows to include in archive, '
                              'then click a row to inspect details.'))
            for btn in (
                self._cleanup_btn_open, self._cleanup_btn_copy,
                self._cleanup_btn_exclude, self._cleanup_btn_preview,
            ):
                btn.config(state='disabled')
            return
        idx = self._cleanup_item_index(sel[0])
        if idx is None:
            if self._is_cleanup_group_row(sel[0]):
                gname = self.cleanup_tree.item(sel[0], 'text') or 'Group'
                self._cleanup_detail_name.config(text=gname)
                self._cleanup_detail_path.config(text='')
                self._cleanup_detail_reason.config(text='')
                self._cleanup_detail_size.config(text='')
                self._cleanup_detail_archive.config(text='')
                self._cleanup_detail_receipt.config(text='')
                self._cleanup_detail_why.config(
                    text='Expand the group and select a file to inspect path, reason, and archive destination.')
            for btn in (
                self._cleanup_btn_open, self._cleanup_btn_copy,
                self._cleanup_btn_exclude, self._cleanup_btn_preview,
            ):
                btn.config(state='disabled')
            return
        if idx < 0 or idx >= len(self.cleanup_items):
            return
        item = self.cleanup_items[idx]
        path = item.get('path') or '—'
        name = Path(path).name if path and path != '—' else '—'
        reason = item.get('reason') or 'other'
        cfg = self._cached_cfg() or {}
        archive_dest = self._planned_archive_dest(item, cfg)
        checked = idx in self.cleanup_selected
        self._cleanup_detail_name.config(text=name)
        self._cleanup_detail_path.config(text=f'Path:\n{path}')
        self._cleanup_detail_reason.config(text=f'Category: {reason}')
        self._cleanup_detail_size.config(text=f'Size: {self._format_size(item.get("size", 0))}')
        self._cleanup_detail_archive.config(text=f'Archive destination:\n{archive_dest}')
        self._cleanup_detail_receipt.config(
            text='Receipt: Draft on preview' if checked else 'Receipt: Not included until checked')
        self._cleanup_detail_why.config(text=self._cleanup_reason_hint(reason))
        for btn in (
            self._cleanup_btn_open, self._cleanup_btn_copy,
            self._cleanup_btn_exclude, self._cleanup_btn_preview,
        ):
            btn.config(state='normal')

    def _on_cleanup_double_click(self, _event=None):
        self._on_cleanup_select()
        self._cleanup_open_location()

    def _on_cleanup_right_click(self, event):
        row = self.cleanup_tree.identify_row(event.y)
        if row:
            self.cleanup_tree.selection_set(row)
            self.cleanup_tree.focus(row)
        self._on_cleanup_select()
        idx = self._selected_cleanup_index()
        has = idx is not None
        checked = idx in self.cleanup_selected if idx is not None else False
        scan_done = getattr(self, '_scan_session_done', False)
        can_archive = (
            scan_done and bool(self.cleanup_selected)
            and not getattr(self, '_cleaner_loading', False)
        )
        self._show_row_popover(
            event.x_root, event.y_root,
            [
                ('Check selected' if not checked else 'Uncheck selected',
                 lambda: self._toggle_cleanup_index(idx) if idx is not None else None, has),
                ('Select all in category', self._cleanup_select_in_category, has),
                ('Open file location', self._cleanup_open_location, has),
                ('Copy path', self._cleanup_copy_path, has),
                ('Copy item details', self._cleanup_copy_item_details, has),
                ('Preview receipt for selection', self._cleanup_preview_single, has),
                ('Review risk/details', self._on_cleanup_select, has),
                ('Exclude from future scans', self._cleanup_exclude_selected, has),
                ('Archive selected', self.apply_cleanup, can_archive),
            ],
            title='Candidate',
        )
        return 'break'

    def _cleanup_select_in_category(self):
        sel = self.cleanup_tree.selection()
        if not sel or self._is_cleanup_group_row(sel[0]):
            return
        parent = self.cleanup_tree.parent(sel[0])
        if not parent:
            return
        for child in self.cleanup_tree.get_children(parent):
            cidx = self._cleanup_item_index(child)
            if cidx is not None:
                self.cleanup_selected.add(cidx)
        self._update_cleanup_tree()
        self._update_cleanup_summary(self._cached_cfg())

    def _cleanup_copy_item_details(self):
        idx = self._selected_cleanup_index()
        if idx is None:
            return
        item = self.cleanup_items[idx]
        cfg = self._cached_cfg() or {}
        text = (
            f"Path: {item.get('path') or '—'}\n"
            f"Reason: {item.get('reason') or '—'}\n"
            f"Size: {self._format_size(item.get('size', 0))}\n"
            f"Planned archive: {self._planned_archive_dest(item, cfg)}"
        )
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Item details copied.')
        except tk.TclError:
            messagebox.showinfo('Item details', text)

    def _cleanup_reason_hint(self, reason: str) -> str:
        hints = {
            'zero-byte': 'Empty file past age threshold — usually safe to archive.',
            'partial-download': 'Abandoned partial download — typically safe to archive.',
            'installer/archive': 'Old installer or archive — review before archiving.',
            'large-file': 'Large file — review carefully; highest reclaim per item.',
        }
        return hints.get(reason, 'Review the path — archive only if you recognize and no longer need it.')

    def _planned_archive_dest(self, item, cfg):
        path = item.get('path') or ''
        if not path:
            return '—'
        archive_dir = (cfg or {}).get('archive_dir') or '(auto archive folder on apply)'
        name = Path(path).name
        return f'{archive_dir}/{name}'

    def _cleanup_group_for_reason(self, reason):
        r = reason or 'other'
        for label, keys in CLEANUP_REASON_GROUPS:
            if keys is None:
                return label
            if r in keys:
                return label
        return 'Other'

    def _is_cleanup_group_row(self, row_id):
        if not row_id:
            return False
        return 'group' in self.cleanup_tree.item(row_id, 'tags')

    def _cleanup_item_index(self, row_id):
        if not row_id or self._is_cleanup_group_row(row_id):
            return None
        for tag in self.cleanup_tree.item(row_id, 'tags'):
            if tag.startswith('idx:'):
                try:
                    return int(tag[4:])
                except ValueError:
                    pass
        return None

    def _refresh_cleanup_group_headers(self):
        for gid in self.cleanup_tree.get_children(''):
            if not self._is_cleanup_group_row(gid):
                continue
            checked_n = 0
            total_n = 0
            for row in self.cleanup_tree.get_children(gid):
                idx = self._cleanup_item_index(row)
                if idx is None:
                    continue
                total_n += 1
                if idx in self.cleanup_selected:
                    checked_n += 1
            label = (self.cleanup_tree.item(gid, 'text') or 'Group').split(' (')[0]
            self.cleanup_tree.item(gid, text=f'{label} ({total_n})')
            self.cleanup_tree.set(gid, 'size', f'{checked_n} checked')

    def _selected_cleanup_index(self):
        sel = self.cleanup_tree.selection()
        if not sel or not self.cleanup_items:
            return None
        return self._cleanup_item_index(sel[0])

    def _cleanup_open_location(self):
        idx = self._selected_cleanup_index()
        if idx is None:
            return
        path = self.cleanup_items[idx].get('path')
        if not path:
            return
        folder = Path(path).parent
        if folder.is_dir():
            try:
                os.startfile(str(folder))
            except OSError as e:
                messagebox.showerror('Open location', str(e))
        else:
            messagebox.showinfo('Open location', 'Folder not found on disk.')

    def _cleanup_copy_path(self):
        idx = self._selected_cleanup_index()
        if idx is None:
            return
        path = self.cleanup_items[idx].get('path') or ''
        try:
            self.clipboard_clear()
            self.clipboard_append(path)
            self._set_status('Path copied to clipboard.')
        except tk.TclError:
            messagebox.showinfo('Copy path', path)

    def _cleanup_exclude_selected(self):
        idx = self._selected_cleanup_index()
        if idx is None:
            return
        item = self.cleanup_items.pop(idx)
        self.cleanup_selected = {i if i < idx else i - 1 for i in self.cleanup_selected if i != idx}
        self._update_cleanup_tree()
        self._update_cleanup_summary(self._cached_cfg())
        self._set_status(
            f'Removed from scan: {Path(item.get("path") or "").name}. '
            'Add an exclude pattern in Settings → Advanced to persist.')

    def _cleanup_preview_single(self):
        idx = self._selected_cleanup_index()
        if idx is None:
            return
        if idx not in self.cleanup_selected:
            self.cleanup_selected.add(idx)
            self._update_cleanup_tree()
        self.preview_cleanup_receipt()

    def _update_cleaner_hero(self):
        self._sync_cleaner_state()

    def _populate_recommendation_cards(self, recs):
        if not hasattr(self, '_rec_cards_scroll'):
            return
        for child in self._rec_cards_scroll.winfo_children():
            child.destroy()
        self._rec_card_frames = []
        for i, r in enumerate(recs):
            card = recommendation_card(
                self._rec_cards_scroll,
                index=i,
                severity=r.get('severity', 'info'),
                title=r.get('title', ''),
                detail=r.get('detail', ''),
                card_bg=CARD_BG,
                text_color=TEXT,
                muted=MUTED,
                accent=ACCENT,
                border=BORDER,
                on_select=self._select_recommendation_card,
                on_double=lambda idx: self._recommendation_primary_action(),
                on_right=self._on_recommendation_card_right,
            )
            card.pack(fill='x', pady=(0, 8), padx=2)
            self._rec_card_frames.append(card)

    def _select_recommendation_card(self, index: int):
        self._selected_rec_idx = index
        for i, card in enumerate(self._rec_card_frames):
            try:
                card.configure(border_color=ACCENT if i == index else BORDER)
            except Exception:
                pass
        self._on_recommendation_select()

    def _on_recommendation_card_right(self, event, index: int):
        self._select_recommendation_card(index)
        rec = self._selected_recommendation()
        has = rec is not None
        title = (rec.get('title') or '').lower() if rec else ''
        is_archive = 'archive' in title and 'candidate' in title
        is_large = 'large' in title
        has_receipt = bool(getattr(self, '_scan_session_done', False) and self.cleanup_items)
        self._show_row_popover(
            event.x_root, event.y_root,
            [
                ('Open related page', self._recommendation_primary_action, has),
                ('View details', self._recommendation_primary_action, has),
                ('Copy recommendation', self._recommendation_copy_details, has),
                ('Copy proof summary', self._copy_latest_receipt_summary, has_receipt),
                ('Open receipt', self.preview_cleanup_receipt, has_receipt),
                ('Open Proof Ledger', lambda: self._navigate_to_tab(1), True),
                ('Review candidates', lambda: self._navigate_to_tab(3), is_archive),
                ('Open Cleaner (large files)', self._recommendation_open_large_files, is_large),
            ],
            title='Recommendation',
        )

    def _recommendation_open_large_files(self):
        self._navigate_to_tab(3)

    def _build_restore_tab(self):
        header = ttk.Frame(self.restore_tab, style='Content.TFrame')
        header.pack(fill='x', padx=10, pady=10)
        ttk.Label(header, text='Restore', style='Header.TLabel').pack(anchor='w')
        ttk.Label(header, text='Restore archived files safely from the cleanup log.',
                  style='SubHeader.TLabel').pack(anchor='w', pady=(4, 0))

        controls = ttk.Frame(self.restore_tab, style='Content.TFrame')
        controls.pack(fill='x', padx=10, pady=(8, 4))
        btn_row = ttk.Frame(controls, style='Content.TFrame')
        btn_row.pack(fill='x')
        self.reload_restore_btn = ttk.Button(btn_row, text='Reload Log', style='Action.TButton',
                                             command=self.refresh_restore)
        self.reload_restore_btn.pack(side='left')
        self.restore_selected_btn = ttk.Button(btn_row, text='Restore Selected', style='Action.TButton',
                                               command=self.restore_selected_entry)
        self.restore_selected_btn.pack(side='left', padx=6)
        self.restore_all_btn = ttk.Button(btn_row, text='Restore All', style='Action.TButton',
                                          command=self.restore_all_entries)
        self.restore_all_btn.pack(side='left', padx=6)
        self.time_machine_btn = ttk.Button(btn_row, text='🕐 Cleanroom Rewind', style='Action.TButton',
                                           command=self.open_time_machine)
        self.time_machine_btn.pack(side='left', padx=6)
        self.delete_restore_archive_btn = ttk.Button(
            btn_row, text='Delete from Archive…', style='Action.TButton',
            command=self.confirm_delete_restore_selected)
        self.delete_restore_archive_btn.pack(side='left', padx=6)
        self._add_tooltip(self.time_machine_btn,
                          'See every cleanup day at a glance and roll a whole day back.')
        self._add_tooltip(self.delete_restore_archive_btn,
                          'Permanently delete the archived copy of the selected item.\n'
                          'Original live files are not touched.')
        filter_row = ttk.Frame(controls, style='Content.TFrame')
        filter_row.pack(fill='x', pady=(6, 0))
        self.restore_filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_row, textvariable=self.restore_filter_var, width=28, style='Search.TEntry')
        filter_entry.pack(side='right')
        filter_entry.bind('<Return>', lambda e: self.refresh_restore())
        ttk.Label(filter_row, text='Filter:', style='Info.TLabel').pack(side='right', padx=(0, 6))

        restore_frame = ttk.Frame(self.restore_tab)
        restore_frame.pack(fill='both', expand=True, padx=10, pady=(6, 10))
        self._restore_frame = restore_frame

        self._restore_pane, restore_left, restore_right = create_horizontal_pane(
            restore_frame, use_pack=True)
        self._bind_pane(self._restore_pane, 'restore_split', default=520)

        self._restore_empty_panel = self._build_workspace_empty_panel(
            restore_frame,
            'No restore entries',
            'Archived files appear here after a cleanup.',
            'Reload Log', self.refresh_restore,
        )
        self._restore_loading_lbl = ttk.Label(
            restore_frame, text='Loading restore log…',
            style='Info.TLabel', anchor='center', font=('Segoe UI', 12))

        restore_left.grid_rowconfigure(0, weight=1)
        restore_left.grid_columnconfigure(0, weight=1)
        self._restore_left = restore_left
        restore_cols = ('src', 'dest', 'time')
        self.restore_tree = ttk.Treeview(restore_left, columns=restore_cols, show='headings', selectmode='browse')
        self.restore_tree.heading('src', text='Original Path')
        self.restore_tree.heading('dest', text='Archived Path')
        self.restore_tree.heading('time', text='Time')
        self.restore_tree.column('src', width=240, anchor='w', stretch=True, minwidth=120)
        self.restore_tree.column('dest', width=240, anchor='w', stretch=True, minwidth=120)
        self.restore_tree.column('time', width=140, anchor='center', stretch=False, minwidth=100)
        self.restore_tree.tag_configure('oddrow', background=CARD_BG)
        self.restore_tree.tag_configure('evenrow', background=ROW_ALT)
        self.restore_empty_hint = self._make_empty_hint(
            self.restore_tree, 'No restore entries.\nArchived files appear here after a cleanup.')
        self._refresh_empty_hint(self.restore_empty_hint, self.restore_tree)
        restore_vscroll = ttk.Scrollbar(restore_left, orient='vertical', command=self.restore_tree.yview)
        restore_hscroll = ttk.Scrollbar(restore_left, orient='horizontal', command=self.restore_tree.xview)
        self.restore_tree.configure(yscrollcommand=restore_vscroll.set, xscrollcommand=restore_hscroll.set)
        self.restore_tree.grid(row=0, column=0, sticky='nsew')
        restore_vscroll.grid(row=0, column=1, sticky='ns')
        restore_hscroll.grid(row=1, column=0, sticky='ew')

        right = ttk.Frame(restore_right, style='Card.TFrame')
        self._restore_preview_panel = right
        right.pack(fill='both', expand=True)
        ttk.Label(right, text='Preview', font=('Segoe UI', 11, 'bold'), background=CARD_BG).pack(anchor='w', padx=8, pady=(8, 4))
        self.restore_detail_src = ttk.Label(right, text='Original: —', style='CardInfo.TLabel', wraplength=360, justify='left')
        self.restore_detail_dest = ttk.Label(right, text='Archived: —', style='CardInfo.TLabel', wraplength=360, justify='left')
        self.restore_detail_time = ttk.Label(right, text='Time: —', style='CardInfo.TLabel')
        self.restore_detail_exists = ttk.Label(right, text='Archived exists: —', style='CardInfo.TLabel')
        self.restore_detail_size = ttk.Label(right, text='Size: —', style='CardInfo.TLabel')
        self.restore_detail_src.pack(anchor='w', padx=8, pady=(6, 2))
        self.restore_detail_dest.pack(anchor='w', padx=8, pady=(2, 2))
        self.restore_detail_time.pack(anchor='w', padx=8, pady=(2, 2))
        self.restore_detail_exists.pack(anchor='w', padx=8, pady=(2, 2))
        self.restore_detail_size.pack(anchor='w', padx=8, pady=(2, 8))

        detail_actions = ttk.Frame(right, style='Card.TFrame')
        detail_actions.pack(side='bottom', fill='x', padx=8, pady=(0, 8))
        self.preview_btn = ttk.Button(detail_actions, text='Preview (Dry-run)', style='Action.TButton',
                                      command=self.restore_selected_entry)
        self.preview_btn.pack(side='left')
        self.apply_restore_btn = ttk.Button(detail_actions, text='Restore Now', style='Primary.TButton',
                                            command=lambda: self.restore_selected_entry(apply=True))
        self.apply_restore_btn.pack(side='left', padx=6)
        self.open_archived_btn = ttk.Button(detail_actions, text='Open Archived', style='Action.TButton',
                                            command=self._open_archived_selected)
        self.open_archived_btn.pack(side='left', padx=6)
        self.delete_restore_detail_btn = ttk.Button(
            detail_actions, text='Delete from Archive…', style='Action.TButton',
            command=self.confirm_delete_restore_selected)
        self.delete_restore_detail_btn.pack(side='left', padx=6)
        self._add_tooltip(self.delete_restore_detail_btn,
                          'Permanently delete this archived copy. Original live files are not touched.')

        preview_box = ttk.Labelframe(right, text='File preview', style='Detail.TLabelframe')
        preview_box.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self._preview_photo = None
        self.preview_image_label = ttk.Label(preview_box, background=CARD_BG, anchor='center')
        self.preview_text = tk.Text(preview_box, height=8, wrap='none', state='disabled',
                                    font=('Consolas', 9), background=PREVIEW_BG, relief='flat',
                                    borderwidth=0, foreground=TEXT, insertbackground=TEXT)
        self.preview_text.pack(fill='both', expand=True, padx=6, pady=6)

        self.restore_tree.bind('<<TreeviewSelect>>', lambda e: self._on_restore_select())
        self.restore_tree.bind('<Return>', lambda e: self.restore_selected_entry())
        self.restore_tree.bind('<Button-3>', self._on_restore_right_click)

        status = ttk.Frame(self.restore_tab)
        status.pack(fill='x', padx=10, pady=(0, 10))
        self.restore_status_lbl = ttk.Label(status, text='Ready to restore from cleanup_log.json.', style='Info.TLabel')
        self.restore_status_lbl.pack(side='left')

        self._add_tooltip(self.reload_restore_btn, 'Reload archived restore entries from cleanup_log.json.')
        self._add_tooltip(self.restore_selected_btn, 'Preview then restore the selected archived file.')
        self._add_tooltip(self.restore_all_btn, 'Preview then restore all displayed archived entries.')
        self._add_tooltip(self.preview_btn, 'Dry-run: shows what the restore would do.')
        self._add_tooltip(self.apply_restore_btn, 'Restore the selected file immediately.')
        self._add_tooltip(self.open_archived_btn, 'Open the archived copy with its default application.')

    def _build_settings_tab(self):
        self.settings_tab.grid_rowconfigure(0, weight=1)
        self.settings_tab.grid_columnconfigure(0, weight=1)

        body = ttk.Frame(self.settings_tab, style='Content.TFrame')
        body.grid(row=0, column=0, sticky='nsew', padx=6, pady=(4, 8))
        body.grid_rowconfigure(2, weight=1)
        body.grid_rowconfigure(3, weight=0, minsize=52)
        body.grid_columnconfigure(0, weight=1)

        hdr = ctk_theme.frame(body, BG)
        hdr.grid(row=0, column=0, sticky='ew', pady=(0, 2))
        ctk_theme.label(
            hdr, 'Settings', text_color=TEXT, font_size=ctk_theme.TYPE_PAGE, weight='bold',
        ).pack(anchor='w')
        ctk_theme.label(
            hdr, 'Scan paths, archive rules, and application preferences.',
            text_color=MUTED, font_size=ctk_theme.TYPE_MICRO,
        ).pack(anchor='w', pady=(2, 0))

        pill_host = ctk_theme.frame(body, BG)
        pill_host.grid(row=1, column=0, sticky='ew', pady=(0, 6))

        content = ctk.CTkScrollableFrame(
            body, fg_color=BG, corner_radius=10,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=ACCENT_SOFT,
        )
        content.grid(row=2, column=0, sticky='nsew')

        self._settings_section_frames = {}
        for name in ('General', 'Scan', 'Archive', 'Explorer', 'Receipts', 'Advanced'):
            frame = ctk_theme.frame(content, BG)
            self._settings_section_frames[name] = frame

        def _select_settings_section(name):
            for key, frame in self._settings_section_frames.items():
                if key == name:
                    frame.pack(fill='x', padx=2, pady=2)
                else:
                    frame.pack_forget()
            for key, btn in self._settings_nav_btns.items():
                if key == name:
                    btn.configure(fg_color=ACCENT_SOFT, text_color=ACCENT,
                                  font=ctk_theme.font(11, 'bold'))
                else:
                    btn.configure(fg_color='transparent', text_color=TEXT,
                                  font=ctk_theme.font(11, 'normal'))

        self._settings_nav_btns = settings_pill_nav(
            pill_host,
            (
                ('General', 'General'),
                ('Scan folders', 'Scan'),
                ('Archive custody', 'Archive'),
                ('Explorer', 'Explorer'),
                ('Receipts', 'Receipts'),
                ('Advanced', 'Advanced'),
            ),
            bg=BG, accent=ACCENT_SOFT, muted=MUTED, text_color=TEXT,
            on_select=_select_settings_section,
        )
        self._select_settings_section = _select_settings_section
        _select_settings_section('General')

        general = self._settings_section_frames['General']

        local_body = settings_card(general, 'Local-only proof mode', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            local_body, ctk_theme.LOCAL_ONLY_TEXT, text_color=TEXT, font_size=11,
            wraplength=680, justify='left',
        ).pack(anchor='w')
        ctk_theme.label(
            local_body,
            'All receipts, custody checks, and proof packs stay on this PC. '
            'Nothing is uploaded or shared.',
            text_color=MUTED, font_size=10, wraplength=680, justify='left',
        ).pack(anchor='w', pady=(6, 0))

        app_body = settings_card(general, 'Application', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            app_body,
            'Startup behavior, appearance, and window preferences.',
            text_color=MUTED, font_size=10, wraplength=680, justify='left',
        ).pack(anchor='w', pady=(0, 8))

        self.set_scan_on_startup = tk.BooleanVar(
            value=bool(load_ui_prefs().get('scan_on_startup', False)))
        ctk_theme.switch(
            app_body, 'Scan on startup (default off)', self.set_scan_on_startup,
            text_color=TEXT, progress_color=ACCENT,
            button_color=BORDER, button_hover_color=ACCENT,
        ).pack(anchor='w', pady=(0, 8))

        self.set_remember_geometry = tk.BooleanVar(
            value=bool(load_ui_prefs().get('remember_window_geometry', True)))
        ctk_theme.switch(
            app_body, 'Remember window size and position', self.set_remember_geometry,
            text_color=TEXT, progress_color=ACCENT,
            button_color=BORDER, button_hover_color=ACCENT,
        ).pack(anchor='w', pady=(0, 8))

        self.set_remember_last_tab = tk.BooleanVar(
            value=bool(load_ui_prefs().get('remember_last_tab', True)))
        ctk_theme.switch(
            app_body, 'Remember last tab on launch', self.set_remember_last_tab,
            text_color=TEXT, progress_color=ACCENT,
            button_color=BORDER, button_hover_color=ACCENT,
        ).pack(anchor='w', pady=(0, 8))

        theme_row = ttk.Frame(app_body, style='Card.TFrame')
        theme_row.pack(fill='x', pady=(0, 4))
        ttk.Label(theme_row, text='Theme:', style='CardInfo.TLabel').pack(side='left')
        self.set_theme_var = tk.StringVar(value=PALETTES[CURRENT_THEME]['LABEL'])
        theme_combo = ttk.Combobox(theme_row, textvariable=self.set_theme_var, state='readonly',
                                   values=[PALETTES[t]['LABEL'] for t in THEME_ORDER], width=28)
        theme_combo.pack(side='left', padx=(8, 0))
        self._add_tooltip(theme_combo, 'Applied when you click Save Settings (window rebuilds).')

        launch_row = ttk.Frame(app_body, style='Card.TFrame')
        launch_row.pack(fill='x', pady=(4, 0))
        ttk.Label(launch_row, text='Default tab when not remembering:',
                  style='CardInfo.TLabel').pack(side='left')
        self.set_default_tab_var = tk.StringVar(value='Home')
        ttk.Combobox(
            launch_row, textvariable=self.set_default_tab_var, state='readonly', width=24,
            values=('Home', 'Activity', 'Startup', 'Cleaner', 'Archive', 'Settings'),
        ).pack(side='left', padx=(8, 0))

        config_body = settings_card(general, 'Configuration', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            config_body,
            'Cleanup rules live in a local YAML file. Open it to inspect or edit directly.',
            text_color=MUTED, font_size=10, wraplength=680, justify='left',
        ).pack(anchor='w', pady=(0, 8))
        self._settings_config_path_lbl = ctk_theme.label(
            config_body, '', text_color=TEXT, font_size=10, wraplength=680, justify='left')
        self._settings_config_path_lbl.pack(anchor='w', pady=(0, 8))
        cfg_btns = ttk.Frame(config_body, style='Card.TFrame')
        cfg_btns.pack(fill='x')
        ttk.Button(cfg_btns, text='Open config file', style='Action.TButton',
                   command=self._settings_open_config).pack(side='left')
        ttk.Button(cfg_btns, text='Open data folder', style='Action.TButton',
                   command=self._settings_open_data_dir).pack(side='left', padx=(8, 0))

        shell_body = settings_card(
            self._settings_section_frames['Explorer'], 'Explorer integration', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            shell_body,
            'Advanced utility — install Cleanroom actions in File Explorer (per-user HKCU). '
            'Choose presets, add custom menus, then Install or Remove from Explorer.',
            text_color=MUTED, font_size=10, wraplength=720, justify='left',
        ).pack(anchor='w', pady=(0, 8))
        shell_row = ttk.Frame(shell_body, style='Card.TFrame')
        shell_row.pack(anchor='w')
        self._settings_shell_btn = ttk.Button(
            shell_row, text='Open Context Menu Editor…', style='Action.TButton',
            command=self.open_shell_context_menu_tool,
        )
        self._settings_shell_btn.pack(side='left')
        ctk_theme.label(
            shell_row,
            'Also available under sidebar → Tools.',
            text_color=MUTED, font_size=9,
        ).pack(side='left', padx=(10, 0), pady=(4, 0))

        self._settings_downloads_path = str(
            Path(os.environ.get('USERPROFILE', Path.home())) / 'Downloads')
        self._settings_temp_path = os.environ.get('TEMP') or str(
            Path(os.environ.get('USERPROFILE', Path.home())) / 'AppData' / 'Local' / 'Temp')

        self.set_scan_downloads = tk.BooleanVar(value=True)
        self.set_scan_temp = tk.BooleanVar(value=True)
        self.set_relaxed_scan = tk.BooleanVar(value=False)
        self.set_dedupe_default = self.dedupe_enabled

        scan_body = settings_card(
            self._settings_section_frames['Scan'], 'Scan folders', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            scan_body,
            'Folders Cleanroom scans, age thresholds, and quick toggles. Save Settings to apply.',
            text_color=MUTED, font_size=10, wraplength=720, justify='left',
        ).pack(anchor='w', pady=(0, 8))

        scan_cols = ttk.Frame(scan_body, style='Card.TFrame')
        scan_cols.pack(fill='both', expand=True)
        paths_col = ttk.Frame(scan_cols, style='Card.TFrame')
        paths_col.pack(side='left', fill='both', expand=True, padx=(0, 10))
        ttk.Label(paths_col, text='Folders to scan', style='CardInfo.TLabel').pack(anchor='w', pady=(0, 4))
        self.set_paths_list = tk.Listbox(paths_col, height=5, activestyle='dotbox',
                                         font=('Segoe UI', 10), relief='flat',
                                         bg=PREVIEW_BG, fg=TEXT, selectbackground=ACCENT,
                                         selectforeground=ON_ACCENT,
                                         highlightthickness=0)
        self.set_paths_list.pack(fill='both', expand=True)
        self.set_paths_list.bind('<Button-3>', self._on_settings_paths_right_click)
        path_btns = ttk.Frame(paths_col, style='Card.TFrame')
        path_btns.pack(fill='x', pady=(6, 0))
        ttk.Button(path_btns, text='Add Folder…', style='Action.TButton',
                   command=self._settings_add_path).pack(side='left')
        ttk.Button(path_btns, text='Remove Selected', style='Action.TButton',
                   command=self._settings_remove_path).pack(side='left', padx=6)

        opts_col = ttk.Frame(scan_cols, style='Card.TFrame')
        opts_col.pack(side='left', fill='both', expand=True)
        ttk.Label(
            opts_col, text='Quick scan toggles', style='CardInfo.TLabel',
        ).pack(anchor='w', pady=(0, 6))

        quick_grid = ctk_theme.frame(opts_col, CARD_BG)
        quick_grid.pack(fill='x')
        for col in range(2):
            quick_grid.columnconfigure(col, weight=1)

        def _quick_switch(row, col, text, var, command=None):
            sw = ctk_theme.switch(
                quick_grid, text, var, command,
                text_color=TEXT, progress_color=ACCENT,
                button_color=BORDER, button_hover_color=ACCENT,
            )
            sw.grid(row=row, column=col, sticky='w', padx=(0, 16), pady=4)
            return sw

        _quick_switch(0, 0, 'Scan Downloads folder', self.set_scan_downloads)
        _quick_switch(0, 1, 'Scan Temp folder', self.set_scan_temp)
        _quick_switch(1, 0, 'Relaxed scan (for testing / empty folders)',
                       self.set_relaxed_scan, self._settings_relaxed_toggle)
        _quick_switch(1, 1, 'Deduplicate before archive', self.set_dedupe_default)

        self.set_temp_age = tk.IntVar(value=7)
        self.set_installer_age = tk.IntVar(value=30)
        self.set_size_mb = tk.IntVar(value=200)
        self.set_confirm_gb = tk.DoubleVar(value=5.0)
        self.set_ext_var = tk.StringVar()

        archive_body = settings_card(
            self._settings_section_frames['Archive'], 'Archive location & thresholds', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            archive_body,
            'Where archived copies are stored and when files become eligible for custody review.',
            text_color=MUTED, font_size=10, wraplength=720, justify='left',
        ).pack(anchor='w', pady=(0, 8))
        archive_grid = ttk.Frame(archive_body, style='Card.TFrame')
        archive_grid.pack(fill='x')
        ttk.Label(archive_grid, text='Archive folder:', style='CardInfo.TLabel').grid(
            row=0, column=0, sticky='w', pady=3)
        self.set_archive_var = tk.StringVar()
        ttk.Entry(archive_grid, textvariable=self.set_archive_var, width=32,
                  style='Search.TEntry').grid(row=0, column=1, sticky='we', pady=3)
        ttk.Button(archive_grid, text='Browse…', style='Action.TButton',
                   command=self._settings_browse_archive).grid(row=0, column=2, padx=(6, 0), pady=3)

        def spin_row(row, label, var, lo, hi, inc=1):
            ttk.Label(archive_grid, text=label, style='CardInfo.TLabel').grid(
                row=row, column=0, sticky='w', pady=3)
            ttk.Spinbox(archive_grid, from_=lo, to=hi, increment=inc, textvariable=var,
                        width=10).grid(row=row, column=1, sticky='w', pady=3)

        spin_row(1, 'Temp files — archive after (days):', self.set_temp_age, 1, 365)
        spin_row(2, 'Installers — archive after (days):', self.set_installer_age, 1, 3650)
        spin_row(3, 'Large file threshold (MB):', self.set_size_mb, 1, 1024 * 100)
        spin_row(4, 'Confirm archive above (GB):', self.set_confirm_gb, 0.1, 1000, 0.5)
        ttk.Label(archive_grid, text='Archive extensions (comma-sep):',
                  style='CardInfo.TLabel').grid(row=5, column=0, sticky='w', pady=3)
        ttk.Entry(archive_grid, textvariable=self.set_ext_var, width=32,
                  style='Search.TEntry').grid(row=5, column=1, columnspan=2, sticky='we', pady=3)
        archive_grid.columnconfigure(1, weight=1)

        custody_body = settings_card(
            self._settings_section_frames['Archive'], 'Custody rules', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            custody_body,
            'Control when archived copies become safe to delete. Deleting from archive removes '
            'the archived copy only — original live files are never touched.',
            text_color=MUTED, font_size=10, wraplength=720, justify='left',
        ).pack(anchor='w', pady=(0, 8))
        custody_grid = ttk.Frame(custody_body, style='Card.TFrame')
        custody_grid.pack(fill='x')
        self.set_prune_recent_days = tk.IntVar(value=7)
        ttk.Label(custody_grid, text='Protect archive items newer than (days):',
                  style='CardInfo.TLabel').grid(row=0, column=0, sticky='w', pady=3)
        ttk.Spinbox(custody_grid, from_=0, to=365, textvariable=self.set_prune_recent_days,
                    width=10).grid(row=0, column=1, sticky='w', pady=3, padx=(8, 0))
        ttk.Label(custody_grid, text='(0 = no protection)',
                  style='Info.TLabel').grid(row=0, column=2, sticky='w', padx=(8, 0), pady=3)
        archive_btns = ttk.Frame(custody_body, style='Card.TFrame')
        archive_btns.pack(fill='x', pady=(8, 0))
        ttk.Button(archive_btns, text='Open Archive Browser…', style='Action.TButton',
                   command=self.open_archive_browser_tab).pack(side='left')
        ttk.Button(archive_btns, text='Show Safe to Delete…', style='Action.TButton',
                   command=self.prune_archive_dialog).pack(side='left', padx=(8, 0))

        receipt_body = settings_card(
            self._settings_section_frames['Receipts'], 'Receipt files', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            receipt_body,
            'Cleanroom writes human-readable .cleanroom-receipt files after each archive. '
            'Legacy .txt receipts still open. Receipts stay local — no upload.',
            text_color=MUTED, font_size=10, wraplength=720, justify='left',
        ).pack(anchor='w', pady=(0, 8))
        receipt_btns = ttk.Frame(receipt_body, style='Card.TFrame')
        receipt_btns.pack(fill='x')
        ttk.Button(receipt_btns, text='Open Latest Receipt', style='Action.TButton',
                   command=self.open_last_receipt).pack(side='left')
        ttk.Button(receipt_btns, text='Proof Pack (HTML)', style='Action.TButton',
                   command=self.export_audit).pack(side='left', padx=(8, 0))

        self.set_power_var = tk.BooleanVar(value=bool(load_ui_prefs().get('power_user')))
        power_body = settings_card(
            self._settings_section_frames['Advanced'], 'Power user', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            power_body,
            'Denser tables and tighter spacing for experienced operators.',
            text_color=MUTED, font_size=10, wraplength=720, justify='left',
        ).pack(anchor='w', pady=(0, 8))
        ctk_theme.switch(
            power_body, 'Power user mode (denser tables)', self.set_power_var,
            text_color=TEXT, progress_color=ACCENT,
            button_color=BORDER, button_hover_color=ACCENT,
        ).pack(anchor='w')

        safety_body = settings_card(
            self._settings_section_frames['Advanced'], 'Advanced safety rules', card_bg=CARD_BG, accent=ACCENT)
        ctk_theme.label(
            safety_body,
            'Exclude patterns and whitelist entries Cleanroom must never touch during scan.',
            text_color=MUTED, font_size=10, wraplength=720, justify='left',
        ).pack(anchor='w', pady=(0, 8))
        patterns = ttk.Frame(safety_body, style='Card.TFrame')
        patterns.pack(fill='both', expand=True)
        excl_col = ttk.Frame(patterns, style='Card.TFrame')
        excl_col.pack(side='left', fill='both', expand=True, padx=(0, 8))
        ttk.Label(excl_col, text='Exclude patterns', style='CardInfo.TLabel').pack(anchor='w', pady=(0, 4))
        self.set_exclude_text = tk.Text(excl_col, height=4, font=('Consolas', 9), relief='flat',
                                        bg=PREVIEW_BG, fg=TEXT, insertbackground=TEXT,
                                        highlightthickness=0)
        self.set_exclude_text.pack(fill='both', expand=True)
        white_col = ttk.Frame(patterns, style='Card.TFrame')
        white_col.pack(side='left', fill='both', expand=True)
        ttk.Label(white_col, text='Whitelist', style='CardInfo.TLabel').pack(anchor='w', pady=(0, 4))
        self.set_whitelist_text = tk.Text(white_col, height=4, font=('Consolas', 9), relief='flat',
                                          bg=PREVIEW_BG, fg=TEXT, insertbackground=TEXT,
                                          highlightthickness=0)
        self.set_whitelist_text.pack(fill='both', expand=True)

        self._settings_scroll_spacer = ctk.CTkFrame(content, fg_color=BG, height=20, corner_radius=0)
        self._settings_scroll_spacer.pack(fill='x', pady=(4, 12))
        self._settings_scroll = content

        # Footer — docked below scroll region (never overlays scroll content)
        footer = ttk.Frame(body, style='Content.TFrame')
        footer.grid(row=3, column=0, sticky='ew', pady=(6, 0))
        footer_inner = ctk_theme.frame(footer, HEAD_BG, corner_radius=8)
        footer_inner.pack(fill='x')
        btn_row = ttk.Frame(footer_inner, style='Card.TFrame')
        btn_row.pack(fill='x', padx=12, pady=10)
        self.save_settings_btn = ttk.Button(btn_row, text='Save Settings', style='Primary.TButton',
                                            command=self.save_settings)
        self.save_settings_btn.pack(side='left')
        ttk.Button(btn_row, text='Discard Changes', style='Action.TButton',
                   command=self.load_settings_form).pack(side='left', padx=(8, 0))
        ttk.Button(btn_row, text='Open data folder', style='Action.TButton',
                   command=self._settings_open_data_dir).pack(side='left', padx=(8, 0))
        self.settings_status_lbl = ttk.Label(btn_row, text='', style='Info.TLabel')
        self.settings_status_lbl.pack(side='left', padx=12)
        self._add_tooltip(self.save_settings_btn, 'Write these values to the active cleanup config.')

        self.load_settings_form()
        self._bind_settings_dirty_tracking()

    def _settings_relaxed_toggle(self):
        if self.set_relaxed_scan.get():
            self.set_temp_age.set(0)
            self.set_installer_age.set(0)
            self.set_size_mb.set(1)
        else:
            self.set_temp_age.set(7)
            self.set_installer_age.set(30)
            self.set_size_mb.set(200)

    def _settings_sync_path_toggles(self, paths):
        paths = {str(Path(p)) for p in (paths or [])}
        dl = str(Path(self._settings_downloads_path))
        tp = str(Path(self._settings_temp_path))
        self.set_scan_downloads.set(dl in paths)
        self.set_scan_temp.set(tp in paths)

    def _settings_apply_path_toggles(self, paths):
        paths = [str(Path(p)) for p in (paths or [])]
        dl = str(Path(self._settings_downloads_path))
        tp = str(Path(self._settings_temp_path))
        paths = [p for p in paths if p not in (dl, tp)]
        if self.set_scan_downloads.get():
            paths.insert(0, dl)
        if self.set_scan_temp.get():
            paths.append(tp)
        return paths

    def _settings_add_path(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            self.set_paths_list.insert('end', str(Path(folder)))
            self._mark_settings_dirty()

    def _settings_remove_path(self):
        for idx in reversed(self.set_paths_list.curselection()):
            self.set_paths_list.delete(idx)
        self._mark_settings_dirty()

    def _on_settings_paths_right_click(self, event):
        lb = self.set_paths_list
        idx = lb.nearest(event.y)
        if idx >= 0:
            lb.selection_clear(0, 'end')
            lb.selection_set(idx)
        has_sel = bool(lb.curselection())
        path = lb.get(lb.curselection()[0]) if has_sel else ''

        def _copy_path():
            if not path:
                return
            try:
                self.clipboard_clear()
                self.clipboard_append(path)
                self._set_status('Path copied.')
            except tk.TclError:
                messagebox.showinfo('Copy path', path)

        def _open_path():
            if path and Path(path).exists():
                os.startfile(path)
            elif path:
                messagebox.showinfo('Open path', f'Path not found:\n{path}')

        self._show_row_popover(
            event.x_root, event.y_root,
            [
                ('Add folder…', self._settings_add_path, True),
                ('Remove selected', self._settings_remove_path, has_sel),
                ('Copy path', _copy_path, has_sel),
                ('Open path', _open_path, has_sel),
                ('Reset to default', self.load_settings_form, True),
            ],
            title='Scan folders',
        )
        return 'break'

    def _settings_browse_archive(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            self.set_archive_var.set(str(Path(folder)))
            self._mark_settings_dirty()

    def load_settings_form(self):
        self._settings_dirty = False
        try:
            cfg = cleanup_main.load_config(self.cleanup_config_path) if cleanup_main else {}
        except Exception:
            cfg = {}
        cfg = cfg or {}
        paths = cfg.get('paths', []) or []
        self._settings_sync_path_toggles(paths)
        self.set_paths_list.delete(0, 'end')
        dl = str(Path(self._settings_downloads_path))
        tp = str(Path(self._settings_temp_path))
        for p in paths:
            ps = str(p)
            if ps in (dl, tp):
                continue
            self.set_paths_list.insert('end', ps)
        ages = cfg.get('age_days', {}) or {}
        temp_age = int(ages.get('temp', 7))
        inst_age = int(ages.get('installers', 30))
        size_mb = int(cfg.get('size_threshold_mb', 200))
        self.set_temp_age.set(temp_age)
        self.set_installer_age.set(inst_age)
        self.set_size_mb.set(size_mb)
        self.set_relaxed_scan.set(temp_age == 0 and inst_age == 0 and size_mb <= 1)
        self.set_archive_var.set(str(cfg.get('archive_dir') or ''))
        self.set_confirm_gb.set(round((cfg.get('confirm_threshold_bytes') or 5 * 1024 ** 3) / 1024 ** 3, 2))
        self.set_ext_var.set(', '.join(cfg.get('extensions_archive', []) or []))
        self.set_exclude_text.delete('1.0', 'end')
        excl = cfg.get('exclude_patterns', []) or []
        if excl:
            self.set_exclude_text.insert('1.0', '\n'.join(excl))
        else:
            self.set_exclude_text.insert(
                '1.0', '# One glob pattern per line (e.g. **\\\\node_modules\\\\**)\n')
        self.set_whitelist_text.delete('1.0', 'end')
        white = cfg.get('whitelist', []) or []
        if white:
            self.set_whitelist_text.insert('1.0', '\n'.join(white))
        else:
            self.set_whitelist_text.insert(
                '1.0', '# Paths Cleanroom must never scan or archive\n')
        self.set_prune_recent_days.set(int(cfg.get('prune_recent_days', 7)))
        prefs = load_ui_prefs()
        self.set_scan_on_startup.set(bool(prefs.get('scan_on_startup', False)))
        self.set_remember_geometry.set(bool(prefs.get('remember_window_geometry', True)))
        self.set_remember_last_tab.set(bool(prefs.get('remember_last_tab', True)))
        self.set_power_var.set(bool(prefs.get('power_user', False)))
        self.set_theme_var.set(PALETTES.get(prefs.get('theme', CURRENT_THEME), PALETTES[CURRENT_THEME])['LABEL'])
        default_map = {0: 'Home', 1: 'Activity', 2: 'Startup', 3: 'Cleaner', 6: 'Archive', 7: 'Settings'}
        self.set_default_tab_var.set(prefs.get('default_tab') or default_map.get(int(prefs.get('last_tab', 0)), 'Home'))
        if hasattr(self, '_settings_config_path_lbl'):
            self._settings_config_path_lbl.configure(text=f'Active config: {self._config_status_label()}')
        self.settings_status_lbl.config(text=self._config_status_label())
        self._update_brand_identity()

    def _settings_open_config(self):
        path = Path(self.cleanup_config_path)
        if not path.exists():
            messagebox.showinfo('Config', 'Config file not found yet. Save Settings first to create it.')
            return
        try:
            os.startfile(str(path))
        except Exception as e:
            messagebox.showerror('Config', f'Unable to open config file:\n{e}')

    def _settings_open_data_dir(self):
        folder = brand.user_data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))
        except Exception as e:
            messagebox.showerror('Data folder', f'Unable to open data folder:\n{e}')

    def save_settings(self):
        try:
            cfg = cleanup_main.load_config(self.cleanup_config_path) if cleanup_main else {}
        except Exception:
            cfg = {}
        cfg = cfg or {}
        exts = []
        for raw in self.set_ext_var.get().split(','):
            e = raw.strip().lower()
            if not e:
                continue
            exts.append(e if e.startswith('.') else '.' + e)
        cfg.update({
            'paths': self._settings_apply_path_toggles(list(self.set_paths_list.get(0, 'end'))),
            'archive_dir': self.set_archive_var.get().strip() or cfg.get('archive_dir'),
            'age_days': {'temp': int(self.set_temp_age.get()), 'installers': int(self.set_installer_age.get())},
            'size_threshold_mb': int(self.set_size_mb.get()),
            'confirm_threshold_bytes': int(float(self.set_confirm_gb.get()) * 1024 ** 3),
            'extensions_archive': exts,
            'exclude_patterns': [l.strip() for l in self.set_exclude_text.get('1.0', 'end').splitlines() if l.strip()],
            'whitelist': [l.strip() for l in self.set_whitelist_text.get('1.0', 'end').splitlines() if l.strip()],
            'prune_recent_days': int(self.set_prune_recent_days.get()),
        })
        self.dedupe_enabled.set(bool(self.set_dedupe_default.get()))
        prefs = load_ui_prefs()
        old_theme = prefs.get('theme', CURRENT_THEME)
        prefs['scan_on_startup'] = bool(self.set_scan_on_startup.get())
        prefs['remember_window_geometry'] = bool(self.set_remember_geometry.get())
        prefs['remember_last_tab'] = bool(self.set_remember_last_tab.get())
        prefs['default_tab'] = self.set_default_tab_var.get()
        prefs['power_user'] = bool(self.set_power_var.get())
        label = self.set_theme_var.get()
        new_theme = old_theme
        for t in THEME_ORDER:
            if PALETTES[t]['LABEL'] == label:
                new_theme = t
                prefs['theme'] = t
                break
        save_ui_prefs(prefs)
        try:
            written_to = self._write_config(cfg)
        except Exception as e:
            messagebox.showerror('Settings', f'Unable to save settings:\n{e}')
            return
        self._settings_dirty = False
        self.settings_status_lbl.config(text='Settings saved')
        self._update_brand_identity()
        self._set_status('Settings saved. Click Scan to apply new paths.')
        theme_changed = new_theme != old_theme
        power_changed = bool(self.set_power_var.get()) != bool(self.power_user)
        if theme_changed or power_changed:
            apply_palette(new_theme)
            self.wants_restart = True
            self.destroy()

    def _write_config(self, cfg):
        """Write config to the active path; fall back to the per-user copy if
        the active one isn't writable (e.g. Program Files)."""
        text = yaml.safe_dump(cfg, sort_keys=False) if yaml else json.dumps(cfg, indent=2)
        path = Path(self.cleanup_config_path)
        try:
            path.write_text(text, encoding='utf-8')
            return path
        except (PermissionError, OSError):
            if not cleanup_main:
                raise
            alt = cleanup_main.user_config_dir() / 'cleanup_config.yaml'
            alt.parent.mkdir(parents=True, exist_ok=True)
            alt.write_text(text, encoding='utf-8')
            self.cleanup_config_path = alt
            return alt

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=STATUS_BG)
        bar.pack(fill='x', side='bottom')
        tk.Frame(self, height=1, bg=BORDER).pack(fill='x', side='bottom')
        self.global_status = tk.Label(bar, text='Ready.', bg=STATUS_BG, fg=TEXT,
                                      font=('Segoe UI', 9), anchor='w', padx=8, pady=4)
        self.global_status.pack(side='left', fill='x', expand=True)
        tk.Label(bar, text=f'{brand.APP_DISPLAY} v{APP_VERSION}', bg=STATUS_BG, fg=MUTED,
                 font=('Segoe UI', 9), padx=8).pack(side='right')

    # ------------------------------------------------------------------
    # Uninstaller tab (IObit-style installed-programs manager)
    # ------------------------------------------------------------------
    def _build_uninstaller_tab(self):
        head = ttk.Frame(self.uninstall_tab, style='Content.TFrame')
        head.pack(fill='x', padx=10, pady=(10, 4))
        ttk.Label(head, text='Uninstaller', font=('Segoe UI', 13, 'bold'),
                  background=BG).pack(side='left')
        self.uninst_count_lbl = ttk.Label(head, text='0 programs', style='Badge.TLabel')
        self.uninst_count_lbl.pack(side='left', padx=(10, 0))
        self.uninst_size_lbl = ttk.Label(head, text='', style='Badge.TLabel')
        self.uninst_size_lbl.pack(side='left', padx=(6, 0))

        # IObit-style smart filter chips
        chips = ttk.Frame(self.uninstall_tab, style='Content.TFrame')
        chips.pack(fill='x', padx=10, pady=(0, 4))
        self.uninst_mode = 'all'
        self._uninst_chip_btns = {}
        chip_defs = [('all', '▦ All Programs'), ('large', '🐘 Large (1GB+)'),
                     ('recent', '🆕 Recently Installed'), ('old', '🕰 Over a Year Old')]
        for mode, label in chip_defs:
            btn = ttk.Button(chips, text=label, style='Sidebar.TButton',
                             command=lambda m=mode: self._set_uninstall_mode(m))
            btn.pack(side='left', padx=(0, 4))
            self._uninst_chip_btns[mode] = btn

        bar = ttk.Frame(self.uninstall_tab, style='Content.TFrame')
        bar.pack(fill='x', padx=10, pady=(0, 6))
        self.uninst_filter_var = tk.StringVar()
        flt = ttk.Entry(bar, textvariable=self.uninst_filter_var, width=32, style='Search.TEntry')
        flt.pack(side='left')
        flt.bind('<KeyRelease>', lambda e: self._populate_uninstall_tree())
        self._add_tooltip(flt, 'Filter programs by name or publisher.')
        ttk.Button(bar, text='Refresh', style='Action.TButton',
                   command=self.refresh_uninstaller).pack(side='left', padx=6)
        self.uninst_quiet_var = tk.BooleanVar(value=False)
        self._uninst_quiet_cb = ttk.Checkbutton(bar, text='Silent uninstall when possible',
                        variable=self.uninst_quiet_var)
        self._uninst_quiet_cb.pack(side='left', padx=6)
        self.uninst_leftover_btn = ttk.Button(bar, text='Scan Leftovers…', style='Action.TButton',
                                              command=self.scan_leftovers_for_selected)
        self.uninst_leftover_btn.pack(side='right')
        self.uninst_force_btn = ttk.Button(bar, text='Force Remove…', style='Action.TButton',
                                           command=self.force_remove_selected)
        self.uninst_force_btn.pack(side='right', padx=6)
        self._add_tooltip(self.uninst_force_btn,
                          'For broken/missing uninstallers: archive leftover files and registry\n'
                          'keys, then remove the orphaned entry from this list (backed up as .reg).')
        self.uninst_uninstall_btn = ttk.Button(bar, text='Uninstall', style='Primary.TButton',
                                               command=self.uninstall_selected_program)
        self.uninst_uninstall_btn.pack(side='right', padx=6)
        self._add_tooltip(self.uninst_uninstall_btn,
                          'Run the selected program\'s uninstaller.\n'
                          'Select several (Ctrl/Shift-click) for a batch queue.')
        self._add_tooltip(self.uninst_leftover_btn,
                          'Find leftover folders for the selected program and archive them (restorable).')

        uninst_body = ttk.Frame(self.uninstall_tab, style='Content.TFrame')
        uninst_body.pack(fill='both', expand=True, padx=10, pady=(0, 6))
        self._uninst_pane, uninst_left, uninst_right = create_horizontal_pane(
            uninst_body, use_pack=True)
        self._bind_pane(self._uninst_pane, 'uninstaller_split', default=520)

        self._uninst_empty_panel = self._build_workspace_empty_panel(
            uninst_body,
            'No installed programs',
            'Click Refresh to scan the Programs list.',
            'Refresh', self.refresh_uninstaller,
        )
        self._uninst_loading_lbl = ttk.Label(
            uninst_body, text='Scanning installed programs…',
            style='Info.TLabel', anchor='center', font=('Segoe UI', 12))

        wrap = ttk.Frame(uninst_left, style='Card.TFrame')
        wrap.pack(fill='both', expand=True)
        cols = ['sel', 'name', 'publisher', 'version', 'size', 'installed']
        if self.power_user:
            cols.append('key')
        cols.append('action')
        self.uninstall_tree = ttk.Treeview(wrap, columns=tuple(cols), show='headings',
                                           selectmode='extended')
        headings = {'sel': '✓', 'name': 'Program', 'publisher': 'Publisher',
                    'version': 'Version', 'size': 'Size', 'installed': 'Installed',
                    'key': 'Registry Key', 'action': ''}
        widths = {'sel': 36, 'name': 300, 'publisher': 180, 'version': 100, 'size': 86,
                  'installed': 96, 'key': 220, 'action': 44}
        for c in cols:
            if c == 'sel':
                self.uninstall_tree.heading(c, text=headings[c],
                                            command=self._toggle_all_uninstall_checks)
            elif c == 'action':
                self.uninstall_tree.heading(c, text=headings[c])
            else:
                self.uninstall_tree.heading(c, text=headings[c],
                                            command=lambda col=c: self._uninstall_sort(col))
            anchor = 'center' if c in ('sel', 'action') else ('e' if c == 'size' else 'w')
            stretch = c == 'name'
            self.uninstall_tree.column(c, width=widths[c], anchor=anchor, stretch=stretch)
        vsb = ttk.Scrollbar(wrap, orient='vertical', command=self.uninstall_tree.yview)
        self.uninstall_tree.configure(yscrollcommand=vsb.set)
        self.uninstall_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self.uninstall_tree.tag_configure('oddrow', background=CARD_BG)
        self.uninstall_tree.tag_configure('evenrow', background=ROW_ALT)
        self.uninstall_tree.tag_configure('actioncol', foreground=ACCENT)
        self.uninstall_tree.bind('<Double-1>', self._on_uninstall_double)
        self.uninstall_tree.bind('<Button-1>', self._on_uninstall_click)
        self.uninstall_tree.bind('<Button-3>', self._on_uninstall_right_click)
        self.uninstall_tree.bind('<space>', self._on_uninstall_space)
        self.uninstall_tree.bind('<<TreeviewSelect>>', self._on_uninstall_select)
        self._uninst_context_menu = None
        self.uninst_empty_hint = self._make_empty_hint(
            self.uninstall_tree, 'No programs match this view.\nTry "All Programs" or Refresh.')

        detail_frame = ttk.Labelframe(
            uninst_right,
            text='Program summary — local guidance (no web lookup)',
            style='Detail.TLabelframe',
        )
        detail_frame.pack(fill='both', expand=True)
        detail_grid = ttk.Frame(detail_frame, style='Detail.TLabelframe')
        detail_grid.pack(fill='x', padx=10, pady=10)
        self.uninst_detail_name = ttk.Label(
            detail_grid, text='Select a program above.', style='CardInfo.TLabel',
            font=('Segoe UI', 10, 'bold'))
        self.uninst_detail_name.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 4))
        ttk.Label(detail_grid, text='What it is:', style='CardInfo.TLabel').grid(
            row=1, column=0, sticky='nw', padx=(0, 8))
        self.uninst_detail_what = ttk.Label(
            detail_grid, text='—', style='CardInfo.TLabel', wraplength=820, justify='left')
        self.uninst_detail_what.grid(row=1, column=1, sticky='w', pady=2)
        ttk.Label(detail_grid, text='What it does:', style='CardInfo.TLabel').grid(
            row=2, column=0, sticky='nw', padx=(0, 8))
        self.uninst_detail_does = ttk.Label(
            detail_grid, text='—', style='CardInfo.TLabel', wraplength=820, justify='left')
        self.uninst_detail_does.grid(row=2, column=1, sticky='w', pady=2)
        ttk.Label(detail_grid, text='Do you need it?', style='CardInfo.TLabel').grid(
            row=3, column=0, sticky='nw', padx=(0, 8))
        self.uninst_detail_need = ttk.Label(
            detail_grid, text='—', style='CardInfo.TLabel', wraplength=820, justify='left')
        self.uninst_detail_need.grid(row=3, column=1, sticky='w', pady=2)
        ttk.Label(detail_grid, text='Uninstaller:', style='CardInfo.TLabel').grid(
            row=4, column=0, sticky='nw', padx=(0, 8))
        self.uninst_detail_uninst = ttk.Label(
            detail_grid, text='—', style='CardInfo.TLabel', wraplength=820, justify='left')
        self.uninst_detail_uninst.grid(row=4, column=1, sticky='w', pady=2)
        detail_grid.columnconfigure(1, weight=1)

        self.uninst_status_lbl = ttk.Label(self.uninstall_tab, text='', style='Info.TLabel')
        self.uninst_status_lbl.pack(anchor='w', padx=12, pady=(0, 8))

        self.uninstall_entries = []
        self.uninst_checked = set()
        self._uninst_sort_col = 'name'
        self._uninst_sort_desc = False
        self._refresh_uninstall_chips()

    def refresh_uninstaller(self):
        if uninstaller is None:
            self.uninst_status_lbl.config(text='Uninstaller module unavailable.')
            return
        self._sync_uninst_view(loading=True)
        self.uninst_status_lbl.config(text='Scanning installed programs…')

        def done(result, err):
            if err is not None:
                self.uninst_status_lbl.config(text=f'Failed to list programs: {err}')
                self._sync_uninst_view(loading=False)
                return
            self.uninstall_entries = result or []
            self.uninst_checked.clear()  # indices change with every rescan
            self._populate_uninstall_tree()
            self.uninst_status_lbl.config(text='')

        self._run_bg(uninstaller.list_installed_programs, done)

    def _set_uninstall_mode(self, mode):
        self.uninst_mode = mode
        self._refresh_uninstall_chips()
        self._populate_uninstall_tree()

    def _refresh_uninstall_chips(self):
        for mode, btn in self._uninst_chip_btns.items():
            btn.configure(style='Sidebar.Selected.TButton' if mode == self.uninst_mode
                          else 'Sidebar.TButton')

    def _visible_uninstall_rows(self):
        rows = uninstaller.filter_programs(self.uninstall_entries, self.uninst_mode) \
            if uninstaller else list(self.uninstall_entries)
        flt = (self.uninst_filter_var.get() or '').strip().lower()
        if flt:
            rows = [e for e in rows
                    if flt in e['name'].lower() or flt in e['publisher'].lower()]
        return rows

    def _populate_uninstall_tree(self):
        tree = self.uninstall_tree
        self._cancel_chunked_work('uninstall_tree')
        rows = self._visible_uninstall_rows()
        col = self._uninst_sort_col
        if col == 'size':
            rows.sort(key=lambda e: e['size_kb'], reverse=self._uninst_sort_desc)
        elif col == 'installed':
            rows.sort(key=lambda e: e['install_date'], reverse=self._uninst_sort_desc)
        elif col in ('name', 'publisher', 'version', 'key'):
            k = 'subkey' if col == 'key' else col
            rows.sort(key=lambda e: str(e.get(k, '')).lower(), reverse=self._uninst_sort_desc)
        total_kb = sum(e['size_kb'] for e in rows)
        entry_to_idx = {id(e): i for i, e in enumerate(self.uninstall_entries)}
        rows_with_idx = [(entry_to_idx[id(e)], e) for e in rows]
        checked_visible = sum(1 for idx, _e in rows_with_idx if idx in self.uninst_checked)

        def build_row(i, item):
            idx, e = item
            size = self._format_size(e['size_kb'] * 1024) if e['size_kb'] else ''
            check = '☑' if idx in self.uninst_checked else '☐'
            values = [check, e['name'], e['publisher'], e['version'], size, e['install_date']]
            if self.power_user:
                hive_short = 'HKLM' if 'LOCAL_MACHINE' in e.get('hive', '') else 'HKCU'
                values.append(f"{hive_short}\\…\\{e.get('subkey', '')}")
            values.append('🗑')
            return (str(idx), tuple(values), ('evenrow' if i % 2 else 'oddrow',))

        def on_complete():
            label = f'{len(rows):,} programs'
            if checked_visible:
                label += f' · {checked_visible:,} checked'
            self.uninst_count_lbl.config(text=label)
            self.uninst_size_lbl.config(
                text=self._format_size(total_kb * 1024) if total_kb else '')
            self._sync_uninst_view(loading=False)

        self._chunked_tree_populate(
            tree,
            rows_with_idx,
            build_row,
            status_lbl=self.uninst_status_lbl,
            empty_hint=self.uninst_empty_hint,
            on_complete=on_complete,
            token_key='uninstall_tree',
            clear_selection=False,
        )
        if not rows_with_idx:
            on_complete()

    def _uninstall_sort(self, col):
        if self._uninst_sort_col == col:
            self._uninst_sort_desc = not self._uninst_sort_desc
        else:
            self._uninst_sort_col, self._uninst_sort_desc = col, False
        self._populate_uninstall_tree()

    def _toggle_uninstall_check(self, idx):
        if idx in self.uninst_checked:
            self.uninst_checked.discard(idx)
        else:
            self.uninst_checked.add(idx)
        self._populate_uninstall_tree()

    def _toggle_all_uninstall_checks(self):
        visible = {self.uninstall_entries.index(e) for e in self._visible_uninstall_rows()}
        if visible and visible.issubset(self.uninst_checked):
            self.uninst_checked -= visible
        else:
            self.uninst_checked |= visible
        self._populate_uninstall_tree()

    def _on_uninstall_click(self, event):
        tree = self.uninstall_tree
        if tree.identify_region(event.x, event.y) != 'cell':
            return
        iid = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        if not iid:
            return
        last_col = f'#{len(tree["columns"])}'
        if column == '#1':
            self._toggle_uninstall_check(int(iid))
            return 'break'
        if column == last_col:
            try:
                entry = self.uninstall_entries[int(iid)]
            except (ValueError, IndexError):
                return
            tree.selection_set(iid)
            self._uninstall_one(entry)
            return 'break'

    def _on_uninstall_space(self, event):
        for iid in self.uninstall_tree.selection():
            try:
                self._toggle_uninstall_check(int(iid))
            except ValueError:
                pass
        return 'break'

    def _on_uninstall_double(self, event):
        # Ignore double-clicks on the checkbox/action columns (handled on click)
        column = self.uninstall_tree.identify_column(event.x)
        last_col = f'#{len(self.uninstall_tree["columns"])}'
        if column in ('#1', last_col):
            return
        self.uninstall_selected_program()

    def _uninst_verdict_color(self, verdict: str) -> str:
        if verdict in (program_advice.KEEP, program_advice.USUALLY_KEEP) if program_advice else False:
            return REASON_COLORS.get('installer/archive', ACCENT)
        if verdict == program_advice.CAUTION if program_advice else False:
            return REASON_COLORS.get('uninstall-leftover', TEXT)
        if verdict in (program_advice.SAFE_IF_UNUSED, program_advice.OPTIONAL) if program_advice else False:
            return REASON_COLORS.get('large-file', TEXT)
        return TEXT

    def _on_uninstall_select(self, event=None):
        self._update_uninstall_detail()
        self._update_context_panel()

    def _update_uninstall_detail(self):
        if not hasattr(self, 'uninst_detail_name'):
            return
        entry = self._selected_program()
        if not entry:
            self.uninst_detail_name.config(text='Select a program above.')
            for lbl in (self.uninst_detail_what, self.uninst_detail_does,
                        self.uninst_detail_need, self.uninst_detail_uninst):
                lbl.config(text='—', foreground=TEXT)
            return
        self.uninst_detail_name.config(text=entry.get('name') or '—')
        if not program_advice:
            self.uninst_detail_what.config(text='Guidance module unavailable.', foreground=TEXT)
            self.uninst_detail_does.config(text='—', foreground=TEXT)
            self.uninst_detail_need.config(text='—', foreground=TEXT)
            self.uninst_detail_uninst.config(text='—', foreground=TEXT)
            return
        advice = program_advice.analyze_program(entry)
        color = self._uninst_verdict_color(advice['verdict'])
        self.uninst_detail_what.config(text=advice['what_is'], foreground=TEXT)
        self.uninst_detail_does.config(text=advice['what_does'], foreground=TEXT)
        self.uninst_detail_need.config(text=advice['need'], foreground=color)
        self.uninst_detail_uninst.config(text=advice['uninstaller_note'], foreground=TEXT)
        if entry.get('install_location'):
            loc = entry['install_location']
            self.uninst_detail_what.config(
                text=f"{advice['what_is']} Install folder: {loc}")

    def _uninstall_registry_key_text(self, entry):
        if not entry:
            return ''
        hive = entry.get('hive') or ''
        key = entry.get('key') or ''
        sub = entry.get('subkey') or ''
        if hive and key and sub:
            return f'{hive}\\{key}\\{sub}'
        return ''

    def _ensure_uninstall_context_menu(self):
        if self._uninst_context_menu is not None:
            return
        menu = tk.Menu(
            self.uninstall_tree, tearoff=0,
            bg=CARD_BG, fg=TEXT,
            activebackground=ACCENT_SOFT, activeforeground=TEXT,
            disabledforeground=MUTED, bd=1, relief='solid',
            font=('Segoe UI', 10),
        )
        menu.add_command(label='Uninstall…', command=self.uninstall_selected_program)
        menu.add_command(label='Scan Leftovers…', command=self.scan_leftovers_for_selected)
        menu.add_command(label='Force Remove…', command=self.force_remove_selected)
        menu.add_separator()
        menu.add_command(label='Check / Uncheck', command=self._uninstall_ctx_toggle_check)
        menu.add_command(label='Check all visible', command=self._uninstall_ctx_check_all)
        menu.add_command(label='Uncheck all visible', command=self._uninstall_ctx_uncheck_all)
        menu.add_separator()
        menu.add_command(label='Copy program name', command=self._uninstall_copy_name)
        menu.add_command(label='Copy uninstall command', command=self._uninstall_copy_command)
        menu.add_command(label='Copy registry key', command=self._uninstall_copy_registry_key)
        menu.add_separator()
        menu.add_command(label='Refresh list', command=self.refresh_uninstaller)
        self._uninst_context_menu = menu

    def _on_uninstall_right_click(self, event):
        iid = self.uninstall_tree.identify_row(event.y)
        if iid:
            if iid not in self.uninstall_tree.selection():
                self.uninstall_tree.selection_set(iid)
        self._on_uninstall_select()
        entry = None
        if iid:
            try:
                entry = self.uninstall_entries[int(iid)]
            except (ValueError, IndexError):
                entry = None
        has_entry = entry is not None
        has_cmd = bool(entry and uninstaller and uninstaller.build_uninstall_command(
            entry, quiet=bool(self.uninst_quiet_var.get())))
        has_key = bool(self._uninstall_registry_key_text(entry))
        has_publisher = bool(entry and entry.get('publisher'))
        self._show_row_popover(
            event.x_root, event.y_root,
            [
                ('Uninstall…', self.uninstall_selected_program, has_entry),
                ('Scan leftovers…', self.scan_leftovers_for_selected, has_entry),
                ('Force Remove…', self.force_remove_selected, has_entry),
                ('Copy program name', self._uninstall_copy_name, has_entry),
                ('Copy publisher', self._uninstall_copy_publisher, has_publisher),
                ('Copy uninstall command', self._uninstall_copy_command, has_cmd),
                ('Copy registry key', self._uninstall_copy_registry_key, has_key),
                ('Search online', self._uninstall_search_online, has_entry),
                ('Refresh list', self.refresh_uninstaller, True),
            ],
            title='Uninstaller',
        )
        return 'break'

    def _uninstall_ctx_toggle_check(self):
        for iid in self.uninstall_tree.selection():
            try:
                self._toggle_uninstall_check(int(iid))
            except ValueError:
                pass
            break

    def _uninstall_ctx_check_all(self):
        visible = {self.uninstall_entries.index(e) for e in self._visible_uninstall_rows()}
        self.uninst_checked |= visible
        self._populate_uninstall_tree()

    def _uninstall_ctx_uncheck_all(self):
        visible = {self.uninstall_entries.index(e) for e in self._visible_uninstall_rows()}
        self.uninst_checked -= visible
        self._populate_uninstall_tree()

    def _uninstall_copy_name(self):
        entry = self._selected_program()
        if not entry:
            return
        self.clipboard_clear()
        self.clipboard_append(entry.get('name') or '')
        self.update()
        self._set_status('Program name copied to clipboard.')

    def _uninstall_copy_publisher(self):
        entry = self._selected_program()
        if not entry:
            return
        pub = entry.get('publisher') or ''
        self.clipboard_clear()
        self.clipboard_append(pub)
        self.update()
        self._set_status('Publisher copied to clipboard.')

    def _uninstall_search_online(self):
        import urllib.parse
        import webbrowser
        entry = self._selected_program()
        if not entry:
            return
        name = entry.get('name') or 'program'
        pub = entry.get('publisher') or ''
        q = urllib.parse.quote(f'{name} {pub} uninstall'.strip())
        webbrowser.open(f'https://www.google.com/search?q={q}')

    def _uninstall_copy_command(self):
        entry = self._selected_program()
        if not entry or not uninstaller:
            return
        cmd = uninstaller.build_uninstall_command(entry, quiet=bool(self.uninst_quiet_var.get()))
        if not cmd:
            messagebox.showinfo('Copy', 'No uninstall command available for this program.')
            return
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self.update()
        self._set_status('Uninstall command copied to clipboard.')

    def _uninstall_copy_registry_key(self):
        entry = self._selected_program()
        text = self._uninstall_registry_key_text(entry)
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self._set_status('Registry key copied to clipboard.')

    def _selected_programs(self):
        # Checked items win (IObit-style batch); fall back to the row selection.
        if self.uninst_checked:
            return [self.uninstall_entries[i] for i in sorted(self.uninst_checked)
                    if 0 <= i < len(self.uninstall_entries)]
        out = []
        for iid in self.uninstall_tree.selection():
            try:
                out.append(self.uninstall_entries[int(iid)])
            except (ValueError, IndexError):
                pass
        return out

    def _selected_program(self):
        progs = self._selected_programs()
        return progs[0] if progs else None

    def uninstall_selected_program(self):
        entries = self._selected_programs()
        if not entries:
            messagebox.showinfo('Uninstall', 'Check or select a program first.')
            return
        if len(entries) > 1:
            self._batch_uninstall(entries)
            return
        self._uninstall_one(entries[0])

    def _uninstall_one(self, entry):
        if not messagebox.askyesno(
                'Uninstall',
                f"Uninstall \"{entry['name']}\"?\n\nThis launches the program's own "
                'uninstaller. After it finishes you can scan for leftovers.'):
            return
        quiet = bool(self.uninst_quiet_var.get())
        self.uninst_uninstall_btn.config(state='disabled')
        self.uninst_status_lbl.config(text=f"Running uninstaller for {entry['name']}…")

        def work():
            before = proof_module.disk_free() if proof_module else 0
            code, msg = uninstaller.run_uninstall(entry, quiet=quiet)
            measured = (proof_module.disk_free() - before) if proof_module else 0
            return code, msg, measured

        def done(result, err):
            self.uninst_uninstall_btn.config(state='normal')
            if err is not None:
                self.uninst_status_lbl.config(text=f'Uninstall failed: {err}')
                return
            code, msg, measured = result
            if code == 0 and measured > 0:
                msg += f' OS-measured space freed: {self._format_size(measured)}.'
            self.uninst_status_lbl.config(text=msg)
            self.refresh_uninstaller()
            if code != 0:
                if messagebox.askyesno(
                        'Uninstall problem',
                        f"The uninstaller for \"{entry['name']}\" exited with code {code} — "
                        'it may be broken or cancelled.\n\nForce remove instead? This archives '
                        'leftover files and registry keys, then removes the orphaned entry '
                        'from the Programs list (everything backed up, restorable).'):
                    self._scan_leftovers(entry, force_remove=True)
                return
            if messagebox.askyesno('Leftovers',
                                   f"Scan for leftover folders of \"{entry['name']}\" "
                                   'and archive them (restorable)?'):
                self._scan_leftovers(entry)

        self._run_bg(work, done)

    def force_remove_selected(self):
        entry = self._selected_program()
        if entry is None:
            messagebox.showinfo('Force remove', 'Select a program first.')
            return
        advice_text = ''
        if program_advice:
            a = program_advice.analyze_program(entry)
            advice_text = (
                f"\n\nLocal guidance: {a['need']}\n{a['uninstaller_note']}"
            )
        admin_note = ''
        if uninstaller and uninstaller.entry_requires_admin(entry):
            admin_note = (
                '\n\nNote: this entry is under HKLM — removing it from the Programs list '
                'may require running Cleanroom as administrator.'
            )
            try:
                if startup_manager_admin and not startup_manager_admin.is_admin():
                    admin_note += ' You are not elevated right now.'
            except Exception:
                pass
        if not messagebox.askyesno(
                'Force remove',
                f"Force remove \"{entry['name']}\"?\n\n"
                'Use when the normal uninstaller is broken or missing. Cleanroom will:\n'
                '  1. Archive leftover folders + install location (moved, not deleted)\n'
                '  2. Export + remove matching registry keys (.reg backups)\n'
                '  3. Remove the orphaned Programs-list entry (.reg backup)\n\n'
                f'Everything is restorable from Restore or Cleanroom Rewind.'
                f'{advice_text}{admin_note}'):
            return
        self._scan_leftovers(entry, force_remove=True)

    def _batch_uninstall(self, entries):
        """Uninstall several programs sequentially (IObit-style batch queue)."""
        names = '\n'.join(f'  • {e["name"]}' for e in entries[:12])
        if len(entries) > 12:
            names += f'\n  … and {len(entries) - 12} more'
        if not messagebox.askyesno(
                'Batch uninstall',
                f'Uninstall {len(entries)} programs one after another?\n\n{names}\n\n'
                'Each program\'s own uninstaller runs in turn; silent mode is used '
                'where available if enabled.'):
            return
        quiet = bool(self.uninst_quiet_var.get())
        self.uninst_uninstall_btn.config(state='disabled')

        def progress(text):
            # Marshal a status update onto the Tk thread via the bg queue.
            self._bg_queue.put((lambda _r, _e: self.uninst_status_lbl.config(text=text), None, None))

        def work():
            results = []
            for i, entry in enumerate(entries, 1):
                progress(f'[{i}/{len(entries)}] Uninstalling {entry["name"]}…')
                code, msg = uninstaller.run_uninstall(entry, quiet=quiet)
                results.append((entry['name'], code))
            return results

        def done(result, err):
            self.uninst_uninstall_btn.config(state='normal')
            if err is not None:
                self.uninst_status_lbl.config(text=f'Batch uninstall failed: {err}')
                return
            results = result or []
            ok = sum(1 for _, code in results if code == 0)
            self.uninst_status_lbl.config(
                text=f'Batch finished: {ok}/{len(results)} uninstallers exited cleanly.')
            lines = '\n'.join(f'  {"✔" if code == 0 else "✖"} {name} (exit {code})'
                              for name, code in results)
            messagebox.showinfo('Batch uninstall',
                                f'Finished {len(results)} uninstall(s):\n\n{lines}\n\n'
                                'Use "Scan Leftovers…" on each program name to clean remnants.')
            self.refresh_uninstaller()

        self._run_bg(work, done)

    def scan_leftovers_for_selected(self):
        entry = self._selected_program()
        if entry is None:
            messagebox.showinfo('Leftovers', 'Select a program first.')
            return
        self._scan_leftovers(entry)

    def _archive_dir_from_config(self):
        try:
            if cleanup_main:
                cfg = cleanup_main.load_config(self.cleanup_config_path) or {}
                if cfg.get('archive_dir'):
                    return cfg['archive_dir']
        except Exception:
            pass
        return str(Path.home() / 'cleanup_archive')

    def _scan_leftovers(self, entry, *, force_remove=False):
        if uninstaller is None or not entry:
            return
        name = entry.get('name') or 'program'
        self.uninst_status_lbl.config(text=f'Scanning for leftovers of {name}…')

        def work():
            return uninstaller.collect_force_remove_targets(entry, name)

        def done(result, err):
            self.uninst_status_lbl.config(text='')
            if err is not None:
                messagebox.showerror('Leftovers', f'Leftover scan failed: {err}')
                return
            dirs, keys = result or ([], [])
            if not dirs and not keys:
                if force_remove:
                    self._remove_orphan_entry(entry)
                else:
                    messagebox.showinfo(
                        'Leftovers',
                        f'No leftover folders or registry keys found for "{name}".')
                return
            self._show_leftover_dialog(entry, dirs, keys, force_remove=force_remove)

        self._run_bg(work, done)

    def _remove_orphan_entry(self, entry):
        archive_dir = self._archive_dir_from_config()
        self.uninst_status_lbl.config(text=f"Removing entry for {entry['name']}…")

        def done(result, err):
            self.uninst_status_lbl.config(text='')
            if err is not None or result is None:
                messagebox.showerror(
                    'Force remove',
                    f"Could not remove the Programs-list entry for \"{entry['name']}\".\n"
                    'HKLM entries require running Cleanroom as administrator.')
                return
            messagebox.showinfo(
                'Force remove',
                f"Removed \"{entry['name']}\" from the Programs list.\n"
                f"Backup: {result['dest']}\n\nRestorable from the Restore tab.")
            self.refresh_uninstaller()
            self.refresh_restore()

        self._run_bg(lambda: uninstaller.remove_uninstall_entry(
            entry, archive_dir, str(self.restore_log_path)), done)

    def _show_leftover_dialog(self, entry, paths, reg_keys=(), force_remove=False):
        program_name = entry.get('name') or 'program'
        title = ('Force removal' if force_remove else 'Leftovers') + f' — "{program_name}"'
        dlg = CleanroomModal(
            self, 'Force removal' if force_remove else 'Leftovers found',
            width=680, height=440, resizable=True, colors=self._dialog_colors(),
        )
        dlg.heading(title)
        if program_advice:
            advice = program_advice.analyze_program(entry)
            dlg.message(advice['need'], wrap=620)
        note = ('Checked folders are MOVED to the archive (not deleted). Checked registry '
                'keys are EXPORTED to a .reg file in the archive before removal. Both can '
                'be restored from the Restore tab or Cleanroom Rewind.')
        if force_remove:
            note += ' The orphaned Programs-list entry is removed afterwards (.reg backup).'
        ctk_theme.label(
            dlg.body, note, text_color=dlg.colors['muted'], font_size=10,
            wraplength=620, justify='left',
        ).pack(anchor='w', pady=(8, 0))

        scroll_host = ctk.CTkFrame(dlg.body, fg_color=dlg.colors['head'], corner_radius=8)
        scroll_host.pack(fill='both', expand=True, pady=(10, 0))
        canvas = tk.Canvas(scroll_host, bg=dlg.colors['head'], highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_host, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas, style='Card.TFrame')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side='left', fill='both', expand=True, padx=4, pady=4)
        vsb.pack(side='right', fill='y', pady=4)

        check_vars = []
        for p in paths:
            var = tk.BooleanVar(value=True)
            size = uninstaller.dir_size(p)
            label = f'🗂 {p}  ({self._format_size(size)})' if size else f'🗂 {p}'
            cb = ttk.Checkbutton(inner, text=label, variable=var)
            cb.configure(style='TCheckbutton')
            cb.pack(anchor='w', padx=8, pady=2)
            check_vars.append((var, 'dir', p))
        for k in reg_keys:
            var = tk.BooleanVar(value=force_remove)
            cb = ttk.Checkbutton(inner, text=f'🗝 {k}', variable=var)
            cb.configure(style='TCheckbutton')
            cb.pack(anchor='w', padx=8, pady=2)
            check_vars.append((var, 'reg', k))
        if force_remove:
            ttk.Label(inner, text='Programs-list entry (always removed on confirm):',
                      style='CardInfo.TLabel').pack(anchor='w', padx=8, pady=(6, 2))
            ttk.Label(inner, text=f'🗝 {uninstaller.uninstall_key_path(entry)}',
                      style='CardInfo.TLabel').pack(anchor='w', padx=16, pady=(0, 4))

        def do_archive():
            chosen_dirs = [p for var, kind, p in check_vars if var.get() and kind == 'dir']
            chosen_keys = [p for var, kind, p in check_vars if var.get() and kind == 'reg']
            dlg.close()
            if not chosen_dirs and not chosen_keys and not force_remove:
                return
            archive_dir = self._archive_dir_from_config()
            self.uninst_status_lbl.config(
                text=f'Archiving {len(chosen_dirs)} folder(s) + {len(chosen_keys)} registry key(s)…')

            def work():
                return uninstaller.force_remove(
                    entry, archive_dir, str(self.restore_log_path),
                    chosen_dirs=chosen_dirs, chosen_keys=chosen_keys,
                    remove_list_entry=force_remove,
                )

            def done(result, err):
                self.uninst_status_lbl.config(text='')
                if err is not None:
                    messagebox.showerror('Leftovers', f'Archiving failed: {err}')
                    return
                result = result or {}
                moved = result.get('folders') or []
                reg_moved = result.get('registry') or []
                entry_removed = result.get('list_entry')
                summary = f'Archived {len(moved)} folder(s)'
                if chosen_keys:
                    summary += f' and {len(reg_moved)} registry key(s) (exported to .reg)'
                summary += f' under:\n{archive_dir}\\uninstall_leftovers'
                if force_remove:
                    if entry_removed:
                        summary += '\n\nThe orphaned Programs-list entry was removed (.reg backup).'
                    else:
                        summary += ('\n\nCould not remove the Programs-list entry — HKLM entries '
                                    'require running as administrator.')
                summary += '\n\nEverything appears in the Restore tab if you change your mind.'
                self._show_info_modal(
                    'Force remove' if force_remove else 'Leftovers', summary,
                    width=520, height=280,
                )
                self.refresh_restore()
                if force_remove:
                    self.refresh_uninstaller()

            self._run_bg(work, done)

        btn_label = 'Archive & force remove' if force_remove else 'Archive selected'
        dlg.add_button('Cancel', dlg.close)
        dlg.add_button(btn_label, do_archive, primary=True)

    # ------------------------------------------------------------------
    # Keyboard shortcuts / accessibility
    # ------------------------------------------------------------------
    def _bind_shortcuts(self):
        self.bind('<F5>', lambda e: self._refresh_all())
        self.bind('<Control-f>', lambda e: self._focus_search())
        self.bind('<Control-F>', lambda e: self._focus_search())
        self.bind('<Control-comma>', lambda e: self._open_settings())
        for i in range(8):
            self.bind(f'<Control-Key-{i + 1}>', lambda e, idx=i: self.tab_control.select(idx))

    def _refresh_all(self):
        self.refresh()
        self.refresh_cleanup()
        self.refresh_restore()
        self.refresh_activity()
        self.refresh_archive_browser()

    def _focus_search(self):
        self.tab_control.select(self.startup_tab)  # search lives on the Startup tab
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
        return 'break'

    # ------------------------------------------------------------------
    # Background-thread helper (UI updates marshalled back to main thread)
    # ------------------------------------------------------------------
    # Workers never touch Tk directly: they push results onto a queue that
    # the main thread drains. Calling after() from a worker thread raises
    # "main thread is not in main loop" when the mainloop isn't running.
    def _run_bg(self, work, done):
        def runner():
            try:
                result, err = work(), None
            except Exception as e:
                result, err = None, e
            self._bg_queue.put((done, result, err))
        threading.Thread(target=runner, daemon=True).start()

    def _poll_bg_queue(self):
        try:
            while True:
                item = self._bg_queue.get_nowait()
                if isinstance(item, tuple) and len(item) == 3 and item[0] == 'scan_progress':
                    _, progress, _ = item
                    self._queue_scan_progress(progress)
                    continue
                done, result, err = item
                try:
                    done(result, err)
                except Exception:
                    pass
        except queue.Empty:
            pass
        try:
            self.after(50, self._poll_bg_queue)
        except Exception:
            pass  # window destroyed

    def _cancel_chunked_work(self, key='tree'):
        token = self._chunk_tokens.get(key, 0) + 1
        self._chunk_tokens[key] = token
        return token

    def _chunk_work_alive(self, key, token):
        return self._chunk_tokens.get(key, 0) == token

    def _chunked_tree_populate(
        self,
        tree,
        rows,
        row_builder,
        *,
        batch_size=60,
        status_lbl=None,
        empty_hint=None,
        on_complete=None,
        token_key='tree',
        clear_selection=True,
        on_progress=None,
    ):
        """Insert tree rows in small batches so the Tk event loop stays responsive."""
        token = self._cancel_chunked_work(token_key)
        try:
            tree.delete(*tree.get_children())
        except Exception:
            pass
        if clear_selection:
            try:
                tree.selection_set(())
            except Exception:
                pass

        total = len(rows)
        if total == 0:
            if empty_hint is not None:
                empty_hint.place(relx=0.5, rely=0.4, anchor='center')
            if status_lbl is not None:
                status_lbl.config(text='')
            if on_complete:
                on_complete()
            return

        if empty_hint is not None:
            empty_hint.place_forget()

        if animations_disabled():
            for j in range(total):
                iid, values, tags = row_builder(j, rows[j])
                tree.insert('', 'end', iid=iid, values=values, tags=tags)
            if status_lbl is not None:
                status_lbl.config(text='')
            if on_complete:
                on_complete()
            return

        if status_lbl is not None:
            status_lbl.config(text=f'Loading… 0/{total:,}')
        if on_progress:
            on_progress(0, total)

        state = {'idx': 0}

        def pump():
            if not self._chunk_work_alive(token_key, token):
                return
            end = min(state['idx'] + batch_size, total)
            for j in range(state['idx'], end):
                iid, values, tags = row_builder(j, rows[j])
                tree.insert('', 'end', iid=iid, values=values, tags=tags)
            state['idx'] = end
            if status_lbl is not None:
                if state['idx'] < total:
                    status_lbl.config(text=f'Loading… {state["idx"]:,}/{total:,}')
                else:
                    status_lbl.config(text='')
            if on_progress:
                on_progress(state['idx'], total)
            if state['idx'] < total:
                self.after(1, pump)
            elif on_complete:
                on_complete()

        self.after(0, pump)

    def _chunked_tree_select(
        self,
        tree,
        iids,
        *,
        batch_size=250,
        status_lbl=None,
        on_complete=None,
        token_key='sel',
    ):
        """Select many rows without blocking the UI thread."""
        token = self._cancel_chunked_work(token_key)
        try:
            tree.selection_set(())
        except Exception:
            pass
        total = len(iids)
        if not total:
            if on_complete:
                on_complete()
            return

        if animations_disabled():
            tree.selection_set(*iids)
            if on_complete:
                on_complete()
            return

        if status_lbl is not None:
            status_lbl.config(text=f'Selecting… 0/{total:,}')

        state = {'idx': 0, 'first': True}

        def pump():
            if not self._chunk_work_alive(token_key, token):
                return
            end = min(state['idx'] + batch_size, total)
            batch = iids[state['idx']:end]
            if state['first']:
                tree.selection_set(*batch)
                state['first'] = False
            else:
                tree.selection_add(*batch)
            state['idx'] = end
            if status_lbl is not None:
                status_lbl.config(
                    text=f'Selecting… {state["idx"]:,}/{total:,}' if state['idx'] < total else '')
            if state['idx'] < total:
                self.after(1, pump)
            elif on_complete:
                on_complete()

        self.after(0, pump)

    def _set_archive_footer_loading(self, current: int, total: int):
        if not hasattr(self, 'archive_status_lbl'):
            return
        if total > 0:
            self.archive_status_lbl.config(
                text=f'Loading archive custody… {current:,} / {total:,} displayed')
        else:
            self.archive_status_lbl.config(text='Loading archive custody…')

    def _set_archive_footer_ready(self, shown: int, total: int):
        if not hasattr(self, 'archive_status_lbl'):
            return
        sel = len(self.archive_tree.selection()) if hasattr(self, 'archive_tree') else 0
        self.archive_status_lbl.config(
            text=f'Showing {shown:,} of {total:,} archive records · {sel:,} selected')

    def _set_archive_footer_empty(self):
        if hasattr(self, 'archive_status_lbl'):
            self.archive_status_lbl.config(text='No archive records in custody.')

    def _set_archive_footer_error(self, msg: str):
        if hasattr(self, 'archive_status_lbl'):
            self.archive_status_lbl.config(text=msg or 'Load failed.')

    def _set_archive_busy(self, busy: bool, message: str = ''):
        self._archive_busy = busy
        self._sync_archive_view(loading=busy)
        if busy:
            self._archive_loaded = False
            self._set_archive_footer_loading(0, 0)
            self._update_archive_stat_cards(loading=True)
        elif message:
            if hasattr(self, 'archive_status_lbl'):
                self.archive_status_lbl.config(text=message)
        self._sync_archive_action_states()
        self._update_brand_identity()

    def _sync_archive_action_states(self):
        """Disable archive restore/delete/search until custody records are loaded."""
        busy = getattr(self, '_archive_busy', False)
        loaded = getattr(self, '_archive_loaded', False) and not busy
        total = int((getattr(self, '_archive_stats', {}) or {}).get('total', 0) or 0)
        sel = len(self.archive_tree.selection()) if hasattr(self, 'archive_tree') else 0
        can_restore = loaded and sel > 0
        can_delete = loaded and sel > 0
        refresh = getattr(self, '_archive_refresh_btn', None)
        if refresh is not None:
            try:
                refresh.config(state='disabled' if busy else 'normal')
            except Exception:
                pass
        restore_btn = getattr(self, '_archive_restore_btn', None)
        if restore_btn is not None:
            try:
                restore_btn.config(state='normal' if can_restore else 'disabled')
            except Exception:
                pass
        for btn in getattr(self, '_archive_action_btns', []):
            try:
                btn.config(state='normal' if can_delete else 'disabled')
            except Exception:
                pass
        for w in getattr(self, '_archive_filter_widgets', []):
            try:
                w.config(state='disabled' if (busy or not loaded) else 'normal')
            except Exception:
                pass

    def _show_delete_archive_confirm(self, recs, *, title='Delete from Archive', on_confirm, preview=None):
        """Summary-only delete confirmation with eligible vs skipped buckets."""
        selected = len(recs)
        if preview is None and archive_custody is not None:
            try:
                preview = archive_custody.apply_prune(
                    recs, str(self.restore_log_path),
                    receipt_dir=brand.user_data_dir() / 'receipts', dry_run=True)
            except Exception:
                preview = None
        eligible_list = (preview or {}).get('pruned') or recs
        eligible = len(eligible_list)
        skipped_list = (preview or {}).get('skipped') or []
        skipped = len(skipped_list)
        eligible_bytes = int((preview or {}).get('bytes_pruned') or 0)
        if not eligible_bytes:
            eligible_bytes = sum(int(r.get('size') or 0) for r in eligible_list)

        reason_counts: dict[str, int] = {}
        skip_labels = {
            'missing dest evidence': 'missing archive proof',
            'not in archive': 'not in archive / already removed',
            'refuses live path': 'unsafe — matches live file path',
        }
        for s in skipped_list:
            reason = skip_labels.get(s.get('reason') or 'other', s.get('reason') or 'other')
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        eligible_dests = {r.get('dest') for r in eligible_list}
        if archive_custody:
            rank_labels = {
                archive_custody.PRUNE_KEEP: 'keep in custody',
                archive_custody.PRUNE_REVIEW: 'review recommended — not marked safe',
            }
            for r in recs:
                dest = r.get('dest')
                if dest in eligible_dests:
                    continue
                rank = r.get('prune_rank')
                lbl = rank_labels.get(rank)
                if lbl and dest not in {s.get('dest') for s in skipped_list}:
                    reason_counts[lbl] = reason_counts.get(lbl, 0) + 1

        skipped_display = max(skipped, selected - eligible)
        dlg = CleanroomModal(
            self, title, width=500, height=360, colors=self._dialog_colors(),
        )
        dlg.heading('Delete from archive custody')
        summary_lines = [
            f'Selected: {selected:,}',
            f'Eligible to delete now: {eligible:,}',
            f'Eligible size: {self._format_size(eligible_bytes)}',
            f'Will be skipped: {skipped_display:,}',
            '',
            'Original live files are not touched.',
            'This permanently removes archived copies from Cleanroom custody.',
        ]
        if reason_counts:
            summary_lines.append('')
            summary_lines.append('Why skipped:')
            for reason, cnt in sorted(reason_counts.items(), key=lambda x: -x[1])[:8]:
                summary_lines.append(f'  · {reason}: {cnt:,}')
        dlg.message('\n'.join(summary_lines), wrap=440)

        delete_lbl = (
            f'Delete {eligible:,} eligible item{"s" if eligible != 1 else ""}'
            if eligible else 'Nothing eligible to delete')

        def _confirm_delete():
            dlg.close()
            on_confirm()

        dlg.add_button('Show file list…', lambda: self._show_delete_file_list(recs), side='left')
        dlg.add_button('Cancel', dlg.close)
        delete_btn = dlg.add_button(delete_lbl, _confirm_delete, primary=True)
        if eligible == 0:
            delete_btn.configure(state='disabled')

    def _show_delete_file_list(self, recs, *, parent=None):
        """Scrollable optional file list for large archive delete selections."""
        dlg = CleanroomModal(
            parent or self, 'Selected archive files',
            width=680, height=480, colors=self._dialog_colors(), resizable=True,
        )
        dlg.heading(f'{len(recs):,} archived file(s)', size=14)
        txt = dlg.scroll_text('', height=320, mono=True)

        token = self._cancel_chunked_work('delete_list')
        state = {'idx': 0}
        batch = 120

        def pump():
            if not self._chunk_work_alive('delete_list', token):
                return
            end = min(state['idx'] + batch, len(recs))
            lines = []
            for r in recs[state['idx']:end]:
                lines.append(f'{self._format_size(r.get("size", 0))}  {r.get("dest", "")}')
            txt.config(state='normal')
            txt.insert('end', '\n'.join(lines) + ('\n' if end < len(recs) else ''))
            txt.config(state='disabled')
            txt.see('end')
            state['idx'] = end
            if state['idx'] < len(recs):
                self.after(1, pump)

        dlg.add_button('Close', dlg.close, primary=True)
        self.after(0, pump)

    def get_tray_tooltip(self) -> str:
        """Live tray tooltip — proof state, not just app name."""
        try:
            if getattr(self, '_cleaner_loading', False):
                prog = getattr(self, '_scan_progress', None) or {}
                files = int(prog.get('files_checked', 0) or 0)
                cands = int(prog.get('candidates_found', 0) or 0)
                tip = f'{brand.APP_DISPLAY} — Scanning · {files:,} checked'
                if cands:
                    tip += f' · {cands} candidate(s)'
                return tip
            if getattr(self, '_scan_stopped', False):
                return f'{brand.APP_DISPLAY} — Scan stopped'
            state = self._compute_brand_state()
            pill = state.get('pill') or brand.APP_LOCKUP_PILL
            status = state.get('status') or ''
            if status:
                return f'{brand.APP_DISPLAY} — {status}'
            return f'{brand.APP_DISPLAY} — {pill}'
        except Exception:
            pass
        try:
            txt = self.global_status.cget('text')
            if txt:
                return f'{brand.APP_DISPLAY} — {txt}'
        except Exception:
            pass
        return f'{brand.APP_DISPLAY} — Archive-first ON'

    def _refresh_tray_tooltip(self):
        tray = getattr(self, '_tray', None)
        if tray is not None:
            try:
                tray.refresh_tooltip()
            except Exception:
                pass

    def _set_status(self, text, *, pulse=False):
        try:
            self.global_status.config(text=text)
            if pulse and not animations_disabled():
                self.global_status.config(fg=ACCENT)
                self.after(420, lambda: self.global_status.config(fg=TEXT))
            self._refresh_tray_tooltip()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Empty-state hints (centered label shown when a tree has no rows)
    # ------------------------------------------------------------------
    def _make_empty_hint(self, tree, text):
        return tk.Label(tree, text=text, bg=CARD_BG, fg=MUTED,
                        font=('Segoe UI', 10, 'italic'), justify='center')

    def _build_workspace_empty_panel(self, parent, title, body, button_text='', command=None):
        panel = ctk_theme.frame(parent, CARD_BG, corner_radius=12)
        inner = ttk.Frame(panel, style='Card.TFrame')
        inner.place(relx=0.5, rely=0.42, anchor='center')
        ttk.Label(inner, text=title, font=('Segoe UI', 16, 'bold'),
                  background=CARD_BG).pack(anchor='center')
        ttk.Label(inner, text=body, style='Info.TLabel',
                  wraplength=440, justify='center').pack(anchor='center', pady=(8, 16))
        if button_text and command:
            ttk.Button(inner, text=button_text, style='Primary.TButton',
                       command=command).pack(anchor='center')
        return panel

    def _sync_startup_view(self, *, loading=False):
        has = bool(self.tree.get_children()) if hasattr(self, 'tree') else False
        sync_split_workspace(
            loading=loading, has_rows=has,
            pane=getattr(self, '_startup_pane', None),
            empty_panel=getattr(self, '_startup_empty_panel', None),
            loading_panel=getattr(self, '_startup_loading_lbl', None),
        )

    def _sync_restore_view(self, *, loading=False):
        has = bool(self.restore_tree.get_children()) if hasattr(self, 'restore_tree') else False
        sync_split_workspace(
            loading=loading, has_rows=has,
            pane=getattr(self, '_restore_pane', None),
            empty_panel=getattr(self, '_restore_empty_panel', None),
            loading_panel=getattr(self, '_restore_loading_lbl', None),
        )

    def _sync_uninst_view(self, *, loading=False):
        has = bool(self.uninstall_tree.get_children()) if hasattr(self, 'uninstall_tree') else False
        sync_split_workspace(
            loading=loading, has_rows=has,
            pane=getattr(self, '_uninst_pane', None),
            empty_panel=getattr(self, '_uninst_empty_panel', None),
            loading_panel=getattr(self, '_uninst_loading_lbl', None),
        )

    def _sync_archive_view(self, *, loading=False):
        has = bool(self.archive_tree.get_children()) if hasattr(self, 'archive_tree') else False
        sync_split_workspace(
            loading=loading, has_rows=has,
            pane=getattr(self, '_archive_pane', None),
            empty_panel=getattr(self, '_archive_empty_panel', None),
            loading_panel=getattr(self, '_archive_loading_lbl', None),
        )

    def _sync_activity_view(self, *, loading=False):
        has = bool(self.activity_tree.get_children()) if hasattr(self, 'activity_tree') else False
        sync_split_workspace(
            loading=loading, has_rows=has,
            pane=getattr(self, '_activity_pane', None),
            empty_panel=getattr(self, '_activity_empty_panel', None),
            loading_panel=getattr(self, '_activity_loading_lbl', None),
        )

    def _show_info_modal(self, title, message, *, width=460, height=220):
        dlg = CleanroomModal(
            self, title, width=width, height=height, colors=self._dialog_colors(),
        )
        dlg.heading(title)
        dlg.message(message, wrap=max(280, width - 80))
        dlg.add_button('OK', dlg.close, primary=True)

    def _refresh_empty_hint(self, hint, tree):
        if tree.get_children():
            hint.place_forget()
        else:
            hint.place(relx=0.5, rely=0.35, anchor='center')

    # ------------------------------------------------------------------
    # Search / filter / sort
    # ------------------------------------------------------------------
    def _clear_search_placeholder(self, event=None):
        if self.search_var.get() == SEARCH_PLACEHOLDER:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(foreground=TEXT)

    def _restore_search_placeholder(self, event=None):
        if not self.search_var.get().strip():
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, SEARCH_PLACEHOLDER)
            self.search_entry.config(foreground=PLACEHOLDER)

    def _refresh_category_buttons(self):
        for button, category in ((self.cat_all, 'All'), (self.cat_folders, 'Folders'),
                                 (self.cat_registry, 'Registry'), (self.cat_tasks, 'Tasks'),
                                 (self.cat_disabled, 'Disabled')):
            button.configure(style='Sidebar.Selected.TButton' if self.current_category == category else 'Sidebar.TButton')

    def _add_tooltip(self, widget, text):
        ToolTip(widget, text)

    def _on_row_select(self, event):
        self._update_detail()
        self._update_actions()

    def _on_search(self, txt):
        if txt.strip() == SEARCH_PLACEHOLDER:
            self.search_text = ''
        else:
            self.search_text = txt.strip()
        self._apply_filter()

    def _set_category(self, cat):
        self.current_category = cat
        self._refresh_category_buttons()
        self._apply_filter()
        self._update_context_panel()

    def _startup_type(self, entry):
        source = ((entry or {}).get('source') or '').lower()
        return {
            'registry': 'Registry',
            'folder': 'Folder',
            'folders': 'Folder',
            'task': 'Scheduled task',
            'tasks': 'Scheduled task',
            'disabled': 'Disabled backup',
        }.get(source, source.replace('_', ' ').title() or 'Unknown')

    def _startup_status(self, entry):
        source = ((entry or {}).get('source') or '').lower()
        if source == 'disabled':
            return 'Disabled — restorable'
        return 'Active'

    def _startup_sort_key(self, item, key):
        if key == 'type':
            return self._startup_type(item).lower()
        if key == 'status':
            return self._startup_status(item).lower()
        return (item.get(key) or '').lower()

    def _startup_row_values(self, entry):
        return (
            entry.get('name') or '',
            self._startup_type(entry),
            entry.get('source') or '',
            self._startup_status(entry),
        )

    def _sort_column(self, col):
        reverse = self.current_sort[0] == col and not self.current_sort[1]
        self.current_sort = (col, reverse)
        self._apply_filter()

    def _apply_filter(self):
        q = self.search_text.lower()
        self._cancel_chunked_work('startup_tree')

        def matches(v):
            if not q:
                return True
            return q in (v.get('name') or '').lower() or q in (v.get('command') or '').lower() or q in (v.get('location') or '').lower()

        rows = []
        if self.current_category in ('All', 'Folders'):
            for e in self.data.get('folders', []):
                v = {'name': e.get('name') or Path(e.get('path', '')).name,
                     'source': e.get('source'),
                     'location': e.get('location'),
                     'command': e.get('path')}
                if matches(v):
                    rows.append(v)
        if self.current_category in ('All', 'Registry'):
            for r in self.data.get('registry', []):
                v = {'name': r.get('name'),
                     'source': r.get('source'),
                     'location': r.get('key'),
                     'command': r.get('command')}
                if matches(v):
                    rows.append(v)
        if self.current_category in ('All', 'Tasks'):
            for t in self.data.get('tasks', []):
                v = {'name': t.get('name'),
                     'source': t.get('source'),
                     'location': t.get('location'),
                     'command': t.get('command')}
                if matches(v):
                    rows.append(v)
        if self.current_category in ('All', 'Disabled'):
            for d in self.data.get('disabled', []):
                v = {'name': d.get('name'),
                     'source': 'disabled',
                     'location': f"{d.get('hive')}\\{d.get('key')}",
                     'command': d.get('command')}
                if matches(v):
                    rows.append(v)

        key = self.current_sort[0]
        rows.sort(key=lambda item: self._startup_sort_key(item, key), reverse=self.current_sort[1])

        def build_row(idx, v):
            tag = 'evenrow' if idx % 2 else 'oddrow'
            return (str(idx), self._startup_row_values(v), (tag,))

        def on_complete():
            self._startup_rows = list(rows)
            self._refresh_empty_hint(self.startup_empty_hint, self.tree)
            self._update_context_panel()

        if hasattr(self, 'status_lbl') and rows:
            self.status_lbl.config(text=f'Loading {len(rows):,} entries…')

        def on_done():
            if hasattr(self, 'status_lbl'):
                total = len(self.data.get('folders', [])) + len(self.data.get('registry', []))
                shown = len(rows)
                self.status_lbl.config(
                    text=f'{shown:,} shown' if shown != total else f'{total:,} entries')
            on_complete()
            self._sync_startup_view(loading=False)

        self._chunked_tree_populate(
            self.tree,
            rows,
            build_row,
            status_lbl=getattr(self, 'status_lbl', None),
            empty_hint=self.startup_empty_hint,
            on_complete=on_done,
            token_key='startup_tree',
        )

    def _update_actions(self):
        ent = self._selected_entry()
        source = (ent or {}).get('source')
        if source == 'registry':
            self.enable_btn.config(state='normal', text='Enable Selected')
            self.disable_btn.config(state='normal')
        elif source == 'disabled':
            self.enable_btn.config(state='normal', text='Re-enable Selected')
            self.disable_btn.config(state='disabled')
        else:
            self.enable_btn.config(state='disabled', text='Enable Selected')
            self.disable_btn.config(state='disabled')

    # ------------------------------------------------------------------
    # Cleaner
    # ------------------------------------------------------------------
    def _load_cleanup_config(self):
        if not cleanup_main:
            messagebox.showerror('Cleanup error', 'Cleanup module is unavailable.')
            return None
        try:
            return cleanup_main.load_config(self.cleanup_config_path)
        except Exception as e:
            messagebox.showerror('Cleanup config error', f'Unable to load cleanup config:\n{e}')
            return None

    def _sync_scan_progress_ui(self):
        prog = getattr(self, '_scan_progress', None) or {}
        folder = (prog.get('current_folder') or '').strip()
        sub = f'Scanning: {folder}' if folder else 'Reviewing configured folders for candidates.'
        if hasattr(self, '_scan_loading_sub'):
            self._scan_loading_sub.config(text=sub)
        folders = int(prog.get('folders_scanned', 0) or 0)
        files = int(prog.get('files_checked', 0) or 0)
        cands = int(prog.get('candidates_found', 0) or 0)
        size = prog.get('reclaimable_label') or self._format_size(prog.get('reclaimable_bytes', 0))
        elapsed = int(prog.get('elapsed_s', 0) or 0)
        m, s = divmod(elapsed, 60)
        elapsed_txt = f'{m}m {s}s' if m else f'{s}s'
        if hasattr(self, '_scan_counter_folders'):
            self._scan_counter_folders.config(text=f'Folders: {folders}')
            self._scan_counter_files.config(text=f'Files checked: {files:,}')
            self._scan_counter_candidates.config(text=f'Candidates: {cands}')
            self._scan_counter_size.config(text=f'Reclaimable: {size}')
            self._scan_counter_elapsed.config(text=f'Elapsed: {elapsed_txt}')
        if hasattr(self, '_scan_loading_bar'):
            try:
                if self._cleaner_loading:
                    self._scan_loading_bar.start(12)
                else:
                    self._scan_loading_bar.stop()
            except Exception:
                pass

    def _schedule_scan_progress_tick(self):
        if not getattr(self, '_cleaner_loading', False):
            self._scan_progress_job = None
            return
        self._sync_scan_progress_ui()
        self._sync_cleaner_state()
        self._sync_home_state()
        self._scan_progress_job = self.after(400, self._schedule_scan_progress_tick)

    def _queue_scan_progress(self, progress: dict):
        self._scan_progress = dict(progress or {})
        self._scan_diag.update(self._scan_progress)

    def stop_scan(self):
        if not getattr(self, '_cleaner_loading', False):
            return
        logger.info('Scan stop requested')
        self._scan_cancel_event.set()
        self._scan_diag['stop_requested'] = True
        self._set_status('Stopping scan…')

    def skip_scan_folder(self):
        if not getattr(self, '_cleaner_loading', False):
            return
        folder = (getattr(self, '_scan_progress', None) or {}).get('current_folder', '')
        if folder:
            self._scan_skip_folders.add(folder)
            self._set_status(f'Skipping folder: {folder}')
        else:
            self._set_status('No active folder to skip.')

    def refresh_cleanup(self):
        if getattr(self, '_cleaner_loading', False):
            logger.info('Scan already running — ignoring duplicate start')
            return
        cfg = self._load_cleanup_config()
        if cfg is None:
            return

        self._scan_worker_id += 1
        worker_id = self._scan_worker_id
        self._scan_cancel_event = threading.Event()
        self._scan_progress = {}
        self._scan_diag = {
            'started_at': time.time(),
            'configured_roots': list(cfg.get('paths') or []),
            'exclude_patterns': list(cfg.get('exclude_patterns') or []),
        }
        self._scan_stopped = False
        self._scan_skip_folders = set()
        self._cleaner_loading = True
        self._cleaner_error = ''
        self.tb_preview.configure(state='disabled')
        self.tb_apply.configure(state='disabled')
        self._sync_cleaner_state()
        self._sync_home_state()
        self._schedule_scan_progress_tick()

        def progress_cb(prog):
            if worker_id != self._scan_worker_id:
                return
            self._bg_queue.put(('scan_progress', prog, None))

        def work():
            skip_folders = self._scan_skip_folders

            def skip_check(folder):
                return folder in skip_folders

            items = cleanup_main.scan_candidates(
                cfg,
                cancel_check=self._scan_cancel_event.is_set,
                on_progress=progress_cb,
                skip_folder_check=skip_check,
            )
            cancelled = self._scan_cancel_event.is_set()
            return {'items': items, 'cancelled': cancelled, 'cfg': cfg}

        def done(result, err):
            if worker_id != self._scan_worker_id:
                return
            self._finish_scan_worker(result, err)

        self._run_bg(work, done)

    def _finish_scan_worker(self, result, err):
        self._cleaner_loading = False
        if self._scan_progress_job is not None:
            try:
                self.after_cancel(self._scan_progress_job)
            except Exception:
                pass
            self._scan_progress_job = None
        self.tb_preview.configure(state='normal')
        self.tb_apply.configure(state='normal')
        try:
            if hasattr(self, '_scan_loading_bar'):
                self._scan_loading_bar.stop()
        except Exception:
            pass

        cancelled = False
        items = []
        cfg = None
        if isinstance(result, dict):
            items = result.get('items') or []
            cancelled = bool(result.get('cancelled'))
            cfg = result.get('cfg')

        self._scan_diag['worker_exit'] = 'cancelled' if cancelled else ('error' if err else 'completed')
        self._scan_diag['stop_completed'] = cancelled
        logger.info('Scan worker exit: %s', self._scan_diag.get('worker_exit'))

        if err is not None and not cancelled:
            self._cleaner_error = str(err)
            self._scan_stopped = False
            self._sync_cleaner_state()
            self._sync_home_state()
            self._update_context_panel()
            self._maybe_finish_pending_shutdown()
            return

        if cancelled:
            self._scan_stopped = True
            self.cleanup_items = []
            self.cleanup_selected = set()
            self.cleanup_total_size = 0
            self._sync_cleaner_state()
            self._sync_home_state()
            self._update_context_panel()
            self._maybe_finish_pending_shutdown()
            return

        self._scan_stopped = False
        self.cleanup_items = items
        self.cleanup_selected = set(range(len(items)))
        self.cleanup_total_size = sum(item.get('size', 0) for item in items)
        if cfg is not None:
            self._last_cfg = cfg
            self._update_cleanup_summary(cfg)
        self._update_cleanup_tree()
        self._scan_session_done = True
        self._save_scan_cache()
        self._sync_cleaner_state()
        self.refresh_dashboard()
        self._update_context_panel()
        self._maybe_finish_pending_shutdown()

    def _maybe_finish_pending_shutdown(self):
        if getattr(self, '_pending_shutdown', False):
            self._pending_shutdown = False
            self.after(50, lambda: self._shutdown_app(reason='tray-quit-after-scan-stop'))

    def _format_size(self, bytes_value):
        if cleanup_main:
            return cleanup_main.human_size(bytes_value)
        return f'{bytes_value}B'

    def _update_cleanup_summary(self, cfg=None):
        selected_size = sum(self.cleanup_items[i].get('size', 0) for i in self.cleanup_selected
                            if 0 <= i < len(self.cleanup_items))
        n = len(self.cleanup_items)
        checked = len(self.cleanup_selected)
        self.cleanup_count_label.config(text=f'{n} candidates · {checked} checked')
        self.cleanup_size_label.config(text=f'{self._format_size(selected_size)} reclaimable')
        reason_counts = {}
        for item in self.cleanup_items:
            reason = item.get('reason') or 'other'
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if reason_counts and hasattr(self, 'cleanup_cat_lbl'):
            top = sorted(reason_counts.items(), key=lambda x: -x[1])[:3]
            self.cleanup_cat_lbl.config(
                text=' · '.join(f'{k}: {v}' for k, v in top))
        self._refresh_header_proof_badges()
        archive = (cfg or {}).get('archive_dir') if cfg else None
        self.cleanup_archive_label.config(text=f'Archive: {archive or "auto"}')
        self._sync_cleaner_state()

    def _update_cleanup_tree(self):
        self.cleanup_tree.delete(*self.cleanup_tree.get_children())
        grouped = {label: [] for label, _ in CLEANUP_REASON_GROUPS}
        for idx, item in enumerate(self.cleanup_items):
            gname = self._cleanup_group_for_reason(item.get('reason'))
            grouped.setdefault(gname, []).append((idx, item))

        row_counter = 0
        for label, _keys in CLEANUP_REASON_GROUPS:
            items = grouped.get(label, [])
            if not items:
                continue
            checked_n = sum(1 for idx, _ in items if idx in self.cleanup_selected)
            gid = self.cleanup_tree.insert(
                '', 'end', text=f'{label} ({len(items)})',
                values=('', f'{checked_n} checked', ''), tags=('group',))
            self.cleanup_tree.item(gid, open=True)
            for idx, item in items:
                stripe = 'evenrow' if row_counter % 2 else 'oddrow'
                row_counter += 1
                reason = item.get('reason') or ''
                mark = '☑' if idx in self.cleanup_selected else '☐'
                path = item.get('path') or ''
                name = Path(path).name if path else '—'
                tags = [stripe, f'reason:{reason}', f'idx:{idx}']
                if idx in self.cleanup_selected:
                    tags.append('checked')
                self.cleanup_tree.insert(
                    gid, 'end', text=name,
                    values=(mark, self._format_size(item.get('size', 0)), reason),
                    tags=tuple(tags))
        self._update_cleanup_empty_state()
        self._on_cleanup_select()

    def _toggle_cleanup_index(self, idx):
        if idx in self.cleanup_selected:
            self.cleanup_selected.discard(idx)
        else:
            self.cleanup_selected.add(idx)
        for gid in self.cleanup_tree.get_children(''):
            for row in self.cleanup_tree.get_children(gid):
                if f'idx:{idx}' in self.cleanup_tree.item(row, 'tags'):
                    self.cleanup_tree.set(row, 'sel', '☑' if idx in self.cleanup_selected else '☐')
                    tags = list(self.cleanup_tree.item(row, 'tags'))
                    if idx in self.cleanup_selected:
                        if 'checked' not in tags:
                            tags.append('checked')
                    elif 'checked' in tags:
                        tags.remove('checked')
                    self.cleanup_tree.item(row, tags=tuple(tags))
                    break
        self._refresh_cleanup_group_headers()
        self._update_cleanup_summary(self._cached_cfg())

    def _cached_cfg(self):
        return getattr(self, '_last_cfg', None)

    def _on_cleanup_click(self, event):
        region = self.cleanup_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        row_id = self.cleanup_tree.identify_row(event.y)
        if not row_id or self._is_cleanup_group_row(row_id):
            return
        col = self.cleanup_tree.identify_column(event.x)
        if col == '#1':
            idx = self._cleanup_item_index(row_id)
            if idx is not None:
                self._toggle_cleanup_index(idx)
        self.cleanup_tree.selection_set(row_id)
        self.cleanup_tree.focus(row_id)
        self._on_cleanup_select()

    def _on_cleanup_space(self, event):
        sel = self.cleanup_tree.selection()
        if sel and not self._is_cleanup_group_row(sel[0]):
            idx = self._cleanup_item_index(sel[0])
            if idx is not None:
                self._toggle_cleanup_index(idx)
        return 'break'

    def _set_cleanup_selection(self, select_all):
        self.cleanup_selected = set(range(len(self.cleanup_items))) if select_all else set()
        self._update_cleanup_tree()
        self._update_cleanup_summary(self._cached_cfg())

    def _toggle_all_cleanup_selection(self):
        self._set_cleanup_selection(len(self.cleanup_selected) < len(self.cleanup_items))

    def apply_cleanup(self):
        if not cleanup_main:
            messagebox.showerror('Cleanup error', 'Cleanup module is unavailable.')
            return
        cfg = self._load_cleanup_config()
        if cfg is None:
            return
        if not self.cleanup_items:
            messagebox.showinfo('Cleanup', 'No cleanup candidates available. Scan first.')
            return
        items = [self.cleanup_items[i] for i in sorted(self.cleanup_selected)
                 if 0 <= i < len(self.cleanup_items)]
        if not items:
            messagebox.showinfo('Cleanup', 'No candidates are checked. Check at least one item to apply.')
            return

        total_bytes = sum(item.get('size', 0) for item in items)
        threshold = cfg.get('confirm_threshold_bytes') or 5 * 1024 * 1024 * 1024
        if total_bytes >= threshold:
            answer = messagebox.askyesno(
                'Confirm cleanup',
                f'Cleanup will archive {len(items)} items and reclaim {self._format_size(total_bytes)}. Continue?')
            if not answer:
                return

        dedupe = self.dedupe_enabled.get()
        archive_dir = cfg.get('archive_dir') or str(Path(__file__).parent / ('archive_' + datetime.now().strftime('%Y%m%d%H%M%S')))

        self.apply_clean_btn.config(state='disabled')
        self.tb_apply.configure(state='disabled')
        self._set_status('Archiving files to Cleanroom archive…')

        def work():
            volume = proof_module.volume_of(archive_dir) if proof_module else None
            before_free = proof_module.disk_free(volume) if proof_module else 0
            if dedupe:
                keep, duplicates = cleanup_main.dedupe_candidates(items)
            else:
                keep, duplicates = items, []
            log = cleanup_main.apply_actions(keep, cfg, archive_dir)
            if duplicates:
                dup_dir = Path(archive_dir) / 'duplicates'
                dup_dir.mkdir(parents=True, exist_ok=True)
                for d in duplicates:
                    try:
                        src = Path(d['path'])
                        if not src.exists():
                            continue
                        dest = dup_dir / src.name
                        if dest.exists():
                            dest = dup_dir / (datetime.now().strftime('%Y%m%d%H%M%S_') + src.name)
                        shutil.move(str(src), str(dest))
                    except Exception:
                        pass
            prf = None
            if proof_module:
                prf = proof_module.build_proof(before_free, proof_module.disk_free(volume), log)
            return log, len(duplicates), prf

        def done(result, err):
            self.apply_clean_btn.config(state='normal')
            self.tb_apply.configure(state='normal')
            if err is not None:
                self._set_status('Cleanup failed.')
                messagebox.showerror('Cleanup failed', f'Cleanup failed: {err}')
                return
            log, dup_count, prf = result
            extra = f' ({dup_count} duplicate(s) separated)' if dup_count else ''
            self._set_status(f'Cleanup finished: {len(log)} item(s) archived{extra}.')
            bought = None
            receipt_path = None
            if receipts_module and log:
                try:
                    if foresight:
                        fc = foresight.forecast(foresight.load_history())
                        freed = sum(int(e.get('size') or 0) for e in log)
                        bought = foresight.days_bought(freed, fc['slope_per_day'])
                    receipt_path = receipts_module.write_receipt(log, days_bought=bought, proof=prf)
                except Exception:
                    pass
            if prf and log:
                def _open_proof_report():
                    self._show_proof_report(
                        log, prf, receipt_path=receipt_path,
                        days_bought=bought, dup_count=dup_count)

                if receipt_path and Path(receipt_path).is_file():
                    self._play_receipt_animation(
                        'RECEIPT GENERATED',
                        on_complete=_open_proof_report,
                    )
                else:
                    c = prf.get('custody') or {}
                    ok = c.get('missing', 0) == 0 and c.get('total', 0) > 0
                    self._play_receipt_animation(
                        'CUSTODY VERIFIED' if ok else 'RECEIPT GENERATED',
                        on_complete=_open_proof_report,
                    )
            else:
                messagebox.showinfo('Cleanup', f'Finished cleanup: {len(log)} items archived.{extra}')
            self._brand_phase = 'archived'
            self._update_brand_identity()
            self.refresh_cleanup()
            self.refresh_restore()
            self.refresh_activity()

        self._run_bg(work, done)

    def _load_log_dicts(self):
        if restore_module is None or not self.restore_log_path.exists():
            return []
        try:
            actions = restore_module.load_log(str(self.restore_log_path))
            return [t[3] for t in restore_module.entries_from_log(actions)]
        except Exception:
            return []

    def refresh_activity(self):
        if ledger_module is None or proof_module is None:
            return
        self._cancel_chunked_work('activity_tree')
        self.act_refresh_btn.config(state='disabled')
        self.act_status_lbl.config(text='Loading proof ledger…')
        self._set_activity_loading(True)

        log_path = str(self.restore_log_path)

        def work():
            actions = []
            if Path(log_path).exists() and restore_module:
                try:
                    actions = restore_module.load_log(log_path)
                except Exception:
                    actions = []
            feed = ledger_module.build_activity_feed(actions)
            entries = [t[3] for t in restore_module.entries_from_log(actions)] if restore_module else []
            custody = proof_module.verify_entries(entries)
            summary = ledger_module.summarize_feed(feed)
            trust = ledger_module.trust_score(custody['verified'], custody['total'])
            return feed, custody, summary, trust

        def done(result, err):
            self.act_refresh_btn.config(state='normal')
            if err is not None:
                self._set_activity_loading(False)
                self.act_status_lbl.config(text=f'Load failed: {err}')
                return
            feed, custody, summary, trust = result
            self._activity_feed = feed
            tone = ACCENT if trust >= 95 else (SEVERITY_COLORS['medium'] if trust >= 70
                                               else SEVERITY_COLORS['high'])
            band = 'VERIFIED' if custody['missing'] == 0 and custody['total'] else (
                'NO DATA' if custody['total'] == 0 else 'GAPS')
            self._draw_trust_ring(trust, tone)
            self.trust_band_lbl.config(text=band, fg=tone)
            self.trust_sub_lbl.config(
                text=f"{custody['verified']}/{custody['total']} artifacts on disk · "
                     f"{self._format_size(custody['bytes_in_custody'])} in custody")
            self.stat_act_total.config(text=str(summary['total_actions']))
            self.stat_act_present.config(text=str(summary['present']))
            self.stat_act_bytes.config(text=self._format_size(custody['bytes_in_custody']))
            if hasattr(self, 'stat_act_pruned'):
                self.stat_act_pruned.config(text=self._format_size(summary.get('bytes_pruned', 0)))
            self._refresh_header_proof_badges()

            rows = [(i, e) for i, e in enumerate(feed) if e.get('kind') != 'restore']

            def build_row(_j, item):
                i, e = item
                when = (e.get('when') or '')[:19].replace('T', ' ')
                tag = 'present' if e.get('present') else 'missing'
                if e.get('kind') == 'prune':
                    tag = 'missing'
                stripe = 'evenrow' if _j % 2 else 'oddrow'
                status = '✓' if e.get('present') else '✗'
                src = e.get('src') or ''
                item_name = Path(src).name if src else '—'
                kind = e.get('kind') or ''
                event = ACTIVITY_EVENT_LABELS.get(kind, kind.replace('_', ' ').title())
                return (
                    str(i),
                    (status, when, event,
                     e.get('reason', ''), item_name,
                     self._format_size(e.get('size', 0))),
                    (stripe, tag),
                )

            def on_complete():
                self._set_activity_loading(False)
                self._sync_activity_view(loading=False)
                self.act_status_lbl.config(
                    text=f'{summary["total_actions"]:,} actions · custody trust {trust}%'
                    if custody['total'] else 'Awaiting first action')
                if rows:
                    try:
                        first = self.activity_tree.get_children()[0]
                        self.activity_tree.selection_set(first)
                        self.activity_tree.focus(first)
                    except Exception:
                        pass
                self._on_activity_select()
                self._update_brand_identity()
                if hasattr(self, '_activity_pane'):
                    self.after(50, lambda: self._ensure_pane(
                        self._activity_pane, 'activity_split', default=520,
                        min_left=340, min_right=260, default_ratio=0.68))

            self._chunked_tree_populate(
                self.activity_tree,
                rows,
                build_row,
                status_lbl=self.act_status_lbl,
                empty_hint=self.activity_empty,
                on_complete=on_complete,
                token_key='activity_tree',
            )

        self._run_bg(work, done)

    def open_archive_browser_tab(self):
        self.tab_control.select(self.archive_tab)
        self.refresh_archive_browser()

    def refresh_archive_browser(self):
        if archive_custody is None or restore_module is None:
            return
        self._cancel_chunked_work('archive_tree')
        self._cancel_chunked_work('archive_sel')
        self._set_archive_busy(True, 'Loading archive custody…')
        log_path = str(self.restore_log_path)
        cfg = self._load_cleanup_config() or {}
        receipt_dir = brand.user_data_dir() / 'receipts'

        def work():
            actions = []
            if Path(log_path).exists():
                try:
                    actions = restore_module.load_log(log_path)
                except Exception:
                    actions = []
            records = archive_custody.build_archive_records(
                actions, receipt_dir=receipt_dir, config=cfg)
            stats = archive_custody.summarize_archive_records(records)
            return records, stats

        def done(result, err):
            if err is not None:
                self._set_archive_busy(False)
                self._set_archive_footer_error(f'Load failed: {err}')
                self._sync_archive_action_states()
                return
            self._archive_records_all, self._archive_stats = result
            self._update_archive_stat_cards(loading=True)
            self._apply_archive_view_filters()
            self._update_context_panel()

        self._run_bg(work, done)

    def _update_archive_stat_cards(self, *, loading=False):
        stats = getattr(self, '_archive_stats', {}) or {}
        placeholder = '…' if loading or getattr(self, '_archive_busy', False) else '0'
        if hasattr(self, 'stat_arch_total'):
            self.stat_arch_total.config(
                text=placeholder if loading else str(stats.get('total', 0)))
            self.stat_arch_safe.config(
                text=placeholder if loading else str(stats.get('safe_count', 0)))
            self.stat_arch_bytes.config(
                text=placeholder if loading else self._format_size(stats.get('bytes_total', 0)))
        sel = len(self.archive_tree.selection()) if hasattr(self, 'archive_tree') else 0
        if hasattr(self, 'stat_arch_selected'):
            self.stat_arch_selected.config(text=str(sel) if not loading else '…')

    def _apply_archive_view_filters(self):
        if archive_custody is None or not hasattr(self, 'archive_tree'):
            return
        self._cancel_chunked_work('archive_tree')
        self._cancel_chunked_work('archive_sel')
        records = list(getattr(self, '_archive_records_all', []) or [])
        rank_filter = getattr(self, '_archive_prune_filter', None)
        filt = rank_filter.get() if rank_filter else ''
        if filt:
            records = archive_custody.filter_by_prune_rank(records, filt)
        search_var = getattr(self, '_archive_search_var', None)
        if search_var:
            records = archive_custody.filter_by_search(records, search_var.get())
        self._archive_records = records

        rank_tags = {
            archive_custody.PRUNE_SAFE: 'safe',
            archive_custody.PRUNE_REVIEW: 'review',
            archive_custody.PRUNE_KEEP: 'keep',
        }

        def build_row(i, rec):
            when = (rec.get('when') or '')[:19].replace('T', ' ')
            rp = rec.get('receipt_path')
            rank_tag = rank_tags.get(rec.get('prune_rank'), 'review')
            stripe = 'evenrow' if i % 2 else 'oddrow'
            src = rec.get('src') or ''
            item_name = Path(src).name if src else '—'
            return (
                str(i),
                (
                    when,
                    item_name,
                    rec.get('reason', ''),
                    self._format_size(rec.get('size', 0)),
                    'Yes' if rec.get('restorable') else 'No',
                    'Yes' if rp else '—',
                    rec.get('prune_rank', ''),
                ),
                (rank_tag, stripe),
            )

        def on_complete():
            total_all = len(getattr(self, '_archive_records_all', []) or [])
            shown = len(records)
            self._archive_loaded = True
            self._set_archive_busy(False)
            if shown:
                self._set_archive_footer_ready(shown, total_all)
            else:
                self._set_archive_footer_empty()
            self._update_archive_stat_cards()
            self._on_archive_select()
            self._sync_archive_view(loading=False)
            self._sync_archive_action_states()

        if records:
            self._set_archive_footer_loading(0, len(records))
        self._chunked_tree_populate(
            self.archive_tree,
            records,
            build_row,
            empty_hint=self.archive_empty,
            on_complete=on_complete,
            on_progress=(
                lambda cur, tot: self._set_archive_footer_loading(cur, tot) if records else None
            ),
            token_key='archive_tree',
            clear_selection=True,
        )

    def _on_archive_select(self):
        if not hasattr(self, '_archive_detail_src'):
            return
        recs = self._selected_archive_records()
        self._update_archive_stat_cards()
        if not recs:
            self._archive_detail_src.config(text='Original: —')
            self._archive_detail_dest.config(text='Archive: —')
            self._archive_detail_meta.config(text='Select a row to view custody proof and actions.')
            self._archive_detail_rank.config(text='Recommendation: —')
            self._update_context_panel()
            return
        r = recs[0]
        when = (r.get('when') or '')[:19].replace('T', ' ')
        self._archive_detail_src.config(text=f'Original:\n{r.get("src", "—")}')
        self._archive_detail_dest.config(text=f'Archive:\n{r.get("dest", "—")}')
        custody = 'Verified on disk ✓' if r.get('restorable') else 'Not found on disk ✗'
        extra = f'{len(recs)} selected · {self._format_size(sum(int(x.get("size") or 0) for x in recs))}'
        if len(recs) == 1:
            extra = (f'{when} · {r.get("reason", "—")} · {self._format_size(r.get("size", 0))}\n'
                     f'{custody}')
        self._archive_detail_meta.config(text=extra)
        ranks = {x.get('prune_rank') for x in recs}
        rank_txt = ranks.pop() if len(ranks) == 1 else 'Mixed recommendations'
        if archive_custody and rank_txt == archive_custody.PRUNE_SAFE:
            hint = 'Safe to delete after review — original files stay untouched.'
        elif archive_custody and rank_txt == archive_custody.PRUNE_REVIEW:
            hint = 'Review carefully before deleting from archive.'
        elif archive_custody and rank_txt == archive_custody.PRUNE_KEEP:
            hint = 'Keep in custody — recent or protected item.'
        else:
            hint = 'Use the action panel or right-click menu.'
        self._archive_detail_rank.config(text=f'Recommendation: {rank_txt}\n{hint}')
        self._update_context_panel()

    def _archive_clear_selection(self):
        try:
            self.archive_tree.selection_set(())
        except Exception:
            pass
        self._on_archive_select()

    def _archive_select_all_safe(self):
        if archive_custody is None:
            return
        safe_iids = [
            str(i) for i, rec in enumerate(self._archive_records)
            if rec.get('prune_rank') == archive_custody.PRUNE_SAFE
        ]
        if not safe_iids:
            self.archive_status_lbl.config(text='No safe-to-delete items in this view.')
            self._archive_clear_selection()
            return
        self._chunked_tree_select(
            self.archive_tree,
            safe_iids,
            status_lbl=self.archive_status_lbl,
            on_complete=self._on_archive_select,
            token_key='archive_sel',
        )

    def _archive_select_visible(self):
        iids = [str(i) for i in range(len(self._archive_records))]
        if not iids:
            self._archive_clear_selection()
            return
        self._chunked_tree_select(
            self.archive_tree,
            iids,
            status_lbl=self.archive_status_lbl,
            on_complete=self._on_archive_select,
            token_key='archive_sel',
        )

    def confirm_delete_all_safe(self):
        if archive_custody is None:
            return
        recs = [r for r in getattr(self, '_archive_records_all', [])
                if r.get('prune_rank') == archive_custody.PRUNE_SAFE and r.get('restorable')]
        if not recs:
            messagebox.showinfo('Delete from Archive', 'No items marked Safe to delete right now.')
            return
        self._show_delete_archive_confirm(
            recs,
            title='Delete All Safe',
            on_confirm=lambda: self._run_archive_delete(recs, context='archive', skip_confirm=True),
        )

    def confirm_delete_older_than(self):
        if archive_custody is None:
            return
        dlg = CleanroomModal(
            self, 'Delete Older Than', width=440, height=280, colors=self._dialog_colors(),
        )
        dlg.heading('Delete older archive copies')
        dlg.message(
            'Permanently delete archive copies older than the selected age.\n'
            'Original live files are never touched.',
            wrap=380,
        )
        spin_row = ctk.CTkFrame(dlg.body, fg_color=dlg.colors['card'])
        spin_row.pack(anchor='w', pady=(8, 0))
        ctk_theme.label(spin_row, 'Older than (days):', text_color=dlg.colors['text']).pack(side='left')
        days_var = tk.IntVar(value=90)
        spin = ttk.Spinbox(spin_row, from_=1, to=3650, textvariable=days_var, width=8)
        spin.pack(side='left', padx=(8, 0))
        preview_lbl = ctk_theme.label(
            dlg.body, '', text_color=dlg.colors['muted'], font_size=10, wraplength=380, justify='left',
        )
        preview_lbl.pack(anchor='w', pady=(10, 0))

        def refresh_preview(*_):
            recs = archive_custody.filter_older_than_days(
                getattr(self, '_archive_records_all', []) or [], days_var.get())
            freed = self._format_size(sum(int(r.get('size') or 0) for r in recs))
            preview_lbl.configure(text=f'Preview: {len(recs)} item(s) · {freed}')

        days_var.trace_add('write', refresh_preview)
        refresh_preview()

        def go():
            recs = archive_custody.filter_older_than_days(
                getattr(self, '_archive_records_all', []) or [], days_var.get())
            dlg.close()
            if not recs:
                self._show_info_modal('Delete from Archive', 'No matching archive items for that age.')
                return
            self._run_archive_delete(recs, context='archive')

        dlg.add_button('Cancel', dlg.close)
        dlg.add_button('Delete Matching Items', go, primary=True)

    def _selected_archive_records(self):
        sel = self.archive_tree.selection()
        out = []
        for iid in sel:
            try:
                idx = int(iid)
                if 0 <= idx < len(self._archive_records):
                    out.append(self._archive_records[idx])
            except ValueError:
                pass
        return out

    def _archive_restore_selected(self):
        recs = self._selected_archive_records()
        if not recs:
            messagebox.showinfo('Restore', 'Select archived item(s) to restore.')
            return
        if restore_module is None:
            messagebox.showerror('Restore', 'Restore module unavailable.')
            return
        lines = [f'{r["dest"]}\n  → {r["src"]}' for r in recs[:12]]
        if len(recs) > 12:
            lines.append(f'… and {len(recs) - 12} more')
        if not messagebox.askyesno(
                'Restore Selected',
                'Restore selected archived copies to their original paths?\n\n' + '\n'.join(lines)):
            return

        def work():
            ok = fail = 0
            msgs = []
            for r in recs:
                success, msg = self._smart_restore(r['src'], r['dest'], apply=True)
                if success:
                    ok += 1
                else:
                    fail += 1
                    msgs.append(msg)
            return ok, fail, msgs

        def done(result, err):
            if err is not None:
                messagebox.showerror('Restore', str(err))
                return
            ok, fail, msgs = result
            summary = f'Restored {ok} item(s).'
            if fail:
                summary += f' {fail} failed/skipped.'
            messagebox.showinfo('Restore', summary + ('\n\n' + '\n'.join(msgs[:5]) if msgs else ''))
            self.refresh_restore()
            self.refresh_activity()

        self._run_bg(work, done)

    def _archive_open_original(self):
        recs = self._selected_archive_records()
        if not recs:
            messagebox.showinfo('Archive Browser', 'Select a row first.')
            return
        src = Path(recs[0]['src'])
        folder = src.parent if not str(recs[0]['src']).startswith('REGISTRY::') else None
        if folder and folder.is_dir():
            os.startfile(str(folder))
        else:
            messagebox.showinfo('Archive Browser', f'Original location not available:\n{recs[0]["src"]}')

    def _archive_open_archive(self):
        recs = self._selected_archive_records()
        if not recs:
            messagebox.showinfo('Archive Browser', 'Select a row first.')
            return
        dest = Path(recs[0]['dest'])
        if dest.is_file():
            os.startfile(str(dest.parent))
        elif dest.is_dir():
            os.startfile(str(dest))
        else:
            messagebox.showinfo('Archive Browser', f'Archive path not found:\n{recs[0]["dest"]}')

    def _archive_open_receipt(self):
        recs = self._selected_archive_records()
        if not recs:
            messagebox.showinfo('Archive Browser', 'Select a row first.')
            return
        rp = recs[0].get('receipt_path')
        if not rp or not Path(rp).is_file():
            messagebox.showinfo('Archive Browser', 'No linked receipt file for this entry.')
            return
        self._view_receipt_file(rp)

    def _archive_copy_path(self):
        recs = self._selected_archive_records()
        if not recs:
            return
        text = recs[0].get('dest') or recs[0].get('src') or ''
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Path copied to clipboard.')
        except tk.TclError:
            messagebox.showinfo('Copy Path', text)

    def _bind_selectable_table(self, tree, *, on_select, on_double=None, on_right=None, on_enter=None):
        """Wire standard table selection: click, keyboard, double-click, right-click."""
        tree.bind('<<TreeviewSelect>>', lambda e: on_select())
        if on_double:
            tree.bind('<Double-Button-1>', on_double)
        if on_right:
            tree.bind('<Button-3>', on_right)
        if on_enter:
            tree.bind('<Return>', on_enter)
        for key in ('<Up>', '<Down>', '<Prior>', '<Next>'):
            tree.bind(key, lambda e: self.after_idle(on_select))

        def _click(_event):
            sel = tree.selection()
            if sel:
                try:
                    tree.focus(sel[0])
                except Exception:
                    pass
            self.after_idle(on_select)

        tree.bind('<Button-1>', _click, add='+')

    def _set_btn_state(self, btn, enabled: bool, tip: str = ''):
        if btn is None:
            return
        try:
            btn.config(state='normal' if enabled else 'disabled')
        except Exception:
            pass
        if tip:
            self._add_tooltip(btn, tip)

    def _selected_activity_entry(self):
        sel = self.activity_tree.selection() if hasattr(self, 'activity_tree') else ()
        if not sel:
            return None
        try:
            idx = int(sel[0])
            if 0 <= idx < len(self._activity_feed):
                return self._activity_feed[idx]
        except (ValueError, TypeError):
            pass
        return None

    def _find_receipt_for_paths(self, src, dest):
        for rec in getattr(self, '_archive_records_all', []) or []:
            if rec.get('src') == src and rec.get('dest') == dest:
                rp = rec.get('receipt_path')
                if rp and Path(rp).is_file():
                    return Path(rp)
        return None

    def _activity_proof_lines(self, entry):
        if not entry:
            return [], ''
        when = (entry.get('when') or '')[:19].replace('T', ' ')
        kind = entry.get('kind') or 'file'
        present = bool(entry.get('present'))
        custody = 'Verified on disk' if present else 'Missing from custody'
        lines = [
            'ACTIVITY PROOF',
            f'When: {when}',
            f'Type: {kind}',
            f'Status: {custody}',
            f'Reason: {entry.get("reason") or "—"}',
            f'Size: {self._format_size(entry.get("size", 0))}',
        ]
        src = entry.get('src') or '—'
        dest = entry.get('dest') or '—'
        if len(src) > 42:
            src = src[:39] + '…'
        if len(dest) > 42:
            dest = dest[:39] + '…'
        lines.append(f'From: {src}')
        lines.append(f'Custody: {dest}')
        stamp = 'VERIFIED ✓' if present else 'MISSING ✗'
        return lines[:8], stamp

    def _on_activity_select(self):
        entry = self._selected_activity_entry()
        if not entry:
            feed_n = len(getattr(self, '_activity_feed', []) or [])
            self._act_detail_type.config(text='Type: —')
            self._act_detail_when.config(text='When: —')
            self._act_detail_custody.config(text='Custody: —')
            self._act_detail_src.config(text='Source: —')
            self._act_detail_dest.config(text='Archive path: —')
            if feed_n:
                self._act_detail_hint.config(
                    text=(f'No row selected. {feed_n:,} action(s) logged — '
                          'click a row to view proof details and available actions.'))
            else:
                self._act_detail_hint.config(
                    text='No actions logged yet. Run a cleanup to populate the proof ledger.')
            for btn in (self._act_btn_receipt, self._act_btn_archive, self._act_btn_copy,
                        self._act_btn_proof, self._act_btn_restore):
                self._set_btn_state(btn, False)
            self._set_btn_state(self._act_btn_verify, feed_n > 0,
                                'Audit all archived artifacts on disk.' if feed_n else
                                'No custody records to verify yet.')
            return

        when = (entry.get('when') or '')[:19].replace('T', ' ')
        kind = entry.get('kind') or 'file'
        present = bool(entry.get('present'))
        self._act_detail_type.config(text=f'Type: {kind}')
        self._act_detail_when.config(text=f'When: {when}')
        self._act_detail_custody.config(
            text=f'Custody: {"Verified on disk ✓" if present else "Missing from archive ✗"}')
        self._act_detail_src.config(text=f'Source:\n{entry.get("src") or "—"}')
        self._act_detail_dest.config(text=f'Archive path:\n{entry.get("dest") or "—"}')
        if entry.get('kind') == 'prune':
            self._act_detail_hint.config(text='Historical proof only — this archive copy was pruned.')
        elif present:
            self._act_detail_hint.config(text='Artifact verified in custody. Restore or open receipt below.')
        else:
            self._act_detail_hint.config(text='Artifact missing — review custody or restore from backup.')

        rp = self._find_receipt_for_paths(entry.get('src'), entry.get('dest'))
        self._set_btn_state(self._act_btn_receipt, bool(rp),
                            'Open linked Cleanroom Receipt.' if rp else 'No receipt file linked to this row.')
        self._set_btn_state(self._act_btn_archive, bool(entry.get('dest')),
                            'Open the archive folder in Explorer.')
        self._set_btn_state(self._act_btn_copy, bool(entry.get('dest') or entry.get('src')),
                            'Copy archive path to clipboard.')
        self._set_btn_state(self._act_btn_proof, True, 'Copy proof summary text to clipboard.')
        self._set_btn_state(self._act_btn_verify, True, 'Run a full custody audit.')
        can_restore = present and entry.get('kind') not in ('prune', 'restore')
        self._set_btn_state(self._act_btn_restore, can_restore,
                            'Restore this archived copy to its original path.' if can_restore
                            else 'Restore unavailable for this record.')
        self._update_context_panel()

    def _on_activity_double_click(self, _event=None):
        entry = self._selected_activity_entry()
        if not entry:
            return
        rp = self._find_receipt_for_paths(entry.get('src'), entry.get('dest'))
        if rp:
            self._view_receipt_file(rp, action_key='cleaner_archive')
        elif entry.get('present') and entry.get('dest'):
            self._activity_open_archive()
        else:
            self._activity_copy_proof()

    def _ensure_activity_context_menu(self):
        if self._activity_context_menu is not None:
            return
        menu = self._tree_context_menu(self.activity_tree)
        menu.add_command(label='Open Receipt', command=self._activity_open_receipt)
        menu.add_command(label='Open Archive Folder', command=self._activity_open_archive)
        menu.add_command(label='Copy archive path', command=self._activity_copy_path)
        menu.add_command(label='Copy proof details', command=self._activity_copy_proof)
        menu.add_separator()
        menu.add_command(label='Restore', command=self._activity_restore_selected)
        menu.add_command(label='Verify Custody', command=self.verify_custody)
        menu.add_separator()
        menu.add_command(label='Open Archive Tab', command=self.open_archive_browser_tab)
        menu.add_command(label='Refresh', command=self.refresh_activity)
        self._activity_context_menu = menu

    def _on_activity_right_click(self, event):
        self._tree_right_click_select(self.activity_tree, event)
        self._on_activity_select()
        entry = self._selected_activity_entry()
        rp = self._find_receipt_for_paths(
            entry.get('src') if entry else None, entry.get('dest') if entry else None)
        has = entry is not None
        can_restore = (
            has and bool(entry.get('present'))
            and entry.get('kind') not in ('prune', 'restore')
        )
        has_path = has and bool(entry.get('dest') or entry.get('src'))
        has_arch = has and bool(entry.get('dest'))
        has_src = has and bool(entry.get('src'))
        self._show_row_popover(
            event.x_root, event.y_root,
            [
                ('Open receipt', self._activity_open_receipt, has and bool(rp)),
                ('Open archive', self._activity_open_archive, has_arch),
                ('Copy proof', self._activity_copy_proof, has),
                ('Copy event details', self._activity_copy_proof, has),
                ('Verify custody', self.verify_custody, True),
                ('Restore', self._activity_restore_selected, can_restore),
                ('Copy source path', self._activity_copy_source_path, has_src),
                ('Copy archive path', self._activity_copy_archive_path, has_arch),
            ],
            title='Proof ledger',
        )
        return 'break'

    def _activity_copy_source_path(self):
        entry = self._selected_activity_entry()
        if not entry or not entry.get('src'):
            return
        text = entry['src']
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Source path copied.')
        except tk.TclError:
            messagebox.showinfo('Copy Path', text)

    def _activity_copy_archive_path(self):
        entry = self._selected_activity_entry()
        if not entry or not entry.get('dest'):
            return
        text = entry['dest']
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Archive path copied.')
        except tk.TclError:
            messagebox.showinfo('Copy Path', text)

    def _activity_open_receipt(self):
        entry = self._selected_activity_entry()
        if not entry:
            return
        rp = self._find_receipt_for_paths(entry.get('src'), entry.get('dest'))
        if rp:
            self._view_receipt_file(rp, action_key='cleaner_archive')
        else:
            messagebox.showinfo('Activity Ledger', 'No linked receipt file for this row.')

    def _activity_open_archive(self):
        entry = self._selected_activity_entry()
        if not entry or not entry.get('dest'):
            return
        dest = Path(entry['dest'])
        folder = dest if dest.is_dir() else dest.parent
        if folder.exists():
            os.startfile(str(folder))
        else:
            messagebox.showinfo('Activity Ledger', f'Archive path not found:\n{dest}')

    def _activity_copy_path(self):
        entry = self._selected_activity_entry()
        if not entry:
            return
        text = entry.get('dest') or entry.get('src') or ''
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Path copied to clipboard.')
        except tk.TclError:
            messagebox.showinfo('Copy Path', text)

    def _activity_copy_proof(self):
        entry = self._selected_activity_entry()
        if not entry:
            return
        lines, stamp = self._activity_proof_lines(entry)
        text = '\n'.join(lines) + (f'\n\n{stamp}' if stamp else '')
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Proof details copied.')
        except tk.TclError:
            messagebox.showinfo('Proof Details', text)

    def _activity_restore_selected(self):
        entry = self._selected_activity_entry()
        if not entry or not entry.get('present'):
            messagebox.showinfo('Restore', 'Select a restorable archive row first.')
            return
        if entry.get('kind') in ('prune', 'restore'):
            messagebox.showinfo('Restore', 'This historical record cannot be restored from here.')
            return
        success, msg = self._smart_restore(entry['src'], entry['dest'], apply=True)
        if success:
            self._set_status('Restore complete.')
            self.refresh_activity()
            self.refresh_restore()
        else:
            messagebox.showerror('Restore', msg or 'Restore failed.')

    def _selected_recommendation(self):
        idx = getattr(self, '_selected_rec_idx', None)
        if idx is None:
            return None
        recs = getattr(self, '_dashboard_recommendations', [])
        if 0 <= idx < len(recs):
            return recs[idx]
        return None

    def _recommendation_primary_action(self):
        rec = self._selected_recommendation()
        if not rec:
            messagebox.showinfo('Recommendations', 'Select a recommendation row first.')
            return
        title = (rec.get('title') or '').lower()
        if 'archive' in title and 'candidate' in title:
            self._navigate_to_tab(3)
        elif 'no cleanup' in title or 're-scan' in (rec.get('detail') or '').lower():
            self.refresh_cleanup()
        elif 'registry' in title or 'startup' in title:
            self._navigate_to_tab(2)
        elif 'schedule' in title:
            self.schedule_optimization()
        elif 'restore history' in title:
            self._navigate_to_tab(5)
        else:
            self._recommendation_copy_details()

    def _recommendation_copy_details(self):
        rec = self._selected_recommendation()
        if not rec:
            return
        text = f"{rec.get('title', '')}\n\n{rec.get('detail', '')}\n\nPriority: {rec.get('severity', 'info')}"
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Recommendation copied.')
        except tk.TclError:
            messagebox.showinfo('Recommendation', text)

    def _on_recommendation_select(self):
        rec = self._selected_recommendation()
        if not rec:
            if hasattr(self, '_proof_summary'):
                self._proof_summary.show_idle()
            return
        if hasattr(self, '_proof_summary'):
            self._proof_summary.show_recommendation(rec)
            self._proof_summary.set_action_handlers()

    def _recommendation_action_label(self, rec):
        title = (rec.get('title') or '').lower()
        if 'archive' in title and 'candidate' in title:
            return 'Go to Cleaner tab'
        if 'no cleanup' in title:
            return 'Scan configured folders'
        if 'registry' in title or 'startup' in title:
            return 'Review Startup tab'
        if 'schedule' in title:
            return 'Schedule cleanup'
        if 'restore history' in title:
            return 'Open Restore tab'
        if 'large file' in title:
            return 'Go to Cleaner tab'
        return 'Copy details (informational)'

    def _on_recommendation_double_click(self, _event=None):
        self._recommendation_primary_action()

    def _ensure_rec_context_menu(self):
        if self._rec_context_menu is not None:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label='Take action', command=self._recommendation_primary_action)
        menu.add_command(label='Copy details', command=self._recommendation_copy_details)
        menu.add_separator()
        menu.add_command(label='Scan now', command=self.refresh_cleanup)
        menu.add_command(label='Open Cleaner', command=lambda: self._navigate_to_tab(3))
        menu.add_command(label='Open Startup', command=lambda: self._navigate_to_tab(2))
        self._rec_context_menu = menu

    def _on_recommendation_right_click(self, event):
        idx = getattr(self, '_selected_rec_idx', None)
        if idx is not None:
            self._on_recommendation_card_right(event, idx)
        return 'break'

    def _on_archive_double_click(self, _event=None):
        recs = self._selected_archive_records()
        if not recs:
            return
        if recs[0].get('receipt_path') and Path(recs[0]['receipt_path']).is_file():
            self._archive_open_receipt()
        elif recs[0].get('restorable'):
            self._archive_open_archive()
        else:
            self._archive_copy_path()

    def _tree_context_menu(self, parent):
        return tk.Menu(
            parent, tearoff=0,
            bg=CARD_BG, fg=TEXT,
            activebackground=ACCENT_SOFT, activeforeground=TEXT,
            disabledforeground=MUTED, bd=1, relief='solid',
            font=('Segoe UI', 10),
        )

    def _tree_right_click_select(self, tree, event):
        iid = tree.identify_row(event.y)
        if iid:
            if iid not in tree.selection():
                tree.selection_set(iid)
        return iid

    def _ensure_archive_context_menu(self):
        if self._archive_context_menu is not None:
            return
        menu = self._tree_context_menu(self.archive_tree)
        menu.add_command(label='Restore Selected', command=self._archive_restore_selected)
        menu.add_command(label='Delete from Archive…', command=self.confirm_prune_selected)
        menu.add_separator()
        menu.add_command(label='Open Archive Location', command=self._archive_open_archive)
        menu.add_command(label='Open Original Location', command=self._archive_open_original)
        menu.add_command(label='Open Receipt', command=self._archive_open_receipt)
        menu.add_separator()
        menu.add_command(label='Copy archive path', command=self._archive_copy_path)
        menu.add_command(label='Copy original path', command=self._archive_copy_original_path)
        menu.add_separator()
        menu.add_command(label='Select all safe to delete', command=self._archive_select_all_safe)
        menu.add_command(label='Select visible', command=self._archive_select_visible)
        menu.add_command(label='Clear selection', command=self._archive_clear_selection)
        menu.add_command(label='Delete all safe…', command=self.confirm_delete_all_safe)
        menu.add_command(label='Delete older than…', command=self.confirm_delete_older_than)
        menu.add_separator()
        menu.add_command(label='Refresh', command=self.refresh_archive_browser)
        self._archive_context_menu = menu

    def _on_archive_right_click(self, event):
        self._tree_right_click_select(self.archive_tree, event)
        self._on_archive_select()
        recs = self._selected_archive_records()
        has_sel = bool(recs)
        rec = recs[0] if recs else {}
        has_orig = bool(rec.get('src') and Path(rec.get('src')).exists())
        has_arch = bool(rec.get('dest') and Path(rec.get('dest')).exists())
        has_receipt = bool(rec.get('receipt_path') and Path(rec.get('receipt_path')).is_file())
        loaded = getattr(self, '_archive_loaded', False) and not getattr(self, '_archive_busy', False)
        safe_rank = archive_custody.PRUNE_SAFE if archive_custody else 'Safe to delete'
        safe_delete = loaded and has_sel and rec.get('prune_rank') == safe_rank
        self._show_row_popover(
            event.x_root, event.y_root,
            [
                ('Restore selected', self._archive_restore_selected, has_sel and loaded),
                ('Open archived copy location', self._archive_open_archive, has_sel and has_arch),
                ('Open original path', self._archive_open_original, has_sel and has_orig),
                ('Open receipt', self._archive_open_receipt, has_sel and has_receipt),
                ('Verify custody', self.verify_custody, loaded),
                ('Copy archive path', self._archive_copy_path, has_sel),
                ('Copy original path', self._archive_copy_original_path, has_sel),
                ('Copy proof', self._archive_copy_proof, has_sel),
                ('Delete archived copy only…', self.confirm_prune_selected, safe_delete),
                ('Refresh', self.refresh_archive_browser, True),
            ],
            title='Archive custody',
        )
        return 'break'

    def _archive_copy_proof(self):
        recs = self._selected_archive_records()
        if not recs:
            return
        rec = recs[0]
        lines = [
            f"Original: {rec.get('src') or '—'}",
            f"Archive: {rec.get('dest') or '—'}",
            f"When: {rec.get('when') or '—'}",
            f"Reason: {rec.get('reason') or '—'}",
            f"Size: {self._format_size(rec.get('size', 0))}",
            f"Receipt: {rec.get('receipt_path') or '—'}",
        ]
        text = '\n'.join(lines)
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Archive proof copied.')
        except tk.TclError:
            messagebox.showinfo('Archive proof', text)

    def _archive_copy_original_path(self):
        recs = self._selected_archive_records()
        if not recs:
            return
        text = recs[0].get('src') or ''
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Original path copied.')
        except tk.TclError:
            messagebox.showinfo('Copy Path', text)

    def _ensure_restore_context_menu(self):
        if self._restore_context_menu is not None:
            return
        menu = self._tree_context_menu(self.restore_tree)
        menu.add_command(label='Restore Selected', command=self.restore_selected_entry)
        menu.add_command(label='Restore Now', command=lambda: self.restore_selected_entry(apply=True))
        menu.add_command(label='Delete from Archive…', command=self.confirm_delete_restore_selected)
        menu.add_separator()
        menu.add_command(label='Open Archived File', command=self._open_archived_selected)
        menu.add_command(label='Open Archive Tab', command=self.open_archive_browser_tab)
        menu.add_separator()
        menu.add_command(label='Copy original path', command=self._restore_copy_original)
        menu.add_command(label='Copy archive path', command=self._restore_copy_archive)
        menu.add_separator()
        menu.add_command(label='Reload log', command=self.refresh_restore)
        self._restore_context_menu = menu

    def _on_restore_right_click(self, event):
        self._tree_right_click_select(self.restore_tree, event)
        has_sel = self._selected_restore_index() is not None
        self._show_row_popover(
            event.x_root, event.y_root,
            [
                ('Restore Selected', self.restore_selected_entry, has_sel),
                ('Restore Now', lambda: self.restore_selected_entry(apply=True), has_sel),
                ('Delete from Archive…', self.confirm_delete_restore_selected, has_sel),
                ('Open Archived File', self._open_archived_selected, has_sel),
                ('Open Archive Tab', self.open_archive_browser_tab, True),
                ('Copy original path', self._restore_copy_original, has_sel),
                ('Copy archive path', self._restore_copy_archive, has_sel),
                ('Reload log', self.refresh_restore, True),
            ],
            title='Restore',
        )
        return 'break'

    def _restore_copy_original(self):
        idx = self._selected_restore_index()
        if idx is None:
            return
        text = self.restore_entries[idx][0] or ''
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Original path copied.')
        except tk.TclError:
            messagebox.showinfo('Copy Path', text)

    def _restore_copy_archive(self):
        idx = self._selected_restore_index()
        if idx is None:
            return
        text = self.restore_entries[idx][1] or ''
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Archive path copied.')
        except tk.TclError:
            messagebox.showinfo('Copy Path', text)

    def _shell_exe_path(self):
        return sys.executable if getattr(sys, 'frozen', False) else str(Path(__file__).resolve())

    def open_shell_context_menu_tool(self):
        """Build/install Windows Explorer right-click menus for Cleanroom."""
        if shell_menu_module is None:
            messagebox.showerror('Context Menus', 'Shell menu module unavailable.')
            return
        dlg = CleanroomModal(
            self, 'Explorer Context Menu Editor',
            width=640, height=580, colors=self._dialog_colors(), resizable=True,
        )
        dlg.heading('Explorer Context Menu Editor')
        dlg.subheading(
            'Install Cleanroom actions in File Explorer (per-user, HKCU). '
            'Use %1 in custom commands for the selected file or folder path.',
        )
        frm = ttk.Frame(dlg.body, style='Card.TFrame')
        frm.pack(fill='both', expand=True, pady=(8, 0))

        cfg = shell_menu_module.load_config()
        preset_vars = {}
        presets_box = ctk.CTkFrame(frm, fg_color=HEAD_BG, corner_radius=8)
        presets_box.pack(fill='x', pady=(0, 8))
        ctk_theme.label(
            presets_box, 'Built-in menus', text_color=ACCENT,
            font_size=10, weight='bold',
        ).pack(anchor='w', padx=10, pady=(8, 4))
        preset_inner = ttk.Frame(presets_box, style='Card.TFrame')
        preset_inner.pack(fill='x', padx=8, pady=(0, 8))
        for preset in shell_menu_module.PRESETS:
            var = tk.BooleanVar(value=bool(cfg.get('presets', {}).get(preset['id'], preset['enabled_default'])))
            preset_vars[preset['id']] = var
            target_label = shell_menu_module.TARGETS.get(preset['target'], ('', ''))[0]
            ttk.Checkbutton(
                preset_inner,
                text=f'{preset["label"]}  ({target_label})',
                variable=var,
            ).pack(anchor='w', pady=3)

        custom_box = ctk.CTkFrame(frm, fg_color=HEAD_BG, corner_radius=8)
        custom_box.pack(fill='both', expand=True, pady=(0, 8))
        ctk_theme.label(
            custom_box, 'Custom menus', text_color=ACCENT,
            font_size=10, weight='bold',
        ).pack(anchor='w', padx=10, pady=(8, 4))
        custom_list = tk.Listbox(
            custom_box, height=5, font=('Segoe UI', 10),
            bg=PREVIEW_BG, fg=TEXT, selectbackground=ACCENT,
            selectforeground=ON_ACCENT, relief='flat', highlightthickness=0,
        )
        custom_list.pack(fill='both', expand=True, padx=10, pady=(0, 4))

        def refresh_custom_list():
            custom_list.delete(0, 'end')
            for item in cfg.get('custom') or []:
                target_label = shell_menu_module.TARGETS.get(item.get('target', ''), ('?', ''))[0]
                custom_list.insert('end', f'{item.get("label", "?")}  [{target_label}]')

        refresh_custom_list()

        custom_btns = ttk.Frame(custom_box, style='Card.TFrame')
        custom_btns.pack(fill='x', padx=10, pady=(0, 8))

        def add_custom():
            sub = CleanroomModal(
                dlg.win, 'Add custom menu',
                width=480, height=360, colors=self._dialog_colors(),
            )
            sub.heading('Add custom menu')
            body = ttk.Frame(sub.body, style='Card.TFrame')
            body.pack(fill='both', expand=True)
            ttk.Label(body, text='Menu label:').grid(row=0, column=0, sticky='w', pady=6)
            label_var = tk.StringVar(value='Cleanroom action')
            ttk.Entry(body, textvariable=label_var, width=36).grid(row=0, column=1, sticky='we', pady=6)
            ttk.Label(body, text='Right-click on:').grid(row=1, column=0, sticky='w', pady=6)
            target_keys = list(shell_menu_module.TARGETS.keys())
            target_labels = [shell_menu_module.TARGETS[k][0] for k in target_keys]
            target_var = tk.StringVar(value=target_labels[0])
            ttk.Combobox(
                body, textvariable=target_var, state='readonly', width=34,
                values=target_labels,
            ).grid(row=1, column=1, sticky='we', pady=6)
            ttk.Label(body, text='Action:').grid(row=2, column=0, sticky='w', pady=6)
            action_keys = list(shell_menu_module.ACTION_TEMPLATES.keys())
            action_labels = [shell_menu_module.ACTION_TEMPLATES[k][0] for k in action_keys]
            action_var = tk.StringVar(value=action_labels[0])
            ttk.Combobox(
                body, textvariable=action_var, state='readonly', width=34,
                values=action_labels,
            ).grid(row=2, column=1, sticky='we', pady=6)
            ttk.Label(body, text='Custom args (optional):').grid(row=3, column=0, sticky='w', pady=6)
            args_var = tk.StringVar(value='')
            ttk.Entry(body, textvariable=args_var, width=36).grid(row=3, column=1, sticky='we', pady=6)
            ttk.Label(body, text='Example: --shell-archive "%1"', style='Info.TLabel').grid(
                row=4, column=1, sticky='w')
            body.columnconfigure(1, weight=1)

            def save_custom():
                label = label_var.get().strip()
                if not label:
                    return
                try:
                    target_key = target_keys[target_labels.index(target_var.get())]
                except ValueError:
                    target_key = target_keys[0]
                try:
                    action_key = action_keys[action_labels.index(action_var.get())]
                except ValueError:
                    action_key = action_keys[0]
                cfg.setdefault('custom', []).append({
                    'id': f'custom_{len(cfg.get("custom") or []) + 1}',
                    'label': label,
                    'target': target_key,
                    'action': action_key,
                    'custom_args': args_var.get().strip(),
                    'enabled': True,
                })
                refresh_custom_list()
                sub.close()

            sub.add_button('Cancel', sub.close)
            sub.add_button('Add', save_custom, primary=True)

        def remove_custom():
            sel = custom_list.curselection()
            if not sel:
                return
            idx = sel[0]
            customs = cfg.get('custom') or []
            if 0 <= idx < len(customs):
                customs.pop(idx)
                cfg['custom'] = customs
                refresh_custom_list()

        ttk.Button(custom_btns, text='Add custom menu…', command=add_custom).pack(side='left')
        ttk.Button(custom_btns, text='Remove selected', command=remove_custom).pack(side='left', padx=6)

        def _on_shell_custom_right(event):
            idx = custom_list.nearest(event.y)
            if idx >= 0:
                custom_list.selection_clear(0, 'end')
                custom_list.selection_set(idx)
            sel = custom_list.curselection()
            has = bool(sel)
            item = (cfg.get('custom') or [])[sel[0]] if has else {}

            def _copy_label():
                if item.get('label'):
                    self.clipboard_clear()
                    self.clipboard_append(item['label'])

            def _toggle_enabled():
                if has:
                    item['enabled'] = not bool(item.get('enabled', True))
                    refresh_custom_list()

            self._show_row_popover(
                event.x_root, event.y_root,
                [
                    ('Enable item', _toggle_enabled, has and not item.get('enabled', True)),
                    ('Disable item', _toggle_enabled, has and item.get('enabled', True)),
                    ('Copy menu label', _copy_label, has),
                    ('Remove selected', remove_custom, has),
                    ('Restore default', lambda: (cfg.update({'custom': []}), refresh_custom_list()), True),
                ],
                title='Explorer menu item',
            )
            return 'break'

        custom_list.bind('<Button-3>', _on_shell_custom_right)

        status = ttk.Label(frm, text='', style='Info.TLabel', wraplength=560)
        status.pack(anchor='w', pady=(0, 4))

        def save_cfg_from_ui():
            cfg['presets'] = {pid: bool(var.get()) for pid, var in preset_vars.items()}
            shell_menu_module.save_config(cfg)

        def do_install():
            save_cfg_from_ui()
            try:
                shell_menu_module.uninstall_all(cfg)
                installed = shell_menu_module.install_all(self._shell_exe_path(), cfg)
            except OSError as e:
                messagebox.showerror('Context Menus', str(e), parent=dlg.win)
                return
            status.config(text=f'Installed {len(installed)} Explorer menu(s). '
                                 'Right-click files or folders in File Explorer to use them.')
            if installed:
                preview = installed[0].get('command', '')
                status.config(text=status.cget('text') + f'\nExample: {preview}')

        def do_remove():
            save_cfg_from_ui()
            try:
                shell_menu_module.uninstall_all(cfg)
            except OSError as e:
                messagebox.showerror('Context Menus', str(e), parent=dlg.win)
                return
            status.config(text='Removed Cleanroom entries from Explorer context menus.')

        dlg.add_button('Close', dlg.close)
        dlg.add_button('Remove from Explorer', do_remove)
        dlg.add_button('Install to Explorer', do_install, primary=True)

    def _view_receipt_file(self, path, preview=False, *, module=None, action=None, action_key=None):
        if receipts_module is None:
            messagebox.showerror('Receipt', 'Receipts module unavailable.')
            return
        try:
            body = receipts_module.read_receipt(path)
        except Exception as e:
            messagebox.showerror('Receipt', f'Unable to read receipt:\n{e}')
            return
        try:
            from ui.receipt_identity import receipt_context
            ctx = receipt_context(
                body, module=module, action=action,
                preview=preview, action_key=action_key,
            )
        except Exception:
            ctx = {
                'title': 'Cleanroom Receipt',
                'preview': preview,
                'module': module or 'Cleanroom',
                'action': action or 'Receipt',
            }
        if show_receipt:
            avail = bool(receipt_bridge and receipt_bridge.is_available())
            show_receipt(
                self, body, receipt_path=path,
                preview=ctx.get('preview', preview),
                module=ctx.get('module'),
                action=ctx.get('action'),
                action_key=action_key,
                title=ctx.get('title'),
                bg=BG, card=CARD_BG, text_fg=TEXT, accent=ACCENT,
                muted=MUTED, border=BORDER, on_accent=ON_ACCENT,
                receipt_available=avail,
                open_in_receipt=(receipt_bridge.open_receipt
                                 if receipt_bridge else None),
            )
        else:
            self._show_text_dialog(ctx.get('title', 'Cleanroom Receipt'), body)

    def confirm_prune_selected(self):
        recs = self._selected_archive_records()
        self._run_archive_delete(recs, context='archive')

    def _open_archive_settings(self):
        self.tab_control.select(self.settings_tab)

    def _restore_row_to_archive_record(self, idx):
        src, dest, ts, entry = self.restore_entries[idx]
        if isinstance(entry, dict):
            return {
                'src': src,
                'dest': dest,
                'when': entry.get('when') or ts,
                'size': entry.get('size', 0),
                'reason': entry.get('reason', ''),
            }
        return {'src': src, 'dest': dest, 'when': ts, 'size': 0, 'reason': ''}

    def confirm_delete_restore_selected(self):
        idx = self._selected_restore_index()
        if idx is None:
            messagebox.showinfo('Delete from Archive', 'Select a restore entry first.')
            return
        src, dest, ts, entry = self.restore_entries[idx]
        if not dest:
            messagebox.showinfo('Delete from Archive', 'No archive path recorded for this entry.')
            return
        if not Path(dest).exists():
            messagebox.showinfo(
                'Delete from Archive',
                f'The archived copy is already gone or missing:\n{dest}')
            return
        rec = self._restore_row_to_archive_record(idx)
        self._run_archive_delete([rec], context='restore')

    def _run_archive_delete(self, recs, context='archive', *, skip_confirm=False):
        if archive_custody is None:
            messagebox.showerror('Delete from Archive', 'Archive custody module unavailable.')
            return
        if not recs:
            messagebox.showinfo('Delete from Archive', 'Select archived file(s) to delete.')
            return

        def proceed():
            log_path = self.restore_log_path

            def work():
                return archive_custody.apply_prune(
                    recs, log_path, receipt_dir=brand.user_data_dir() / 'receipts', dry_run=False)

            def done(result, err):
                if err is not None:
                    messagebox.showerror('Delete from Archive', str(err))
                    return
                n = len(result.get('pruned', []))
                skipped = result.get('skipped') or []
                freed = self._format_size(result.get('bytes_pruned', 0))
                rp = result.get('receipt_path')
                self._show_delete_result_dialog(
                    deleted=n, skipped=len(skipped), freed=freed, receipt_path=rp)
                self.refresh_activity()
                self.refresh_restore()
                if context == 'archive':
                    self.refresh_archive_browser()

            self._run_bg(work, done)

        if skip_confirm:
            proceed()
            return

        def show_confirm():
            preview = None
            try:
                preview = archive_custody.apply_prune(
                    recs, str(self.restore_log_path),
                    receipt_dir=brand.user_data_dir() / 'receipts', dry_run=True)
            except Exception:
                pass
            self._show_delete_archive_confirm(recs, on_confirm=proceed, preview=preview)

        show_confirm()

    def prune_archive_dialog(self):
        """Open Archive Browser filtered to Safe to delete recommendations."""
        if archive_custody and hasattr(self, '_archive_prune_filter'):
            self._archive_prune_filter.set(archive_custody.PRUNE_SAFE)
        self.open_archive_browser_tab()

    def export_audit(self):
        if audit_module is None or ledger_module is None or proof_module is None:
            messagebox.showerror('Export Audit', 'Audit modules unavailable.')
            return
        self.refresh_activity()
        entries = self._load_log_dicts()
        custody = proof_module.verify_entries(entries)
        summary = ledger_module.summarize_feed(self._activity_feed)
        trust = ledger_module.trust_score(custody['verified'], custody['total'])
        out_dir = brand.user_data_dir() / 'audits'
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f'audit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        try:
            audit_module.export_html_audit(
                self._activity_feed, custody, summary, trust, path, app_version=APP_VERSION)
            if not path.is_file():
                raise OSError(f'Proof Pack not written: {path}')

            def _open_proof_pack():
                os.startfile(str(path))
                messagebox.showinfo(
                    'Export Audit',
                    f'Proof audit saved and opened in your browser:\n{path}')

            self._play_receipt_animation(
                'CUSTODY VERIFIED',
                lines=PROOF_PACK_LINES,
                on_complete=_open_proof_pack,
            )
        except Exception as e:
            messagebox.showerror('Export Audit', f'Failed to write audit:\n{e}')

    def _show_proof_report(self, log, prf, receipt_path=None, days_bought=None, dup_count=0):
        """Visual proof screen — dark modal matching product chrome."""
        c = prf.get('custody') or {}
        ok = c.get('missing', 0) == 0 and c.get('total', 0) > 0
        head_txt = 'CUSTODY VERIFIED ✓' if ok else 'ARCHIVED WITH PROOF'

        moved = sum(int(e.get('size') or 0) for e in log)
        lines = [
            f'Items archived: {len(log)}',
            f'Space moved: {self._format_size(moved)} — to archive, not deleted',
        ]
        if proof_module:
            lines.extend([
                f'Free before: {proof_module._human(prf.get("before_free", 0))}',
                f'Free after: {proof_module._human(prf.get("after_free", 0))}',
                f'OS measured Δ: {proof_module._human(prf.get("measured_delta", 0))}',
            ])
        lines.append(
            f'Custody check: {c.get("verified", 0)}/{c.get("total", 0)} verified on disk right now')
        if days_bought and days_bought >= 1:
            lines.append(f'Disk life bought: ~{days_bought:.0f} days (Disk Foresight trend)')
        elif dup_count:
            lines.append(f'Duplicates separated: {dup_count}')
        if prf.get('measured_delta', 0) < moved // 2:
            lines.append('')
            lines.append(
                'Files were moved to the archive on the same drive — free space barely '
                'changes until you prune. That is honest; other cleaners lie about this.')

        dlg = CleanroomModal(
            self, 'Cleanroom Proof Report', width=560, height=460,
            colors=self._dialog_colors(),
        )
        dlg.heading(head_txt, size=17)
        dlg.subheading(brand.APP_MOTTO)
        dlg.message('Measured by Windows — not estimated. Every item is in the archive.')
        dlg.scroll_text('\n'.join(lines), height=200)

        proof_text = '\n'.join(lines)

        def _copy_proof():
            try:
                self.clipboard_clear()
                self.clipboard_append(proof_text)
                self._set_status('Proof summary copied.')
            except tk.TclError:
                pass

        if receipt_path:
            dlg.add_button(
                'Open Receipt',
                lambda: self._view_receipt_file(receipt_path, action_key='cleaner_archive'),
                side='left',
            )
        dlg.add_button('Open Archive Folder', self.open_archive_folder, side='left')
        dlg.add_button('Copy Proof', _copy_proof, side='left')
        dlg.add_button(
            'View Ledger',
            lambda: (dlg.close(), self.tab_control.select(self.activity_tab), self.refresh_activity()),
            side='left',
        )
        dlg.add_button('Close', dlg.close, primary=True)
        dlg.win.bind('<Return>', lambda _e: dlg.close())
        self._last_proof_report = dlg.win

    def open_last_receipt(self):
        if receipts_module is None:
            messagebox.showerror('Receipt', 'Receipts module unavailable.')
            return
        path = receipts_module.latest_receipt()
        if path is None:
            self._show_info_modal(
                'Receipt',
                'No receipts yet — run a cleanup first.',
            )
            return
        self._view_receipt_file(path, action_key='latest')

    # ------------------------------------------------------------------
    # Verify Custody (prove the reversibility promise on demand)
    # ------------------------------------------------------------------
    def verify_custody(self):
        """Audit the cleanup log: every outstanding archived artifact must
        still exist on disk. This is the receipt for ALL of history."""
        if proof_module is None or restore_module is None:
            messagebox.showerror('Verify Custody', 'Proof/restore modules unavailable.')
            return
        entries = []
        if self.restore_log_path.exists():
            try:
                actions = restore_module.load_log(str(self.restore_log_path))
                # entries_from_log yields (src, dest, ts, entry); custody wants the dicts
                entries = [t[3] for t in restore_module.entries_from_log(actions)]
            except Exception as e:
                messagebox.showerror('Verify Custody', f'Unable to load cleanup log:\n{e}')
                return
        if not entries:
            self._show_info_modal(
                'Verify Custody',
                'Nothing to verify yet — the cleanup log is empty.',
            )
            return
        self._set_status(f'Verifying custody of {len(entries)} archived item(s)…')

        def done(result, err):
            self._set_status('Ready')
            if err is not None:
                messagebox.showerror('Verify Custody', f'Verification failed: {err}')
                return
            ok = result['missing'] == 0
            if ok:
                body = (f"{result['verified']}/{result['total']} archived item(s) are "
                        f"present on disk right now "
                        f"({self._format_size(result['bytes_in_custody'])} in custody).\n\n"
                        'Every file Cleanroom has archived is still where the log says it is.')
                ok_dlg = CleanroomModal(
                    self, 'Verify Custody', width=460, height=240, colors=self._dialog_colors(),
                )
                ok_dlg.heading('CUSTODY VERIFIED ✓')
                ok_dlg.message(body, wrap=420)
                ok_dlg.add_button('OK', ok_dlg.close, primary=True)
                self._set_status(
                    f'CUSTODY VERIFIED ✓ — {result["verified"]}/{result["total"]} present')
            else:
                self._show_custody_verify_summary(result)
            self.refresh_activity()

        self._run_bg(lambda: proof_module.verify_entries(entries), done)

    # ------------------------------------------------------------------
    # Registry Snapshot (safe, evidence-based; archive-first repairs)
    # ------------------------------------------------------------------
    def open_registry_health(self):
        if registry_health is None:
            messagebox.showerror('Registry Snapshot', 'Registry snapshot module unavailable.')
            return
        self._set_status('Scanning registry snapshot…')
        self.reg_health_btn.config(state='disabled')

        def done(result, err):
            self.reg_health_btn.config(state='normal')
            self._set_status('Ready')
            if err is not None:
                messagebox.showerror('Registry Snapshot', f'Scan failed: {err}')
                return
            if not result:
                self._show_info_modal(
                    'Registry Snapshot',
                    'No issues found — every startup ref, App Paths entry '
                    'and uninstaller this scan can verify points to a real file.',
                    height=240,
                )
                return
            self._show_registry_health_dialog(result)

        self._run_bg(registry_health.find_registry_issues, done)

    def _show_registry_health_dialog(self, issues):
        dlg = CleanroomModal(
            self, 'Registry Snapshot', width=720, height=420,
            resizable=True, colors=self._dialog_colors(),
        )
        dlg.heading(f'{len(issues)} issue(s) found')
        dlg.message(
            'Only entries that verifiably point to missing files are listed. '
            'Checked items are EXPORTED to .reg backups in the archive before '
            'removal — restorable from the Restore tab or Cleanroom Rewind. '
            'HKLM items need admin rights.',
            wrap=660,
        )

        scroll_host = ctk.CTkFrame(dlg.body, fg_color=dlg.colors['head'], corner_radius=8)
        scroll_host.pack(fill='both', expand=True, pady=(10, 0))
        canvas = tk.Canvas(scroll_host, bg=dlg.colors['head'], highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_host, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas, style='Card.TFrame')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side='left', fill='both', expand=True, padx=4, pady=4)
        vsb.pack(side='right', fill='y', pady=4)

        icons = {'startup-ref': '🚀', 'app-path': '🔗', 'uninstall-entry': '🧩'}
        check_vars = []
        for issue in issues:
            var = tk.BooleanVar(value=issue['type'] != 'uninstall-entry')
            row = ttk.Frame(inner, style='Card.TFrame')
            row.pack(fill='x', padx=8, pady=2)
            cb = ttk.Checkbutton(
                row, variable=var,
                text=f"{icons.get(issue['type'], '•')} {issue['display']}  —  {issue['detail']}")
            cb.pack(anchor='w')
            self._add_tooltip(cb, f"{issue['hive']}\\{issue['key']}"
                                  + (f" :: {issue['value_name']}" if issue['value_name'] else ''))
            check_vars.append((var, issue))

        def repair():
            chosen = [issue for var, issue in check_vars if var.get()]
            dlg.close()
            if not chosen:
                return
            archive_dir = self._archive_dir_from_config()
            self._set_status(f'Repairing {len(chosen)} registry issue(s)…')

            def work():
                return registry_health.archive_registry_issues(
                    chosen, archive_dir, str(self.restore_log_path))

            def done(result, err):
                self._set_status('Ready')
                if err is not None:
                    messagebox.showerror('Registry Snapshot', f'Repair failed: {err}')
                    return
                fixed = len(result or [])
                skipped = len(chosen) - fixed
                msg = f'Repaired {fixed} issue(s) — .reg backups are in the archive.'
                if skipped:
                    msg += (f'\n{skipped} item(s) could not be removed '
                            '(HKLM entries need admin rights).')
                self._show_info_modal('Registry Snapshot', msg, width=480, height=240)
                self.refresh_restore()
                self.refresh_uninstaller()

            self._run_bg(work, done)

        self._reg_health_repair = repair  # E2E hook
        dlg.win.bind('<Return>', lambda e: repair())
        dlg.add_button('Cancel', dlg.close)
        dlg.add_button('Repair (Archive First)', repair, primary=True)

    # ------------------------------------------------------------------
    # Cleanroom Rewind (roll back whole days of actions)
    # ------------------------------------------------------------------
    def open_time_machine(self):
        if timeline_module is None or restore_module is None:
            messagebox.showerror('Cleanroom Rewind', 'Timeline/restore modules unavailable.')
            return
        actions = []
        if self.restore_log_path.exists():
            try:
                actions = restore_module.load_log(str(self.restore_log_path))
            except Exception as e:
                messagebox.showerror('Cleanroom Rewind', f'Unable to load cleanup log:\n{e}')
                return
        buckets = timeline_module.build_timeline(actions)

        dlg = CleanroomModal(
            self, 'Cleanroom Rewind', width=760, height=440,
            resizable=True, colors=self._dialog_colors(),
        )
        dlg.heading('Cleanroom Rewind')
        dlg.message(
            'Every archive-first action grouped by day. Pick a day and roll the whole '
            'thing back — files return to their original locations.',
            wrap=720,
        )

        wrap = ttk.Frame(dlg.body, style='Card.TFrame')
        wrap.pack(fill='both', expand=True, pady=(10, 0))
        cols = ('date', 'count', 'size', 'restorable', 'reasons')
        tree = ttk.Treeview(wrap, columns=cols, show='headings', selectmode='browse')
        tree.heading('date', text='Day')
        tree.heading('count', text='Actions')
        tree.heading('size', text='Moved')
        tree.heading('restorable', text='Still in archive')
        tree.heading('reasons', text='What happened')
        tree.column('date', width=100, anchor='center')
        tree.column('count', width=70, anchor='e')
        tree.column('size', width=90, anchor='e')
        tree.column('restorable', width=110, anchor='e')
        tree.column('reasons', width=330, anchor='w')
        vsb = ttk.Scrollbar(wrap, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        tree.tag_configure('oddrow', background=CARD_BG)
        tree.tag_configure('evenrow', background=ROW_ALT)

        for i, b in enumerate(buckets):
            reasons_txt = ', '.join(f'{r} ×{n}' for r, n in b['reasons'].most_common(3))
            tree.insert('', 'end', iid=str(i),
                        values=(b['date'], b['count'], self._format_size(b['bytes']),
                                b['restorable'], reasons_txt),
                        tags=('evenrow' if i % 2 else 'oddrow',))
        if not buckets:
            tk.Label(tree, text='No history yet.\nDays appear here after cleanups.',
                     bg=CARD_BG, fg=MUTED, font=('Segoe UI', 10, 'italic'),
                     justify='center').place(relx=0.5, rely=0.4, anchor='center')

        status_lbl = ttk.Label(dlg.body, text='', style='Info.TLabel')
        status_lbl.pack(anchor='w', pady=(6, 0))

        def do_rollback():
            sel = tree.selection()
            if not sel:
                self._show_info_modal('Cleanroom Rewind', 'Select a day first.')
                return
            bucket = buckets[int(sel[0])]
            if bucket['restorable'] == 0:
                self._show_info_modal(
                    'Cleanroom Rewind', 'Nothing from that day is still in the archive.',
                )
                return
            if not messagebox.askyesno(
                    'Cleanroom Rewind',
                    f"Roll back {bucket['date']}?\n\n{bucket['restorable']} item(s) will be moved "
                    'from the archive back to their original locations.', parent=dlg.win):
                return
            rollback_btn.configure(state='disabled')
            status_lbl.config(text=f"Rolling back {bucket['date']}…")

            def work():
                return timeline_module.rollback_day(
                    bucket, lambda s, d: self._smart_restore(s, d, apply=True))

            def done(result, err):
                rollback_btn.configure(state='normal')
                if err is not None:
                    status_lbl.config(text='Rollback failed.')
                    messagebox.showerror('Cleanroom Rewind', f'Rollback failed: {err}', parent=dlg.win)
                    return
                restored, skipped, failed, msgs = result
                status_lbl.config(text=f'Restored {restored}, skipped {skipped}, failed {failed}.')
                summary = f'Restored {restored} item(s).'
                if skipped:
                    summary += f'\n{skipped} skipped (no longer in archive).'
                if failed:
                    summary += f'\n{failed} failed:\n' + '\n'.join(msgs[:5])
                self._show_info_modal('Cleanroom Rewind', summary, width=480, height=260)
                self.refresh_restore()

            self._run_bg(work, done)

        rollback_btn = dlg.add_button('Roll Back This Day', do_rollback, primary=True, side='left')
        dlg.add_button('Close', dlg.close, side='left')

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------
    def _smart_restore(self, src, dest, apply=False):
        """Route restores: registry exports re-import via reg, files move back."""
        if uninstaller and str(src).startswith(uninstaller.REG_PREFIX):
            if not apply:
                if Path(dest).exists():
                    return True, f'would import {dest} back into the registry'
                return False, f'missing registry export: {dest}'
            return uninstaller.restore_registry_export(dest)
        return restore_module.restore_one(src, dest, apply=apply)

    def _load_restore_log(self):
        if restore_module is None:
            messagebox.showerror('Restore error', 'Restore module is unavailable.')
            return None
        try:
            entries = restore_module.load_log(str(self.restore_log_path))
            return list(restore_module.entries_from_log(entries))
        except Exception as e:
            messagebox.showerror('Restore error', f'Unable to load restore log:\n{e}')
            return None

    def refresh_restore(self):
        if not self.restore_log_path.exists():
            self.restore_status_lbl.config(text=f'Log not found: {self.restore_log_path}')
            self.restore_tree.delete(*self.restore_tree.get_children())
            self.restore_entries = []
            self._clear_restore_detail()
            self._sync_restore_view(loading=False)
            return
        self._sync_restore_view(loading=True)
        self.restore_status_lbl.config(text='Loading restore log…')
        log_path = str(self.restore_log_path)
        filter_text = self.restore_filter_var.get().strip().lower()

        def work():
            entries = restore_module.load_log(log_path)
            return list(restore_module.entries_from_log(entries))

        def done(result, err):
            if err is not None:
                self.restore_status_lbl.config(text=f'Load failed: {err}')
                self._sync_restore_view(loading=False)
                messagebox.showerror('Restore error', f'Unable to load restore log:\n{err}')
                return
            entries = result
            if filter_text:
                entries = [e for e in entries
                           if filter_text in (e[0] or '').lower() or filter_text in (e[1] or '').lower()]
            self.restore_entries = entries
            self._update_restore_tree()
            self.refresh_dashboard()
            self.refresh_activity()
            self.restore_status_lbl.config(text=f'Loaded {len(entries):,} restore entries.')

        if restore_module is None:
            messagebox.showerror('Restore error', 'Restore module is unavailable.')
            return
        self._run_bg(work, done)

    def _update_restore_tree(self):
        entries = self.restore_entries

        def build_row(idx, item):
            src, dest, ts, _entry = item
            tag = 'evenrow' if idx % 2 else 'oddrow'
            return (str(idx), (src, dest, ts or ''), (tag,))

        def on_complete():
            self._sync_restore_view(loading=False)

        self._chunked_tree_populate(
            self.restore_tree,
            entries,
            build_row,
            empty_hint=self.restore_empty_hint,
            on_complete=on_complete,
            token_key='restore_tree',
        )
        if not entries:
            on_complete()

    def _selected_restore_index(self):
        sel = self.restore_tree.selection()
        if not sel:
            return None
        idx = self.restore_tree.index(sel[0])
        if 0 <= idx < len(self.restore_entries):
            return idx
        return None

    def _on_restore_select(self):
        idx = self._selected_restore_index()
        if idx is None:
            self._clear_restore_detail()
            return
        src, dest, ts, entry = self.restore_entries[idx]
        self.restore_detail_src.config(text=f'Original: {src}')
        self.restore_detail_dest.config(text=f'Archived: {dest}')
        self.restore_detail_time.config(text=f'Time: {ts or "—"}')
        exists = Path(dest).exists()
        self.restore_detail_exists.config(text=f'Archived exists: {"Yes" if exists else "No"}')
        try:
            size = Path(dest).stat().st_size if exists else 0
            self.restore_detail_size.config(text=f'Size: {self._format_size(size)}')
        except Exception:
            self.restore_detail_size.config(text='Size: —')
        self._update_file_preview(dest)

    IMAGE_EXTS = {'.png', '.gif', '.ppm', '.pgm'}
    # Pillow unlocks the formats Tk can't load natively
    PIL_IMAGE_EXTS = {'.jpg', '.jpeg', '.webp', '.bmp', '.ico', '.tif', '.tiff'}
    TEXT_EXTS = {'.txt', '.log', '.json', '.md', '.py', '.yaml', '.yml', '.csv',
                 '.ini', '.cfg', '.xml', '.html', '.htm', '.bat', '.ps1', '.js', '.css'}

    def _set_preview_message(self, message):
        self.preview_image_label.pack_forget()
        self._preview_photo = None
        self.preview_text.pack(fill='both', expand=True, padx=6, pady=6)
        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', message)
        self.preview_text.config(state='disabled')

    def _show_preview_photo(self, photo):
        self._preview_photo = photo  # keep a reference so Tk doesn't GC it
        self.preview_text.pack_forget()
        self.preview_image_label.config(image=photo, text='')
        self.preview_image_label.pack(fill='both', expand=True, padx=6, pady=6)

    def _update_file_preview(self, dest):
        path = Path(dest)
        if not path.exists():
            self._set_preview_message('Archived file not found — no preview available.')
            return
        ext = path.suffix.lower()
        max_w, max_h = 340, 240
        if PILImage and ext in (self.PIL_IMAGE_EXTS | self.IMAGE_EXTS):
            try:
                with PILImage.open(path) as img:
                    img = img.convert('RGBA')
                    img.thumbnail((max_w, max_h), PILImage.LANCZOS)
                    self._show_preview_photo(PILImageTk.PhotoImage(img, master=self))
                return
            except Exception:
                self._set_preview_message('Unable to render image preview.')
                return
        if ext in self.IMAGE_EXTS:
            try:
                photo = tk.PhotoImage(file=str(path))
                factor = max(1, (photo.width() + max_w - 1) // max_w,
                             (photo.height() + max_h - 1) // max_h)
                if factor > 1:
                    photo = photo.subsample(factor, factor)
                self._show_preview_photo(photo)
                return
            except Exception:
                self._set_preview_message('Unable to render image preview.')
                return
        if ext in self.TEXT_EXTS:
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    snippet = f.read(4096)
                more = '\n…' if path.stat().st_size > 4096 else ''
                self._set_preview_message(snippet + more)
                return
            except Exception:
                self._set_preview_message('Unable to read file for preview.')
                return
        self._set_preview_message(f'No preview available for "{ext or "this"}" files.\n\nUse "Open Archived" to view it externally.')

    def _clear_restore_detail(self):
        self.restore_detail_src.config(text='Original: —')
        self.restore_detail_dest.config(text='Archived: —')
        self.restore_detail_time.config(text='Time: —')
        self.restore_detail_exists.config(text='Archived exists: —')
        self.restore_detail_size.config(text='Size: —')
        self._set_preview_message('Select an entry to preview it.')

    def _open_archived_selected(self):
        idx = self._selected_restore_index()
        if idx is None:
            return
        src, dest, ts, entry = self.restore_entries[idx]
        try:
            if Path(dest).exists():
                os.startfile(str(dest))
            else:
                messagebox.showwarning('Open archived', 'Archived file not found.')
        except Exception as e:
            messagebox.showerror('Open archived', f'Unable to open archived file:\n{e}')

    def restore_selected_entry(self, apply=False):
        idx = self._selected_restore_index()
        if idx is None:
            messagebox.showinfo('Restore', 'No entry selected.')
            return
        src, dest, ts, entry = self.restore_entries[idx]
        if restore_module is None:
            messagebox.showerror('Restore', 'Restore module unavailable.')
            return
        # Dry-run first
        ok, msg = self._smart_restore(src, dest, apply=False)
        if apply:
            proceed = True
        else:
            txt = f'Preview result:\n{msg}\n\nProceed to perform the actual restore?'
            proceed = messagebox.askyesno('Preview restore', txt)
        if not proceed:
            return
        ok2, msg2 = self._smart_restore(src, dest, apply=True)
        if ok2:
            self._set_status('Restore succeeded.')
            messagebox.showinfo('Restore', f'Restore succeeded:\n{msg2}')
        else:
            self._set_status('Restore failed.')
            messagebox.showerror('Restore', f'Restore failed:\n{msg2}')
        self.refresh_restore()

    def restore_all_entries(self):
        if not self.restore_entries:
            messagebox.showinfo('Restore', 'No restore entries available.')
            return
        if restore_module is None:
            messagebox.showerror('Restore', 'Restore module unavailable.')
            return
        missing = 0
        for src, dest, ts, entry in self.restore_entries:
            ok, msg = self._smart_restore(src, dest, apply=False)
            if not ok:
                missing += 1
        txt = f'Preview: {len(self.restore_entries)} entries. {missing} issue(s) detected.\nProceed to restore all shown entries?'
        if not messagebox.askyesno('Preview restore all', txt):
            return
        success = 0
        failed = 0
        for src, dest, ts, entry in self.restore_entries:
            ok, msg = self._smart_restore(src, dest, apply=True)
            if ok:
                success += 1
            else:
                failed += 1
        self._set_status(f'Restore all complete: {success} succeeded, {failed} failed.')
        messagebox.showinfo('Restore all', f'Restore complete. Succeeded: {success}. Failed: {failed}.')
        self.refresh_restore()

    # ------------------------------------------------------------------
    # Dashboard / recommendations
    # ------------------------------------------------------------------
    def refresh_dashboard(self):
        folder_count = len(self.data.get('folders', []))
        registry_count = len(self.data.get('registry', []))
        startup_count = folder_count + registry_count
        cleanup_count = len(self.cleanup_items) if self._scan_session_done else self._cached_scan_count
        display_size = self.cleanup_total_size if self._scan_session_done else self._cached_scan_size
        reason_counts = {}
        for item in self.cleanup_items:
            reason = item.get('reason') or 'other'
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if rec_engine:
            recs = rec_engine.build_recommendations(
                folder_count=folder_count,
                registry_count=registry_count,
                cleanup_count=cleanup_count,
                cleanup_bytes=display_size,
                restore_count=len(self.restore_entries),
                reason_counts=reason_counts)
        else:
            recs = []

        review_count = cleanup_count
        if review_count == 0:
            tone, band_text = ACCENT, 'Nothing pending'
        elif review_count < 10:
            tone, band_text = SEVERITY_COLORS['low'], f'{review_count} to review'
        elif review_count < 30:
            tone, band_text = SEVERITY_COLORS['medium'], f'{review_count} to review'
        else:
            tone, band_text = SEVERITY_COLORS['high'], f'{review_count} to review'

        self._draw_review_gauge(review_count, tone)
        self.health_band_lbl.config(text=band_text, fg=tone)
        self.stat_startup_value.config(text=str(startup_count))
        self.stat_cleanup_value.config(text=str(cleanup_count))
        self.stat_size_value.config(text=self._format_size(display_size))

        self._populate_recommendation_cards(recs)
        self._dashboard_recommendations = list(recs)
        if hasattr(self, '_home_rec_pane'):
            sync_table_empty_view(
                has_rows=bool(recs),
                empty_panel=self._home_rec_empty_panel,
                pane=self._home_rec_pane,
            )
        if recs:
            self._select_recommendation_card(0)
        else:
            self._selected_rec_idx = None
        self._sync_home_proof_panel()

        self.refresh_foresight()
        self._refresh_header_proof_badges()
        self._update_dashboard_cta()
        self._update_recent_proof()

    refresh_optimizer = refresh_dashboard

    def _sync_home_proof_panel(self):
        """Keep Home proof summary live — never a dead panel when scan/receipt data exists."""
        if not hasattr(self, '_proof_summary'):
            return
        ps = self._proof_summary
        recs = getattr(self, '_dashboard_recommendations', []) or []
        if recs:
            if getattr(self, '_selected_rec_idx', None) is None:
                self._select_recommendation_card(0)
            return
        count = len(self.cleanup_items) if getattr(self, '_scan_session_done', False) else 0
        if not count:
            count = int(getattr(self, '_cached_scan_count', 0) or 0)
        if count > 0:
            checked = len(self.cleanup_selected)
            size = self._format_size(self.cleanup_total_size)
            ps.show_scan_results(count, size, checked)
            ps.set_action_handlers(
                open_cb=self.preview_cleanup_receipt,
                copy_cb=self._copy_scan_summary,
                view_cb=lambda: self._navigate_to_tab(3),
            )
            return
        if receipts_module:
            try:
                path = receipts_module.latest_receipt()
                if path:
                    ps.show_latest_receipt(Path(path).name)
                    ps.set_action_handlers(
                        open_cb=self.open_last_receipt,
                        copy_cb=self._copy_latest_receipt_summary,
                        view_cb=self.open_last_receipt,
                    )
                    return
            except Exception:
                pass
        ps.show_idle('Run Scan to review folders, or open Proof Ledger for custody history.')

    def _copy_scan_summary(self):
        n = len(self.cleanup_items)
        checked = len(self.cleanup_selected)
        size = self._format_size(self.cleanup_total_size)
        text = (
            'CLEANROOM — SCAN SUMMARY\n\n'
            f'Candidates: {n:,}\n'
            f'Checked for archive: {checked:,}\n'
            f'Reclaimable: {size}\n\n'
            'Open Cleaner to review paths and preview the receipt before archiving.'
        )
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Scan summary copied.')
        except tk.TclError:
            messagebox.showinfo('Scan Summary', text)

    def _copy_latest_receipt_summary(self):
        if not receipts_module:
            return
        try:
            path = receipts_module.latest_receipt()
        except Exception:
            path = None
        if not path:
            messagebox.showinfo('Receipt', 'No receipt on disk yet.')
            return
        text = f'CLEANROOM — LATEST RECEIPT\n\n{Path(path).name}\n{path}'
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status('Receipt summary copied.')
        except tk.TclError:
            messagebox.showinfo('Receipt', text)

    def _update_dashboard_cta(self):
        if not hasattr(self, 'dashboard_primary_btn'):
            return
        custody = {'verified': 0, 'total': 0, 'missing': 0}
        entries = self._load_log_dicts()
        if proof_module and entries:
            try:
                custody = proof_module.verify_entries(entries)
            except Exception:
                pass
        self._sync_home_state(custody_missing=int(custody.get('missing', 0) or 0))
        self._update_brand_identity()

    def _update_recent_proof(self):
        if not hasattr(self, 'recent_receipt_lbl'):
            return
        receipt_path = None
        if receipts_module:
            try:
                receipt_path = receipts_module.latest_receipt()
            except Exception:
                pass
        if receipt_path:
            stamp = receipt_path.stem.replace('receipt_', '')
            if len(stamp) >= 8:
                stamp = f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}'
            self.recent_receipt_lbl.configure(text=stamp)
        else:
            self.recent_receipt_lbl.configure(text='None yet')

        entries = self._load_log_dicts()
        archive_entry = None
        for e in reversed(entries):
            if e.get('kind') not in ('restore', 'prune'):
                archive_entry = e
                break
        if archive_entry:
            when = (archive_entry.get('when') or '')[:19].replace('T', ' ')
            self.recent_archive_lbl.configure(text=when or 'Logged')
        else:
            self.recent_archive_lbl.configure(text='None yet')

        audit_dir = brand.user_data_dir() / 'audits'
        latest_audit = None
        if audit_dir.is_dir():
            audits = sorted(audit_dir.glob('audit_*.html'), key=lambda p: p.stat().st_mtime, reverse=True)
            latest_audit = audits[0] if audits else None
        if latest_audit:
            self.recent_proofpack_lbl.configure(text=latest_audit.stem.replace('audit_', ''))
        else:
            self.recent_proofpack_lbl.configure(text='None yet')

    def _open_lights_out(self):
        """Companion app — confirm before opening the release page (never auto-download)."""
        dlg = CleanroomModal(
            self, 'Lights Out', width=480, height=280, colors=self._dialog_colors(),
        )
        dlg.heading('Companion app')
        dlg.message(
            'Lights Out is a separate companion app for wind-down and shutdown timing.\n\n'
            'Cleanroom does not install anything automatically. You can review the '
            'official release page in your browser.',
            wrap=420,
        )

        def _open_release_page():
            import webbrowser
            try:
                webbrowser.open(brand.LIGHTS_OUT_RELEASE_URL)
                self._set_status('Opening Lights Out release page…')
            except Exception as e:
                messagebox.showerror('Lights Out', f'Unable to open release page:\n{e}')
            dlg.close()

        dlg.add_button('Open release page', _open_release_page, primary=True, side='left')
        dlg.add_button('Cancel', dlg.close)

    def open_archive_folder(self):
        cfg = self._load_cleanup_config()
        if cfg is None:
            return
        archive_dir = cfg.get('archive_dir') or str(Path(__file__).parent)
        try:
            os.startfile(str(archive_dir))
        except Exception as e:
            messagebox.showerror('Open archive', f'Unable to open archive folder:\n{e}')

    def open_cleanup_log(self):
        if not self.restore_log_path.exists():
            messagebox.showwarning('Open log', f'Cleanup log not found: {self.restore_log_path}')
            return
        try:
            os.startfile(str(self.restore_log_path))
        except Exception as e:
            messagebox.showerror('Open log', f'Unable to open cleanup log:\n{e}')

    # ------------------------------------------------------------------
    # Scheduling wizard
    # ------------------------------------------------------------------
    def schedule_optimization(self):
        script = _resource_path('register_task.ps1')
        if not script.exists():
            messagebox.showerror('Schedule', 'Schedule script not found.')
            return

        dialog = CleanroomModal(
            self, 'Schedule Cleanup', width=440, height=400,
            colors=self._dialog_colors(),
        )
        dialog.heading('Schedule recurring cleanup')
        dialog.message(
            'Creates a Windows scheduled task named CleanroomDaily that runs Cleanroom non-interactively.',
            wrap=380,
        )

        form = ctk.CTkFrame(dialog.body, fg_color=dialog.colors['card'])
        form.pack(fill='x', pady=(8, 0))

        time_row = ttk.Frame(form, style='Card.TFrame')
        time_row.pack(anchor='w', pady=(0, 8))
        ttk.Label(time_row, text='Run at:').pack(side='left', padx=(0, 8))
        hour_var = tk.StringVar(value='02')
        minute_var = tk.StringVar(value='00')
        hour_spin = ttk.Spinbox(time_row, from_=0, to=23, width=4, textvariable=hour_var,
                                format='%02.0f', wrap=True, state='readonly')
        minute_spin = ttk.Spinbox(time_row, from_=0, to=55, increment=5, width=4, textvariable=minute_var,
                                  format='%02.0f', wrap=True, state='readonly')
        hour_spin.pack(side='left')
        ttk.Label(time_row, text=':').pack(side='left', padx=2)
        minute_spin.pack(side='left')

        # Recurrence
        recur_row = ttk.Frame(form, style='Card.TFrame')
        recur_row.pack(anchor='w', pady=(0, 8))
        ttk.Label(recur_row, text='Repeat:').pack(side='left', padx=(0, 8))
        recur_var = tk.StringVar(value='Daily')
        recur_combo = ttk.Combobox(recur_row, textvariable=recur_var, state='readonly',
                                   values=('Daily', 'Weekly'), width=10)
        recur_combo.pack(side='left')

        # Weekday selection (enabled only for weekly)
        days_frame = ttk.Labelframe(form, text='Days (weekly)')
        days_frame.pack(fill='x', pady=(0, 8))
        day_codes = [('Mon', 'MON'), ('Tue', 'TUE'), ('Wed', 'WED'), ('Thu', 'THU'),
                     ('Fri', 'FRI'), ('Sat', 'SAT'), ('Sun', 'SUN')]
        day_vars = {}
        day_checks = {}
        inner = ttk.Frame(days_frame)
        inner.pack(padx=8, pady=6)
        for i, (label, code) in enumerate(day_codes):
            var = tk.BooleanVar(value=(code == 'SUN'))
            cb = ttk.Checkbutton(inner, text=label, variable=var, state='disabled')
            cb.grid(row=0, column=i, padx=3)
            day_vars[code] = var
            day_checks[code] = cb

        def on_recur_change(event=None):
            state = 'normal' if recur_var.get() == 'Weekly' else 'disabled'
            for cb in day_checks.values():
                cb.config(state=state)
        recur_combo.bind('<<ComboboxSelected>>', on_recur_change)

        dedupe_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text='Deduplicate files during scheduled runs', variable=dedupe_var).pack(anchor='w', pady=(2, 0))

        status_lbl = ttk.Label(dialog.body, text='', style='Info.TLabel', wraplength=380)
        status_lbl.pack(anchor='w', pady=(8, 0))

        def on_schedule():
            time_value = f'{int(hour_var.get()):02d}:{int(minute_var.get()):02d}'
            schedule = 'WEEKLY' if recur_var.get() == 'Weekly' else 'DAILY'
            days = ','.join(code for code, var in day_vars.items() if var.get())
            if schedule == 'WEEKLY' and not days:
                self._show_info_modal('Schedule', 'Select at least one weekday.')
                return
            args = [
                'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script),
                '-TaskName', 'CleanroomDaily',
                '-Time', time_value,
                '-Schedule', schedule,
            ]
            if schedule == 'WEEKLY':
                args += ['-Days', days]
            if dedupe_var.get():
                args.append('-Dedup')
            if getattr(sys, 'frozen', False):
                # Packaged app: schedule this very exe in headless mode
                args += ['-ExePath', sys.executable]

            schedule_btn.configure(state='disabled')
            status_lbl.config(text='Creating scheduled task...')

            def work():
                return subprocess.run(args, capture_output=True, text=True)

            def done(result, err):
                if not dialog.win.winfo_exists():
                    return
                schedule_btn.configure(state='normal')
                if err is not None:
                    status_lbl.config(text='')
                    messagebox.showerror('Schedule failed', f'Unable to schedule optimization:\n{err}', parent=dialog.win)
                    return
                if result.returncode == 0:
                    when = f'{recur_var.get().lower()} at {time_value}' + (f' on {days}' if schedule == 'WEEKLY' else '')
                    self._set_status(f'Scheduled optimization {when}.')
                    self._show_info_modal('Schedule', f'Scheduled optimization {when}.')
                    dialog.close()
                else:
                    status_lbl.config(text='')
                    messagebox.showerror('Schedule failed', result.stderr or result.stdout or 'Unknown error', parent=dialog.win)

            self._run_bg(work, done)

        schedule_btn = dialog.add_button('Schedule', on_schedule, primary=True)
        dialog.add_button('Cancel', dialog.close)
        hour_spin.focus_set()

    # ------------------------------------------------------------------
    # Diagnostics dialog (local-only; no cloud)
    # ------------------------------------------------------------------
    def _show_delete_result_dialog(self, *, deleted, skipped, freed, receipt_path=None):
        lines = [
            f'Deleted: {deleted:,} archived file(s) ({freed})',
            f'Skipped: {skipped:,} item(s)',
            '',
            'Original live files were not touched.',
        ]
        if receipt_path:
            lines.append(f'Receipt: {receipt_path}')
        dlg = CleanroomModal(
            self, 'Delete from Archive — Result',
            width=480, height=280, colors=self._dialog_colors(),
        )
        dlg.heading('Archive delete complete')
        dlg.message('\n'.join(lines), wrap=420)
        if receipt_path and Path(receipt_path).is_file():
            dlg.add_button(
                'Open Receipt',
                lambda: (self._view_receipt_file(receipt_path, action_key='archive_prune'), dlg.close()),
                side='left', primary=True,
            )
        dlg.add_button('OK', dlg.close, primary=True)

    def _show_custody_verify_summary(self, result):
        verified = result.get('verified', 0)
        total = result.get('total', 0)
        missing = result.get('missing', 0)
        summary = (
            f'{verified:,} / {total:,} archived items are present on disk.\n'
            f'{missing:,} items are missing from archive.\n\n'
            'This usually means files were pruned, moved, or deleted outside Cleanroom.'
        )
        missing_items = result.get('missing_items') or []
        report_body = '\n'.join([
            'CLEANROOM — CUSTODY VERIFY REPORT',
            '',
            summary,
            '',
            'Missing items:',
            *[f'  · {p}' for p in missing_items],
        ])

        dlg = CleanroomModal(
            self, 'Verify Custody', width=500, height=300, colors=self._dialog_colors(),
        )
        dlg.heading('Custody check failed')
        dlg.message(summary, wrap=440)

        def _copy_summary():
            try:
                self.clipboard_clear()
                self.clipboard_append(summary)
                self._set_status('Custody summary copied.')
            except tk.TclError:
                pass

        dlg.add_button(
            'Open full report',
            lambda: show_report_modal(
                self, title='Custody Verify — Full Report', headline='Full custody report',
                body=report_body, colors=self._dialog_colors(),
            ),
            side='left',
        )
        dlg.add_button('Copy summary', _copy_summary, side='left')
        dlg.add_button('OK', dlg.close, primary=True)

    def _show_diagnostics_dialog(self):
        dlg = CleanroomModal(
            self, 'Diagnostics', width=460, height=260, colors=self._dialog_colors(),
        )
        dlg.heading('Local diagnostics')
        dlg.message(
            'Local-only logs and optional anonymous metrics. Nothing leaves this PC unless '
            'you opt in. Adjust diagnostics preferences below.',
            wrap=400,
        )
        var = tk.BooleanVar(value=False)
        try:
            if enable_telemetry and enable_telemetry.is_opted_in():
                var.set(True)
        except Exception:
            var.set(False)
        row = ctk.CTkFrame(dlg.body, fg_color=dlg.colors['card'])
        row.pack(anchor='w', pady=(12, 0))
        ctk_theme.switch(
            row, 'Enable anonymous usage metrics (opt-in, local only)', var,
            text_color=TEXT, progress_color=ACCENT,
            button_color=BORDER, button_hover_color=ACCENT,
        ).pack(anchor='w')

        def _save():
            try:
                if enable_telemetry:
                    enable_telemetry.set_opt_in(bool(var.get()))
                self.refresh_dashboard()
            except Exception:
                pass
            dlg.close()

        dlg.add_button('Save', _save, primary=True)
        dlg.add_button('Cancel', dlg.close)

    def _show_telemetry_dialog(self):
        """Legacy alias — opens Local Logs / Diagnostics panel."""
        self._show_diagnostics_dialog()

    # ------------------------------------------------------------------
    # Startup tab actions
    # ------------------------------------------------------------------
    def _update_summary(self):
        folders = len(self.data.get('folders', []))
        registry = len(self.data.get('registry', []))
        tasks = len(self.data.get('tasks', []))
        disabled = len(self.data.get('disabled', []))
        total = folders + registry + tasks
        self.total_label.config(text=str(total))
        self.folder_label.config(text=str(folders))
        self.registry_label.config(text=str(registry))
        self.tasks_label.config(text=str(tasks))
        self.disabled_label.config(text=str(disabled))

    def _selected_entry(self):
        sel = self.tree.selection()
        if not sel:
            return None
        idx = self.tree.index(sel[0])
        rows = getattr(self, '_startup_rows', None)
        if rows and 0 <= idx < len(rows):
            return dict(rows[idx])
        item = self.tree.item(sel[0])
        vals = item.get('values') or []
        return {
            'name': vals[0] if len(vals) > 0 else None,
            'source': vals[1] if len(vals) > 1 else None,
            'location': vals[2] if len(vals) > 2 else None,
            'command': vals[3] if len(vals) > 3 else None,
        }

    def _startup_menu_state(self, ent):
        """Return action availability for startup context menu."""
        source = ((ent or {}).get('source') or '').lower()
        can_enable = source in ('registry', 'disabled')
        can_disable = source == 'registry'
        cmd = (ent or {}).get('command') or ''
        path = self._startup_extract_path(cmd)
        can_open_file = bool(path and Path(path).exists())
        can_open_reg = source == 'registry' and bool((ent or {}).get('location'))
        can_open_task = source == 'task'
        return {
            'enable': (can_enable, 'Registry/disabled entries only'),
            'disable': (can_disable, 'Registry Run keys only'),
            'copy': (bool(cmd), 'No command recorded'),
            'open_file': (can_open_file, 'Executable not found on disk'),
            'open_loc': (can_open_reg or can_open_task,
                         'Registry key or scheduled task only'),
            'search': (bool((ent or {}).get('name')), 'No name to search'),
            'details': (ent is not None, ''),
        }

    def _startup_extract_path(self, command):
        if not command:
            return None
        cmd = command.strip()
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            if end > 1:
                return cmd[1:end]
        parts = cmd.split()
        return parts[0] if parts else None

    def _on_startup_double_click(self, _event=None):
        self._update_detail()
        self._update_actions()

    def _on_startup_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.tree.focus(row)
            self._update_detail()
            self._update_actions()
        ent = self._selected_entry()
        states = self._startup_menu_state(ent)
        self._show_row_popover(
            event.x_root, event.y_root,
            [
                ('Enable selected', self.enable_selected, states['enable'][0]),
                ('Disable selected', self.disable_selected, states['disable'][0]),
                ('Copy command', self.copy_command, states['copy'][0]),
                ('Copy entry name', self._startup_copy_name, states['details'][0]),
                ('Open file location', self._startup_open_file_location, states['open_file'][0]),
                ('Open registry / Task Scheduler', self._startup_open_source_location, states['open_loc'][0]),
                ('Search online', self._startup_search_online, states['search'][0]),
                ('Show details', self._on_startup_double_click, states['details'][0]),
            ],
            title='Startup',
        )
        return 'break'

    def _startup_open_file_location(self):
        ent = self._selected_entry()
        if not ent:
            return
        path = self._startup_extract_path(ent.get('command'))
        if not path:
            messagebox.showinfo('Open location', 'No executable path found in command.')
            return
        p = Path(path)
        if p.is_file():
            try:
                os.startfile(str(p.parent))
            except OSError as e:
                messagebox.showerror('Open location', str(e))
        elif p.parent.is_dir():
            os.startfile(str(p.parent))
        else:
            messagebox.showinfo('Open location', 'File location not found on disk.')

    def _startup_open_source_location(self):
        ent = self._selected_entry()
        if not ent:
            return
        source = (ent.get('source') or '').lower()
        if source == 'registry':
            key = ent.get('location') or ''
            if key:
                try:
                    self.clipboard_clear()
                    self.clipboard_append(key)
                except tk.TclError:
                    pass
            try:
                os.startfile('regedit.exe')
            except OSError as e:
                messagebox.showerror('Registry', str(e))
            self._set_status(f'Registry Editor opened — path copied: {key or "—"}')
        elif source == 'task':
            try:
                os.startfile('taskschd.msc')
            except OSError as e:
                messagebox.showerror('Task Scheduler', str(e))
            self._set_status('Task Scheduler opened — find the task by name in the list.')
        else:
            messagebox.showinfo('Open location', 'Available for registry and scheduled task entries.')

    def _startup_search_online(self):
        import urllib.parse
        import webbrowser
        ent = self._selected_entry()
        if not ent:
            return
        name = ent.get('name') or 'startup program'
        q = urllib.parse.quote(f'{name} startup program')
        webbrowser.open(f'https://www.google.com/search?q={q}')

    def _startup_copy_name(self):
        ent = self._selected_entry()
        if not ent:
            return
        name = ent.get('name') or ''
        try:
            self.clipboard_clear()
            self.clipboard_append(name)
            self._set_status('Entry name copied.')
        except tk.TclError:
            messagebox.showinfo('Copy name', name)

    def _update_detail(self):
        ent = self._selected_entry()
        if not ent:
            self.detail_name.config(text='—')
            self.detail_type.config(text='—')
            self.detail_status.config(text='—')
            self.detail_location.config(text='—')
            self.detail_command_text.configure(state='normal')
            self.detail_command_text.delete('1.0', 'end')
            self.detail_command_text.insert('1.0', '—')
            self.detail_command_text.configure(state='disabled')
            self.detail_hint.config(text='Select a startup item to review its command and available actions.')
            self._update_context_panel()
            return
        self.detail_name.config(text=ent.get('name') or '—')
        self.detail_type.config(text=self._startup_type(ent))
        self.detail_status.config(text=self._startup_status(ent))
        self.detail_location.config(text=ent.get('location') or '—')
        self.detail_command_text.configure(state='normal')
        self.detail_command_text.delete('1.0', 'end')
        self.detail_command_text.insert('1.0', ent.get('command') or '—')
        self.detail_command_text.configure(state='disabled')
        src = (ent.get('source') or '').lower()
        if src == 'registry':
            hint = ('Registry Run key — Disable Selected backs up the value and stops this at sign-in. '
                    'Re-enable anytime from the Disabled filter.')
        elif src == 'disabled':
            hint = 'Previously disabled by Cleanroom — Re-enable Selected restores the original Run value.'
        elif src == 'task':
            hint = ('Scheduled task — open Task Scheduler to disable, or verify the command path is expected.')
        elif src == 'folder':
            hint = ('Startup folder shortcut — delete the .lnk in the folder shown in Location, '
                    'or move it out of the startup directory.')
        else:
            hint = 'Review the command path — disable only if you recognize and no longer need this entry.'
        self.detail_hint.config(text=hint)
        self._update_context_panel()

    def enable_selected(self):
        ent = self._selected_entry()
        if not ent:
            messagebox.showwarning('No selection', 'Please select an item to enable.')
            return
        name = ent.get('name') or 'App'
        cmd = ent.get('command') or ''
        from_backup = ent.get('source') == 'disabled'
        try:
            if startup_manager_admin and startup_manager_admin.is_admin():
                if from_backup:
                    success, msg = startup_manager_admin.restore_disabled(name)
                else:
                    success, msg = startup_manager_admin.enable_registry_run(name, cmd)
                messagebox.showinfo('Result', msg)
                self.refresh()
                return
        except Exception:
            pass
        admin_py = Path(__file__).parent / 'startup_manager_admin.py'
        if from_backup:
            cli = f"{sys.executable} \"{admin_py}\" --restore {name} --json"
        else:
            cli = f"{sys.executable} \"{admin_py}\" --enable {name}={cmd} --json"
        if messagebox.askyesno('Run as admin?', 'To enable this entry you must run as administrator.\n\nRun elevated now?'):
            self._run_elevated(cli)

    def disable_selected(self):
        ent = self._selected_entry()
        if not ent:
            messagebox.showwarning('No selection', 'Please select an item to disable.')
            return
        name = ent.get('name')
        if not name:
            messagebox.showerror('Error', 'Could not determine entry name.')
            return
        try:
            if startup_manager_admin and startup_manager_admin.is_admin():
                success, msg = startup_manager_admin.disable_registry_run(name)
                messagebox.showinfo('Result', msg)
                self.refresh()
                return
        except Exception:
            pass
        cli = f"{sys.executable} \"{Path(__file__).parent / 'startup_manager_admin.py'}\" --disable {name} --json"
        if messagebox.askyesno('Run as admin?', 'To disable this entry you must run as administrator.\n\nRun elevated now?'):
            self._run_elevated(cli)

    def copy_command(self):
        ent = self._selected_entry()
        if not ent:
            return
        cmd = ent.get('command') or ''
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self._set_status('Command copied to clipboard.')

    def _run_elevated(self, cli_cmd):
        ps = f"Start-Process -FilePath '{sys.executable}' -ArgumentList \"{cli_cmd.replace('\"', '\\\"')}\" -Verb RunAs"
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps])
        except Exception as e:
            messagebox.showerror('Failed', f'Failed to start elevated process: {e}')

    def refresh(self):
        self.refresh_btn.config(state='disabled')
        self._sync_startup_view(loading=True)
        self.status_lbl.config(text='Refreshing...')
        self._set_status('Refreshing startup entries...')

        def done(data, err):
            self.refresh_btn.config(state='normal')
            if err is not None:
                self.status_lbl.config(text=f'Refresh failed: {err}')
                self._set_status('Refresh failed.')
                self._sync_startup_view(loading=False)
                return
            self.data = data
            self._apply_filter()
            self._update_summary()
            self._update_detail()
            self._update_actions()
            self.refresh_dashboard()
            total = len(data.get('folders', [])) + len(data.get('registry', []))
            self.status_lbl.config(text=f'{total} entries')
            self._set_status(f'Startup list refreshed: {total} entries.')

        def work():
            data = startup_manager.list_startup_entries() if startup_manager else {'folders': [], 'registry': []}
            try:
                data['disabled'] = startup_manager_admin.list_disabled() if startup_manager_admin else []
            except Exception:
                data['disabled'] = []
            return data

        self._run_bg(work, done)


class ToolTip:
    """Simple delayed tooltip for any widget."""
    DELAY_MS = 450

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self._after_id = None
        self.widget.bind('<Enter>', self._schedule)
        self.widget.bind('<Leave>', self.hide)
        self.widget.bind('<ButtonPress>', self.hide)

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.DELAY_MS, lambda: self.show(event))

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def show(self, event=None):
        if self.tipwindow or not self.text:
            return
        try:
            x = event.x_root + 10 if event else self.widget.winfo_rootx() + 10
            y = event.y_root + 10 if event else self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tipwindow = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f'+{x}+{y}')
            label = tk.Label(tw, text=self.text, justify='left', background=TOOLTIP_BG,
                             foreground=TOOLTIP_FG, relief='solid', borderwidth=1,
                             font=('Segoe UI', 9))
            label.pack(ipadx=4, ipady=2)
        except Exception:
            self.tipwindow = None

    def hide(self, event=None):
        self._cancel()
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            try:
                tw.destroy()
            except Exception:
                pass


def _focus_existing_cleanroom_window() -> bool:
    """Try to raise an already-running Cleanroom window."""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, brand.APP_DISPLAY)
        if not hwnd:
            return False
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        logger.debug('Focus existing Cleanroom window failed', exc_info=True)
        return False


_APP_INSTANCE = None
_SINGLE_INSTANCE_MUTEX = None


def _acquire_single_instance():
    """Prevent duplicate GUI processes (and tray icon piles) on Windows."""
    global _SINGLE_INSTANCE_MUTEX
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        mutex = ctypes.windll.kernel32.CreateMutexW(
            None, True, 'Local\\CleanroomWindowsSingleInstance')
        _SINGLE_INSTANCE_MUTEX = mutex
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            focused = _focus_existing_cleanroom_window()
            try:
                msg = ('Cleanroom is already running.\n'
                       'Brought the existing window forward.'
                       if focused else
                       'Cleanroom is already running.\n'
                       'Check the system tray or taskbar.')
                ctypes.windll.user32.MessageBoxW(
                    0, msg, brand.APP_DISPLAY, 0x40)
            except Exception:
                pass
            logger.info('Second Cleanroom launch blocked (focused=%s)', focused)
            return False
        return True
    except Exception:
        return True


def _headless_main(argv):
    """Cleanroom.exe --headless-clean [--config X] [--dedupe]: run the cleaner
    without any UI so Task Scheduler doesn't need a Python install."""
    import argparse
    ap = argparse.ArgumentParser(prog='Cleanroom --headless-clean', add_help=False)
    ap.add_argument('--headless-clean', action='store_true')
    ap.add_argument('--config', default=None)
    ap.add_argument('--dedupe', action='store_true')
    args, _ = ap.parse_known_args(argv)
    if cleanup_main is None:
        return 2
    return cleanup_main.run_headless(config_path=args.config, dedupe=args.dedupe)


def _parse_startup_argv(argv):
    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--open-receipt', metavar='PATH', default=None)
    ap.add_argument('--open-tab', choices=('archive', 'restore', 'settings'), default=None)
    ap.add_argument('--shell-archive', metavar='PATH', default=None)
    ap.add_argument('--shell-delete-archive', metavar='PATH', default=None)
    args, _ = ap.parse_known_args(argv)
    return args


def open_receipt_standalone(path_str):
    """Open a receipt file in the in-app viewer without running cleanup."""
    path = Path(path_str)
    if not path.is_file():
        return 1
    if receipts_module is None:
        return 2
    if not receipts_module.is_receipt_path(path):
        return 2
    try:
        body = receipts_module.read_receipt(path)
    except Exception:
        return 2

    root = tk.Tk()
    root.withdraw()
    try:
        if show_receipt:
            avail = bool(receipt_bridge and receipt_bridge.is_available())
            dlg = show_receipt(root, body, receipt_path=path,
                               bg=BG, card=CARD_BG, text_fg=TEXT,
                               receipt_available=avail,
                               open_in_receipt=(receipt_bridge.open_receipt
                                                if receipt_bridge else None))

            def _close():
                try:
                    dlg._modal.close()
                except Exception:
                    pass
                root.quit()

            dlg._modal.win.protocol('WM_DELETE_WINDOW', _close)
            root.mainloop()
        else:
            messagebox.showerror('Receipt', 'Receipt viewer unavailable.', parent=root)
            return 2
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    return 0


if __name__ == '__main__':
    _startup = _parse_startup_argv(sys.argv[1:])
    if _startup.open_receipt:
        sys.exit(open_receipt_standalone(_startup.open_receipt))
    if _startup.shell_archive:
        if shell_actions_module is None:
            print('shell-actions unavailable', file=sys.stderr)
            sys.exit(2)
        ok, msg = shell_actions_module.archive_path(_startup.shell_archive)
        print(msg)
        sys.exit(0 if ok else 1)
    if _startup.shell_delete_archive:
        if shell_actions_module is None:
            print('shell-actions unavailable', file=sys.stderr)
            sys.exit(2)
        ok, msg = shell_actions_module.delete_archive_path(_startup.shell_delete_archive)
        print(msg)
        sys.exit(0 if ok else 1)
    if '--headless-clean' in sys.argv[1:]:
        sys.exit(_headless_main(sys.argv[1:]))
    if not _acquire_single_instance():
        sys.exit(0)
    # Rebuild the window when the user flips the theme.
    while True:
        app = StartupManagerGUI(initial_tab=_startup.open_tab)
        app.mainloop()
        if not getattr(app, 'wants_restart', False):
            break
    from ui.tray import shutdown_all_trays
    shutdown_all_trays()
    sys.exit(0)
