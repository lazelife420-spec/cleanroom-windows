"""Proof dashboard UI building blocks — command bar, proof cards, drawer."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ui import ctk_theme
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


def trust_card(
    parent,
    *,
    card_bg: str,
    accent_soft: str,
    accent: str,
    text_color: str,
    head_bg: str,
    on_why,
) -> tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel, ctk.CTkButton]:
    """Custody trust hero card; returns (frame, value_label, caption_label, why_button)."""
    card = ctk_theme.frame(
        parent, accent_soft, corner_radius=10,
    )
    inner = ctk_theme.frame(card, accent_soft, corner_radius=10)
    inner.pack(fill='both', expand=True, padx=14, pady=10)
    ctk_theme.label(
        inner, 'Custody Trust', text_color=accent, font_size=9, weight='bold',
    ).pack(anchor='w')
    row = ctk_theme.frame(inner, accent_soft)
    row.pack(anchor='w', pady=(4, 0))
    value = ctk_theme.label(row, '—', text_color=accent, font_size=22, weight='bold', width=48)
    value.pack(side='left')
    caption = ctk_theme.label(row, '% verified', text_color=text_color, font_size=10)
    caption.pack(side='left', padx=(6, 0), pady=(6, 0))
    why = ctk_theme.button(
        inner, 'Why?', on_why,
        fg_color=head_bg, hover_color=accent_soft, text_color=text_color,
        width=52, height=22,
    )
    why.pack(anchor='w', pady=(6, 0))
    return card, value, caption, why


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
        more_items: list[tuple[str, callable]],
    ):
        self._bg = bg
        self._card_bg = card_bg
        self._head_bg = head_bg
        self._accent = accent
        self._accent_dark = accent_dark
        self._accent_soft = accent_soft
        self._on_accent = on_accent
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
            fg_color=accent, hover_color=accent_dark, text_color=on_accent, primary=True,
            height=34,
        )
        self.tb_apply.pack(side='left', padx=(0, 6))
        self.tb_restore = ctk_theme.button(
            self._primary, 'Restore', on_restore,
            fg_color=head_bg, hover_color=accent_soft, text_color=text, height=34,
        )
        self.tb_restore.pack(side='left', padx=(0, 6))

        self._more_items = more_items
        self._more_menu = tk.Menu(parent, tearoff=0)
        for label, cmd in more_items:
            self._more_menu.add_command(label=label, command=cmd)
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

    def _show_more(self):
        try:
            x = self._more_btn.winfo_rootx()
            y = self._more_btn.winfo_rooty() + self._more_btn.winfo_height()
            self._more_menu.tk_popup(x, y)
        finally:
            try:
                self._more_menu.grab_release()
            except Exception:
                pass

    def set_context(self, tab_idx: int) -> None:
        """Emphasize primary actions for the active page."""
        if self._dashboard_mode:
            return
        for btn in (self.tb_scan, self.tb_preview, self.tb_restore):
            btn.configure(fg_color=self._head_bg, hover_color=self._accent_soft)
        self.tb_apply.configure(fg_color=self._head_bg, hover_color=self._accent_soft)
        if tab_idx in (0, 3):
            self.tb_apply.configure(fg_color=self._accent, hover_color=self._accent_dark)
        elif tab_idx in (5, 6):
            self.tb_restore.configure(fg_color=self._accent, hover_color=self._accent_dark)

    def set_page_mode(self, *, dashboard: bool, tab_idx: int = 0) -> None:
        """Home: compact secondary strip. Workspace: integrated workflow bar."""
        self._dashboard_mode = dashboard
        if dashboard:
            self._shell.configure(fg_color=self._bg)
            for btn in (self.tb_scan, self.tb_preview, self.tb_apply, self.tb_restore, self._more_btn):
                btn.configure(fg_color=self._head_bg, hover_color=self._accent_soft, height=30)
            self._proof_flow_lbl.pack_forget()
        else:
            self._shell.configure(fg_color=self._card_bg)
            for btn in (self.tb_scan, self.tb_preview, self.tb_apply, self.tb_restore, self._more_btn):
                btn.configure(height=34)
            self._proof_flow_lbl.pack(side='right', padx=(8, 0))
            self.set_context(tab_idx)

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
    box.pack(fill='x', padx=12, pady=(0, 14))
    ctk_theme.label(
        box, title, text_color=accent, font_size=15, weight='bold',
    ).pack(anchor='w', padx=18, pady=(16, 8))
    body = ctk_theme.frame(box, card_bg, corner_radius=12)
    body.pack(fill='x', padx=18, pady=(0, 16))
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


def settings_section_nav(parent, labels: list[str], *, sidebar_bg: str, accent: str, muted: str, on_select):
    """Horizontal segmented settings nav (legacy); prefer settings_sidebar_nav."""
    row = ctk_theme.frame(parent, sidebar_bg)
    row.pack(fill='x', padx=12, pady=(0, 8))
    buttons = {}
    for label in labels:
        btn = ctk_theme.button(
            row, label, lambda l=label: on_select(l),
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
            anchor='w', height=34, width=width,
        )
        btn.pack(fill='x', pady=2)
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
    default_status: str = 'Ready to prove your cleanup.',
) -> dict:
    """Product identity strip: logo, dynamic title/status, pill badge, accent line."""
    wrap = ctk_theme.frame(parent, bg, corner_radius=10)
    inner = ctk_theme.frame(wrap, bg)
    inner.pack(fill='x', padx=10, pady=(12, 10))

    top_row = ctk_theme.frame(inner, bg)
    top_row.pack(fill='x')

    if logo_photo is not None:
        logo_lbl = tk.Label(top_row, image=logo_photo, bg=bg)
        logo_lbl.image = logo_photo
        logo_lbl.pack(side='left', padx=(0, 8))

    text_col = ctk_theme.frame(top_row, bg)
    text_col.pack(side='left', fill='x', expand=True)

    title_lbl = ctk_theme.label(
        text_col, default_title, text_color=text_color, font_size=14, weight='bold',
    )
    title_lbl.pack(anchor='w')
    status_lbl = ctk_theme.label(
        text_col, default_status, text_color=muted, font_size=9,
        wraplength=168, justify='left',
    )
    status_lbl.pack(anchor='w', pady=(2, 0))

    pill_frame = ctk_theme.frame(inner, accent_soft, corner_radius=10)
    pill_frame.pack(anchor='w', pady=(8, 0))
    pill_lbl = ctk_theme.label(
        pill_frame, 'Local-only proof', text_color=accent, font_size=9, weight='bold',
    )
    pill_lbl.pack(padx=8, pady=3)

    accent_line = ctk_theme.frame(inner, accent, corner_radius=1)
    accent_line.configure(height=2)
    accent_line.pack(fill='x', pady=(10, 0))

    return {
        'frame': wrap,
        'title_lbl': title_lbl,
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
    start_open: bool = True,
) -> tuple[ctk.CTkButton, ctk.CTkFrame]:
    """Collapsible sidebar group; returns (toggle_button, body_frame)."""
    accent_soft = accent_soft or sidebar_bg
    block = ctk_theme.frame(parent, sidebar_bg)
    block.pack(fill='x', padx=4, pady=(0, 10))
    state = {'open': start_open}

    header = ctk_theme.frame(block, accent_soft if start_open else sidebar_bg, corner_radius=8)
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
        hover_color=accent_soft,
        text_color=muted,
        anchor='w',
        height=32,
        font=ctk_theme.font(10, 'bold'),
    )
    toggle.pack(fill='x', padx=10, pady=5)

    def _flip():
        state['open'] = not state['open']
        if state['open']:
            body.pack(fill='x', padx=6, pady=(0, 4))
            header.configure(fg_color=accent_soft)
            toggle.configure(text=f'▾  {title}')
        else:
            body.pack_forget()
            header.configure(fg_color=sidebar_bg)
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
) -> ctk.CTkButton:
    """Full-width sidebar navigation row."""
    return ctk_theme.button(
        parent, label, command,
        fg_color='transparent', hover_color=accent_soft, text_color=text_color,
        anchor='w', height=36, corner_radius=8,
    )
