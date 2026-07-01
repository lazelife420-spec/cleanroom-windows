"""Proof dashboard UI building blocks — command bar, proof cards, drawer."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from ui import ctk_theme
from ui.product_dialogs import show_grouped_popover
from ui.receipt_animation import ReceiptPrinterPanel


def proof_card(
    parent,
    *,
    title: str,
    card_bg: str,
    text_color: str,
    muted: str,
    accent: str,
    icon: str = '',
    min_width: int = 120,
) -> tuple[ctk.CTkFrame, ctk.CTkLabel]:
    """Readable proof metric card; returns (frame, value_label)."""
    card = ctk_theme.frame(parent, card_bg, corner_radius=10)
    card.grid_columnconfigure(0, weight=1)
    inner = ctk_theme.frame(card, card_bg, corner_radius=10)
    inner.pack(fill='both', expand=True, padx=14, pady=10)
    cap = f'{icon} {title}'.strip() if icon else title
    ctk_theme.label(
        inner, cap, text_color=muted, font_size=9, weight='bold',
    ).pack(anchor='w')
    value = ctk_theme.label(
        inner, '—', text_color=text_color, font_size=18, weight='bold',
    )
    value.pack(anchor='w', pady=(4, 0))
    card.configure(width=min_width)
    return card, value


def hero_state_panel(
    parent,
    *,
    title: str = '',
    card_bg: str,
    title_color: str,
    state_text: str,
    state_color: str,
    subtitle: str = '',
    title_font_size: int = 15,
    state_font_size: int = 11,
    subtitle_wrap: int = 480,
    art_photo=None,
) -> dict:
    """Shared hero shell for Home/Cleaner state and CTA rows."""
    shell = ctk_theme.frame(parent, card_bg, corner_radius=ctk_theme.RADIUS_MD)
    inner = tk.Frame(shell, bg=card_bg)
    inner.pack(fill='x', padx=ctk_theme.SPACE_3, pady=ctk_theme.SPACE_2)
    body_row = tk.Frame(inner, bg=card_bg)
    body_row.pack(fill='x')
    copy_col = tk.Frame(body_row, bg=card_bg)
    copy_col.pack(side='left', fill='x', expand=True)
    title_row = tk.Frame(copy_col, bg=card_bg)
    title_row.pack(fill='x')
    title_lbl = None
    if title:
        title_lbl = tk.Label(
            title_row, text=title, bg=card_bg, fg=title_color,
            font=('Segoe UI', title_font_size, 'bold'),
        )
        title_lbl.pack(side='left')
    state_lbl = tk.Label(
        title_row, text=state_text, bg=card_bg, fg=state_color,
        font=('Segoe UI', state_font_size, 'bold'),
    )
    state_pad = (12, 0) if title else (0, 0)
    state_lbl.pack(side='left', padx=state_pad)
    subtitle_lbl = None
    if subtitle is not None:
        subtitle_lbl = tk.Label(
            title_row,
            text=subtitle,
            bg=card_bg,
            fg=title_color,
            font=('Segoe UI', ctk_theme.TYPE_BODY),
            wraplength=subtitle_wrap,
            justify='left',
        )
        subtitle_lbl.pack(side='left', padx=(ctk_theme.SPACE_2, 0))
    art_lbl = None
    if art_photo is not None:
        art_shell = tk.Frame(
            body_row,
            bg=card_bg,
            highlightbackground=state_color,
            highlightthickness=1,
        )
        art_shell.pack(side='right', padx=(ctk_theme.SPACE_3, 0))
        art_lbl = tk.Label(art_shell, image=art_photo, text='', bg=card_bg)
        art_lbl.image = art_photo
        art_lbl.pack(padx=ctk_theme.SPACE_1, pady=ctk_theme.SPACE_1)
    action_row = tk.Frame(copy_col, bg=card_bg)
    action_row.pack(anchor='w', pady=(ctk_theme.SPACE_2, 0))
    return {
        'frame': shell,
        'inner': inner,
        'body_row': body_row,
        'copy_col': copy_col,
        'title_row': title_row,
        'title_lbl': title_lbl,
        'state_lbl': state_lbl,
        'subtitle_lbl': subtitle_lbl,
        'action_row': action_row,
        'art_lbl': art_lbl,
    }


def trust_stat_tile(parent, *, caption: str, card_bg: str, text_color: str, muted: str) -> dict:
    """Compact trust/stat tile with optional canvas for small Home metrics."""
    card = tk.Frame(parent, bg=card_bg, highlightthickness=0)
    inner = tk.Frame(card, bg=card_bg)
    inner.pack(fill='x', padx=10, pady=5)
    canvas = tk.Canvas(inner, width=56, height=56, bg=card_bg, highlightthickness=0)
    text_col = tk.Frame(inner, bg=card_bg)
    tk.Label(
        text_col, text=caption, bg=card_bg, fg=muted, font=('Segoe UI', 7, 'bold'),
    ).pack(anchor='w')
    value_lbl = tk.Label(
        text_col, text='—', bg=card_bg, fg=text_color, font=('Segoe UI', 12, 'bold'),
    )
    value_lbl.pack(anchor='w')
    note_lbl = tk.Label(
        text_col, text='', bg=card_bg, fg=muted, font=('Segoe UI', 7),
    )
    note_lbl.pack(anchor='w')
    return {
        'frame': card,
        'inner': inner,
        'canvas': canvas,
        'text_col': text_col,
        'value_lbl': value_lbl,
        'note_lbl': note_lbl,
    }


def app_shell_header(
    parent,
    *,
    bg: str,
    bar_bg: str,
    text: str,
    muted: str,
    proof: str,
    proof_soft: str,
    head_bg: str,
    logo_photo=None,
    on_why,
    on_settings,
    on_more,
) -> dict:
    """Global app chrome — identity + status chips left; Settings + More right."""
    bar = ctk_theme.frame(parent, bar_bg, corner_radius=8)
    bar.pack(fill='x')
    row = ctk_theme.frame(bar, bar_bg)
    row.pack(fill='x', padx=10, pady=7)

    left = ctk_theme.frame(row, bar_bg)
    left.pack(side='left', fill='x', expand=True)

    brand_row = ctk_theme.frame(left, bar_bg)
    brand_row.pack(side='left')
    if logo_photo is not None:
        logo_lbl = tk.Label(brand_row, image=logo_photo, bg=bar_bg)
        logo_lbl.image = logo_photo
        logo_lbl.pack(side='left', padx=(0, 6))
    ctk_theme.label(
        brand_row, 'Cleanroom', text_color=text, font_size=14, weight='bold',
    ).pack(side='left')

    custody_frame = ctk_theme.frame(left, bar_bg)
    custody_frame.pack(side='left', padx=(12, 0))
    pill = ctk_theme.frame(custody_frame, proof_soft, corner_radius=14)
    pill.pack(side='left')
    inner = ctk_theme.frame(pill, proof_soft, corner_radius=14)
    inner.pack(padx=8, pady=4)
    trust_value = ctk_theme.label(
        inner, 'Custody trust —', text_color=proof, font_size=ctk_theme.TYPE_MICRO, weight='bold',
    )
    trust_value.pack(side='left')
    trust_caption = ctk_theme.label(
        inner, '—', text_color=text, font_size=ctk_theme.TYPE_MICRO,
    )
    trust_caption.pack(side='left', padx=(4, 0))
    why_btn = ctk_theme.button(
        inner, 'Why?', on_why,
        fg_color=head_bg, hover_color=bg, text_color=muted,
        width=42, height=22, corner_radius=10,
    )
    why_btn.pack(side='left', padx=(6, 0))

    archive_badge = ctk_theme.frame(left, proof_soft, corner_radius=10)
    ctk_theme.label(
        archive_badge, 'Archive-first ON',
        text_color=proof, font_size=ctk_theme.TYPE_MICRO, weight='bold',
    ).pack(padx=8, pady=3)
    archive_badge.pack(side='left', padx=(8, 0))

    right = ctk_theme.frame(row, bar_bg)
    right.pack(side='right')
    settings_btn = ctk_theme.button(
        right, 'Settings', on_settings,
        fg_color=head_bg, hover_color=proof_soft, text_color=text,
        height=32, width=88, corner_radius=8,
    )
    settings_btn.pack(side='left', padx=(0, 6))
    more_btn = ctk_theme.button(
        right, 'More ▾', on_more,
        fg_color=head_bg, hover_color=proof_soft, text_color=text,
        height=32, width=72, corner_radius=8,
    )
    more_btn.pack(side='left')

    return {
        'frame': bar,
        'custody_frame': custody_frame,
        'trust_value': trust_value,
        'trust_caption': trust_caption,
        'why_btn': why_btn,
        'archive_badge': archive_badge,
        'settings_btn': settings_btn,
        'more_btn': more_btn,
    }


def sidebar_compact_brand(
    parent,
    *,
    bg: str,
    accent: str,
    text_color: str,
    muted: str,
    logo_photo=None,
    tagline: str = '',
) -> dict:
    """Compact sidebar brand row — logo, wordmark, tagline only."""
    row = ctk_theme.frame(parent, bg)
    row.pack(fill='x', padx=8, pady=(6, 2))
    if logo_photo is not None:
        logo_lbl = tk.Label(row, image=logo_photo, bg=bg)
        logo_lbl.image = logo_photo
        logo_lbl.pack(side='left', padx=(0, 6))
    col = ctk_theme.frame(row, bg)
    col.pack(side='left', fill='x', expand=True)
    title_lbl = ctk_theme.label(
        col, 'Cleanroom', text_color=accent, font_size=13, weight='bold',
    )
    title_lbl.pack(anchor='w')
    tagline_lbl = ctk_theme.label(
        col, tagline, text_color=muted, font_size=ctk_theme.TYPE_MICRO,
        wraplength=168, justify='left',
    )
    tagline_lbl.pack(anchor='w', pady=(1, 0))
    status_lbl = ctk_theme.label(
        col, '', text_color=text_color, font_size=ctk_theme.TYPE_MICRO,
        wraplength=168, justify='left',
    )
    return {
        'frame': row,
        'title_lbl': title_lbl,
        'tagline_lbl': tagline_lbl,
        'status_lbl': status_lbl,
        'pill_lbl': None,
        'pill_frame': None,
    }


def trust_compact_strip(
    parent,
    *,
    bg: str,
    proof_soft: str,
    proof: str,
    text_color: str,
    muted: str,
    head_bg: str,
    on_why,
) -> tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel, ctk.CTkButton]:
    """Compact custody trust pill — not a full-width hero banner."""
    strip = ctk_theme.frame(parent, bg)
    pill = ctk_theme.frame(strip, proof_soft, corner_radius=16)
    pill.pack(fill='x')
    inner = ctk_theme.frame(pill, proof_soft, corner_radius=16)
    inner.pack(fill='x', padx=10, pady=5)
    ctk_theme.label(
        inner, 'Custody trust', text_color=muted, font_size=9, weight='bold',
    ).pack(side='left')
    value = ctk_theme.label(inner, '—', text_color=proof, font_size=13, weight='bold')
    value.pack(side='left', padx=(8, 0))
    caption = ctk_theme.label(inner, '', text_color=text_color, font_size=9)
    caption.pack(side='left', padx=(6, 0))
    why = ctk_theme.button(
        inner, 'Why?', on_why,
        fg_color=head_bg, hover_color=bg, text_color=text_color,
        width=44, height=22,
    )
    why.pack(side='right')
    return strip, value, caption, why


class CommandBar:
    """Top command bar: primary proof actions + More menu for secondary tools."""

    def __init__(
        self,
        parent,
        *,
        bg: str,
        card_bg: str,
        head_bg: str,
        accent: str,
        accent_dark: str,
        accent_soft: str,
        text: str,
        on_accent: str,
        on_scan,
        on_preview,
        on_apply,
        on_restore,
        proof: str = '',
        proof_dark: str = '',
        more_groups: list[tuple[str, list[tuple[str, callable]]]] | None = None,
        more_items: list[tuple[str, callable]] | None = None,
    ):
        self._bg = bg
        self._card_bg = card_bg
        self._head_bg = head_bg
        self._accent = accent
        self._accent_dark = accent_dark
        self._accent_soft = accent_soft
        self._proof = proof or accent
        self._proof_dark = proof_dark or accent_dark
        self._on_accent = on_accent
        self._text = text
        self._muted = accent_soft  # placeholder; overridden below if needed
        self._shell = ctk_theme.frame(parent, card_bg, corner_radius=10)
        self._shell.pack(fill='x', pady=(4, 0))
        inner = ctk_theme.frame(self._shell, card_bg)
        inner.pack(fill='x', padx=10, pady=8)
        self.frame = inner
        self._primary = ctk_theme.frame(inner, card_bg)
        self._primary.pack(side='left')

        self.tb_scan = ctk_theme.button(
            self._primary, 'Scan', on_scan,
            fg_color=head_bg, hover_color=accent_soft, text_color=text, height=34,
        )
        self.tb_scan.pack(side='left', padx=(0, 6))
        self.tb_preview = ctk_theme.button(
            self._primary, 'Preview Receipt', on_preview,
            fg_color=head_bg, hover_color=accent_soft, text_color=text, height=34,
        )
        self.tb_preview.pack(side='left', padx=(0, 6))
        self.tb_apply = ctk_theme.button(
            self._primary, 'Archive & Clean', on_apply,
            fg_color=self._proof, hover_color=self._proof_dark, text_color=on_accent, primary=True,
            height=34,
        )
        self.tb_apply.pack(side='left', padx=(0, 6))
        self.tb_restore = ctk_theme.button(
            self._primary, 'Restore', on_restore,
            fg_color=head_bg, hover_color=accent_soft, text_color=text, height=34,
        )
        self.tb_restore.pack(side='left', padx=(0, 6))

        if more_groups is None and more_items:
            more_groups = [('More', list(more_items))]
        self._more_groups = more_groups or []
        self._more_popover = None
        self._more_btn = ctk_theme.button(
            inner, 'More ▾', self._show_more,
            fg_color=head_bg, hover_color=accent_soft, text_color=text, width=72, height=34,
        )
        self._more_btn.pack(side='left', padx=(0, 8))

        flow = ctk_theme.label(
            inner, ctk_theme.PROOF_FLOW_TEXT, text_color=text, font_size=9,
        )
        self._proof_flow_lbl = flow
        flow.pack(side='right', padx=(8, 0))
        self._dashboard_mode = False
        self._popover_colors = dict(
            bg=card_bg, card=card_bg, head=head_bg, accent=accent,
            accent_soft=accent_soft, text=text, muted=accent_soft,
            border=head_bg, on_accent=on_accent,
        )

    def _show_more(self, anchor=None):
        if self._more_popover and self._more_popover.winfo_exists():
            try:
                self._more_popover.destroy()
            except Exception:
                pass
        btn = anchor or self._more_btn
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height() + 2
        groups = [
            (section, [(label, cmd) for label, cmd in items])
            for section, items in self._more_groups
        ]
        self._more_popover = show_grouped_popover(
            btn.winfo_toplevel(), x, y, groups,
            colors=self._popover_colors, width=232,
        )

    def show_more_at(self, anchor):
        """Open More menu anchored to header or toolbar button."""
        self._show_more(anchor=anchor)

    def set_context(self, tab_idx: int) -> None:
        """Emphasize primary actions for the active page."""
        if self._dashboard_mode:
            return
        for btn in (self.tb_scan, self.tb_preview, self.tb_restore):
            btn.configure(fg_color=self._head_bg, hover_color=self._accent_soft)
        self.tb_apply.configure(fg_color=self._head_bg, hover_color=self._accent_soft)
        if tab_idx in (0, 3):
            self.tb_apply.configure(fg_color=self._proof, hover_color=self._proof_dark)
        elif tab_idx in (5, 6):
            self.tb_restore.configure(fg_color=self._proof, hover_color=self._proof_dark)

    def set_page_mode(self, *, dashboard: bool, tab_idx: int = 0) -> None:
        """Global bar hidden — page heroes and sidebar own primary actions."""
        self._dashboard_mode = dashboard
        self._shell.pack_forget()

    def set_compact_labels(self, compact: bool) -> None:
        self.tb_preview.configure(text='Preview' if compact else 'Preview Receipt')
        self.tb_apply.configure(text='Archive' if compact else 'Archive & Clean')


class ProofDrawer(tk.Frame):
    """Collapsible proof output panel wrapping ReceiptPrinterPanel."""

    def __init__(
        self,
        master,
        *,
        panel_bg: str,
        paper_bg: str,
        accent: str,
        text_color: str,
        muted: str,
        border: str,
        width: int = 240,
        height: int = 200,
    ):
        super().__init__(master, bg=panel_bg, width=width)
        self._expanded = True
        self._panel_bg = panel_bg
        self._full_width = width
        self._height = height

        hdr = tk.Frame(self, bg=panel_bg)
        hdr.pack(fill='x', padx=6, pady=(4, 0))
        tk.Label(
            hdr, text='Proof Output', bg=panel_bg, fg=muted,
            font=('Segoe UI', 9, 'bold'),
        ).pack(side='left')
        self._toggle_btn = tk.Label(
            hdr, text='−', bg=panel_bg, fg=text_color,
            font=('Segoe UI', 11, 'bold'), cursor='hand2',
        )
        self._toggle_btn.pack(side='right')
        self._toggle_btn.bind('<Button-1>', lambda e: self.toggle())

        self._body = tk.Frame(self, bg=panel_bg)
        self._body.pack(fill='both', expand=True)

        self.printer = ReceiptPrinterPanel(
            self._body,
            width=width - 12,
            height=height - 28,
            panel_bg=panel_bg,
            paper_bg=paper_bg,
            accent=accent,
            text_color=text_color,
            muted=muted,
            border=border,
        )
        self.printer.pack(fill='both', expand=True, padx=4, pady=(0, 6))
        self.configure(width=width, height=height)
        self.pack_propagate(False)

    @property
    def expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self._body.pack(fill='both', expand=True)
            self._toggle_btn.configure(text='−')
            self.configure(width=self._full_width)
        else:
            self._body.pack_forget()
            self._toggle_btn.configure(text='+')
            self.configure(width=36)

    def play(self, *args, **kwargs):
        return self.printer.play(*args, **kwargs)

    def show_idle(self, message='Select a row to view proof details'):
        if not self._expanded:
            self.toggle()
        self.printer.show_idle(message)

    def show_static(self, lines, stamp=''):
        if not self._expanded:
            self.toggle()
        self.printer.show_static(lines, stamp=stamp)


def settings_card(parent, title: str, *, card_bg: str, accent: str) -> ctk.CTkFrame:
    """Settings section card with heading."""
    box = ctk_theme.frame(parent, card_bg, corner_radius=12)
    box.pack(fill='x', padx=4, pady=(0, 12))
    ctk_theme.label(
        box, title, text_color=accent, font_size=ctk_theme.TYPE_SECTION, weight='bold',
    ).pack(anchor='w', padx=16, pady=(14, 6))
    body = ctk_theme.frame(box, card_bg, corner_radius=12)
    body.pack(fill='x', padx=16, pady=(0, 14))
    return body


def recent_proof_tile(
    parent,
    *,
    title: str,
    card_bg: str,
    text_color: str,
    muted: str,
    accent: str,
    command=None,
) -> tuple[ctk.CTkFrame, ctk.CTkLabel]:
    """Small recent-proof card; returns (frame, detail_label)."""
    card = ctk_theme.frame(parent, card_bg, corner_radius=10)
    inner = ctk_theme.frame(card, card_bg, corner_radius=10)
    inner.pack(fill='both', expand=True, padx=12, pady=10)
    ctk_theme.label(inner, title, text_color=muted, font_size=9, weight='bold').pack(anchor='w')
    detail = ctk_theme.label(inner, '—', text_color=text_color, font_size=11, weight='bold')
    detail.pack(anchor='w', pady=(4, 6))
    if command:
        ctk_theme.button(
            inner, 'Open', command,
            fg_color=accent, hover_color=accent, text_color=text_color,
            width=64, height=24,
        ).pack(anchor='w')
    return card, detail


def guided_action_card(*args, **kwargs) -> ctk.CTkFrame:
    """Named wrapper for Home guided actions; delegates to recommendation_card."""
    return recommendation_card(*args, **kwargs)


def recommendation_card(
    parent,
    *,
    index: int,
    severity: str,
    title: str,
    detail: str,
    card_bg: str,
    text_color: str,
    muted: str,
    accent: str,
    border: str,
    on_select,
    on_double=None,
    on_right=None,
) -> ctk.CTkFrame:
    """Single recommendation card for Home dashboard (not a table row)."""
    sev = (severity or 'info').lower()
    sev_colors = {
        'high': '#F87171',
        'medium': '#FBBF24',
        'low': accent,
        'info': muted,
    }
    badge_color = sev_colors.get(sev, muted)

    card = ctk_theme.frame(parent, card_bg, corner_radius=10, border_color=border, border_width=1)
    inner = ctk_theme.frame(card, card_bg, corner_radius=10)
    inner.pack(fill='x', padx=12, pady=10)

    top = ctk_theme.frame(inner, card_bg)
    top.pack(fill='x')
    ctk_theme.label(
        top, sev.upper(), text_color=badge_color, font_size=8, weight='bold',
    ).pack(side='left')
    ctk_theme.label(
        top, title, text_color=text_color, font_size=12, weight='bold',
        wraplength=420, justify='left',
    ).pack(side='left', padx=(8, 0), fill='x', expand=True)

    ctk_theme.label(
        inner, detail, text_color=muted, font_size=10,
        wraplength=460, justify='left',
    ).pack(anchor='w', pady=(6, 0))

    def _bind(widget):
        widget.bind('<Button-1>', lambda e, i=index: on_select(i))
        if on_double:
            widget.bind('<Double-Button-1>', lambda e, i=index: on_double(i))
        if on_right:
            widget.bind('<Button-3>', lambda e, i=index: on_right(e, i))

    for w in (card, inner, top):
        _bind(w)
    for child in inner.winfo_children():
        try:
            _bind(child)
            for sub in child.winfo_children():
                _bind(sub)
        except Exception:
            pass
    return card


def cleaner_summary_tile(parent, *, text: str, row: int, column: int, padx=(0, 8)) -> ttk.Label:
    """Shared summary pill for Cleaner top-line metrics."""
    lbl = ttk.Label(parent, text=text, style='Badge.TLabel')
    lbl.grid(row=row, column=column, sticky='w', padx=padx)
    return lbl


def candidate_detail_panel(
    parent,
    *,
    card_bg: str,
    proof: str,
    wraplength: int = 260,
) -> dict:
    """Shared Cleaner detail shell with standard labels and actions row."""
    detail = ctk_theme.frame(parent, card_bg, corner_radius=ctk_theme.RADIUS_MD)
    detail_inner = ttk.Frame(detail, style='Card.TFrame')
    detail_inner.pack(fill='both', expand=True, padx=ctk_theme.SPACE_3, pady=ctk_theme.SPACE_3)
    ttk.Label(
        detail_inner, text='Candidate details', font=('Segoe UI', 11, 'bold'),
        background=card_bg,
    ).pack(anchor='w', pady=(0, ctk_theme.SPACE_2))
    name_lbl = ttk.Label(
        detail_inner, text='No candidate selected', style='CardInfo.TLabel',
        wraplength=wraplength, font=('Segoe UI', 11, 'bold'),
    )
    name_lbl.pack(anchor='w', pady=(0, ctk_theme.SPACE_2))
    path_lbl = ttk.Label(detail_inner, text='', style='CardInfo.TLabel', wraplength=wraplength, justify='left')
    reason_lbl = ttk.Label(detail_inner, text='', style='CardInfo.TLabel', wraplength=wraplength, justify='left')
    size_lbl = ttk.Label(detail_inner, text='', style='CardInfo.TLabel', wraplength=wraplength)
    archive_lbl = ttk.Label(detail_inner, text='', style='CardInfo.TLabel', wraplength=wraplength, justify='left')
    receipt_lbl = ttk.Label(detail_inner, text='', style='CardInfo.TLabel', wraplength=wraplength, justify='left')
    why_lbl = ttk.Label(
        detail_inner,
        text='Run Scan to populate candidates, then click a row to review path, archive destination, and safety notes.',
        style='CardInfo.TLabel',
        wraplength=wraplength,
        justify='left',
        foreground=proof,
    )
    for lbl in (path_lbl, reason_lbl, size_lbl, archive_lbl, receipt_lbl, why_lbl):
        lbl.pack(anchor='w', pady=(0, ctk_theme.SPACE_2))
    btn_row = ttk.Frame(detail_inner, style='Card.TFrame')
    btn_row.pack(fill='x', pady=(ctk_theme.SPACE_1, 0))
    return {
        'frame': detail,
        'inner': detail_inner,
        'name_lbl': name_lbl,
        'path_lbl': path_lbl,
        'reason_lbl': reason_lbl,
        'size_lbl': size_lbl,
        'archive_lbl': archive_lbl,
        'receipt_lbl': receipt_lbl,
        'why_lbl': why_lbl,
        'button_row': btn_row,
    }


class ProofSummaryCard(tk.Frame):
    """Dark proof summary panel — no white receipt preview on the dashboard."""

    def __init__(
        self,
        master,
        *,
        panel_bg: str,
        card_bg: str,
        accent: str,
        proof: str,
        text_color: str,
        muted: str,
        on_open_receipt=None,
        on_copy_proof=None,
        on_view_details=None,
    ):
        super().__init__(master, bg=panel_bg)
        self._panel_bg = panel_bg
        self._card_bg = card_bg
        self._accent = accent
        self._proof = proof
        self._text = text_color
        self._muted = muted
        self._on_open = on_open_receipt
        self._on_copy = on_copy_proof
        self._on_view = on_view_details

        shell = tk.Frame(self, bg=card_bg)
        shell.pack(fill='both', expand=True, padx=4, pady=4)
        inner = tk.Frame(shell, bg=card_bg)
        inner.pack(fill='both', expand=True, padx=14, pady=14)

        tk.Label(
            inner, text='Proof summary', bg=card_bg, fg=muted,
            font=('Segoe UI', 9, 'bold'),
        ).pack(anchor='w')
        self._title_lbl = tk.Label(
            inner, text='Select a recommendation', bg=card_bg, fg=text_color,
            font=('Segoe UI', 13, 'bold'), wraplength=260, justify='left',
        )
        self._title_lbl.pack(anchor='w', pady=(8, 4))
        self._badge_lbl = tk.Label(
            inner, text='—', bg=card_bg, fg=proof,
            font=('Segoe UI', 9, 'bold'),
        )
        self._badge_lbl.pack(anchor='w')
        self._summary_lbl = tk.Label(
            inner, text='Choose a recommendation to see guidance and next steps.',
            bg=card_bg, fg=muted, font=('Segoe UI', 10),
            wraplength=260, justify='left',
        )
        self._summary_lbl.pack(anchor='w', pady=(8, 12))

        btns = tk.Frame(inner, bg=card_bg)
        btns.pack(fill='x', side='bottom')
        self._btn_open = tk.Button(
            btns, text='Open Receipt', command=self._open_receipt,
            bg=accent, fg=text_color, relief='flat', padx=8, pady=4,
            font=('Segoe UI', 9), cursor='hand2',
        )
        self._btn_open.pack(side='left')
        self._btn_copy = tk.Button(
            btns, text='Copy Proof', command=self._copy_proof,
            bg=panel_bg, fg=text_color, relief='flat', padx=8, pady=4,
            font=('Segoe UI', 9), cursor='hand2',
        )
        self._btn_copy.pack(side='left', padx=(6, 0))
        self._btn_view = tk.Button(
            btns, text='View Details', command=self._view_details,
            bg=panel_bg, fg=text_color, relief='flat', padx=8, pady=4,
            font=('Segoe UI', 9), cursor='hand2',
        )
        self._btn_view.pack(side='left', padx=(6, 0))

    def _open_receipt(self):
        if self._on_open:
            self._on_open()

    def _copy_proof(self):
        if self._on_copy:
            self._on_copy()

    def _view_details(self):
        if self._on_view:
            self._on_view()

    def set_action_handlers(self, *, open_cb=None, copy_cb=None, view_cb=None):
        """Override quick-action buttons; omit args to restore constructor callbacks."""
        self._btn_open.config(command=open_cb or self._open_receipt)
        self._btn_copy.config(command=copy_cb or self._copy_proof)
        self._btn_view.config(command=view_cb or self._view_details)

    def show_idle(self, message: str = 'Choose a recommendation to see guidance and next steps.'):
        self._title_lbl.config(text='Select a recommendation')
        self._badge_lbl.config(text='GUIDANCE', fg=self._muted)
        self._summary_lbl.config(text=message)
        for btn in (self._btn_open, self._btn_copy, self._btn_view):
            btn.config(state='disabled')

    def show_recommendation(self, rec: dict):
        sev = (rec.get('severity') or 'info').upper()
        title = rec.get('title') or '—'
        detail = rec.get('detail') or '—'
        self._title_lbl.config(text=title)
        self._badge_lbl.config(
            text=sev,
            fg=self._proof if sev != 'INFO' else self._muted,
        )
        self._summary_lbl.config(text=detail)
        for btn in (self._btn_open, self._btn_copy, self._btn_view):
            btn.config(state='normal')

    def show_scan_results(self, count: int, size_text: str, checked: int):
        self._title_lbl.config(text=f'{count:,} cleanup candidate{"s" if count != 1 else ""}')
        self._badge_lbl.config(text='SCAN RESULTS', fg=self._proof)
        self._summary_lbl.config(
            text=(f'{size_text} reclaimable · {checked:,} checked for archive.\n'
                  'Open Cleaner to review paths and preview the receipt before archiving.'))
        self._btn_open.config(state='normal')
        self._btn_copy.config(state='normal')
        self._btn_view.config(state='normal')

    def show_latest_receipt(self, receipt_label: str):
        self._title_lbl.config(text='Latest receipt on disk')
        self._badge_lbl.config(text='PROOF', fg=self._proof)
        self._summary_lbl.config(
            text=f'Most recent Cleanroom receipt: {receipt_label}.\n'
                 'Open it to review measured free-space proof and custody details.')
        self._btn_open.config(state='normal')
        self._btn_copy.config(state='disabled')
        self._btn_view.config(state='disabled')


def settings_pill_nav(
    parent,
    items: list[tuple[str, str]],
    *,
    bg: str,
    accent: str,
    muted: str,
    text_color: str,
    on_select,
) -> dict[str, ctk.CTkButton]:
    """Horizontal pill tabs for Settings — one product page, no inner rail."""
    row = ctk_theme.frame(parent, bg)
    row.pack(fill='x', pady=(0, 8))
    buttons: dict[str, ctk.CTkButton] = {}
    for label, key in items:
        btn = ctk_theme.button(
            row, label, lambda k=key: on_select(k),
            fg_color='transparent', hover_color=accent, text_color=text_color,
            height=32, corner_radius=16,
        )
        btn.pack(side='left', padx=(0, 6))
        buttons[key] = btn
    return buttons


def settings_section_nav(parent, labels: list[str], *, sidebar_bg: str, accent: str, muted: str, on_select):
    """Horizontal segmented settings nav (legacy); prefer settings_sidebar_nav."""
    row = ctk_theme.frame(parent, sidebar_bg)
    row.pack(fill='x', padx=12, pady=(0, 8))
    buttons = {}
    for label in labels:
        btn = ctk_theme.button(
            row, label, lambda selected_label=label: on_select(selected_label),
            fg_color='transparent', hover_color=accent, text_color=muted, width=88,
        )
        btn.pack(side='left', padx=(0, 6))
        buttons[label] = btn
    return buttons


def settings_sidebar_nav(
    parent,
    items: list[tuple[str, str]],
    *,
    sidebar_bg: str,
    accent: str,
    muted: str,
    text_color: str,
    on_select,
    width: int = 168,
) -> dict[str, ctk.CTkButton]:
    """Vertical settings nav; items are (display_label, section_key)."""
    wrap = ctk_theme.frame(parent, sidebar_bg, corner_radius=10)
    wrap.pack(fill='both', expand=True, padx=8, pady=8)
    ctk_theme.label(
        wrap, 'Sections', text_color=muted, font_size=9, weight='bold',
    ).pack(anchor='w', padx=4, pady=(0, 6))
    inner = ctk_theme.frame(wrap, sidebar_bg)
    inner.pack(fill='both', expand=True)
    buttons: dict[str, ctk.CTkButton] = {}
    for label, key in items:
        btn = ctk_theme.button(
            inner, label, lambda k=key: on_select(k),
            fg_color='transparent', hover_color=accent, text_color=text_color,
            anchor='w', height=38, width=width,
        )
        btn.pack(fill='x', pady=4)
        buttons[key] = btn
    return buttons


def brand_identity_block(
    parent,
    *,
    bg: str,
    accent: str,
    accent_soft: str,
    text_color: str,
    muted: str,
    logo_photo=None,
    default_title: str = 'Cleanroom',
    default_tagline: str = 'Archive-first cleanup, with receipts.',
    default_status: str = '',
    default_pill: str = 'Receipt-backed',
) -> dict:
    """Product identity strip: logo, wordmark, tagline, live status, pill, proof trail."""
    wrap = ctk_theme.frame(parent, accent_soft, corner_radius=12, border_width=1)
    inner = ctk_theme.frame(wrap, bg, corner_radius=11)
    inner.pack(fill='x', padx=1, pady=1)
    content = ctk_theme.frame(inner, bg)
    content.pack(fill='x', padx=10, pady=(12, 10))

    top_row = ctk_theme.frame(content, bg)
    top_row.pack(fill='x')

    if logo_photo is not None:
        logo_lbl = tk.Label(top_row, image=logo_photo, bg=bg)
        logo_lbl.image = logo_photo
        logo_lbl.pack(side='left', padx=(0, 8))

    text_col = ctk_theme.frame(top_row, bg)
    text_col.pack(side='left', fill='x', expand=True)

    title_lbl = ctk_theme.label(
        text_col, default_title, text_color=accent, font_size=17, weight='bold',
    )
    title_lbl.pack(anchor='w')
    tagline_lbl = ctk_theme.label(
        text_col, default_tagline, text_color=muted, font_size=9,
        wraplength=168, justify='left',
    )
    tagline_lbl.pack(anchor='w', pady=(2, 0))
    status_lbl = ctk_theme.label(
        text_col, default_status, text_color=text_color, font_size=9,
        wraplength=168, justify='left',
    )
    status_lbl.pack(anchor='w', pady=(2, 0))

    pill_row = ctk_theme.frame(content, bg)
    pill_row.pack(fill='x', pady=(8, 0))
    pill_frame = ctk_theme.frame(pill_row, accent_soft, corner_radius=10)
    pill_frame.pack(side='left')
    pill_lbl = ctk_theme.label(
        pill_frame, default_pill, text_color=accent, font_size=9, weight='bold',
    )
    pill_lbl.pack(padx=8, pady=3)

    accent_line = ctk_theme.frame(content, accent, corner_radius=1)
    accent_line.configure(height=2)
    accent_line.pack(fill='x', pady=(10, 0))

    return {
        'frame': wrap,
        'title_lbl': title_lbl,
        'tagline_lbl': tagline_lbl,
        'status_lbl': status_lbl,
        'pill_lbl': pill_lbl,
        'pill_frame': pill_frame,
        'accent_line': accent_line,
    }


def sidebar_section(parent, title: str, *, sidebar_bg: str, muted: str) -> ctk.CTkFrame:
    """Sidebar group label + container."""
    ctk_theme.label(
        parent, title, text_color=muted, font_size=10, weight='bold',
    ).pack(anchor='w', padx=10, pady=(8, 2))
    wrap = ctk_theme.frame(parent, sidebar_bg)
    wrap.pack(fill='x', padx=4)
    return wrap


def collapsible_section(
    parent,
    title: str,
    *,
    sidebar_bg: str,
    muted: str,
    text_color: str,
    accent_soft: str = '',
    hover_bg: str = '',
    start_open: bool = True,
) -> tuple[ctk.CTkButton, ctk.CTkFrame]:
    """Collapsible sidebar group; returns (toggle_button, body_frame)."""
    accent_soft = accent_soft or sidebar_bg
    hover_bg = hover_bg or sidebar_bg
    block = ctk_theme.frame(parent, sidebar_bg)
    block.pack(fill='x', padx=4, pady=(0, 6))
    state = {'open': start_open}

    header = ctk_theme.frame(block, sidebar_bg, corner_radius=8)
    header.pack(fill='x', padx=2, pady=(0, 4))
    body = ctk_theme.frame(block, sidebar_bg)
    if start_open:
        body.pack(fill='x', padx=6, pady=(0, 4))

    chevron = '▾' if start_open else '▸'
    toggle = ctk_theme.button(
        header,
        f'{chevron}  {title}',
        lambda: None,
        fg_color='transparent',
        hover_color=hover_bg,
        text_color=muted,
        anchor='w',
        height=28,
        font=ctk_theme.font(ctk_theme.TYPE_MICRO, 'bold'),
    )
    toggle.pack(fill='x', padx=8, pady=3)

    def _flip():
        state['open'] = not state['open']
        if state['open']:
            body.pack(fill='x', padx=6, pady=(0, 4))
            toggle.configure(text=f'▾  {title}')
        else:
            body.pack_forget()
            toggle.configure(text=f'▸  {title}')

    toggle.configure(command=_flip)
    return toggle, body


def sidebar_nav_button(
    parent,
    label: str,
    command,
    *,
    sidebar_bg: str,
    accent_soft: str,
    text_color: str,
    hover_color: str = '',
    active: bool = False,
    accent: str = '',
    on_accent: str = '',
) -> ctk.CTkButton:
    """Full-width sidebar navigation row."""
    if active and accent:
        fg, hover, txt = accent, accent, on_accent or text_color
    else:
        fg, hover, txt = 'transparent', hover_color or sidebar_bg, text_color
    return ctk_theme.button(
        parent, label, command,
        fg_color=fg,
        hover_color=hover,
        text_color=txt,
        anchor='w', height=36, corner_radius=8,
        font=ctk_theme.font(ctk_theme.TYPE_BODY, 'bold' if active else 'normal'),
    )
