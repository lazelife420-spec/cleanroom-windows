#!/usr/bin/env python3
"""In-app Cleanroom receipt viewer — branded proof modal with R.E.C.E.I.P.T. identity."""
from __future__ import annotations

import os
import re
import tkinter as tk

import customtkinter as ctk

from ui import ctk_theme
from ui.product_dialogs import CleanroomModal
from ui.receipt_identity import receipt_context


def _parse_receipt_meta(text: str, ctx: dict) -> dict:
    body = text or ''
    meta = {
        'kind': ctx['title'],
        'badge': ctx['badge'],
        'module': ctx['module'],
        'timestamp': '',
        'items': '',
        'bytes': '',
        'proof': ctx.get('safety') or '',
    }
    m = re.search(r'Date:\s+(\S+\s+\S+)', body)
    if m:
        meta['timestamp'] = m.group(1).strip()
    for pat, key in (
        (r'Items moved:\s+(\d+)', 'items'),
        (r'Items pruned:\s+(\d+)', 'items'),
        (r'Space moved:\s+(\S+)', 'bytes'),
        (r'Bytes pruned:\s+(\S+)', 'bytes'),
    ):
        m = re.search(pat, body, re.I)
        if m:
            meta[key] = m.group(1)
    return meta


class ReceiptViewerDialog:
    """Dark Cleanroom receipt modal with proof identity."""

    def __init__(
        self,
        parent,
        text,
        title='Receipt',
        receipt_path=None,
        preview=False,
        module=None,
        action=None,
        action_key=None,
        bg='#1a1d24',
        card='#262c36',
        text_fg='#e5e7eb',
        accent='#3b82f6',
        muted='#9ca3af',
        border='#39414e',
        on_accent='#ffffff',
        **_kwargs,
    ):
        self._receipt_path = receipt_path
        self._text_body = text or ''
        colors = dict(
            bg=bg, card=card, accent=accent, text=text_fg,
            muted=muted, border=border, on_accent=on_accent, head=card,
        )
        ctx = receipt_context(
            self._text_body, module=module, action=action,
            preview=preview, action_key=action_key,
        )
        meta = _parse_receipt_meta(self._text_body, ctx)
        win_title = ctx['title']
        if title and title != 'Receipt' and 'Cleanroom Receipt' in title:
            win_title = title

        self._modal = CleanroomModal(
            parent, win_title, width=680, height=620, colors=colors, resizable=True,
        )
        ctk_theme.label(
            self._modal.body, ctx['acronym'], text_color=accent,
            font_size=11, weight='bold',
        ).pack(anchor='w')
        ctk_theme.label(
            self._modal.body, ctx['expanded'], text_color=muted,
            font_size=9, wraplength=620, justify='left',
        ).pack(anchor='w', pady=(2, 8))

        ctk_theme.label(
            self._modal.body, ctx['title'], text_color=text_fg,
            font_size=16, weight='bold',
        ).pack(anchor='w', pady=(4, 0))
        if meta['timestamp']:
            ctk_theme.label(
                self._modal.body, meta['timestamp'], text_color=muted, font_size=10,
            ).pack(anchor='w', pady=(2, 0))

        if meta['badge']:
            badge_frame = ctk.CTkFrame(self._modal.body, fg_color=accent, corner_radius=6)
            badge_frame.pack(anchor='w', pady=(8, 0))
            ctk_theme.label(
                badge_frame, meta['badge'], text_color=on_accent,
                font_size=10, weight='bold',
            ).pack(padx=10, pady=4)

        stats = ctk.CTkFrame(self._modal.body, fg_color=card)
        stats.pack(fill='x', pady=(10, 0))
        ctk_theme.label(
            stats, f"Module: {meta['module']}", text_color=text_fg, font_size=11,
        ).pack(anchor='w', padx=8, pady=(8, 0))
        if meta['items']:
            ctk_theme.label(
                stats, f"Items: {meta['items']}", text_color=text_fg, font_size=11,
            ).pack(anchor='w', padx=8, pady=(2, 0))
        if meta['bytes']:
            ctk_theme.label(
                stats, f"Size: {meta['bytes']}", text_color=text_fg, font_size=11,
            ).pack(anchor='w', padx=8, pady=(2, 0))
        if meta['proof']:
            ctk_theme.label(
                stats, meta['proof'], text_color=muted,
                font_size=10, wraplength=600, justify='left',
            ).pack(anchor='w', padx=8, pady=(8, 8))

        tabs = ctk.CTkTabview(
            self._modal.body, fg_color=card, segmented_button_fg_color=bg,
            segmented_button_selected_color=accent,
            segmented_button_unselected_color=card,
            text_color=text_fg,
        )
        tabs.pack(fill='both', expand=True, pady=(12, 0))
        summary_tab = tabs.add('Summary')
        raw_tab = tabs.add('Raw receipt')

        summary = tk.Text(
            summary_tab, wrap='word', font=('Segoe UI', 10),
            bg=card, fg=text_fg, relief='flat', padx=8, pady=8,
        )
        summary.pack(fill='both', expand=True)
        summary.insert('1.0', self._summarize_body(meta, ctx))
        summary.configure(state='disabled')

        raw_wrap = ctk.CTkFrame(raw_tab, fg_color=card)
        raw_wrap.pack(fill='both', expand=True)
        raw = tk.Text(
            raw_wrap, wrap='word', font=('Consolas', 10),
            bg='#0f1419', fg=text_fg, relief='flat', padx=10, pady=10,
        )
        scroll = ctk.CTkScrollbar(raw_wrap, command=raw.yview)
        raw.configure(yscrollcommand=scroll.set)
        raw.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        raw.insert('1.0', self._text_body)
        raw.configure(state='disabled')

        self._modal.add_button('Copy Receipt', self._copy, side='left')
        if receipt_path:
            self._modal.add_button('Open Receipt File', self._open_file, side='left')
            self._modal.add_button('Open Receipt Folder', self._open_folder, side='left')
        self._modal.add_button('Close', self._modal.close, primary=True)

    def _summarize_body(self, meta: dict, ctx: dict) -> str:
        lines = [ctx['title'], ctx['acronym'], ctx['expanded'], '']
        if meta['badge']:
            lines.append(f"Status: {meta['badge']}")
        lines.append(f"Module: {meta['module']}")
        if meta['timestamp']:
            lines.append(f"When: {meta['timestamp']}")
        if meta['items']:
            lines.append(f"Items: {meta['items']}")
        if meta['bytes']:
            lines.append(f"Total size: {meta['bytes']}")
        lines.extend(['', meta.get('proof') or '', '', 'See Raw receipt tab for full proof text.'])
        return '\n'.join(lines)

    def _copy(self):
        try:
            root = self._modal.win
            root.clipboard_clear()
            root.clipboard_append(self._text_body)
            root.update_idletasks()
        except tk.TclError:
            pass

    def _open_file(self):
        path = self._receipt_path
        if not path or not os.path.isfile(str(path)):
            return
        try:
            os.startfile(str(path))
        except OSError:
            pass

    def _open_folder(self):
        if not self._receipt_path:
            return
        folder = os.path.dirname(str(self._receipt_path))
        if os.path.isdir(folder):
            try:
                os.startfile(folder)
            except OSError:
                pass


def show_receipt(parent, text, receipt_path=None, preview=False, **kwargs):
    return ReceiptViewerDialog(parent, text, receipt_path=receipt_path, preview=preview, **kwargs)
