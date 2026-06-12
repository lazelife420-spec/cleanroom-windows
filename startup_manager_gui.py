import json
import os
import queue
import brand
import customtkinter as ctk
from ui import ctk_theme
from ui.launcher import run_launch_splash
from ui.window_geometry import apply_window_geometry, bind_window_tracking, animations_disabled
from ui.receipt_animation import (
    ReceiptPrinterPanel,
    DEFAULT_LINES,
    PREVIEW_LINES,
    PROOF_PACK_LINES,
    play_receipt_animation,
)
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import sys
import shutil
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

APP_VERSION = brand.APP_VERSION
SEARCH_PLACEHOLDER = 'Search startup items...  (Ctrl+F)'


class StartupManagerGUI(ctk.CTk):
    """Cleanroom GUI: Review, Activity, Startup, Cleaner, Uninstaller, Restore."""

    def __init__(self, config_path=None, restore_log_path=None):
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
        prefs = load_ui_prefs()
        prefs['window_geometry'] = geo
        save_ui_prefs(prefs)

    def _run_launch_sequence(self):
        if animations_disabled():
            self._finish_launch_sequence()
            return
        self._launch_logo = self._load_logo(96)
        run_launch_splash(
            self,
            title=brand.APP_DISPLAY,
            tagline=brand.APP_MOTTO,
            colors=self._launcher_colors(),
            logo_photo=self._launch_logo,
            on_complete=self._finish_launch_sequence,
            min_ms=1100,
        )

    def _finish_launch_sequence(self):
        if self._launch_done:
            return
        self._launch_done = True
        prefs = load_ui_prefs()
        apply_window_geometry(self, prefs)
        bind_window_tracking(self, on_save=self._save_window_geometry)
        self.deiconify()
        self.lift()
        self.focus_force()
        self._update_responsive_layout()
        if not animations_disabled():
            self._fade_in_window()
            self.after(350, self._pulse_proof_flow)
        self.refresh()
        self.refresh_cleanup()
        self.refresh_restore()
        self.refresh_optimizer()
        self.refresh_activity()
        self.refresh_uninstaller()
        if foresight:
            self._run_bg(foresight.record_snapshot,
                         lambda result, err: self.refresh_foresight())

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
            w = self.winfo_width()
        except Exception:
            return
        if w < 200:
            return
        wrap = max(420, w - 300)
        if hasattr(self, 'ctx_desc_lbl'):
            self.ctx_desc_lbl.configure(wraplength=wrap)
        if hasattr(self, 'ctx_next_lbl'):
            self.ctx_next_lbl.configure(wraplength=max(320, w - 380))
        if hasattr(self, '_hdr_tagline_lbl'):
            self._hdr_tagline_lbl.configure(wraplength=max(360, w - 80))
        if hasattr(self, '_hdr_summary') and hasattr(self, '_hdr_hero'):
            if w < 1180:
                self._hdr_badges.grid(row=0, column=0, columnspan=2, sticky='nw')
                self._hdr_hero.grid(row=1, column=0, sticky='nw', padx=0, pady=(8, 0))
            else:
                self._hdr_badges.grid(row=0, column=0, sticky='nw')
                self._hdr_hero.grid(row=0, column=1, sticky='ne', padx=(16, 0), pady=0)
        self._layout_restore_split(w)
        preview_w = max(240, min(360, int(max(w - 280, 640) * 0.34)))
        if hasattr(self, '_restore_preview_panel'):
            self._restore_preview_panel.configure(width=preview_w)
        for attr in ('restore_detail_src', 'restore_detail_dest'):
            if hasattr(self, attr):
                getattr(self, attr).configure(wraplength=max(180, preview_w - 24))
        if hasattr(self, 'detail_hint'):
            self.detail_hint.configure(wraplength=max(400, w - 360))
        wrap = max(420, w - 340)
        for attr in ('uninst_detail_what', 'uninst_detail_does',
                     'uninst_detail_need', 'uninst_detail_uninst'):
            if hasattr(self, attr):
                getattr(self, attr).configure(wraplength=wrap)

    def _layout_restore_split(self, window_width):
        if not hasattr(self, '_restore_frame'):
            return
        try:
            content_w = self.tab_control.winfo_width()
        except Exception:
            content_w = max(window_width - 260, 640)
        mode = 'stacked' if content_w < 980 else 'wide'
        if mode == getattr(self, '_restore_split_mode', 'wide'):
            return
        self._restore_split_mode = mode
        left = self._restore_left
        right = self._restore_preview_panel
        left.pack_forget()
        right.pack_forget()
        if mode == 'stacked':
            left.pack(fill='both', expand=True)
            right.configure(width=max(280, content_w - 40))
            right.pack(fill='x', pady=(8, 0))
            right.pack_propagate(True)
        else:
            right.configure(width=max(260, min(360, int(content_w * 0.34))))
            left.pack(side='left', fill='both', expand=True)
            right.pack(side='left', fill='y', padx=(8, 0))
            right.pack_propagate(False)

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
                    background=ACCENT, foreground=ON_ACCENT, bordercolor=ACCENT_DARK)
        s.map('Primary.TButton',
              background=[('active', ACCENT_DARK), ('disabled', ACCENT_SOFT)],
              foreground=[('disabled', MUTED)])
        s.configure('Header.TLabel', font=('Segoe UI', 15, 'bold'), background=BG)
        s.configure('SubHeader.TLabel', font=('Segoe UI', 10), background=BG, foreground=MUTED)
        s.configure('Info.TLabel', font=('Segoe UI', 10), background=BG)
        s.configure('CardInfo.TLabel', font=('Segoe UI', 10), background=CARD_BG)
        s.configure('Detail.TLabelframe', background=CARD_BG, bordercolor=BORDER)
        s.configure('Detail.TLabelframe.Label', font=('Segoe UI', 10, 'bold'),
                    background=CARD_BG, foreground=TEXT)
        s.configure('Treeview.Heading', font=('Segoe UI Semibold', 10), background=HEAD_BG,
                    foreground=TEXT, relief='flat')
        s.map('Treeview.Heading', background=[('active', ACCENT_SOFT)])
        row_h, tree_font = (20, ('Segoe UI', 9)) if self.power_user else (24, ('Segoe UI', 10))
        s.configure('Treeview', font=tree_font, rowheight=row_h, background=CARD_BG,
                    foreground=TEXT, fieldbackground=CARD_BG, bordercolor=BORDER)
        s.map('Treeview',
              background=[('selected', ACCENT)],
              foreground=[('selected', ON_ACCENT)])
        badge_fg = ACCENT_DARK if CURRENT_THEME == 'light' else ACCENT
        s.configure('Badge.TLabel', font=('Segoe UI', 10, 'bold'), background=ACCENT_SOFT,
                    foreground=badge_fg, padding=(8, 4))
        s.configure('Status.TLabel', font=('Segoe UI', 9), background=STATUS_BG, foreground=TEXT, padding=(8, 4))
        s.configure('TNotebook', background=BG, borderwidth=0)
        s.configure('TNotebook.Tab', font=('Segoe UI', 10), padding=(14, 7),
                    background=SIDEBAR_BG, foreground=MUTED)
        s.map('TNotebook.Tab',
              background=[('selected', CARD_BG)],
              foreground=[('selected', ACCENT)])
        s.configure('TCheckbutton', background=BG, foreground=TEXT)
        s.map('TCheckbutton', background=[('active', BG)])

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------
    def create_widgets(self):
        self._build_header()
        self._build_proof_flow_bar()
        self._build_context_bar()
        main = ttk.Frame(self)
        main.pack(fill='both', expand=True, padx=10, pady=(0, 0))
        self._build_sidebar(main)

        content = ttk.Frame(main)
        content.pack(side='left', fill='both', expand=True)
        self.tab_control = ttk.Notebook(content)
        self.tab_control.pack(fill='both', expand=True)

        self.optimizer_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.activity_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.startup_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.cleanup_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.uninstall_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.restore_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.settings_tab = ttk.Frame(self.tab_control, style='Content.TFrame')
        self.tab_control.add(self.optimizer_tab, text='  📋 Review  ')
        self.tab_control.add(self.activity_tab, text='  📋 Activity  ')
        self.tab_control.add(self.startup_tab, text='  🚀 Startup  ')
        self.tab_control.add(self.cleanup_tab, text='  🧹 Cleaner  ')
        self.tab_control.add(self.uninstall_tab, text='  🗑 Uninstaller  ')
        self.tab_control.add(self.restore_tab, text='  ↩ Restore  ')
        self.tab_control.add(self.settings_tab, text='  ⚙ Settings  ')

        self._build_optimizer_tab()
        self._build_activity_tab()
        self._build_startup_tab()
        self._build_cleaner_tab()
        self._build_uninstaller_tab()
        self._build_restore_tab()
        self._build_settings_tab()
        self._build_statusbar()
        self.tab_control.bind('<<NotebookTabChanged>>', self._sync_nav_buttons)
        self._sync_nav_buttons()
        self._update_context_panel()

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
                    return PILImageTk.PhotoImage(img)
            photo = tk.PhotoImage(file=str(path))
            factor = max(1, photo.width() // px)
            return photo.subsample(factor, factor)
        except Exception:
            return None

    def _build_header(self):
        top = ctk_theme.frame(self, BG)
        top.pack(fill='x', padx=12, pady=(10, 4))

        toolbar = ctk_theme.frame(top, BG)
        toolbar.pack(fill='x', anchor='e', pady=(0, 8))
        toolbar_inner = ctk_theme.frame(toolbar, BG)
        toolbar_inner.pack(side='right')
        self.tb_scan = ctk_theme.button(
            toolbar_inner, '🔍 Scan', self.refresh_cleanup,
            fg_color=HEAD_BG, hover_color=ACCENT_SOFT, text_color=TEXT)
        self.tb_scan.pack(side='left', padx=4)
        self.tb_preview = ctk_theme.button(
            toolbar_inner, '🧾 Preview Receipt', self.preview_cleanup_receipt,
            fg_color=HEAD_BG, hover_color=ACCENT_SOFT, text_color=TEXT)
        self.tb_preview.pack(side='left', padx=4)
        self.tb_apply = ctk_theme.button(
            toolbar_inner, '🗂 Archive & Clean', self.apply_cleanup,
            fg_color=ACCENT, hover_color=ACCENT_DARK, text_color=ON_ACCENT, primary=True)
        self.tb_apply.pack(side='left', padx=4)
        self.tb_restore = ctk_theme.button(
            toolbar_inner, '↩ Restore',
            lambda: (self.tab_control.select(5), self.refresh_restore()),
            fg_color=HEAD_BG, hover_color=ACCENT_SOFT, text_color=TEXT)
        self.tb_restore.pack(side='left', padx=4)
        theme_btn = ctk_theme.button(
            toolbar_inner, '🎨', self.cycle_theme,
            fg_color=HEAD_BG, hover_color=ACCENT_SOFT, text_color=TEXT, width=40)
        theme_btn.pack(side='left', padx=4)

        title_container = ctk_theme.frame(top, BG)
        title_container.pack(fill='x')

        title_row = ctk_theme.frame(title_container, BG)
        title_row.pack(anchor='w')
        self._logo_photo = self._load_logo(72)
        if self._logo_photo is not None:
            tk.Label(title_row, image=self._logo_photo, bg=BG).pack(side='left', padx=(0, 14))
        title_text = ctk_theme.frame(title_row, BG)
        title_text.pack(side='left')
        ctk_theme.label(title_text, brand.APP_DISPLAY, text_color=TEXT,
                        font_size=22, weight='bold').pack(anchor='w')
        ctk_theme.label(title_text, brand.APP_MOTTO, text_color=ACCENT,
                        font_size=12, weight='bold').pack(anchor='w', pady=(2, 0))
        self._hdr_tagline_lbl = ctk_theme.label(
            title_container, brand.APP_TAGLINE, text_color=MUTED, font_size=11, wraplength=900)
        self._hdr_tagline_lbl.pack(anchor='w', pady=(6, 0))

        banner = ctk_theme.frame(title_container, ACCENT_SOFT, corner_radius=8)
        banner.pack(anchor='w', fill='x', pady=(8, 0))
        ctk_theme.label(
            banner, f'🛡  {ctk_theme.ARCHIVE_BANNER_TEXT}',
            text_color=ACCENT, font_size=11, weight='bold',
        ).pack(anchor='w', padx=12, pady=8)

        self._hdr_summary = ctk_theme.frame(title_container, BG)
        self._hdr_summary.pack(fill='x', pady=(10, 0))
        self._hdr_summary.grid_columnconfigure(0, weight=1)

        self._hdr_badges = ctk_theme.frame(self._hdr_summary, BG)
        self._hdr_badges.grid(row=0, column=0, sticky='nw')
        badge_fg = ACCENT_DARK if CURRENT_THEME == 'light' else ACCENT
        self.hdr_measured_lbl = ctk_theme.label(
            self._hdr_badges, '📁 Measured: —', text_color=badge_fg, font_size=10, weight='bold')
        self.hdr_archived_lbl = ctk_theme.label(
            self._hdr_badges, '🗂 Archived: —', text_color=badge_fg, font_size=10, weight='bold')
        self.hdr_reclaim_lbl = ctk_theme.label(
            self._hdr_badges, '🧹 Reclaimable: —', text_color=badge_fg, font_size=10, weight='bold')
        self.hdr_receipt_lbl = ctk_theme.label(
            self._hdr_badges, '🧾 Last Receipt: —', text_color=badge_fg, font_size=10, weight='bold')
        for col, lbl in enumerate((self.hdr_measured_lbl, self.hdr_archived_lbl,
                                   self.hdr_reclaim_lbl, self.hdr_receipt_lbl)):
            lbl.grid(row=col // 2, column=col % 2, sticky='w', padx=(0, 12), pady=2)

        self._hdr_hero = ctk_theme.frame(
            self._hdr_summary, ACCENT_SOFT, corner_radius=10,
            border_width=2, border_color=ACCENT)
        self._hdr_hero.grid(row=0, column=1, sticky='ne', padx=(16, 0))
        hero_inner = ctk_theme.frame(self._hdr_hero, ACCENT_SOFT, corner_radius=10)
        hero_inner.pack(padx=14, pady=10)
        self.hdr_trust_value = ctk_theme.label(
            hero_inner, '—', text_color=ACCENT, font_size=24, weight='bold')
        self.hdr_trust_value.pack(anchor='w')
        self.hdr_trust_lbl = ctk_theme.label(
            hero_inner, 'Custody Trust', text_color=TEXT, font_size=11, weight='bold')
        self.hdr_trust_lbl.pack(anchor='w')
        self.hdr_trust_why = ctk_theme.button(
            hero_inner, 'Why?', self._show_custody_trust_why,
            fg_color=HEAD_BG, hover_color=ACCENT_SOFT, text_color=TEXT, width=52)
        self.hdr_trust_why.pack(anchor='w', pady=(6, 0))

        self._add_tooltip(self.hdr_measured_lbl,
                          'Measured = logged actions in your history.\n'
                          'Bytes moved = lifetime logged archive movement.')
        self._add_tooltip(self.hdr_archived_lbl,
                          'Archived = artifacts verified on disk and restorable now.')
        self._add_tooltip(self.hdr_reclaim_lbl,
                          'Reclaimable = current scan candidates (checked items ready to archive).')
        self._add_tooltip(self.hdr_trust_value,
                          'Custody trust — % of archived artifacts verified on disk right now.')
        self._add_tooltip(self.hdr_trust_why,
                          'View evidence: what custody trust means and what is missing.')
        self._add_tooltip(self.hdr_receipt_lbl,
                          'Your most recent Cleanroom Receipt after a cleanup.')
        nxt = THEME_ORDER[(THEME_ORDER.index(CURRENT_THEME) + 1) % len(THEME_ORDER)]
        self._add_tooltip(self.tb_scan, 'Scan configured folders for cleanup candidates. (F5 refreshes everything)')
        self._add_tooltip(self.tb_preview, 'Preview what the Cleanroom Receipt will say before you archive anything.')
        self._add_tooltip(self.tb_apply, 'Move checked items to the archive — nothing is permanently deleted.')
        self._add_tooltip(self.tb_restore, 'Open Restore tab and reload archived entries.')
        self._add_tooltip(theme_btn,
                          f"Theme: {PALETTES[CURRENT_THEME]['LABEL']} — click for "
                          f"{PALETTES[nxt]['LABEL']}. All themes are in Settings.")

    def _build_proof_flow_bar(self):
        bar = ctk_theme.frame(self, CARD_BG, corner_radius=8)
        bar.pack(fill='x', padx=12, pady=(0, 8))
        ctk_theme.label(
            bar, ctk_theme.PROOF_FLOW_TEXT, text_color=ACCENT,
            font_size=12, weight='bold',
        ).pack(padx=14, pady=8)

    def _build_context_bar(self):
        """Live context for the active tab / submenu — updates on navigation."""
        bar = ctk_theme.frame(self, SIDEBAR_BG, corner_radius=8)
        bar.pack(fill='x', padx=12, pady=(0, 8))
        top = ctk_theme.frame(bar, SIDEBAR_BG)
        top.pack(fill='x', padx=12, pady=(10, 2))
        self.ctx_title_lbl = ctk_theme.label(
            top, 'Review', text_color=ACCENT, font_size=12, weight='bold')
        self.ctx_title_lbl.pack(side='left')
        self.ctx_subtitle_lbl = ctk_theme.label(
            top, '', text_color=MUTED, font_size=10)
        self.ctx_subtitle_lbl.pack(side='left', padx=(10, 0))
        self.ctx_desc_lbl = ctk_theme.label(
            bar, '', text_color=TEXT, font_size=11, wraplength=980, justify='left')
        self.ctx_desc_lbl.pack(anchor='w', padx=12, pady=(0, 4))
        next_row = ctk_theme.frame(bar, SIDEBAR_BG)
        next_row.pack(fill='x', padx=12, pady=(0, 10))
        ctk_theme.label(next_row, 'Next step', text_color=MUTED, font_size=9, weight='bold').pack(
            side='left', padx=(0, 6))
        self.ctx_next_lbl = ctk_theme.label(
            next_row, '', text_color=ACCENT, font_size=10, wraplength=900, justify='left')
        self.ctx_next_lbl.pack(side='left', fill='x', expand=True)

    def _update_context_panel(self):
        try:
            tab_idx = self.tab_control.index('current')
        except Exception:
            tab_idx = 0
        ctx = (ctk_theme.TAB_CONTEXT[tab_idx] if tab_idx < len(ctk_theme.TAB_CONTEXT)
               else ctk_theme.TAB_CONTEXT[0])
        subtitle = ''
        desc = ctx['description']
        nxt = ctx['next']

        if tab_idx == 2:
            cat = getattr(self, 'current_category', 'All')
            sub = ctk_theme.STARTUP_FILTER_CONTEXT.get(cat)
            if sub:
                subtitle = f'· {sub[0]}'
                desc = sub[1]
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
            checked = len(getattr(self, 'cleanup_selected', set()) or [])
            subtitle = f'· {count} candidates · {checked} checked'
            if count == 0:
                nxt = 'No candidates yet — try Settings → Relaxed scan, then Scan Now.'
            else:
                nxt = f'{checked} item(s) ready — Preview Receipt, then Archive & Clean.'
        elif tab_idx == 4:
            entry = self._selected_program() if hasattr(self, 'uninstall_tree') else None
            if entry and program_advice:
                advice = program_advice.analyze_program(entry)
                subtitle = f'· {advice["category"].replace("_", " ")}'
                nxt = advice['need']
            else:
                nxt = 'Select a program — read the summary panel, then Uninstall or Force Remove.'
        elif tab_idx == 0:
            count = len(getattr(self, 'cleanup_items', []) or [])
            if count:
                subtitle = f'· {count} cleanup candidate(s) awaiting review'

        self.ctx_title_lbl.configure(text=ctx['title'])
        self.ctx_subtitle_lbl.configure(text=subtitle)
        self.ctx_desc_lbl.configure(text=desc)
        self.ctx_next_lbl.configure(text=nxt)

    def _navigate_to_tab(self, idx):
        self.tab_control.select(idx)
        self._update_context_panel()

    def set_theme(self, name):
        if name not in PALETTES:
            return
        prefs = load_ui_prefs()
        prefs['theme'] = name
        save_ui_prefs(prefs)
        apply_palette(name)
        self.wants_restart = True
        self.destroy()

    def cycle_theme(self):
        nxt = THEME_ORDER[(THEME_ORDER.index(CURRENT_THEME) + 1) % len(THEME_ORDER)]
        self.set_theme(nxt)

    def _build_sidebar(self, parent):
        sidebar = ctk_theme.frame(parent, SIDEBAR_BG, corner_radius=8)
        sidebar.pack(side='left', fill='y', padx=(0, 10), pady=(0, 4))
        sidebar.configure(width=220)
        sidebar.pack_propagate(False)

        ctk_theme.label(sidebar, brand.APP_DISPLAY, text_color=TEXT,
                        font_size=13, weight='bold').pack(anchor='w', padx=12, pady=(12, 10))
        self._nav_buttons = []
        nav_tips = (
            'Proof dashboard — candidates, disk foresight, receipt preview.',
            'Activity ledger — every archive with timestamps.',
            'Startup programs — filter by source, enable or disable.',
            'Scan folders and archive reviewed files to custody.',
            'Uninstall programs and archive leftovers.',
            'Restore archived files from the cleanup log.',
            'Scan paths, ages, archive folder, quick toggles.',
        )
        for idx, label in enumerate(('📋  Review', '📊  Activity', '🚀  Startup', '🧹  Cleaner',
                                     '🗑  Uninstaller', '↩  Restore', '⚙  Settings')):
            btn = ctk_theme.button(
                sidebar, label, lambda i=idx: self._navigate_to_tab(i),
                fg_color='transparent', hover_color=ACCENT_SOFT, text_color=TEXT)
            btn.pack(fill='x', pady=2, padx=6)
            self._nav_buttons.append(btn)
            if idx < len(nav_tips):
                self._add_tooltip(btn, nav_tips[idx])

        sep = ctk.CTkFrame(sidebar, height=1, fg_color=BORDER, corner_radius=0)
        sep.pack(fill='x', pady=10, padx=10)
        ctk_theme.label(sidebar, 'Tools', text_color=TEXT, font_size=12, weight='bold').pack(
            anchor='w', padx=12, pady=(0, 8))
        tools = [
            ('📸  Registry Snapshot', self.open_registry_health,
             'Find registry entries pointing at missing files. Archive-first.'),
            ('🕐  Cleanroom Rewind', self.open_time_machine,
             'Roll back whole days of Cleanroom actions.'),
            ('🗂️  Archive Browser', self.open_archive_browser_tab,
             'Browse archived custody with local prune recommendations.'),
            ('🧾  Cleanroom Receipt', self.open_last_receipt,
             'View the receipt from your most recent cleanup in-app.'),
            ('🔬  Custody Check', self.verify_custody,
             'Audit the entire history: prove every archived item\n'
             'is still on disk and restorable, right now.'),
            ('📄  Proof Pack (HTML)', self.export_audit,
             'Generate a shareable HTML proof report of everything\n'
             'Cleanroom has ever done on this PC.'),
            ('⏰  Schedule', self.schedule_optimization,
             'Schedule recurring cleanup via Task Scheduler.'),
        ]
        for label, cmd, tip in tools:
            btn = ctk_theme.button(
                sidebar, label, cmd,
                fg_color='transparent', hover_color=ACCENT_SOFT, text_color=TEXT)
            btn.pack(fill='x', pady=2, padx=6)
            self._add_tooltip(btn, tip)

        sep2 = ctk.CTkFrame(sidebar, height=1, fg_color=BORDER, corner_radius=0)
        sep2.pack(fill='x', pady=10, padx=10)
        ctk_theme.label(sidebar, 'Shortcuts', text_color=TEXT, font_size=12, weight='bold').pack(
            anchor='w', padx=12, pady=(0, 4))
        for txt in ('F5  Refresh all', 'Ctrl+F  Search startup', 'Ctrl+1..7  Switch tab'):
            ctk_theme.label(sidebar, txt, text_color=MUTED, font_size=10).pack(
                anchor='w', padx=14, pady=1)

    def _sync_nav_buttons(self, event=None):
        try:
            current = self.tab_control.index('current')
        except Exception:
            current = 0
        for i, btn in enumerate(self._nav_buttons):
            if i == current:
                btn.configure(fg_color=ACCENT_SOFT, text_color=ACCENT,
                              font=ctk_theme.font(11, 'bold'))
            else:
                btn.configure(fg_color='transparent', text_color=TEXT,
                              font=ctk_theme.font(11, 'normal'))
        self._update_context_panel()

    def _build_optimizer_tab(self):
        header = ttk.Frame(self.optimizer_tab, style='Content.TFrame')
        header.pack(fill='x', padx=10, pady=10)
        ttk.Label(header, text='Review', style='Header.TLabel').pack(anchor='w')
        ttk.Label(header, text='Scan → preview receipt → archive & clean → verify custody → rewind if needed.',
                  style='SubHeader.TLabel').pack(anchor='w', pady=(4, 0))

        cards = ttk.Frame(self.optimizer_tab, style='Content.TFrame')
        cards.pack(fill='x', padx=10, pady=(10, 0))

        # Health ring gauge card
        health_card = tk.Frame(cards, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        health_card.pack(side='left', padx=(0, 10), fill='y')
        self.health_canvas = tk.Canvas(health_card, width=92, height=92, bg=CARD_BG, highlightthickness=0)
        self.health_canvas.pack(side='left', padx=(12, 4), pady=10)
        health_text = tk.Frame(health_card, bg=CARD_BG)
        health_text.pack(side='left', padx=(0, 16), pady=10)
        tk.Label(health_text, text='ITEMS TO REVIEW', bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 8, 'bold')).pack(anchor='w', pady=(8, 2))
        self.health_band_lbl = tk.Label(health_text, text='—', bg=CARD_BG, fg=TEXT,
                                        font=('Segoe UI', 13, 'bold'))
        self.health_band_lbl.pack(anchor='w')
        self.health_note_lbl = tk.Label(health_text, text='Not a PC health score — evidence only.',
                                        bg=CARD_BG, fg=MUTED, font=('Segoe UI', 8), wraplength=140, justify='left')
        self.health_note_lbl.pack(anchor='w', pady=(4, 0))
        self._add_tooltip(health_text, 'How many cleanup candidates await your review.\n'
                                       'Cleanroom never shows fake “PC health” numbers.')

        self.stat_startup_value = self._stat_card(cards, 'Startup items')
        self.stat_cleanup_value = self._stat_card(cards, 'Cleanup candidates')
        self.stat_size_value = self._stat_card(cards, 'Reclaimable space')

        # Disk Foresight card: free-space trend + disk-full prediction
        fs_card = tk.Frame(cards, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        fs_card.pack(side='left', fill='y')
        fs_left = tk.Frame(fs_card, bg=CARD_BG)
        fs_left.pack(side='left', padx=(14, 8), pady=10)
        tk.Label(fs_left, text='DISK FORESIGHT', bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 8, 'bold')).pack(anchor='w')
        self.foresight_lbl = tk.Label(fs_left, text='Collecting data…', bg=CARD_BG, fg=TEXT,
                                      font=('Segoe UI', 11, 'bold'), justify='left')
        self.foresight_lbl.pack(anchor='w', pady=(2, 0))
        self.foresight_sub_lbl = tk.Label(fs_left, text='', bg=CARD_BG, fg=MUTED,
                                          font=('Segoe UI', 9), justify='left')
        self.foresight_sub_lbl.pack(anchor='w')
        self.foresight_canvas = tk.Canvas(fs_card, width=150, height=56, bg=CARD_BG,
                                          highlightthickness=0)
        self.foresight_canvas.pack(side='left', padx=(0, 14), pady=10)
        self._add_tooltip(fs_card, 'Cleanroom records a free-space snapshot on every run\n'
                                   'and predicts when this drive runs out of space.')

        actions = ttk.Frame(self.optimizer_tab, style='Content.TFrame')
        actions.pack(fill='x', padx=10, pady=(10, 8))
        self.schedule_btn = ttk.Button(actions, text='Schedule Cleanup', style='Action.TButton',
                                       command=self.schedule_optimization)
        self.schedule_btn.pack(side='left')
        self.preview_receipt_btn = ttk.Button(actions, text='Preview Receipt', style='Primary.TButton',
                                              command=self.preview_cleanup_receipt)
        self.preview_receipt_btn.pack(side='left', padx=6)
        self.open_archive_btn = ttk.Button(actions, text='Open Archive Folder', style='Action.TButton',
                                           command=self.open_archive_folder)
        self.open_archive_btn.pack(side='left', padx=6)
        self.open_log_btn = ttk.Button(actions, text='Open Cleanup Log', style='Action.TButton',
                                       command=self.open_cleanup_log)
        self.open_log_btn.pack(side='left', padx=6)
        self.telemetry_btn = ttk.Button(actions, text='Telemetry', style='Action.TButton',
                                        command=self._show_telemetry_dialog)
        self.telemetry_btn.pack(side='left', padx=6)
        self.prune_btn = ttk.Button(actions, text='Archive Prune Recommendations…', style='Action.TButton',
                                    command=self.open_archive_browser_tab)
        self.prune_btn.pack(side='left', padx=6)
        self.receipt_btn = ttk.Button(actions, text='Cleanroom Receipt', style='Action.TButton',
                                      command=self.open_last_receipt)
        self.receipt_btn.pack(side='left', padx=6)
        self._add_tooltip(self.receipt_btn, 'Open the receipt from your most recent cleanup:\n'
                                            'what moved, space freed, disk days bought.')
        self.reg_health_btn = ttk.Button(actions, text='📸 Registry Snapshot…', style='Action.TButton',
                                         command=self.open_registry_health)
        self.reg_health_btn.pack(side='left', padx=6)
        self._add_tooltip(self.reg_health_btn,
                          'Snapshot registry entries that verifiably point to missing files\n'
                          '(dead startup refs, broken App Paths, orphaned uninstallers).\n'
                          'Repairs are exported to .reg backups first — fully restorable.')
        self._add_tooltip(self.prune_btn,
                          'Archive Prune Recommendations — permanently remove selected files\n'
                          'from Cleanroom\'s archive custody only. Original live files are not touched.')
        self._add_tooltip(self.preview_receipt_btn, 'See what the receipt will record before archiving.')
        self._add_tooltip(self.schedule_btn, 'Schedule recurring cleanup runs via Task Scheduler.')
        self._add_tooltip(self.open_archive_btn, 'Open the configured archive folder in Explorer.')
        self._add_tooltip(self.open_log_btn, 'Open cleanup_log.json.')
        self._add_tooltip(self.telemetry_btn, 'View or change the local telemetry opt-in.')

        rec_card = ttk.Frame(self.optimizer_tab, style='Card.TFrame')
        rec_card.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        ttk.Label(rec_card, text='What Cleanroom found', font=('Segoe UI', 11, 'bold'),
                  background=CARD_BG).pack(anchor='w', padx=10, pady=(8, 4))
        rec_body = ttk.Frame(rec_card, style='Card.TFrame')
        rec_body.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        rec_left = ttk.Frame(rec_body, style='Card.TFrame')
        rec_left.pack(side='left', fill='both', expand=True)
        self.rec_tree = ttk.Treeview(rec_left, columns=('severity', 'title', 'detail'),
                                     show='headings', selectmode='browse')
        self.rec_tree.heading('severity', text='Priority')
        self.rec_tree.heading('title', text='Recommendation')
        self.rec_tree.heading('detail', text='Why it matters')
        self.rec_tree.column('severity', width=90, anchor='center', stretch=False)
        self.rec_tree.column('title', width=220, anchor='w')
        self.rec_tree.column('detail', width=360, anchor='w')
        rec_scroll = ttk.Scrollbar(rec_left, orient='vertical', command=self.rec_tree.yview)
        self.rec_tree.configure(yscrollcommand=rec_scroll.set)
        self.rec_tree.pack(side='left', fill='both', expand=True)
        rec_scroll.pack(side='right', fill='y')
        self.receipt_printer = ReceiptPrinterPanel(
            rec_body,
            width=240,
            height=200,
            panel_bg=CARD_BG,
            paper_bg='#E8EDF4',
            accent=ACCENT,
            text_color='#1F2937',
            muted='#5B6573',
            border=BORDER,
        )
        self.receipt_printer.pack(side='right', fill='y', padx=(10, 0))
        for sev, color in SEVERITY_COLORS.items():
            self.rec_tree.tag_configure(sev, foreground=color)
        self.rec_empty_hint = self._make_empty_hint(
            self.rec_tree,
            'No findings yet.\n\n'
            'Click Scan in the toolbar to search your configured folders.\n'
            'Cleanroom only shows reviewed candidates — every move gets a receipt.')

    def _build_activity_tab(self):
        """Proof ledger — every action Cleanroom ever took, with custody status."""
        head = ttk.Frame(self.activity_tab, style='Content.TFrame')
        head.pack(fill='x', padx=10, pady=(10, 4))
        ttk.Label(head, text='Cleanroom Activity Ledger', font=('Segoe UI', 13, 'bold'),
                  background=BG).pack(side='left')
        self.act_status_lbl = ttk.Label(head, text='', style='Badge.TLabel')
        self.act_status_lbl.pack(side='left', padx=(10, 0))

        top = ttk.Frame(self.activity_tab, style='Content.TFrame')
        top.pack(fill='x', padx=10, pady=(0, 8))

        trust_card = tk.Frame(top, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        trust_card.pack(side='left', padx=(0, 12))
        self.trust_canvas = tk.Canvas(trust_card, width=100, height=100, bg=CARD_BG, highlightthickness=0)
        self.trust_canvas.pack(side='left', padx=(12, 4), pady=10)
        trust_txt = tk.Frame(trust_card, bg=CARD_BG)
        trust_txt.pack(side='left', padx=(0, 16), pady=10)
        tk.Label(trust_txt, text='CUSTODY TRUST SCORE', bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 8, 'bold')).pack(anchor='w')
        self.trust_band_lbl = tk.Label(trust_txt, text='—', bg=CARD_BG, fg=TEXT,
                                       font=('Segoe UI', 13, 'bold'))
        self.trust_band_lbl.pack(anchor='w')
        self.trust_sub_lbl = tk.Label(trust_txt, text='', bg=CARD_BG, fg=MUTED,
                                      font=('Segoe UI', 9), wraplength=220, justify='left')
        self.trust_sub_lbl.pack(anchor='w', pady=(4, 0))

        self.stat_act_total = self._stat_card(top, 'Actions logged')
        self.stat_act_present = self._stat_card(top, 'Restorable now')
        self.stat_act_bytes = self._stat_card(top, 'Bytes in custody')
        self.stat_act_pruned = self._stat_card(top, 'Bytes pruned')
        self._add_tooltip(self.stat_act_bytes,
                          'Bytes in custody = verified files still restorable in the archive.')
        self._add_tooltip(self.stat_act_pruned,
                          'Bytes pruned = archive custody permanently removed (original files untouched).')
        ttk.Label(top, text='Reclaimable = current scan candidates · '
                            'Bytes in custody = verified restorable files · '
                            'Bytes moved = lifetime logged archive movement',
                  style='Info.TLabel', wraplength=520).pack(side='left', padx=(8, 0), anchor='center')

        bar = ttk.Frame(self.activity_tab, style='Content.TFrame')
        bar.pack(fill='x', padx=10, pady=(0, 6))
        ttk.Button(bar, text='Refresh', style='Action.TButton',
                   command=self.refresh_activity).pack(side='left')
        ttk.Button(bar, text='Verify Custody', style='Action.TButton',
                   command=self.verify_custody).pack(side='left', padx=6)
        ttk.Button(bar, text='Proof Pack (HTML)', style='Primary.TButton',
                   command=self.export_audit).pack(side='left', padx=6)
        ttk.Button(bar, text='Archive Browser', style='Action.TButton',
                   command=self.open_archive_browser_tab).pack(side='left', padx=6)
        ttk.Label(bar, text='Every row is a real archived artifact — ✓ means it\'s still on disk.',
                  style='Info.TLabel').pack(side='left', padx=(12, 0))

        self.act_sub_notebook = ttk.Notebook(self.activity_tab)
        self.act_sub_notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        ledger_panel = ttk.Frame(self.act_sub_notebook, style='Card.TFrame')
        self.act_sub_notebook.add(ledger_panel, text='  Activity Ledger  ')
        wrap = ledger_panel
        cols = ('status', 'when', 'reason', 'source', 'size')
        self.activity_tree = ttk.Treeview(wrap, columns=cols, show='headings', selectmode='browse')
        for c, label, w in (('status', '', 36), ('when', 'When', 140), ('reason', 'Reason', 130),
                            ('source', 'Source', 420), ('size', 'Size', 80)):
            self.activity_tree.heading(c, text=label)
            anchor = 'center' if c in ('status', 'size') else 'w'
            self.activity_tree.column(c, width=w, anchor=anchor, stretch=(c == 'source'))
        vsb = ttk.Scrollbar(wrap, orient='vertical', command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=vsb.set)
        self.activity_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self.activity_tree.tag_configure('present', foreground=ACCENT)
        self.activity_tree.tag_configure('missing', foreground=SEVERITY_COLORS['high'])
        self.activity_empty = self._make_empty_hint(
            self.activity_tree, 'No Cleanroom actions logged yet.\n'
                                'Run a cleanup — every move will appear here with proof status.')
        self._activity_feed = []
        self._build_archive_browser_panel()

    def _build_archive_browser_panel(self):
        """In-app archive custody browser with local prune recommendations."""
        panel = ttk.Frame(self.act_sub_notebook, style='Card.TFrame')
        self.act_sub_notebook.add(panel, text='  Archive Browser  ')

        head = ttk.Frame(panel, style='Content.TFrame')
        head.pack(fill='x', padx=8, pady=(8, 4))
        ttk.Label(head, text='Archive Browser', font=('Segoe UI', 12, 'bold'),
                  background=BG).pack(side='left')
        ttk.Label(head, text='Archive Prune Recommendations — archive custody only',
                  style='Info.TLabel').pack(side='left', padx=(10, 0))

        chip_row = ttk.Frame(panel, style='Content.TFrame')
        chip_row.pack(fill='x', padx=8, pady=(0, 6))
        self._archive_prune_filter = tk.StringVar(value='')
        for label, value in (
            ('All', ''), ('Safe to prune', archive_custody.PRUNE_SAFE if archive_custody else ''),
            ('Review first', archive_custody.PRUNE_REVIEW if archive_custody else ''),
            ('Keep in custody', archive_custody.PRUNE_KEEP if archive_custody else ''),
        ):
            ttk.Radiobutton(chip_row, text=label, value=value, variable=self._archive_prune_filter,
                            command=self.refresh_archive_browser).pack(side='left', padx=(0, 8))

        tree_wrap = ttk.Frame(panel)
        tree_wrap.pack(fill='both', expand=True, padx=8, pady=(0, 6))
        acols = ('when', 'src', 'dest', 'reason', 'size', 'restorable', 'receipt', 'prune_rank')
        self.archive_tree = ttk.Treeview(tree_wrap, columns=acols, show='headings',
                                         selectmode='extended')
        headings = {
            'when': 'Archived date', 'src': 'Original path', 'dest': 'Archive path',
            'reason': 'Reason', 'size': 'Size', 'restorable': 'Restorable',
            'receipt': 'Receipt', 'prune_rank': 'Prune rank',
        }
        widths = {'when': 130, 'src': 220, 'dest': 220, 'reason': 100, 'size': 72,
                  'restorable': 72, 'receipt': 56, 'prune_rank': 110}
        for c in acols:
            self.archive_tree.heading(c, text=headings[c])
            anchor = 'center' if c in ('size', 'restorable', 'receipt', 'prune_rank') else 'w'
            stretch = c in ('src', 'dest')
            self.archive_tree.column(c, width=widths[c], anchor=anchor, stretch=stretch)
        vsb = ttk.Scrollbar(tree_wrap, orient='vertical', command=self.archive_tree.yview)
        hsb = ttk.Scrollbar(tree_wrap, orient='horizontal', command=self.archive_tree.xview)
        self.archive_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.archive_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)
        self.archive_tree.tag_configure('safe', foreground=ACCENT)
        self.archive_tree.tag_configure('review', foreground=SEVERITY_COLORS['medium'])
        self.archive_tree.tag_configure('keep', foreground=MUTED)
        self.archive_empty = self._make_empty_hint(
            self.archive_tree, 'No archive custody records yet.\n'
                                'Archive files with Cleaner — evidence appears here.')
        self._archive_records = []

        actions = ttk.Frame(panel, style='Content.TFrame')
        actions.pack(fill='x', padx=8, pady=(0, 8))
        for txt, cmd in (
            ('Restore Selected', self._archive_restore_selected),
            ('Open Original Location', self._archive_open_original),
            ('Open Archive Location', self._archive_open_archive),
            ('Open Receipt', self._archive_open_receipt),
            ('Copy Path', self._archive_copy_path),
        ):
            ttk.Button(actions, text=txt, style='Action.TButton', command=cmd).pack(side='left', padx=(0, 4))
        ttk.Button(actions, text='Prune Selected from Archive', style='Primary.TButton',
                   command=self.confirm_prune_selected).pack(side='right')
        self.archive_status_lbl = ttk.Label(panel, text='', style='Info.TLabel')
        self.archive_status_lbl.pack(anchor='w', padx=10, pady=(0, 8))

    def _stat_card(self, parent, caption):
        """White stat card with a big value label; returns the value label."""
        card = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        card.pack(side='left', padx=(0, 10), fill='y')
        value = tk.Label(card, text='—', bg=CARD_BG, fg=TEXT, font=('Segoe UI', 22, 'bold'))
        value.pack(anchor='w', padx=16, pady=(14, 0))
        tk.Label(card, text=caption, bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 9)).pack(anchor='w', padx=16, pady=(0, 14))
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
        self.hdr_measured_lbl.configure(text=f'📁 Measured: {measured:,}')
        self.hdr_archived_lbl.configure(text=f'🗂 Archived: {custody.get("verified", 0):,}')
        selected = sum(self.cleanup_items[i].get('size', 0) for i in self.cleanup_selected
                       if 0 <= i < len(self.cleanup_items)) if self.cleanup_items else 0
        reclaim = selected if self.cleanup_selected else self.cleanup_total_size
        self.hdr_reclaim_lbl.configure(text=f'🧹 Reclaimable: {self._format_size(reclaim)}')
        if trust is not None:
            self.hdr_trust_value.configure(text=f'{trust}%')
        else:
            self.hdr_trust_value.configure(text='—')
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
            self.hdr_receipt_lbl.configure(text=f'🧾 Last Receipt: {stamp}')
        else:
            self.hdr_receipt_lbl.configure(text='🧾 Last Receipt: Not generated')

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
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry(f'{width}x{height}')
        dlg.configure(bg=BG)
        dlg.transient(self)
        dlg.grab_set()
        dlg.bind('<Escape>', lambda e: dlg.destroy())
        frame = ttk.Frame(dlg, style='Content.TFrame')
        frame.pack(fill='both', expand=True, padx=12, pady=12)
        txt = tk.Text(frame, wrap='word', font=('Consolas', 10), relief='flat',
                      bg=PREVIEW_BG, fg=TEXT, insertbackground=TEXT,
                      highlightthickness=1, highlightbackground=BORDER)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=txt.yview)
        txt.configure(yscrollcommand=scroll.set)
        txt.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        txt.insert('1.0', text)
        txt.config(state='disabled')
        ttk.Button(dlg, text='Close', style='Primary.TButton', command=dlg.destroy).pack(pady=(0, 12))

    def preview_cleanup_receipt(self):
        """Draft Cleanroom Receipt for checked candidates — before any archive."""
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
                    show_receipt(self, preview, title='Cleanroom Receipt — Preview',
                                 preview=True, bg=BG, card=CARD_BG, text_fg=TEXT)
                else:
                    raise RuntimeError('receipt viewer unavailable')
            except Exception:
                self._show_text_dialog('Cleanroom Receipt — Preview', preview)

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
        self._draw_foresight_sparkline(history)
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
        c = self.foresight_canvas
        c.delete('all')
        try:
            pts = foresight._points(history)
        except Exception:
            pts = []
        w, h, pad = 150, 56, 6
        if len(pts) < 2:
            c.create_text(w / 2, h / 2, text='no trend yet', fill=MUTED,
                          font=('Segoe UI', 8, 'italic'))
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x_span = (xs[-1] - xs[0]) or 1.0
        y_min, y_max = min(ys), max(ys)
        y_span = (y_max - y_min) or 1.0
        coords = []
        for x, y in pts:
            px = pad + (x - xs[0]) / x_span * (w - 2 * pad)
            py = (h - pad) - (y - y_min) / y_span * (h - 2 * pad)
            coords.extend((px, py))
        c.create_line(*coords, fill=ACCENT, width=2, smooth=True)
        c.create_oval(coords[-2] - 3, coords[-1] - 3, coords[-2] + 3, coords[-1] + 3,
                      fill=ACCENT, outline='')

    def _build_startup_tab(self):
        head = ttk.Frame(self.startup_tab, style='Content.TFrame')
        head.pack(fill='x', padx=10, pady=(10, 4))
        ttk.Label(head, text='Startup Manager', font=('Segoe UI', 13, 'bold'),
                  background=BG).pack(side='left')
        self.total_label = ttk.Label(head, text='Total: 0', style='Badge.TLabel')
        self.folder_label = ttk.Label(head, text='Folders: 0', style='Badge.TLabel')
        self.registry_label = ttk.Label(head, text='Registry: 0', style='Badge.TLabel')
        self.tasks_label = ttk.Label(head, text='Tasks: 0', style='Badge.TLabel')
        self.disabled_label = ttk.Label(head, text='Disabled: 0', style='Badge.TLabel')
        for lbl in (self.total_label, self.folder_label, self.registry_label,
                    self.tasks_label, self.disabled_label):
            lbl.pack(side='left', padx=(6, 0))

        # Category chips + search (used to live in the global sidebar/header)
        chips = ttk.Frame(self.startup_tab, style='Content.TFrame')
        chips.pack(fill='x', padx=10, pady=(0, 6))
        self.cat_all = ttk.Button(chips, text='▦ All', style='Sidebar.TButton',
                                  command=lambda: self._set_category('All'))
        self.cat_folders = ttk.Button(chips, text='📁 Startup Folders', style='Sidebar.TButton',
                                      command=lambda: self._set_category('Folders'))
        self.cat_registry = ttk.Button(chips, text='🗝 Registry Run', style='Sidebar.TButton',
                                       command=lambda: self._set_category('Registry'))
        self.cat_tasks = ttk.Button(chips, text='⏱ Scheduled Tasks', style='Sidebar.TButton',
                                    command=lambda: self._set_category('Tasks'))
        self.cat_disabled = ttk.Button(chips, text='⏸ Disabled', style='Sidebar.TButton',
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
        search = ttk.Entry(chips, textvariable=self.search_var, width=30, style='Search.TEntry')
        search.pack(side='right')
        search.insert(0, SEARCH_PLACEHOLDER)
        search.config(foreground=PLACEHOLDER)
        search.bind('<FocusIn>', self._clear_search_placeholder)
        search.bind('<FocusOut>', self._restore_search_placeholder)
        search.bind('<KeyRelease>', lambda e: self._on_search(self.search_var.get()))
        search.bind('<Return>', lambda e: self._on_search(self.search_var.get()))
        self.search_entry = search
        self._add_tooltip(search, 'Search by name, location, or command text. (Ctrl+F)')

        container = ttk.Frame(self.startup_tab)
        container.pack(fill='both', expand=True, padx=10, pady=(0, 4))

        tree_frame = ttk.Frame(container)
        tree_frame.pack(fill='both', expand=True)
        cols = ('name', 'source', 'location', 'command')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        for col, label in (('name', 'Name'), ('source', 'Source'), ('location', 'Location'), ('command', 'Command')):
            self.tree.heading(col, text=label, command=lambda c=col: self._sort_column(c))
        self.tree.column('name', width=170, anchor='w')
        self.tree.column('source', width=110, anchor='center')
        self.tree.column('location', width=240, anchor='w')
        self.tree.column('command', width=410, anchor='w')
        self.tree.pack(fill='both', expand=True, side='left')
        self.tree.tag_configure('oddrow', background=CARD_BG)
        self.tree.tag_configure('evenrow', background=ROW_ALT)
        self.tree.bind('<<TreeviewSelect>>', self._on_row_select)
        self.startup_empty_hint = self._make_empty_hint(
            self.tree, 'No startup items to show.\nTry clearing the search or switching category.')

        vscroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        hscroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        vscroll.pack(side='right', fill='y')
        hscroll.pack(side='bottom', fill='x')

        detail_frame = ttk.Labelframe(container, text='Details', style='Detail.TLabelframe')
        detail_frame.pack(fill='x', pady=(8, 0))
        details_grid = ttk.Frame(detail_frame, style='Detail.TLabelframe')
        details_grid.pack(fill='x', padx=10, pady=10)
        self.detail_name = ttk.Label(details_grid, text='Name: —', style='CardInfo.TLabel')
        self.detail_source = ttk.Label(details_grid, text='Source: —', style='CardInfo.TLabel')
        self.detail_location = ttk.Label(details_grid, text='Location: —', style='CardInfo.TLabel')
        self.detail_command = ttk.Label(details_grid, text='Command: —', style='CardInfo.TLabel')
        self.detail_name.grid(row=0, column=0, sticky='w', padx=(0, 12), pady=2)
        self.detail_source.grid(row=0, column=1, sticky='w', padx=(0, 12), pady=2)
        self.detail_location.grid(row=1, column=0, sticky='w', padx=(0, 12), pady=2, columnspan=2)
        self.detail_command.grid(row=2, column=0, sticky='w', padx=(0, 12), pady=2, columnspan=2)
        self.detail_hint = ttk.Label(details_grid, text='', style='CardInfo.TLabel',
                                     foreground=ACCENT, wraplength=900, justify='left')
        self.detail_hint.grid(row=3, column=0, sticky='w', padx=(0, 12), pady=(6, 2), columnspan=2)
        self.copy_command_detail = ttk.Button(detail_frame, text='Copy Command', style='Action.TButton',
                                              command=self.copy_command)
        self.copy_command_detail.pack(anchor='e', padx=10, pady=(0, 8))

        startup_actions = ttk.Frame(container)
        startup_actions.pack(fill='x', padx=10, pady=(6, 10))
        self.refresh_btn = ttk.Button(startup_actions, text='Refresh', style='Action.TButton', command=self.refresh)
        self.refresh_btn.pack(side='left')
        self.enable_btn = ttk.Button(startup_actions, text='Enable Selected', style='Action.TButton',
                                     command=self.enable_selected)
        self.enable_btn.pack(side='left', padx=6)
        self.disable_btn = ttk.Button(startup_actions, text='Disable Selected', style='Action.TButton',
                                      command=self.disable_selected)
        self.disable_btn.pack(side='left', padx=6)
        self.copy_cmd_btn = ttk.Button(startup_actions, text='Copy Command', style='Action.TButton',
                                       command=self.copy_command)
        self.copy_cmd_btn.pack(side='left', padx=6)
        self.status_lbl = ttk.Label(startup_actions, text='', style='Info.TLabel')
        self.status_lbl.pack(side='right')

        self._add_tooltip(self.refresh_btn, 'Refresh the startup list from registry and startup folders.')
        self._add_tooltip(self.enable_btn, 'Enable the selected registry startup item.')
        self._add_tooltip(self.disable_btn, 'Disable the selected registry startup item.')
        self._add_tooltip(self.copy_cmd_btn, 'Copy the selected command text to clipboard.')
        self._add_tooltip(self.copy_command_detail, 'Copy the selected command from the detail panel.')

    def _build_cleaner_tab(self):
        header = ttk.Frame(self.cleanup_tab, style='Content.TFrame')
        header.pack(fill='x', padx=10, pady=10)
        ttk.Label(header, text='Cleaner', style='Header.TLabel').pack(anchor='w')
        ttk.Label(header, text='Scan configured folders and move reviewed files into custody.',
                  style='SubHeader.TLabel').pack(anchor='w', pady=(4, 0))

        summary = ttk.Frame(header, style='Content.TFrame')
        summary.pack(anchor='w', pady=(8, 0))
        self.cleanup_count_label = ttk.Label(summary, text='Candidates: 0', style='Badge.TLabel')
        self.cleanup_size_label = ttk.Label(summary, text='Reclaimable: 0B', style='Badge.TLabel')
        self.cleanup_archive_label = ttk.Label(summary, text='Archive: —', style='Badge.TLabel')
        self.cleanup_count_label.pack(side='left', padx=(0, 4))
        self.cleanup_size_label.pack(side='left', padx=(0, 4))
        self.cleanup_archive_label.pack(side='left')

        controls = ttk.Frame(self.cleanup_tab, style='Content.TFrame')
        controls.pack(fill='x', padx=10, pady=(0, 6))
        btn_row = ttk.Frame(controls, style='Content.TFrame')
        btn_row.pack(fill='x')
        self.scan_btn = ttk.Button(btn_row, text='Scan Now', style='Primary.TButton', command=self.refresh_cleanup)
        self.scan_btn.pack(side='left')
        self.apply_clean_btn = ttk.Button(btn_row, text='Archive & Clean', style='Primary.TButton',
                                          command=self.apply_cleanup)
        self.apply_clean_btn.pack(side='left', padx=6)
        self.dedupe_check = ttk.Checkbutton(btn_row, text='Deduplicate', variable=self.dedupe_enabled)
        self.dedupe_check.pack(side='left', padx=12)
        self.select_all_btn = ttk.Button(btn_row, text='Select All', style='Action.TButton',
                                         command=lambda: self._set_cleanup_selection(True))
        self.select_all_btn.pack(side='left', padx=(12, 0))
        self.select_none_btn = ttk.Button(btn_row, text='Select None', style='Action.TButton',
                                          command=lambda: self._set_cleanup_selection(False))
        self.select_none_btn.pack(side='left', padx=6)
        progress_row = ttk.Frame(controls, style='Content.TFrame')
        progress_row.pack(fill='x', pady=(6, 0))
        self.cleanup_progress = ttk.Progressbar(progress_row, mode='indeterminate', length=200)

        cleanup_frame = ttk.Frame(self.cleanup_tab)
        cleanup_frame.pack(fill='both', expand=True, padx=10, pady=(6, 10))
        cleanup_cols = ('sel', 'reason', 'size', 'path')
        self.cleanup_tree = ttk.Treeview(cleanup_frame, columns=cleanup_cols, show='headings', selectmode='browse')
        self.cleanup_tree.heading('sel', text='✓', command=self._toggle_all_cleanup_selection)
        self.cleanup_tree.heading('reason', text='Reason')
        self.cleanup_tree.heading('size', text='Size')
        self.cleanup_tree.heading('path', text='Path')
        self.cleanup_tree.column('sel', width=36, anchor='center', stretch=False)
        self.cleanup_tree.column('reason', width=120, anchor='w', stretch=False)
        self.cleanup_tree.column('size', width=90, anchor='center', stretch=False)
        self.cleanup_tree.column('path', width=400, anchor='w', stretch=True)
        self.cleanup_tree.pack(fill='both', expand=True, side='left')
        self.cleanup_tree.tag_configure('oddrow', background=CARD_BG)
        self.cleanup_tree.tag_configure('evenrow', background=ROW_ALT)
        self.cleanup_tree.bind('<Button-1>', self._on_cleanup_click)
        self.cleanup_tree.bind('<space>', self._on_cleanup_space)
        for reason, color in REASON_COLORS.items():
            self.cleanup_tree.tag_configure(f'reason:{reason}', foreground=color)
        self.cleanup_empty_hint = self._make_empty_hint(
            self.cleanup_tree, 'No cleanup candidates.\nClick "Scan Now" to search your configured folders.')
        self._refresh_empty_hint(self.cleanup_empty_hint, self.cleanup_tree)
        cleanup_vscroll = ttk.Scrollbar(cleanup_frame, orient='vertical', command=self.cleanup_tree.yview)
        cleanup_hscroll = ttk.Scrollbar(cleanup_frame, orient='horizontal', command=self.cleanup_tree.xview)
        self.cleanup_tree.configure(yscrollcommand=cleanup_vscroll.set, xscrollcommand=cleanup_hscroll.set)
        cleanup_vscroll.pack(side='right', fill='y')
        cleanup_hscroll.pack(side='bottom', fill='x')

        status = ttk.Frame(self.cleanup_tab)
        status.pack(fill='x', padx=10, pady=(0, 10))
        self.cleanup_status_lbl = ttk.Label(status, text='Ready to scan.', style='Info.TLabel')
        self.cleanup_status_lbl.pack(side='left')
        self._add_tooltip(self.scan_btn, 'Scan configured folders for cleanup candidates.')
        self._add_tooltip(self.apply_clean_btn, 'Archive the checked candidate files.')
        self._add_tooltip(self.dedupe_check, 'Enable duplicate detection before archiving.')
        self._add_tooltip(self.select_all_btn, 'Check every candidate for cleanup.')
        self._add_tooltip(self.select_none_btn, 'Uncheck every candidate.')

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
        self._add_tooltip(self.time_machine_btn,
                          'See every cleanup day at a glance and roll a whole day back.')
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
        left = ttk.Frame(restore_frame)
        self._restore_left = left
        left.pack(side='left', fill='both', expand=True)
        restore_cols = ('src', 'dest', 'time')
        self.restore_tree = ttk.Treeview(left, columns=restore_cols, show='headings', selectmode='browse')
        self.restore_tree.heading('src', text='Original Path')
        self.restore_tree.heading('dest', text='Archived Path')
        self.restore_tree.heading('time', text='Time')
        self.restore_tree.column('src', width=240, anchor='w', stretch=True, minwidth=120)
        self.restore_tree.column('dest', width=240, anchor='w', stretch=True, minwidth=120)
        self.restore_tree.column('time', width=140, anchor='center', stretch=False, minwidth=100)
        self.restore_tree.pack(fill='both', expand=True, side='left')
        self.restore_tree.tag_configure('oddrow', background=CARD_BG)
        self.restore_tree.tag_configure('evenrow', background=ROW_ALT)
        self.restore_empty_hint = self._make_empty_hint(
            self.restore_tree, 'No restore entries.\nArchived files appear here after a cleanup.')
        self._refresh_empty_hint(self.restore_empty_hint, self.restore_tree)
        restore_vscroll = ttk.Scrollbar(left, orient='vertical', command=self.restore_tree.yview)
        restore_hscroll = ttk.Scrollbar(left, orient='horizontal', command=self.restore_tree.xview)
        self.restore_tree.configure(yscrollcommand=restore_vscroll.set, xscrollcommand=restore_hscroll.set)
        restore_vscroll.pack(side='right', fill='y')
        restore_hscroll.pack(side='bottom', fill='x')

        right = ttk.Frame(restore_frame, width=320, style='Card.TFrame')
        self._restore_preview_panel = right
        right.pack(side='left', fill='y', padx=(8, 0))
        right.pack_propagate(False)
        self._restore_split_mode = 'wide'
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
        header = ttk.Frame(self.settings_tab, style='Content.TFrame')
        header.pack(fill='x', padx=10, pady=10)
        ttk.Label(header, text='Settings', style='Header.TLabel').pack(anchor='w')
        ttk.Label(header, text='Edit the cleanup configuration without leaving the app.',
                  style='SubHeader.TLabel').pack(anchor='w', pady=(4, 0))

        local_box = ctk_theme.frame(self.settings_tab, CARD_BG, corner_radius=10)
        local_box.pack(fill='x', padx=10, pady=(0, 10))
        ctk_theme.label(
            local_box, 'Local-only', text_color=ACCENT, font_size=13, weight='bold',
        ).pack(anchor='w', padx=14, pady=(12, 4))
        ctk_theme.label(
            local_box, ctk_theme.LOCAL_ONLY_TEXT, text_color=TEXT, font_size=11,
            wraplength=920, justify='left',
        ).pack(anchor='w', padx=14, pady=(0, 12))

        quick_box = ctk_theme.frame(self.settings_tab, CARD_BG, corner_radius=10)
        quick_box.pack(fill='x', padx=10, pady=(0, 10))
        ctk_theme.label(
            quick_box, 'Quick settings', text_color=ACCENT, font_size=13, weight='bold',
        ).pack(anchor='w', padx=14, pady=(12, 4))
        ctk_theme.label(
            quick_box,
            'Toggle common scan targets and behavior. Click Save Settings to apply.',
            text_color=MUTED, font_size=10,
        ).pack(anchor='w', padx=14, pady=(0, 8))

        self._settings_downloads_path = str(
            Path(os.environ.get('USERPROFILE', Path.home())) / 'Downloads')
        self._settings_temp_path = os.environ.get('TEMP') or str(
            Path(os.environ.get('USERPROFILE', Path.home())) / 'AppData' / 'Local' / 'Temp')

        self.set_scan_downloads = tk.BooleanVar(value=True)
        self.set_scan_temp = tk.BooleanVar(value=True)
        self.set_relaxed_scan = tk.BooleanVar(value=False)
        self.set_dedupe_default = self.dedupe_enabled

        quick_grid = ctk_theme.frame(quick_box, CARD_BG)
        quick_grid.pack(fill='x', padx=14, pady=(0, 12))
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
        self.set_power_var = tk.BooleanVar(value=bool(load_ui_prefs().get('power_user')))
        _quick_switch(2, 0, 'Power user mode (dense lists)', self.set_power_var)

        body = ttk.Frame(self.settings_tab, style='Content.TFrame')
        body.pack(fill='both', expand=True, padx=10)

        # Left: scan paths
        paths_box = ttk.Labelframe(body, text='What Cleanroom scans', style='Detail.TLabelframe')
        paths_box.pack(side='left', fill='both', expand=True, padx=(0, 8))
        self.set_paths_list = tk.Listbox(paths_box, height=6, activestyle='dotbox',
                                         font=('Segoe UI', 10), relief='flat',
                                         bg=PREVIEW_BG, fg=TEXT, selectbackground=ACCENT,
                                         selectforeground=ON_ACCENT,
                                         highlightthickness=1, highlightbackground=BORDER)
        self.set_paths_list.pack(fill='both', expand=True, padx=8, pady=(8, 4))
        path_btns = ttk.Frame(paths_box, style='Card.TFrame')
        path_btns.pack(fill='x', padx=8, pady=(0, 8))
        ttk.Button(path_btns, text='Add Folder…', style='Action.TButton',
                   command=self._settings_add_path).pack(side='left')
        ttk.Button(path_btns, text='Remove Selected', style='Action.TButton',
                   command=self._settings_remove_path).pack(side='left', padx=6)

        # Right: thresholds & archive
        opts_box = ttk.Labelframe(body, text='Where Cleanroom archives files', style='Detail.TLabelframe')
        opts_box.pack(side='left', fill='both', expand=True)
        grid = ttk.Frame(opts_box, style='Card.TFrame')
        grid.pack(fill='x', padx=8, pady=8)

        ttk.Label(grid, text='Archive folder:', style='CardInfo.TLabel').grid(row=0, column=0, sticky='w', pady=3)
        self.set_archive_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.set_archive_var, width=38, style='Search.TEntry').grid(row=0, column=1, sticky='we', pady=3)
        ttk.Button(grid, text='Browse…', style='Action.TButton',
                   command=self._settings_browse_archive).grid(row=0, column=2, padx=(6, 0), pady=3)

        self.set_temp_age = tk.IntVar(value=7)
        self.set_installer_age = tk.IntVar(value=30)
        self.set_size_mb = tk.IntVar(value=200)
        self.set_confirm_gb = tk.DoubleVar(value=5.0)
        self.set_ext_var = tk.StringVar()

        def spin_row(row, label, var, lo, hi, inc=1):
            ttk.Label(grid, text=label, style='CardInfo.TLabel').grid(row=row, column=0, sticky='w', pady=3)
            ttk.Spinbox(grid, from_=lo, to=hi, increment=inc, textvariable=var, width=10).grid(row=row, column=1, sticky='w', pady=3)

        spin_row(1, 'Temp files — archive after (days):', self.set_temp_age, 1, 365)
        spin_row(2, 'Installers — archive after (days):', self.set_installer_age, 1, 3650)
        spin_row(3, 'Large file threshold (MB):', self.set_size_mb, 1, 1024 * 100)
        spin_row(4, 'Confirm archive above (GB):', self.set_confirm_gb, 0.1, 1000, 0.5)
        ttk.Label(grid, text='When files become safe to archive', style='CardInfo.TLabel',
                  font=('Segoe UI', 9, 'bold')).grid(row=5, column=0, columnspan=3, sticky='w', pady=(8, 2))
        ttk.Label(grid, text='Archive extensions (comma-sep):', style='CardInfo.TLabel').grid(row=6, column=0, sticky='w', pady=3)
        ttk.Entry(grid, textvariable=self.set_ext_var, width=38, style='Search.TEntry').grid(row=6, column=1, columnspan=2, sticky='we', pady=3)

        ttk.Label(grid, text='Theme:', style='CardInfo.TLabel').grid(row=7, column=0, sticky='w', pady=(10, 3))
        self.set_theme_var = tk.StringVar(value=PALETTES[CURRENT_THEME]['LABEL'])
        theme_combo = ttk.Combobox(grid, textvariable=self.set_theme_var, state='readonly',
                                   values=[PALETTES[t]['LABEL'] for t in THEME_ORDER], width=20)
        theme_combo.grid(row=7, column=1, sticky='w', pady=(10, 3))

        def _apply_ui():
            prefs = load_ui_prefs()
            label = self.set_theme_var.get()
            for t in THEME_ORDER:
                if PALETTES[t]['LABEL'] == label:
                    prefs['theme'] = t
                    break
            prefs['power_user'] = bool(self.set_power_var.get())
            save_ui_prefs(prefs)
            apply_palette(prefs.get('theme', 'dark'))
            self.wants_restart = True
            self.destroy()

        apply_ui_btn = ttk.Button(grid, text='Save UI Settings', style='Action.TButton',
                                  command=_apply_ui)
        apply_ui_btn.grid(row=7, column=2, sticky='w', padx=(6, 0), pady=(10, 3))
        self._add_tooltip(apply_ui_btn, 'Applies instantly — the window rebuilds with the new look.')
        grid.columnconfigure(1, weight=1)

        # Patterns
        patterns = ttk.Frame(self.settings_tab, style='Content.TFrame')
        patterns.pack(fill='both', expand=True, padx=10, pady=(8, 0))
        excl_box = ttk.Labelframe(patterns, text='What Cleanroom must never touch (exclude patterns)', style='Detail.TLabelframe')
        excl_box.pack(side='left', fill='both', expand=True, padx=(0, 8))
        self.set_exclude_text = tk.Text(excl_box, height=4, font=('Consolas', 9), relief='flat',
                                        bg=PREVIEW_BG, fg=TEXT, insertbackground=TEXT,
                                        highlightthickness=1, highlightbackground=BORDER)
        self.set_exclude_text.pack(fill='both', expand=True, padx=8, pady=8)
        white_box = ttk.Labelframe(patterns, text='What Cleanroom must never touch (whitelist)', style='Detail.TLabelframe')
        white_box.pack(side='left', fill='both', expand=True)
        self.set_whitelist_text = tk.Text(white_box, height=4, font=('Consolas', 9), relief='flat',
                                          bg=PREVIEW_BG, fg=TEXT, insertbackground=TEXT,
                                          highlightthickness=1, highlightbackground=BORDER)
        self.set_whitelist_text.pack(fill='both', expand=True, padx=8, pady=8)

        # Footer
        footer = ttk.Frame(self.settings_tab, style='Content.TFrame')
        footer.pack(fill='x', padx=10, pady=10)
        self.save_settings_btn = ttk.Button(footer, text='Save Settings', style='Primary.TButton',
                                            command=self.save_settings)
        self.save_settings_btn.pack(side='left')
        ttk.Button(footer, text='Discard Changes', style='Action.TButton',
                   command=self.load_settings_form).pack(side='left', padx=6)
        self.settings_status_lbl = ttk.Label(footer, text='', style='Info.TLabel')
        self.settings_status_lbl.pack(side='left', padx=12)
        self._add_tooltip(self.save_settings_btn, 'Write these values to the active cleanup config.')

        self.load_settings_form()

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

    def _settings_remove_path(self):
        for idx in reversed(self.set_paths_list.curselection()):
            self.set_paths_list.delete(idx)

    def _settings_browse_archive(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            self.set_archive_var.set(str(Path(folder)))

    def load_settings_form(self):
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
        self.set_exclude_text.insert('1.0', '\n'.join(cfg.get('exclude_patterns', []) or []))
        self.set_whitelist_text.delete('1.0', 'end')
        self.set_whitelist_text.insert('1.0', '\n'.join(cfg.get('whitelist', []) or []))
        self.settings_status_lbl.config(text=self._config_status_label())

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
        })
        self.dedupe_enabled.set(bool(self.set_dedupe_default.get()))
        try:
            written_to = self._write_config(cfg)
        except Exception as e:
            messagebox.showerror('Settings', f'Unable to save settings:\n{e}')
            return
        self.settings_status_lbl.config(text='Cleanroom configuration saved')
        self._set_status('Settings saved. Re-scanning with new configuration...')
        self.refresh_cleanup()

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
        ttk.Checkbutton(bar, text='Silent uninstall when possible',
                        variable=self.uninst_quiet_var).pack(side='left', padx=6)
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

        wrap = ttk.Frame(self.uninstall_tab, style='Card.TFrame')
        wrap.pack(fill='both', expand=True, padx=10, pady=(0, 6))
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
            self.uninstall_tab,
            text='Program summary — local guidance (no web lookup)',
            style='Detail.TLabelframe',
        )
        detail_frame.pack(fill='x', padx=10, pady=(0, 6))
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
        self.uninst_status_lbl.config(text='Scanning installed programs…')

        def done(result, err):
            if err is not None:
                self.uninst_status_lbl.config(text=f'Failed to list programs: {err}')
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
        tree.delete(*tree.get_children())
        rows = self._visible_uninstall_rows()
        col = self._uninst_sort_col
        if col == 'size':
            rows.sort(key=lambda e: e['size_kb'], reverse=self._uninst_sort_desc)
        elif col == 'installed':
            rows.sort(key=lambda e: e['install_date'], reverse=self._uninst_sort_desc)
        elif col in ('name', 'publisher', 'version', 'key'):
            k = 'subkey' if col == 'key' else col
            rows.sort(key=lambda e: str(e.get(k, '')).lower(), reverse=self._uninst_sort_desc)
        total_kb = 0
        for i, e in enumerate(rows):
            total_kb += e['size_kb']
            idx = self.uninstall_entries.index(e)
            size = self._format_size(e['size_kb'] * 1024) if e['size_kb'] else ''
            check = '☑' if idx in self.uninst_checked else '☐'
            values = [check, e['name'], e['publisher'], e['version'], size, e['install_date']]
            if self.power_user:
                hive_short = 'HKLM' if 'LOCAL_MACHINE' in e.get('hive', '') else 'HKCU'
                values.append(f"{hive_short}\\…\\{e.get('subkey', '')}")
            values.append('🗑')
            tree.insert('', 'end', iid=str(idx), values=tuple(values),
                        tags=('evenrow' if i % 2 else 'oddrow',))
        checked_visible = sum(1 for e in rows
                              if self.uninstall_entries.index(e) in self.uninst_checked)
        label = f'{len(rows)} programs'
        if checked_visible:
            label += f' · {checked_visible} checked'
        self.uninst_count_lbl.config(text=label)
        self.uninst_size_lbl.config(
            text=self._format_size(total_kb * 1024) if total_kb else '')
        if rows:
            self.uninst_empty_hint.place_forget()
        else:
            self.uninst_empty_hint.place(relx=0.5, rely=0.4, anchor='center')

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
        self._ensure_uninstall_context_menu()
        menu = self._uninst_context_menu
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
        for idx, enabled in (
            (0, has_entry), (1, has_entry), (2, has_entry),
            (4, has_entry), (5, True), (6, True),
            (8, has_entry), (9, has_cmd), (10, has_key),
            (12, True),
        ):
            menu.entryconfig(idx, state='normal' if enabled else 'disabled')
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
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
        dlg = tk.Toplevel(self)
        dlg.configure(bg=BG)
        dlg.title('Force removal' if force_remove else 'Leftovers found')
        dlg.geometry('680x440')
        dlg.transient(self)
        dlg.grab_set()
        dlg.bind('<Escape>', lambda e: dlg.destroy())

        title = ('Force removal' if force_remove else 'Leftovers') + f' — "{program_name}"'
        ttk.Label(dlg, text=title,
                  font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=14, pady=(14, 2))
        if program_advice:
            advice = program_advice.analyze_program(entry)
            ttk.Label(dlg, text=advice['need'], style='Info.TLabel',
                      wraplength=640).pack(anchor='w', padx=14, pady=(0, 4))
        note = ('Checked folders are MOVED to the archive (not deleted). Checked registry '
                'keys are EXPORTED to a .reg file in the archive before removal. Both can '
                'be restored from the Restore tab or Cleanroom Rewind.')
        if force_remove:
            note += ' The orphaned Programs-list entry is removed afterwards (.reg backup).'
        ttk.Label(dlg, text=note,
                  style='Info.TLabel', wraplength=640).pack(anchor='w', padx=14, pady=(0, 8))

        body = ttk.Frame(dlg, style='Card.TFrame')
        body.pack(fill='both', expand=True, padx=14, pady=(0, 8))
        canvas = tk.Canvas(body, bg=CARD_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(body, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas, style='Card.TFrame')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

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

        footer = ttk.Frame(dlg, style='Content.TFrame')
        footer.pack(fill='x', padx=14, pady=(0, 12))

        def do_archive():
            chosen_dirs = [p for var, kind, p in check_vars if var.get() and kind == 'dir']
            chosen_keys = [p for var, kind, p in check_vars if var.get() and kind == 'reg']
            dlg.destroy()
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
                messagebox.showinfo('Force remove' if force_remove else 'Leftovers', summary)
                self.refresh_restore()
                if force_remove:
                    self.refresh_uninstaller()

            self._run_bg(work, done)

        btn_label = 'Archive & force remove' if force_remove else 'Archive selected'
        ttk.Button(footer, text=btn_label, style='Primary.TButton',
                   command=do_archive).pack(side='right')
        ttk.Button(footer, text='Cancel', style='Action.TButton',
                   command=dlg.destroy).pack(side='right', padx=(0, 8))

    # ------------------------------------------------------------------
    # Keyboard shortcuts / accessibility
    # ------------------------------------------------------------------
    def _bind_shortcuts(self):
        self.bind('<F5>', lambda e: self._refresh_all())
        self.bind('<Control-f>', lambda e: self._focus_search())
        self.bind('<Control-F>', lambda e: self._focus_search())
        for i in range(7):
            self.bind(f'<Control-Key-{i + 1}>', lambda e, idx=i: self.tab_control.select(idx))

    def _refresh_all(self):
        self.refresh()
        self.refresh_cleanup()
        self.refresh_restore()
        self.refresh_activity()

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
                done, result, err = self._bg_queue.get_nowait()
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

    def _set_status(self, text, *, pulse=False):
        try:
            self.global_status.config(text=text)
            if pulse and not animations_disabled():
                self.global_status.config(fg=ACCENT)
                self.after(420, lambda: self.global_status.config(fg=TEXT))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Empty-state hints (centered label shown when a tree has no rows)
    # ------------------------------------------------------------------
    def _make_empty_hint(self, tree, text):
        return tk.Label(tree, text=text, bg=CARD_BG, fg=MUTED,
                        font=('Segoe UI', 10, 'italic'), justify='center')

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

    def _sort_column(self, col):
        reverse = self.current_sort[0] == col and not self.current_sort[1]
        self.current_sort = (col, reverse)
        self._apply_filter()

    def _apply_filter(self):
        q = self.search_text.lower()
        self.tree.delete(*self.tree.get_children())

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
        rows.sort(key=lambda item: (item.get(key) or '').lower(), reverse=self.current_sort[1])
        for idx, v in enumerate(rows):
            tag = 'evenrow' if idx % 2 else 'oddrow'
            self.tree.insert('', 'end', values=(v['name'], v['source'], v['location'], v['command']), tags=(tag,))
        self._refresh_empty_hint(self.startup_empty_hint, self.tree)
        self._update_context_panel()

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

    def refresh_cleanup(self):
        cfg = self._load_cleanup_config()
        if cfg is None:
            return

        self.scan_btn.config(state='disabled')
        self.tb_scan.configure(state='disabled')
        self.cleanup_status_lbl.config(text='Scanning...')
        self._set_status('Scanning configured folders for cleanup candidates...')
        self.cleanup_progress.pack(side='left', padx=12)
        self.cleanup_progress.start(12)

        def done(items, err):
            self.cleanup_progress.stop()
            self.cleanup_progress.pack_forget()
            self.scan_btn.config(state='normal')
            self.tb_scan.configure(state='normal')
            if err is not None:
                self.cleanup_status_lbl.config(text=f'Scan failed: {err}')
                self._set_status('Scan failed.')
                return
            self.cleanup_items = items
            self.cleanup_selected = set(range(len(items)))  # everything checked by default
            self.cleanup_total_size = sum(item.get('size', 0) for item in items)
            self._last_cfg = cfg
            self._update_cleanup_summary(cfg)
            self._update_cleanup_tree()
            self.refresh_optimizer()
            self.cleanup_status_lbl.config(text=f'Found {len(items)} candidate(s) across configured paths.')
            self._set_status(f'Scan complete — {len(items)} candidate(s).', pulse=True)
            self._update_context_panel()
            self._set_status(f'Scan complete: {len(items)} candidate(s), {self._format_size(self.cleanup_total_size)} reclaimable.')

        self._run_bg(lambda: cleanup_main.scan_candidates(cfg), done)

    def _format_size(self, bytes_value):
        if cleanup_main:
            return cleanup_main.human_size(bytes_value)
        return f'{bytes_value}B'

    def _update_cleanup_summary(self, cfg=None):
        selected_size = sum(self.cleanup_items[i].get('size', 0) for i in self.cleanup_selected
                            if 0 <= i < len(self.cleanup_items))
        self.cleanup_count_label.config(
            text=f'Candidates: {len(self.cleanup_items)} ({len(self.cleanup_selected)} checked)')
        self.cleanup_size_label.config(text=f'Reclaimable: {self._format_size(selected_size)} checked')
        self._refresh_header_proof_badges()
        archive = (cfg or {}).get('archive_dir') if cfg else None
        self.cleanup_archive_label.config(text=f'Archive: {archive or "auto (next to app)"}')

    def _update_cleanup_tree(self):
        self.cleanup_tree.delete(*self.cleanup_tree.get_children())
        for idx, item in enumerate(self.cleanup_items):
            stripe = 'evenrow' if idx % 2 else 'oddrow'
            reason = item.get('reason') or ''
            mark = '☑' if idx in self.cleanup_selected else '☐'
            self.cleanup_tree.insert('', 'end', values=(mark, reason,
                                                        self._format_size(item.get('size', 0)),
                                                        item.get('path')),
                                     tags=(stripe, f'reason:{reason}'))
        self._refresh_empty_hint(self.cleanup_empty_hint, self.cleanup_tree)

    def _toggle_cleanup_index(self, idx):
        if idx in self.cleanup_selected:
            self.cleanup_selected.discard(idx)
        else:
            self.cleanup_selected.add(idx)
        row = self.cleanup_tree.get_children()[idx]
        self.cleanup_tree.set(row, 'sel', '☑' if idx in self.cleanup_selected else '☐')
        self._update_cleanup_summary(self._cached_cfg())

    def _cached_cfg(self):
        return getattr(self, '_last_cfg', None)

    def _on_cleanup_click(self, event):
        if self.cleanup_tree.identify_region(event.x, event.y) != 'cell':
            return
        if self.cleanup_tree.identify_column(event.x) != '#1':
            return
        row = self.cleanup_tree.identify_row(event.y)
        if row:
            self._toggle_cleanup_index(self.cleanup_tree.index(row))

    def _on_cleanup_space(self, event):
        sel = self.cleanup_tree.selection()
        if sel:
            self._toggle_cleanup_index(self.cleanup_tree.index(sel[0]))
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
        actions = []
        if self.restore_log_path.exists() and restore_module:
            try:
                actions = restore_module.load_log(str(self.restore_log_path))
            except Exception:
                actions = []
        feed = ledger_module.build_activity_feed(actions)
        self._activity_feed = feed
        entries = self._load_log_dicts()
        custody = proof_module.verify_entries(entries)
        summary = ledger_module.summarize_feed(feed)
        trust = ledger_module.trust_score(custody['verified'], custody['total'])
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
        self.act_status_lbl.config(
            text=f'Custody trust {trust}%' if custody['total'] else 'Awaiting first action')
        self._refresh_header_proof_badges()

        tree = self.activity_tree
        tree.delete(*tree.get_children())
        for i, e in enumerate(feed):
            if e.get('kind') == 'restore':
                continue
            when = (e.get('when') or '')[:19].replace('T', ' ')
            tag = 'present' if e.get('present') else 'missing'
            if e.get('kind') == 'prune':
                tag = 'missing'
            tree.insert('', 'end', iid=str(i),
                        values=('✓' if e.get('present') else '✗', when,
                                e.get('reason', ''), e.get('src', ''),
                                self._format_size(e.get('size', 0))),
                        tags=(tag,))
        if any(e.get('kind') not in ('restore',) for e in feed):
            self.activity_empty.place_forget()
        else:
            self.activity_empty.place(relx=0.5, rely=0.4, anchor='center')
        self.refresh_archive_browser()

    def open_archive_browser_tab(self):
        self.tab_control.select(self.activity_tab)
        if hasattr(self, 'act_sub_notebook'):
            self.act_sub_notebook.select(1)
        self.refresh_archive_browser()

    def refresh_archive_browser(self):
        if archive_custody is None or restore_module is None:
            return
        actions = []
        if self.restore_log_path.exists():
            try:
                actions = restore_module.load_log(str(self.restore_log_path))
            except Exception:
                actions = []
        cfg = self._load_cleanup_config() or {}
        receipt_dir = brand.user_data_dir() / 'receipts'
        records = archive_custody.build_archive_records(actions, receipt_dir=receipt_dir, config=cfg)
        rank_filter = getattr(self, '_archive_prune_filter', None)
        filt = rank_filter.get() if rank_filter else ''
        if filt:
            records = archive_custody.filter_by_prune_rank(records, filt)
        self._archive_records = records

        tree = self.archive_tree
        tree.delete(*tree.get_children())
        rank_tags = {
            archive_custody.PRUNE_SAFE: 'safe',
            archive_custody.PRUNE_REVIEW: 'review',
            archive_custody.PRUNE_KEEP: 'keep',
        }
        for i, rec in enumerate(records):
            when = (rec.get('when') or '')[:19].replace('T', ' ')
            rp = rec.get('receipt_path')
            tree.insert('', 'end', iid=str(i),
                        values=(
                            when,
                            rec.get('src', ''),
                            rec.get('dest', ''),
                            rec.get('reason', ''),
                            self._format_size(rec.get('size', 0)),
                            'Yes' if rec.get('restorable') else 'No',
                            'Yes' if rp else '—',
                            rec.get('prune_rank', ''),
                        ),
                        tags=(rank_tags.get(rec.get('prune_rank'), 'review'),))
        if records:
            self.archive_empty.place_forget()
        else:
            self.archive_empty.place(relx=0.5, rely=0.4, anchor='center')
        safe_n = sum(1 for r in records if r.get('prune_rank') == archive_custody.PRUNE_SAFE)
        self.archive_status_lbl.config(
            text=f'{len(records)} archive record(s) · {safe_n} marked Safe to prune (local rules only)')

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

    def _view_receipt_file(self, path, preview=False):
        if receipts_module is None:
            messagebox.showerror('Receipt', 'Receipts module unavailable.')
            return
        try:
            body = receipts_module.read_receipt(path)
        except Exception as e:
            messagebox.showerror('Receipt', f'Unable to read receipt:\n{e}')
            return
        if show_receipt:
            show_receipt(self, body, receipt_path=path, preview=preview,
                         bg=BG, card=CARD_BG, text_fg=TEXT)
        else:
            self._show_text_dialog('Cleanroom Receipt', body)

    def confirm_prune_selected(self):
        if archive_custody is None:
            messagebox.showerror('Prune', 'Archive custody module unavailable.')
            return
        recs = self._selected_archive_records()
        if not recs:
            messagebox.showinfo('Archive Prune Recommendations',
                                'Select archived file(s) to prune from custody.')
            return
        lines = [f'{self._format_size(r.get("size", 0))}  {r.get("dest")}' for r in recs[:15]]
        if len(recs) > 15:
            lines.append(f'… and {len(recs) - 15} more')
        msg = (
            'This permanently removes selected files from Cleanroom\'s archive.\n'
            'Original live files are not touched.\n'
            'Restoring these archived copies will no longer be possible after pruning.\n\n'
            + '\n'.join(lines)
        )
        if not messagebox.askokcancel('Archive Prune Recommendations', msg):
            return
        if not messagebox.askokcancel(
                'Confirm Prune',
                f'Prune {len(recs)} archived file(s) from custody?\n\n'
                'This cannot be undone. A Prune Receipt will be written.'):
            return

        log_path = self.restore_log_path

        def work():
            return archive_custody.apply_prune(
                recs, log_path, receipt_dir=brand.user_data_dir() / 'receipts', dry_run=False)

        def done(result, err):
            if err is not None:
                messagebox.showerror('Prune', str(err))
                return
            n = len(result.get('pruned', []))
            freed = self._format_size(result.get('bytes_pruned', 0))
            rp = result.get('receipt_path')
            messagebox.showinfo('Prune Receipt',
                                f'Pruned {n} archived file(s) ({freed}) from custody.\n'
                                f'Original live files were not touched.')
            if rp and Path(rp).is_file():
                self._view_receipt_file(rp)
            self.refresh_activity()
            self.refresh_restore()

        self._run_bg(work, done)

    def prune_archive_dialog(self):
        """Legacy entry — open Archive Browser with Safe to prune filter."""
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
        """Visual proof screen — replaces the fake '1,247 issues fixed!' popup."""
        dlg = tk.Toplevel(self)
        dlg.configure(bg=BG)
        dlg.title('Cleanroom Proof Report')
        dlg.geometry('560x480')
        dlg.transient(self)
        dlg.grab_set()
        dlg.bind('<Escape>', lambda e: dlg.destroy())

        head_row = ttk.Frame(dlg, style='Content.TFrame')
        head_row.pack(fill='x', padx=16, pady=(12, 0))
        logo = self._load_logo(40)
        if logo is not None:
            self._proof_logo = logo
            ttk.Label(head_row, image=logo, background=BG).pack(side='left', padx=(0, 8))
        title_col = ttk.Frame(head_row, style='Content.TFrame')
        title_col.pack(side='left', fill='x', expand=True)

        c = prf.get('custody') or {}
        ok = c.get('missing', 0) == 0 and c.get('total', 0) > 0
        head_color = ACCENT if ok else SEVERITY_COLORS['medium']
        head_txt = 'CUSTODY VERIFIED ✓' if ok else 'ARCHIVED WITH PROOF'

        ttk.Label(title_col, text=head_txt, font=('Segoe UI', 16, 'bold'),
                  foreground=head_color).pack(anchor='w')
        ttk.Label(title_col, text=brand.APP_MOTTO, style='Info.TLabel').pack(anchor='w', pady=(2, 0))
        ttk.Label(dlg, text='Measured by Windows — not estimated. Every item is in the archive.',
                  style='Info.TLabel', wraplength=520).pack(anchor='w', padx=16, pady=(8, 12))

        grid = ttk.Frame(dlg, style='Content.TFrame')
        grid.pack(fill='both', expand=True, padx=16, pady=(0, 8))

        def _card(parent, title, value, sub=''):
            f = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
            f.pack(side='left', fill='both', expand=True, padx=4, pady=4)
            tk.Label(f, text=title, bg=CARD_BG, fg=MUTED, font=('Segoe UI', 8, 'bold')).pack(
                anchor='w', padx=10, pady=(10, 2))
            tk.Label(f, text=value, bg=CARD_BG, fg=TEXT, font=('Segoe UI', 16, 'bold')).pack(
                anchor='w', padx=10)
            if sub:
                tk.Label(f, text=sub, bg=CARD_BG, fg=MUTED, font=('Segoe UI', 8)).pack(
                    anchor='w', padx=10, pady=(0, 10))

        row1 = tk.Frame(grid, bg=BG)
        row1.pack(fill='x')
        moved = sum(int(e.get('size') or 0) for e in log)
        _card(row1, 'ITEMS ARCHIVED', str(len(log)))
        _card(row1, 'SPACE MOVED', self._format_size(moved), 'to archive — not deleted')

        row2 = tk.Frame(grid, bg=BG)
        row2.pack(fill='x', pady=(8, 0))
        if proof_module:
            before = proof_module._human(prf.get('before_free', 0))
            after = proof_module._human(prf.get('after_free', 0))
            delta = proof_module._human(prf.get('measured_delta', 0))
            _card(row2, 'FREE BEFORE', before)
            _card(row2, 'FREE AFTER', after)
            _card(row2, 'OS MEASURED Δ', delta)

        row3 = tk.Frame(grid, bg=BG)
        row3.pack(fill='x', pady=(8, 0))
        _card(row3, 'CUSTODY CHECK', f"{c.get('verified', 0)}/{c.get('total', 0)}",
              'verified on disk right now')
        if days_bought and days_bought >= 1:
            _card(row3, 'DISK LIFE BOUGHT', f'~{days_bought:.0f} days', 'from Disk Foresight trend')
        elif dup_count:
            _card(row3, 'DUPLICATES', str(dup_count), 'separated into archive')

        note = ('Files were MOVED to the archive on the same drive — free space barely '
                'changes until you prune. That is honest; other cleaners lie about this.')
        if prf.get('measured_delta', 0) < moved // 2:
            ttk.Label(dlg, text=note, style='Info.TLabel', wraplength=520).pack(
                anchor='w', padx=16, pady=(8, 0))

        btns = ttk.Frame(dlg, style='Content.TFrame')
        btns.pack(fill='x', padx=16, pady=12)
        if receipt_path:
            ttk.Button(btns, text='Open Receipt', style='Action.TButton',
                       command=lambda: self._view_receipt_file(receipt_path)).pack(side='left')
        ttk.Button(btns, text='View Activity Ledger', style='Action.TButton',
                   command=lambda: (dlg.destroy(), self.tab_control.select(self.activity_tab),
                                    self.refresh_activity())).pack(side='left', padx=6)
        ttk.Button(btns, text='Done', style='Primary.TButton',
                   command=dlg.destroy).pack(side='right')
        dlg.bind('<Return>', lambda e: dlg.destroy())
        self._last_proof_report = dlg  # E2E hook

    def open_last_receipt(self):
        if receipts_module is None:
            messagebox.showerror('Receipt', 'Receipts module unavailable.')
            return
        path = receipts_module.latest_receipt()
        if path is None:
            messagebox.showinfo('Receipt', 'No receipts yet — run a cleanup first.')
            return
        self._view_receipt_file(path)

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
            messagebox.showinfo('Verify Custody',
                                'Nothing to verify yet — the cleanup log is empty.')
            return
        self._set_status(f'Verifying custody of {len(entries)} archived item(s)…')

        def done(result, err):
            self._set_status('Ready')
            if err is not None:
                messagebox.showerror('Verify Custody', f'Verification failed: {err}')
                return
            ok = result['missing'] == 0
            head = ('CUSTODY VERIFIED ✓' if ok else 'CUSTODY CHECK FAILED')
            body = (f"{result['verified']}/{result['total']} archived item(s) are "
                    f"present on disk right now "
                    f"({self._format_size(result['bytes_in_custody'])} in custody).\n\n")
            if ok:
                body += ('Every file and registry key Cleanroom has ever archived '
                         'is still where the log says it is — all of it restorable. '
                         'No other cleaner can show you this.')
                messagebox.showinfo(f'Verify Custody — {head}', body)
            else:
                sample = '\n'.join(result['missing_items'][:8])
                body += (f"{result['missing']} item(s) missing from the archive — "
                         'usually files removed by "Prune Archive" or moved/deleted '
                         f'outside Cleanroom:\n\n{sample}')
                messagebox.showwarning(f'Verify Custody — {head}', body)
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
                messagebox.showinfo('Registry Snapshot',
                                    'No issues found — every startup ref, App Paths entry '
                                    'and uninstaller this scan can verify points to a real file.')
                return
            self._show_registry_health_dialog(result)

        self._run_bg(registry_health.find_registry_issues, done)

    def _show_registry_health_dialog(self, issues):
        dlg = tk.Toplevel(self)
        dlg.configure(bg=BG)
        dlg.title('Registry Snapshot')
        dlg.geometry('720x420')
        dlg.transient(self)
        dlg.grab_set()
        dlg.bind('<Escape>', lambda e: dlg.destroy())

        ttk.Label(dlg, text=f'Registry Snapshot — {len(issues)} issue(s) found',
                  font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=14, pady=(14, 2))
        ttk.Label(dlg, text='Only entries that verifiably point to missing files are listed. '
                            'Checked items are EXPORTED to .reg backups in the archive before '
                            'removal — restorable from the Restore tab or Cleanroom Rewind. '
                            'HKLM items need admin rights.',
                  style='Info.TLabel', wraplength=680).pack(anchor='w', padx=14, pady=(0, 8))

        body = ttk.Frame(dlg, style='Card.TFrame')
        body.pack(fill='both', expand=True, padx=14, pady=(0, 8))
        canvas = tk.Canvas(body, bg=CARD_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(body, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas, style='Card.TFrame')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

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

        btns = ttk.Frame(dlg, style='Content.TFrame')
        btns.pack(fill='x', padx=14, pady=(0, 12))
        ttk.Button(btns, text='Cancel', style='Action.TButton',
                   command=dlg.destroy).pack(side='right')

        def repair():
            chosen = [issue for var, issue in check_vars if var.get()]
            dlg.destroy()
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
                messagebox.showinfo('Registry Snapshot', msg)
                self.refresh_restore()
                self.refresh_uninstaller()

            self._run_bg(work, done)

        repair_btn = ttk.Button(btns, text='Repair (Archive First)', style='Primary.TButton',
                                command=repair)
        repair_btn.pack(side='right', padx=6)
        self._reg_health_repair = repair  # E2E hook
        dlg.bind('<Return>', lambda e: repair())

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

        dlg = tk.Toplevel(self)
        dlg.configure(bg=BG)
        dlg.title('Cleanroom Rewind')
        dlg.geometry('760x440')
        dlg.transient(self)
        dlg.grab_set()
        dlg.bind('<Escape>', lambda e: dlg.destroy())

        ttk.Label(dlg, text='🕐 Cleanroom Rewind', font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=14, pady=(14, 2))
        ttk.Label(dlg, text='Every archive-first action grouped by day. Pick a day and roll the whole '
                            'thing back — files return to their original locations.',
                  style='Info.TLabel', wraplength=720).pack(anchor='w', padx=14, pady=(0, 8))

        wrap = ttk.Frame(dlg, style='Card.TFrame')
        wrap.pack(fill='both', expand=True, padx=14, pady=(0, 8))
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

        footer = ttk.Frame(dlg, style='Content.TFrame')
        footer.pack(fill='x', padx=14, pady=(0, 12))
        status_lbl = ttk.Label(footer, text='', style='Info.TLabel')

        def do_rollback():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo('Cleanroom Rewind', 'Select a day first.', parent=dlg)
                return
            bucket = buckets[int(sel[0])]
            if bucket['restorable'] == 0:
                messagebox.showinfo('Cleanroom Rewind',
                                    'Nothing from that day is still in the archive.', parent=dlg)
                return
            if not messagebox.askyesno(
                    'Cleanroom Rewind',
                    f"Roll back {bucket['date']}?\n\n{bucket['restorable']} item(s) will be moved "
                    'from the archive back to their original locations.', parent=dlg):
                return
            rollback_btn.config(state='disabled')
            status_lbl.config(text=f"Rolling back {bucket['date']}…")

            def work():
                return timeline_module.rollback_day(
                    bucket, lambda s, d: self._smart_restore(s, d, apply=True))

            def done(result, err):
                rollback_btn.config(state='normal')
                if err is not None:
                    status_lbl.config(text='Rollback failed.')
                    messagebox.showerror('Cleanroom Rewind', f'Rollback failed: {err}', parent=dlg)
                    return
                restored, skipped, failed, msgs = result
                status_lbl.config(text=f'Restored {restored}, skipped {skipped}, failed {failed}.')
                summary = f'Restored {restored} item(s).'
                if skipped:
                    summary += f'\n{skipped} skipped (no longer in archive).'
                if failed:
                    summary += f'\n{failed} failed:\n' + '\n'.join(msgs[:5])
                messagebox.showinfo('Cleanroom Rewind', summary, parent=dlg)
                self.refresh_restore()

            self._run_bg(work, done)

        rollback_btn = ttk.Button(footer, text='Roll Back This Day', style='Primary.TButton',
                                  command=do_rollback)
        rollback_btn.pack(side='left')
        ttk.Button(footer, text='Close', style='Action.TButton',
                   command=dlg.destroy).pack(side='left', padx=6)
        status_lbl.pack(side='left', padx=10)

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
            return
        self.restore_status_lbl.config(text='Loading restore log...')
        entries = self._load_restore_log()
        if entries is None:
            return
        filter_text = self.restore_filter_var.get().strip().lower()
        if filter_text:
            entries = [e for e in entries if filter_text in (e[0] or '').lower() or filter_text in (e[1] or '').lower()]
        self.restore_entries = entries
        self._update_restore_tree()
        self.refresh_optimizer()
        self.refresh_activity()
        self.restore_status_lbl.config(text=f'Loaded {len(entries)} restore entries.')

    def _update_restore_tree(self):
        self.restore_tree.delete(*self.restore_tree.get_children())
        for idx, (src, dest, ts, entry) in enumerate(self.restore_entries):
            tag = 'evenrow' if idx % 2 else 'oddrow'
            self.restore_tree.insert('', 'end', values=(src, dest, ts or ''), tags=(tag,))
        self._refresh_empty_hint(self.restore_empty_hint, self.restore_tree)

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
                    self._show_preview_photo(PILImageTk.PhotoImage(img))
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
    # Review tab / recommendations
    # ------------------------------------------------------------------
    def refresh_optimizer(self):
        folder_count = len(self.data.get('folders', []))
        registry_count = len(self.data.get('registry', []))
        startup_count = folder_count + registry_count
        cleanup_count = len(self.cleanup_items)
        reason_counts = {}
        for item in self.cleanup_items:
            reason = item.get('reason') or 'other'
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if rec_engine:
            recs = rec_engine.build_recommendations(
                folder_count=folder_count,
                registry_count=registry_count,
                cleanup_count=cleanup_count,
                cleanup_bytes=self.cleanup_total_size,
                restore_count=len(self.restore_entries),
                reason_counts=reason_counts)
        else:
            recs = []

        review_count = cleanup_count
        if review_count == 0:
            tone, band_text = ACCENT, 'Nothing pending'
        elif review_count < 10:
            tone, band_text = SEVERITY_COLORS['low'], f'{review_count} to archive'
        elif review_count < 30:
            tone, band_text = SEVERITY_COLORS['medium'], f'{review_count} to archive'
        else:
            tone, band_text = SEVERITY_COLORS['high'], f'{review_count} to archive'

        self._draw_review_gauge(review_count, tone)
        self.health_band_lbl.config(text=band_text, fg=tone)
        self.stat_startup_value.config(text=str(startup_count))
        self.stat_cleanup_value.config(text=str(cleanup_count))
        self.stat_size_value.config(text=self._format_size(self.cleanup_total_size))

        self.rec_tree.delete(*self.rec_tree.get_children())
        for r in recs:
            self.rec_tree.insert('', 'end',
                                 values=(r['severity'].upper(), r['title'], r['detail']),
                                 tags=(r['severity'],))
        self._refresh_empty_hint(self.rec_empty_hint, self.rec_tree)

        self.refresh_foresight()
        self._refresh_header_proof_badges()

        try:
            if enable_telemetry and enable_telemetry.is_opted_in():
                self.telemetry_btn.config(text='Telemetry (On)')
            else:
                self.telemetry_btn.config(text='Telemetry')
        except Exception:
            pass

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

        dialog = tk.Toplevel(self)
        dialog.configure(bg=BG)
        dialog.title('Schedule Cleanup')
        dialog.geometry('420x360')
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.bind('<Escape>', lambda e: dialog.destroy())

        ttk.Label(dialog, text='Schedule recurring cleanup', font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=16, pady=(14, 2))
        ttk.Label(dialog, text='Creates a Windows scheduled task named CleanroomDaily that runs Cleanroom non-interactively.',
                  style='Info.TLabel', wraplength=380).pack(anchor='w', padx=16, pady=(0, 10))

        # Time picker
        time_row = ttk.Frame(dialog)
        time_row.pack(anchor='w', padx=16, pady=(0, 8))
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
        recur_row = ttk.Frame(dialog)
        recur_row.pack(anchor='w', padx=16, pady=(0, 8))
        ttk.Label(recur_row, text='Repeat:').pack(side='left', padx=(0, 8))
        recur_var = tk.StringVar(value='Daily')
        recur_combo = ttk.Combobox(recur_row, textvariable=recur_var, state='readonly',
                                   values=('Daily', 'Weekly'), width=10)
        recur_combo.pack(side='left')

        # Weekday selection (enabled only for weekly)
        days_frame = ttk.Labelframe(dialog, text='Days (weekly)')
        days_frame.pack(fill='x', padx=16, pady=(0, 8))
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
        ttk.Checkbutton(dialog, text='Deduplicate files during scheduled runs', variable=dedupe_var).pack(anchor='w', padx=16, pady=(2, 0))

        status_lbl = ttk.Label(dialog, text='', style='Info.TLabel', wraplength=380)
        status_lbl.pack(anchor='w', padx=16, pady=(8, 0))

        btns = ttk.Frame(dialog)
        btns.pack(side='bottom', fill='x', padx=16, pady=14)

        def on_schedule():
            time_value = f'{int(hour_var.get()):02d}:{int(minute_var.get()):02d}'
            schedule = 'WEEKLY' if recur_var.get() == 'Weekly' else 'DAILY'
            days = ','.join(code for code, var in day_vars.items() if var.get())
            if schedule == 'WEEKLY' and not days:
                messagebox.showwarning('Schedule', 'Select at least one weekday.', parent=dialog)
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

            schedule_btn.config(state='disabled')
            status_lbl.config(text='Creating scheduled task...')

            def work():
                return subprocess.run(args, capture_output=True, text=True)

            def done(result, err):
                if not dialog.winfo_exists():
                    return
                schedule_btn.config(state='normal')
                if err is not None:
                    status_lbl.config(text='')
                    messagebox.showerror('Schedule failed', f'Unable to schedule optimization:\n{err}', parent=dialog)
                    return
                if result.returncode == 0:
                    when = f'{recur_var.get().lower()} at {time_value}' + (f' on {days}' if schedule == 'WEEKLY' else '')
                    self._set_status(f'Scheduled optimization {when}.')
                    messagebox.showinfo('Schedule', f'Scheduled optimization {when}.', parent=dialog)
                    dialog.destroy()
                else:
                    status_lbl.config(text='')
                    messagebox.showerror('Schedule failed', result.stderr or result.stdout or 'Unknown error', parent=dialog)

            self._run_bg(work, done)

        schedule_btn = ttk.Button(btns, text='Schedule', style='Primary.TButton', command=on_schedule)
        schedule_btn.pack(side='right')
        ttk.Button(btns, text='Cancel', style='Action.TButton', command=dialog.destroy).pack(side='right', padx=(0, 6))
        hour_spin.focus_set()

    # ------------------------------------------------------------------
    # Telemetry dialog
    # ------------------------------------------------------------------
    def _show_telemetry_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.configure(bg=BG)
        dlg.title('Telemetry settings')
        dlg.geometry('420x220')
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.bind('<Escape>', lambda e: dlg.destroy())

        ttk.Label(dlg, text='Telemetry (opt-in)', font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=12, pady=(12, 4))
        ttk.Label(dlg, text='We collect minimal anonymous usage metrics to improve Cleanroom (no personal files). Opt-in is local and can be turned off anytime.',
                  style='Info.TLabel', wraplength=400).pack(anchor='w', padx=12)
        var = tk.BooleanVar(value=False)
        try:
            if enable_telemetry and enable_telemetry.is_opted_in():
                var.set(True)
        except Exception:
            var.set(False)
        cb = ttk.Checkbutton(dlg, text='Enable anonymous telemetry (opt-in)', variable=var)
        cb.pack(anchor='w', padx=12, pady=(8, 8))

        def _save():
            try:
                if enable_telemetry:
                    enable_telemetry.set_opt_in(bool(var.get()))
                self.refresh_optimizer()
                messagebox.showinfo('Telemetry', 'Telemetry preference saved.', parent=dlg)
            except Exception as e:
                messagebox.showerror('Telemetry', f'Unable to save preference:\n{e}', parent=dlg)
            dlg.destroy()

        btns = ttk.Frame(dlg)
        btns.pack(side='bottom', fill='x', padx=12, pady=12)
        ttk.Button(btns, text='Save', style='Primary.TButton', command=_save).pack(side='right')
        ttk.Button(btns, text='Cancel', style='Action.TButton', command=dlg.destroy).pack(side='right', padx=(0, 6))
        cb.focus_set()

    # ------------------------------------------------------------------
    # Startup tab actions
    # ------------------------------------------------------------------
    def _update_summary(self):
        folders = len(self.data.get('folders', []))
        registry = len(self.data.get('registry', []))
        tasks = len(self.data.get('tasks', []))
        disabled = len(self.data.get('disabled', []))
        total = folders + registry + tasks
        self.total_label.config(text=f'Total: {total}')
        self.folder_label.config(text=f'Folders: {folders}')
        self.registry_label.config(text=f'Registry: {registry}')
        self.tasks_label.config(text=f'Tasks: {tasks}')
        self.disabled_label.config(text=f'Disabled: {disabled}')

    def _selected_entry(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item = self.tree.item(sel[0])
        vals = item.get('values') or []
        return {
            'name': vals[0] if len(vals) > 0 else None,
            'source': vals[1] if len(vals) > 1 else None,
            'location': vals[2] if len(vals) > 2 else None,
            'command': vals[3] if len(vals) > 3 else None,
        }

    def _update_detail(self):
        ent = self._selected_entry()
        if not ent:
            self.detail_name.config(text='Name: —')
            self.detail_source.config(text='Source: —')
            self.detail_location.config(text='Location: —')
            self.detail_command.config(text='Command: —')
            self.detail_hint.config(text='Select a startup item above to see its command and available actions.')
            self._update_context_panel()
            return
        self.detail_name.config(text=f"Name: {ent.get('name') or '—'}")
        self.detail_source.config(text=f"Source: {ent.get('source') or '—'}")
        self.detail_location.config(text=f"Location: {ent.get('location') or '—'}")
        self.detail_command.config(text=f"Command: {ent.get('command') or '—'}")
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
        self.status_lbl.config(text='Refreshing...')
        self._set_status('Refreshing startup entries...')

        def done(data, err):
            self.refresh_btn.config(state='normal')
            if err is not None:
                self.status_lbl.config(text=f'Refresh failed: {err}')
                self._set_status('Refresh failed.')
                return
            self.data = data
            self._apply_filter()
            self._update_summary()
            self._update_detail()
            self._update_actions()
            self.refresh_optimizer()
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


if __name__ == '__main__':
    if '--headless-clean' in sys.argv[1:]:
        sys.exit(_headless_main(sys.argv[1:]))
    # Rebuild the window when the user flips the theme.
    while True:
        app = StartupManagerGUI()
        app.mainloop()
        if not getattr(app, 'wants_restart', False):
            break
