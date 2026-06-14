#!/usr/bin/env python3
"""In-app Cleanroom receipt viewer — dark product UI with summary + raw text."""
from __future__ import annotations

import os
import re
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path


def _parse_receipt_meta(text: str) -> dict:
    """Best-effort parse of receipt header fields from rendered text."""
    body = text or ''
    meta = {
        'kind': 'Receipt',
        'timestamp': '',
        'items': '',
        'bytes': '',
        'proof': '',
    }
    if 'PRUNE RECEIPT' in body.upper():
        meta['kind'] = 'Prune Archive'
        meta['proof'] = 'Archive-only removal. Original live files were not touched.'
    elif 'PREVIEW ONLY' in body.upper():
        meta['kind'] = 'Preview Receipt'
        meta['proof'] = 'Preview only — nothing has been archived yet.'
    else:
        meta['proof'] = (
            'Nothing was deleted. Archived items can be restored from Restore or Cleanroom Rewind.'
        )

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


class ReceiptViewerDialog(tk.Toplevel):
    """Dark Cleanroom receipt viewer with summary header and raw tab."""

    def __init__(
        self,
        parent,
        text,
        title='Receipt',
        receipt_path=None,
        preview=False,
        bg='#1a1a2e',
        card='#16213e',
        text_fg='#eaeaea',
        accent='#7c9cff',
        muted='#9aa3b2',
    ):
        super().__init__(parent)
        self._receipt_path = Path(receipt_path) if receipt_path else None
        self._text_body = text or ''
        self._bg = bg
        self._card = card
        self._text_fg = text_fg
        self._accent = accent
        self._muted = muted
        self.configure(bg=bg)
        self.title(title)
        self.geometry('640x560')
        self.minsize(480, 400)
        self.transient(parent)
        self.grab_set()
        self.bind('<Escape>', lambda e: self.destroy())

        meta = _parse_receipt_meta(self._text_body)
        if preview:
            meta['kind'] = 'Preview Receipt'
            meta['proof'] = 'Preview only — nothing has been archived yet.'

        shell = tk.Frame(self, bg=card, highlightbackground=accent, highlightthickness=1)
        shell.pack(fill='both', expand=True, padx=14, pady=14)

        head = tk.Frame(shell, bg=card)
        head.pack(fill='x', padx=16, pady=(16, 8))
        tk.Label(
            head, text='Receipt', bg=card, fg=accent,
            font=('Segoe UI', 11, 'bold'),
        ).pack(anchor='w')
        title_line = meta['kind']
        if meta['timestamp']:
            title_line = f"{meta['kind']} · {meta['timestamp']}"
        tk.Label(
            head, text=title_line, bg=card, fg=text_fg,
            font=('Segoe UI', 14, 'bold'), wraplength=560, justify='left',
        ).pack(anchor='w', pady=(4, 0))

        stats = tk.Frame(shell, bg=card)
        stats.pack(fill='x', padx=16, pady=(0, 8))
        if meta['items']:
            tk.Label(
                stats, text=f"Items: {meta['items']}", bg=card, fg=text_fg,
                font=('Segoe UI', 10),
            ).pack(anchor='w')
        if meta['bytes']:
            tk.Label(
                stats, text=f"Size: {meta['bytes']}", bg=card, fg=text_fg,
                font=('Segoe UI', 10),
            ).pack(anchor='w', pady=(2, 0))
        if meta['proof']:
            tk.Label(
                stats, text=meta['proof'], bg=card, fg=muted,
                font=('Segoe UI', 9), wraplength=560, justify='left',
            ).pack(anchor='w', pady=(8, 0))

        nb = ttk.Notebook(shell)
        nb.pack(fill='both', expand=True, padx=12, pady=(4, 8))

        summary_frm = tk.Frame(nb, bg=card)
        nb.add(summary_frm, text='Summary')
        summary = tk.Text(
            summary_frm, wrap='word', font=('Segoe UI', 10),
            bg=card, fg=text_fg, insertbackground=text_fg,
            relief='flat', padx=12, pady=12, height=12,
        )
        summary.pack(fill='both', expand=True)
        summary.insert('1.0', self._summarize_body(meta))
        summary.configure(state='disabled')

        raw_frm = tk.Frame(nb, bg=card)
        nb.add(raw_frm, text='Raw receipt')
        raw_wrap = tk.Frame(raw_frm, bg=card)
        raw_wrap.pack(fill='both', expand=True, padx=4, pady=4)
        self._text = tk.Text(
            raw_wrap, wrap='word', font=('Consolas', 10),
            bg='#0f1419', fg=text_fg, insertbackground=text_fg,
            relief='flat', padx=10, pady=10,
        )
        scroll = ttk.Scrollbar(raw_wrap, orient='vertical', command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        self._text.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self._text.insert('1.0', self._text_body)
        self._text.configure(state='disabled')

        btns = tk.Frame(shell, bg=card)
        btns.pack(fill='x', padx=16, pady=(0, 16))
        tk.Button(
            btns, text='Copy Receipt', command=self._copy,
            bg='#2a3344', fg=text_fg, activebackground='#3a4558',
            relief='flat', padx=12, pady=6, cursor='hand2',
        ).pack(side='left')
        if self._receipt_path:
            tk.Button(
                btns, text='Open Receipt File', command=self._open_file,
                bg='#2a3344', fg=text_fg, activebackground='#3a4558',
                relief='flat', padx=12, pady=6, cursor='hand2',
            ).pack(side='left', padx=(8, 0))
            tk.Button(
                btns, text='Open Receipt Folder', command=self._open_folder,
                bg='#2a3344', fg=text_fg, activebackground='#3a4558',
                relief='flat', padx=12, pady=6, cursor='hand2',
            ).pack(side='left', padx=(8, 0))
        tk.Button(
            btns, text='Close', command=self.destroy,
            bg=accent, fg='#ffffff', activebackground=accent,
            relief='flat', padx=16, pady=6, cursor='hand2',
        ).pack(side='right')

    def _summarize_body(self, meta: dict) -> str:
        lines = [
            f"Type: {meta['kind']}",
        ]
        if meta['timestamp']:
            lines.append(f"When: {meta['timestamp']}")
        if meta['items']:
            lines.append(f"Items: {meta['items']}")
        if meta['bytes']:
            lines.append(f"Total size: {meta['bytes']}")
        lines.append('')
        lines.append(meta.get('proof') or '')
        lines.append('')
        lines.append('Open the Raw receipt tab for the full proof text.')
        return '\n'.join(lines)

    def _copy(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self._text_body)
            self.update_idletasks()
        except tk.TclError:
            messagebox.showinfo('Copy Receipt', 'Clipboard unavailable in this session.')

    def _open_file(self):
        if not self._receipt_path or not self._receipt_path.is_file():
            messagebox.showinfo('Receipt', 'Receipt file not found on disk.')
            return
        try:
            os.startfile(str(self._receipt_path))
        except OSError as e:
            messagebox.showerror('Receipt', f'Unable to open receipt file:\n{e}')

    def _open_folder(self):
        if not self._receipt_path:
            return
        folder = self._receipt_path.parent
        if not folder.is_dir():
            messagebox.showinfo('Receipt', 'Receipt folder not found.')
            return
        try:
            os.startfile(str(folder))
        except OSError as e:
            messagebox.showerror('Receipt', f'Unable to open folder:\n{e}')


def show_receipt(parent, text, receipt_path=None, preview=False, **kwargs):
    return ReceiptViewerDialog(parent, text, receipt_path=receipt_path, preview=preview, **kwargs)
