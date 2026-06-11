"""Local-only receipt printer panel — proof moments only (no fake progress)."""
from __future__ import annotations

import os
import tkinter as tk

DEFAULT_LINES = (
    'CLEANROOM — RECEIPT',
    'Archive-first: ON',
    'Measured: verified',
    'Custody: checked',
    'Ledger: updated',
    'Rollback: available',
)

PREVIEW_LINES = (
    'CLEANROOM — RECEIPT',
    'Archive-first: ON',
    'Mode: preview draft',
    'Measured: pending',
    'Custody: pending',
    'Rollback: available',
)

PROOF_PACK_LINES = (
    'CLEANROOM — PROOF PACK',
    'Archive-first: ON',
    'Measured: verified',
    'Custody: checked',
    'Ledger: updated',
    'Rollback: available',
)


def animations_disabled() -> bool:
    """True when animations should be skipped (CI, screenshots, headless)."""
    v = os.environ.get('CLEANROOM_DISABLE_ANIMATIONS', '').strip().lower()
    return v in ('1', 'true', 'yes', 'on')


class ReceiptPrinterPanel(tk.Frame):
    """Small right-side panel: paper slides down, lines type in, stamp appears."""

    PAPER_H = 168

    def __init__(
        self,
        master,
        *,
        width=240,
        height=200,
        panel_bg='#262C36',
        paper_bg='#E8EDF4',
        accent='#3B82F6',
        text_color='#1F2937',
        muted='#6B7280',
        border='#39414E',
    ):
        super().__init__(
            master,
            bg=panel_bg,
            width=width,
            height=height,
            highlightbackground=border,
            highlightthickness=1,
        )
        self.pack_propagate(False)
        self._panel_bg = panel_bg
        self._paper_bg = paper_bg
        self._accent = accent
        self._text_color = text_color
        self._muted = muted
        self._border = border
        self._job_ids: list[str] = []
        self._on_complete = None
        self._playing = False

        tk.Label(
            self, text='PROOF OUTPUT', bg=panel_bg, fg=muted,
            font=('Segoe UI', 7, 'bold'),
        ).pack(anchor='w', padx=8, pady=(6, 2))

        self._slot = tk.Frame(self, bg=panel_bg, height=height - 28)
        self._slot.pack(fill='both', expand=True, padx=6, pady=(0, 6))
        self._slot.pack_propagate(False)

        tk.Frame(self._slot, bg=border, height=4).place(relx=0, rely=0, relwidth=1, height=4)

        self._paper = tk.Frame(
            self._slot, bg=paper_bg,
            highlightbackground=border, highlightthickness=1,
        )

        inner = tk.Frame(self._paper, bg=paper_bg)
        inner.pack(fill='both', expand=True, padx=8, pady=8)

        self._line_labels: list[tk.Label] = []
        for _ in range(len(DEFAULT_LINES)):
            lbl = tk.Label(
                inner, text='', bg=paper_bg, fg=text_color if _ == 0 else muted,
                font=('Consolas', 7, 'bold' if _ == 0 else 'normal'),
                anchor='w',
            )
            lbl.pack(fill='x', pady=1)
            self._line_labels.append(lbl)

        self._stamp_lbl = tk.Label(
            inner, text='', bg=paper_bg, fg=accent,
            font=('Segoe UI', 7, 'bold'), anchor='w',
        )
        self._stamp_lbl.pack(fill='x', pady=(8, 0))

        self._idle_lbl = tk.Label(
            self._slot, text='Awaiting proof…', bg=panel_bg, fg=muted,
            font=('Segoe UI', 8),
        )
        self._idle_lbl.place(relx=0.5, rely=0.55, anchor='center')

        self.bind('<Button-1>', self._skip)
        self._slot.bind('<Button-1>', self._skip)
        self._paper.bind('<Button-1>', self._skip)
        inner.bind('<Button-1>', self._skip)

    def _cancel_jobs(self):
        for jid in self._job_ids:
            try:
                self.after_cancel(jid)
            except Exception:
                pass
        self._job_ids.clear()

    def _skip(self, _event=None):
        if not self._playing:
            return
        cb = self._on_complete
        self._finish(reset_idle=True)
        if cb:
            cb()

    def _finish(self, reset_idle=False):
        self._cancel_jobs()
        self._playing = False
        self._on_complete = None
        if reset_idle:
            self._paper.place_forget()
            self._idle_lbl.place(relx=0.5, rely=0.55, anchor='center')
            for lbl in self._line_labels:
                lbl.config(text='')
            self._stamp_lbl.config(text='')

    def play(self, stamp: str, lines=None, on_complete=None, duration_ms=900):
        """Animate receipt output; invoke on_complete when finished or skipped."""
        self._cancel_jobs()
        if animations_disabled():
            if on_complete:
                self.after(0, on_complete)
            return

        lines = tuple(lines) if lines else DEFAULT_LINES
        n_lines = min(len(lines), len(self._line_labels))
        self._playing = True
        self._on_complete = on_complete
        self._idle_lbl.place_forget()

        for i, lbl in enumerate(self._line_labels):
            lbl.config(text='')
            lbl.config(
                fg=self._text_color if i == 0 else self._muted,
                font=('Consolas', 7, 'bold' if i == 0 else 'normal'),
            )
        self._stamp_lbl.config(text='')

        start_y = -self.PAPER_H
        target_y = 8
        slide_ms = 220
        stamp_ms = 220
        line_ms = max(55, int((duration_ms - slide_ms - stamp_ms) / max(n_lines, 1)))
        slide_steps = 8

        def slide_step(step):
            if not self._playing:
                return
            t = step / slide_steps
            y = int(start_y + (target_y - start_y) * t)
            self._paper.place(relx=0.04, y=y, relwidth=0.92, height=self.PAPER_H)
            if step < slide_steps:
                jid = self.after(int(slide_ms / slide_steps), lambda s=step + 1: slide_step(s))
                self._job_ids.append(jid)
            else:
                show_line(0)

        def show_line(idx):
            if not self._playing:
                return
            if idx < n_lines:
                self._line_labels[idx].config(text=lines[idx])
                jid = self.after(line_ms, lambda i=idx + 1: show_line(i))
                self._job_ids.append(jid)
            else:
                show_stamp()

        def show_stamp():
            if not self._playing:
                return
            self._stamp_lbl.config(text=stamp)
            jid = self.after(stamp_ms, done)
            self._job_ids.append(jid)

        def done():
            if not self._playing:
                return
            cb = self._on_complete
            self._finish(reset_idle=True)
            if cb:
                cb()

        slide_step(0)


def play_receipt_animation(panel, stamp, lines=None, on_complete=None, duration_ms=900):
    """Convenience wrapper — skips straight to on_complete if panel is None."""
    if panel is None:
        if on_complete:
            on_complete()
        return
    panel.play(stamp, lines=lines, on_complete=on_complete, duration_ms=duration_ms)
