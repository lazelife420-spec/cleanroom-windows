#!/usr/bin/env python3
"""In-app Cleanroom receipt viewer — supplements, never replaces, .txt proof files."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


class ReceiptViewerDialog(tk.Toplevel):
    """Native receipt panel with optional external open."""

    def __init__(self, parent, text, title='Cleanroom Receipt', receipt_path=None,
                 preview=False, bg='#1a1a2e', card='#16213e', text_fg='#eaeaea',
                 receipt_available=False, open_in_receipt=None):
        super().__init__(parent)
        self._receipt_path = Path(receipt_path) if receipt_path else None
        self._text_body = text or ''
        # Optional hand-off to the standalone RECEIPT proof viewer. The button
        # stays hidden unless RECEIPT is available AND we have a file on disk.
        self._open_in_receipt_cb = open_in_receipt
        self._receipt_available = bool(receipt_available)
        self.configure(bg=bg)
        self.title(title)
        self.geometry('620x520')
        self.minsize(480, 360)
        self.transient(parent)
        self.grab_set()
        self.bind('<Escape>', lambda e: self.destroy())

        head = ttk.Frame(self)
        head.pack(fill='x', padx=14, pady=(12, 4))
        ttk.Label(head, text='CLEANROOM — RECEIPT', font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Label(head, text='Clean safely. Prove everything. Undo anytime.',
                  font=('Segoe UI', 9)).pack(anchor='w', pady=(2, 0))
        if preview:
            ttk.Label(head, text='Preview only — nothing archived yet.',
                      foreground='#fbbf24').pack(anchor='w', pady=(4, 0))

        wrap = ttk.Frame(self)
        wrap.pack(fill='both', expand=True, padx=14, pady=8)
        self._text = tk.Text(
            wrap, wrap='word', font=('Consolas', 10),
            bg=card, fg=text_fg, insertbackground=text_fg,
            relief='flat', padx=10, pady=10,
        )
        scroll = ttk.Scrollbar(wrap, orient='vertical', command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        self._text.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self._text.insert('1.0', self._text_body)
        self._text.configure(state='disabled')

        btns = ttk.Frame(self)
        btns.pack(fill='x', padx=14, pady=(0, 12))
        ttk.Button(btns, text='Copy Receipt', command=self._copy).pack(side='left')
        if self._receipt_path:
            ttk.Button(btns, text='Open Receipt File',
                       command=self._open_file).pack(side='left', padx=(6, 0))
            ttk.Button(btns, text='Open Receipt Folder',
                       command=self._open_folder).pack(side='left', padx=(6, 0))
            # Hidden entirely unless RECEIPT is available — no disabled button.
            if self._receipt_available and self._open_in_receipt_cb:
                ttk.Button(btns, text='Open in RECEIPT',
                           command=self._open_in_receipt).pack(side='left', padx=(6, 0))
        ttk.Button(btns, text='Close Receipt', command=self.destroy).pack(side='right')

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

    def _open_in_receipt(self):
        if not self._open_in_receipt_cb or not self._receipt_path:
            return
        ok, err = self._open_in_receipt_cb(str(self._receipt_path))
        if not ok:
            detail = err or 'RECEIPT could not be opened.'
            messagebox.showinfo(
                'Open in RECEIPT',
                f"{detail}\n\n"
                "Cleanroom's built-in receipt view is still fully available here. "
                "RECEIPT is an optional, local-only proof viewer — nothing is "
                "uploaded.")


def show_receipt(parent, text, receipt_path=None, preview=False,
                 receipt_available=False, open_in_receipt=None, **kwargs):
    return ReceiptViewerDialog(
        parent, text, receipt_path=receipt_path, preview=preview,
        receipt_available=receipt_available, open_in_receipt=open_in_receipt,
        **kwargs)
