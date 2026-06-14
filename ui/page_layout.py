"""Shared page layout contract — one sizing system for all workspace pages."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from ui import ctk_theme

# Window / content shell contract (logical px at 100% scaling)
CONTENT_MAX_WIDTH = 1180
CONTENT_PADX = 10
LAYOUT_MIN = (920, 580)
LAYOUT_DEFAULT = (1150, 720)


def classify_layout(width: int, height: int, *, scale: float = 1.0) -> str:
    """Return compact | normal | wide for responsive rules."""
    if width < 980 or height < 620 or scale >= 1.45:
        return 'compact'
    if width >= CONTENT_MAX_WIDTH + 80:
        return 'wide'
    return 'normal'


def apply_centered_shell(body_grid, body_center, width: int) -> None:
    """Center main content on ultrawide windows; full width below threshold."""
    if width > CONTENT_MAX_WIDTH + 48:
        gutter = max(0, (width - CONTENT_MAX_WIDTH) // 2)
        body_center.grid(row=0, column=1, columnspan=1, sticky='nsew', padx=0)
        body_grid.grid_columnconfigure(0, weight=1, minsize=gutter)
        body_grid.grid_columnconfigure(
            1, weight=0, minsize=min(CONTENT_MAX_WIDTH, width - 2 * gutter))
        body_grid.grid_columnconfigure(2, weight=1, minsize=gutter)
    else:
        body_center.grid(row=0, column=0, columnspan=3, sticky='nsew')
        body_grid.grid_columnconfigure(0, weight=1, minsize=0)
        body_grid.grid_columnconfigure(1, weight=0, minsize=0)
        body_grid.grid_columnconfigure(2, weight=0, minsize=0)


class PageFrame(ttk.Frame):
    """Standard page container — hero/toolbar fixed, body expands."""

    def __init__(self, master, *, style='Content.TFrame'):
        super().__init__(master, style=style)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)


class PageHeader(ttk.Frame):
    """Title + optional subtitle + right-aligned actions."""

    def __init__(self, master, title: str, *, subtitle: str = '', bg_style='Content.TFrame'):
        super().__init__(master, style=bg_style)
        row = ttk.Frame(self, style=bg_style)
        row.pack(fill='x')
        ttk.Label(row, text=title, font=('Segoe UI', 13, 'bold')).pack(side='left')
        self.subtitle_lbl = ttk.Label(row, text=subtitle, style='SubHeader.TLabel')
        if subtitle:
            self.subtitle_lbl.pack(side='left', padx=(10, 0))
        self.actions = ttk.Frame(row, style=bg_style)
        self.actions.pack(side='right')


class EmptyStateCard:
    """Polished empty state — replaces raw empty tables."""

    def __init__(
        self,
        parent,
        *,
        card_bg: str,
        title: str,
        body: str,
        button_text: str = '',
        command=None,
        proof: str = '#22C55E',
    ):
        self.frame = ctk_theme.frame(parent, card_bg, corner_radius=12)
        inner = ttk.Frame(self.frame, style='Card.TFrame')
        inner.place(relx=0.5, rely=0.44, anchor='center')
        ttk.Label(
            inner, text=title, font=('Segoe UI', 16, 'bold'), background=card_bg,
        ).pack(anchor='center')
        ttk.Label(
            inner, text=body, style='Info.TLabel', wraplength=440, justify='center',
        ).pack(anchor='center', pady=(8, 16))
        self.button = None
        if button_text and command:
            self.button = ttk.Button(
                inner, text=button_text, style='Primary.TButton', command=command)
            self.button.pack(anchor='center')

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def grid_remove(self):
        self.frame.grid_remove()


def _hide_widget(widget) -> None:
    if widget is None:
        return
    try:
        widget.pack_forget()
        return
    except Exception:
        pass
    try:
        widget.grid_remove()
    except Exception:
        pass


def _show_widget_fill(widget) -> None:
    if widget is None:
        return
    try:
        widget.pack(fill='both', expand=True)
        return
    except Exception:
        pass
    try:
        widget.grid(row=0, column=0, sticky='nsew')
    except Exception:
        pass


def sync_split_workspace(
    *,
    loading: bool,
    has_rows: bool,
    pane,
    empty_panel,
    loading_panel=None,
) -> None:
    """Shared Loading / Empty / Results states for table + details splits."""
    _hide_widget(loading_panel)
    if loading:
        _hide_widget(pane)
        _hide_widget(empty_panel)
        _show_widget_fill(loading_panel)
        return
    if has_rows:
        _hide_widget(empty_panel)
        _show_widget_fill(pane)
    else:
        _hide_widget(pane)
        _show_widget_fill(empty_panel)


def sync_table_empty_view(
    *,
    has_rows: bool,
    empty_panel,
    table_card=None,
    detail_panel=None,
    pane=None,
    hide_detail_when_empty: bool = True,
) -> None:
    """Show table+details when rows exist; otherwise show empty card only."""
    if has_rows:
        empty_panel.grid_remove()
        if pane is not None:
            try:
                pane.grid(row=0, column=0, sticky='nsew')
            except Exception:
                try:
                    pane.pack(fill='both', expand=True)
                except Exception:
                    pass
        elif table_card is not None and detail_panel is not None:
            table_card.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
            detail_panel.grid(row=0, column=1, sticky='nsew')
    else:
        if pane is not None:
            try:
                pane.grid_remove()
            except Exception:
                try:
                    pane.pack_forget()
                except Exception:
                    pass
        elif table_card is not None:
            table_card.grid_remove()
            if detail_panel is not None:
                if hide_detail_when_empty:
                    detail_panel.grid_remove()
                else:
                    detail_panel.grid(row=0, column=1, sticky='nsew')
        empty_panel.grid(row=0, column=0, columnspan=2, sticky='nsew')


def bind_pane_persistence(
    pane,
    key: str,
    *,
    get_value,
    set_value,
    default: int | None = None,
    min_left: int = 300,
    min_right: int = 240,
    default_ratio: float = 0.62,
) -> None:
    """Restore and save ttk.PanedWindow sash position under *key*."""
    state = {'last_width': 0}

    def _clamp_pos(total: int) -> int:
        if total < min_left + min_right:
            return max(min_left, total // 2)
        saved = get_value(key, default)
        if saved is None:
            pos = int(total * default_ratio)
        else:
            pos = int(saved)
        lo = min_left
        hi = max(min_left, total - min_right)
        return max(lo, min(pos, hi))

    def _restore(_event=None):
        try:
            pane.update_idletasks()
            total = max(pane.winfo_width(), 1)
            if total < 80:
                return
            if state['last_width'] and abs(total - state['last_width']) < 24:
                return
            state['last_width'] = total
            pane.sashpos(0, _clamp_pos(total))
        except Exception:
            pass

    def _save(_event=None):
        try:
            total = max(pane.winfo_width(), 1)
            pos = pane.sashpos(0)
            set_value(key, _clamp_pos(total) if total > 80 else pos)
        except Exception:
            pass

    pane.bind('<Configure>', _restore, add='+')
    pane.bind('<ButtonRelease-1>', _save, add='+')
    pane.after(120, _restore)
    pane.after(400, _restore)


def ensure_pane_sash(
    pane,
    *,
    get_value,
    key: str,
    default: int | None = None,
    min_left: int = 300,
    min_right: int = 240,
    default_ratio: float = 0.62,
) -> None:
    """Force a sane sash split (e.g. after tab switch or data load)."""
    try:
        pane.update_idletasks()
        total = max(pane.winfo_width(), 1)
        if total < min_left + min_right:
            return
        saved = get_value(key, default)
        pos = int(saved) if saved is not None else int(total * default_ratio)
        lo = min_left
        hi = max(min_left, total - min_right)
        pane.sashpos(0, max(lo, min(pos, hi)))
    except Exception:
        pass


def create_horizontal_pane(parent, *, use_pack: bool = False, min_left: int = 280, min_right: int = 220):
    """Return (panedwindow, left_frame, right_frame)."""
    pane = ttk.PanedWindow(parent, orient='horizontal')
    try:
        pane.configure(sashwidth=6, sashrelief='flat')
    except Exception:
        pass
    if use_pack:
        pane.pack(fill='both', expand=True)
    else:
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        pane.grid(row=0, column=0, sticky='nsew')
    left = ttk.Frame(pane, style='Card.TFrame')
    right = ttk.Frame(pane, style='Card.TFrame')
    pane.add(left, weight=3)
    pane.add(right, weight=1)
    try:
        pane.paneconfig(left, minsize=min_left)
        pane.paneconfig(right, minsize=min_right)
    except Exception:
        pass
    return pane, left, right


class DataTableFrame(ttk.Frame):
    """Tree + scrollbars with stable minimum height."""

    def __init__(self, master, tree: ttk.Treeview, *, min_height: int = 8):
        super().__init__(master, style='Card.TFrame')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        vsb = ttk.Scrollbar(self, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(self, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.configure(height=min_height)
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')


class DetailsPanel(ttk.Frame):
    """Fixed-width details column for split views."""

    def __init__(self, master, *, width: int = 300, style='Card.TFrame'):
        super().__init__(master, width=width, style=style)
        self.pack_propagate(False)
        self.configure(width=width)
        self.body = ttk.Frame(self, style='Card.TFrame')
        self.body.pack(fill='both', expand=True, padx=12, pady=12)


class SplitWorkspace(ttk.Frame):
    """Table + details split with shared empty-state slot."""

    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self._table_host = ttk.Frame(self)
        self._table_host.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        self._table_host.grid_rowconfigure(0, weight=1)
        self._table_host.grid_columnconfigure(0, weight=1)
        self._detail_host = ttk.Frame(self, width=300)
        self._detail_host.grid(row=0, column=1, sticky='ns')
        self._empty_host = ttk.Frame(self)
        self._empty_host.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self._empty_host.grid_remove()
        self.table_card = self._table_host
        self.detail_panel = self._detail_host
        self.empty_panel = self._empty_host

    def set_empty(self, empty: bool, *, hide_detail: bool = True) -> None:
        sync_table_empty_view(
            has_rows=not empty,
            table_card=self._table_host,
            detail_panel=self._detail_host,
            empty_panel=self._empty_host,
            hide_detail_when_empty=hide_detail,
        )
