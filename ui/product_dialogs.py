"""Cleanroom product dialogs — one dark modal / popover style for the whole app."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

import customtkinter as ctk

from ui import ctk_theme

ActionItem = tuple[str, Callable[[], None], bool]  # label, command, enabled
ActionGroup = tuple[str, list[ActionItem]] | tuple[str, list[tuple[str, Callable[[], None], bool]]]
FlatAction = tuple[str, Callable[[], None], bool]


def _palette(**kw) -> dict:
    return {
        'bg': kw.get('bg', '#1a1d24'),
        'card': kw.get('card', '#262c36'),
        'head': kw.get('head', '#2f3640'),
        'accent': kw.get('accent', '#3b82f6'),
        'accent_soft': kw.get('accent_soft', '#1e3a5f'),
        'text': kw.get('text', '#e5e7eb'),
        'muted': kw.get('muted', '#9ca3af'),
        'border': kw.get('border', '#39414e'),
        'on_accent': kw.get('on_accent', '#ffffff'),
        'danger': kw.get('danger', '#ef4444'),
    }


def show_grouped_popover(
    master,
    x: int,
    y: int,
    groups: list[tuple[str, list[tuple[str, Callable[[], None]]]]],
    *,
    colors: dict | None = None,
    width: int = 240,
) -> ctk.CTkToplevel | None:
    """Dark grouped popover menu (More menu, row actions)."""
    if not groups:
        return None
    c = _palette(**(colors or {}))

    pop = ctk.CTkToplevel(master)
    pop.overrideredirect(True)
    pop.configure(fg_color=c['card'])
    try:
        pop.attributes('-topmost', True)
    except Exception:
        pass
    pop.geometry(f'+{x}+{y}')

    shell = ctk.CTkFrame(
        pop, fg_color=c['card'], corner_radius=10,
        border_width=1, border_color=c['border'],
    )
    shell.pack(padx=1, pady=1)
    inner = ctk.CTkFrame(shell, fg_color=c['card'])
    inner.pack(padx=10, pady=10)

    def _close(_e=None):
        try:
            pop.destroy()
        except Exception:
            pass

    pop.bind('<Escape>', _close)
    root = master.winfo_toplevel()

    def _outside(event):
        if not pop.winfo_exists():
            return
        px, py = pop.winfo_rootx(), pop.winfo_rooty()
        pw, ph = max(pop.winfo_width(), 80), max(pop.winfo_height(), 40)
        if px <= event.x_root <= px + pw and py <= event.y_root <= py + ph:
            return
        _close()

    pop.after(60, lambda: root.bind('<Button-1>', _outside, add='+'))
    pop.bind('<Destroy>', lambda _e: root.unbind('<Button-1>'))

    for gi, (section, items) in enumerate(groups):
        if gi:
            ctk.CTkFrame(inner, fg_color=c['border'], height=1).pack(fill='x', pady=(8, 8))
        if section:
            ctk_theme.label(
                inner, section.upper(), text_color=c['accent'],
                font_size=9, weight='bold',
            ).pack(anchor='w', padx=4, pady=(0, 4))
        for entry in items:
            if len(entry) == 3:
                label, cmd, enabled = entry
            else:
                label, cmd = entry
                enabled = True
            state = 'normal' if enabled else 'disabled'
            ctk_theme.button(
                inner, label,
                lambda c=cmd: (c(), _close()),
                fg_color='transparent',
                hover_color=c['accent_soft'],
                text_color=c['muted'] if not enabled else c['text'],
                anchor='w', height=32, width=width,
                state=state,
            ).pack(fill='x', pady=1)

    pop.update_idletasks()
    pop.focus_force()
    return pop


def show_action_popover(
    master,
    x: int,
    y: int,
    items: list[FlatAction],
    *,
    colors: dict | None = None,
    title: str = '',
) -> ctk.CTkToplevel | None:
    """Single-section row action menu."""
    groups: list[tuple[str, list[tuple[str, Callable, bool]]]] = []
    if title:
        groups.append((title, [(a, b, c) for a, b, c in items]))
    else:
        groups.append(('', [(a, b, c) for a, b, c in items]))
    return show_grouped_popover(master, x, y, groups, colors=colors, width=220)


class CleanroomModal:
    """Dark modal shell — card body, headline, actions footer."""

    def __init__(
        self,
        parent,
        title: str,
        *,
        width: int = 520,
        height: int = 360,
        colors: dict | None = None,
        resizable: bool = False,
    ):
        self.colors = _palette(**(colors or {}))
        self.win = ctk.CTkToplevel(parent)
        self.win.title(title)
        self.win.configure(fg_color=self.colors['bg'])
        self.win.transient(parent)
        self.win.grab_set()
        self.win.bind('<Escape>', lambda _e: self.win.destroy())
        if not resizable:
            self.win.resizable(False, False)
        self.win.geometry(f'{width}x{height}')

        outer = ctk.CTkFrame(
            self.win, fg_color=self.colors['card'], corner_radius=12,
            border_width=1, border_color=self.colors['border'],
        )
        outer.pack(fill='both', expand=True, padx=14, pady=14)

        self.body = ctk.CTkFrame(outer, fg_color=self.colors['card'])
        self.body.pack(fill='both', expand=True, padx=16, pady=(16, 8))

        self.footer = ctk.CTkFrame(outer, fg_color=self.colors['card'])
        self.footer.pack(fill='x', padx=16, pady=(0, 16))

    def heading(self, text: str, *, size: int = 16):
        ctk_theme.label(
            self.body, text, text_color=self.colors['accent'],
            font_size=size, weight='bold',
        ).pack(anchor='w')

    def subheading(self, text: str):
        ctk_theme.label(
            self.body, text, text_color=self.colors['muted'],
            font_size=11, wraplength=460, justify='left',
        ).pack(anchor='w', pady=(6, 0))

    def message(self, text: str, *, wrap: int = 460):
        ctk_theme.label(
            self.body, text, text_color=self.colors['text'],
            font_size=11, wraplength=wrap, justify='left',
        ).pack(anchor='w', pady=(12, 0))

    def scroll_text(self, text: str, *, height: int = 220, mono: bool = False):
        wrap = ctk.CTkFrame(self.body, fg_color=self.colors['head'], corner_radius=8)
        wrap.pack(fill='both', expand=True, pady=(12, 0))
        font = ('Consolas', 10) if mono else ('Segoe UI', 10)
        txt = tk.Text(
            wrap, wrap='word', font=font,
            bg=self.colors['head'], fg=self.colors['text'],
            insertbackground=self.colors['text'], relief='flat',
            padx=10, pady=10, height=height // 18,
        )
        scroll = ctk.CTkScrollbar(wrap, command=txt.yview)
        txt.configure(yscrollcommand=scroll.set)
        txt.pack(side='left', fill='both', expand=True, padx=(4, 0), pady=4)
        scroll.pack(side='right', fill='y', padx=(0, 4), pady=4)
        txt.insert('1.0', text)
        txt.configure(state='disabled')
        return txt

    def add_button(self, label: str, command, *, primary: bool = False, side: str = 'right',
                   danger: bool = False):
        fg = self.colors['danger'] if danger else (
            self.colors['accent'] if primary else self.colors['head'])
        hover = self.colors['accent_soft'] if not danger else '#7f1d1d'
        text = self.colors['on_accent'] if primary or danger else self.colors['text']
        btn = ctk_theme.button(
            self.footer, label, command,
            fg_color=fg, hover_color=hover, text_color=text,
            primary=primary or danger, height=34,
        )
        btn.pack(side=side, padx=(8, 0) if side == 'right' else (0, 8))
        return btn

    def close(self):
        try:
            self.win.destroy()
        except Exception:
            pass


def show_summary_modal(
    parent,
    *,
    title: str,
    headline: str,
    body: str,
    colors: dict | None = None,
    buttons: list[tuple[str, Callable, bool]] | None = None,
    width: int = 480,
    height: int = 280,
) -> CleanroomModal:
    dlg = CleanroomModal(parent, title, width=width, height=height, colors=colors)
    dlg.heading(headline)
    dlg.message(body)
    buttons = buttons or [('OK', dlg.close, True)]
    for label, cmd, primary in reversed(buttons):
        dlg.add_button(label, cmd, primary=primary)
    return dlg


def show_report_modal(
    parent,
    *,
    title: str,
    headline: str,
    body: str,
    colors: dict | None = None,
    width: int = 680,
    height: int = 520,
) -> CleanroomModal:
    dlg = CleanroomModal(parent, title, width=width, height=height, colors=colors, resizable=True)
    dlg.heading(headline, size=14)
    dlg.scroll_text(body, height=height - 120, mono=True)
    dlg.add_button('Close', dlg.close, primary=True)
    return dlg
