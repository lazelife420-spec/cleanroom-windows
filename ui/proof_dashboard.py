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
        self.frame = ctk_theme.frame(parent, bg)
        self.frame.pack(fill='x', anchor='w', pady=(6, 0))
        inner = self.frame
        self._primary = ctk_theme.frame(inner, bg)
        self._primary.pack(side='left')

        self.tb_scan = ctk_theme.button(
            self._primary, 'Scan', on_scan,
            fg_color=head_bg, hover_color=accent_soft, text_color=text,
        )
        self.tb_scan.pack(side='left', padx=(0, 6))
        self.tb_preview = ctk_theme.button(
            self._primary, 'Preview Receipt', on_preview,
            fg_color=head_bg, hover_color=accent_soft, text_color=text,
        )
        self.tb_preview.pack(side='left', padx=(0, 6))
        self.tb_apply = ctk_theme.button(
            self._primary, 'Archive & Clean', on_apply,
            fg_color=accent, hover_color=accent_dark, text_color=on_accent, primary=True,
        )
        self.tb_apply.pack(side='left', padx=(0, 6))
        self.tb_restore = ctk_theme.button(
            self._primary, 'Restore', on_restore,
            fg_color=head_bg, hover_color=accent_soft, text_color=text,
        )
        self.tb_restore.pack(side='left', padx=(0, 6))

        self._more_items = more_items
        self._more_menu = tk.Menu(parent, tearoff=0)
        for label, cmd in more_items:
            self._more_menu.add_command(label=label, command=cmd)
        self._more_btn = ctk_theme.button(
            inner, 'More ▾', self._show_more,
            fg_color=head_bg, hover_color=accent_soft, text_color=text, width=72,
        )
        self._more_btn.pack(side='left', padx=(0, 8))

        self._head_bg = head_bg
        self._accent = accent
        self._accent_dark = accent_dark
        self._accent_soft = accent_soft

        flow = ctk_theme.label(
            inner, ctk_theme.PROOF_FLOW_TEXT, text_color=text, font_size=9,
        )
        self._proof_flow_lbl = flow
        flow.pack(side='right', padx=(8, 0))

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
        """Emphasize primary actions for the active page (buttons stay visible for layout gates)."""
        primary = {0, 3}
        restore_emphasis = {5, 6}
        for btn, fg, hover in (
            (self.tb_scan, self._head_bg, self._accent_soft),
            (self.tb_preview, self._head_bg, self._accent_soft),
            (self.tb_apply, self._accent, self._accent_dark),
            (self.tb_restore, self._head_bg, self._accent_soft),
        ):
            btn.configure(fg_color=fg, hover_color=hover)
        if tab_idx in primary:
            self.tb_apply.configure(fg_color=self._accent, hover_color=self._accent_dark)
        elif tab_idx in restore_emphasis:
            self.tb_restore.configure(fg_color=self._accent, hover_color=self._accent_dark)

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


def settings_card(parent, title: str, *, card_bg: str, accent: str) -> ctk.CTkFrame:
    """Settings section card with heading."""
    box = ctk_theme.frame(parent, card_bg, corner_radius=12)
    box.pack(fill='x', padx=12, pady=(0, 12))
    ctk_theme.label(
        box, title, text_color=accent, font_size=14, weight='bold',
    ).pack(anchor='w', padx=16, pady=(14, 6))
    body = ctk_theme.frame(box, card_bg, corner_radius=12)
    body.pack(fill='x', padx=16, pady=(0, 14))
    return body


def sidebar_section(parent, title: str, *, sidebar_bg: str, muted: str) -> ctk.CTkFrame:
    """Sidebar group label + container."""
    ctk_theme.label(
        parent, title, text_color=muted, font_size=10, weight='bold',
    ).pack(anchor='w', padx=10, pady=(8, 2))
    wrap = ctk_theme.frame(parent, sidebar_bg)
    wrap.pack(fill='x', padx=4)
    return wrap
