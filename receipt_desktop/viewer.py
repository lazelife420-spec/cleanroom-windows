"""RECEIPT Desktop — read-only proof viewer window."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Callable

import customtkinter as ctk

import brand
from receipt_core.export import build_proof_pack_html
from receipt_core.parse import parse_file
from receipt_core.schema import ReceiptType
from receipt_core.validate import CustodyStatus, validate
from receipt_desktop.state import ViewerState

# Dark palette — matches Cleanroom's 'dark' theme.
_P = {
    'BG': '#1E232B',
    'SIDEBAR_BG': '#171C23',
    'CARD': '#262C36',
    'ACCENT': '#3B82F6',
    'ACCENT_SOFT': '#1E3A5F',
    'PROOF': '#22C55E',
    'PROOF_DARK': '#16A34A',
    'PROOF_SOFT': '#143D26',
    'ON_ACCENT': '#FFFFFF',
    'TEXT': '#E5E7EB',
    'MUTED': '#9AA4B2',
    'BORDER': '#39414E',
    'HEAD': '#323A46',
    'PREVIEW': '#1A1F26',
    'DANGER': '#F87171',
}

_LOCAL_ONLY = f'Local-only — no account, no cloud, no telemetry. · {brand.PROOF_FOUNDRY_BYLINE}'
_RECEIPT_ACRONYM = 'R.E.C.E.I.P.T.'
_RECEIPT_EXPANDED = (
    'Record · Evidence · Custody · Event · Integrity · Proof · Timestamp'
)


def _font(size: int, weight: str = 'normal') -> ctk.CTkFont:
    return ctk.CTkFont(family='Segoe UI', size=size, weight=weight)


def _human(n: int) -> str:
    sign = '-' if n < 0 else ''
    n = abs(n)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{sign}{n:.1f}{unit}'
        n /= 1024
    return f'{sign}{n:.1f}PB'


class ReceiptViewerApp(ctk.CTk):
    """Standalone RECEIPT proof viewer.

    Launch via ``ReceiptViewerApp().mainloop()`` or
    ``python -m receipt_desktop.app``.
    """

    def __init__(self, receipt_path: str | None = None):
        super().__init__()
        self.title('RECEIPT — Proof Viewer')
        self.geometry('740x620')
        self.minsize(560, 420)
        self.configure(fg_color=_P['BG'])

        self._state = ViewerState()
        self._on_close: Callable[[], None] | None = None

        self._build_top_bar()
        self._build_tabview()
        self._build_footer()

        if receipt_path:
            self.after(100, lambda: self.load_receipt(receipt_path))

    # ------------------------------------------------------------------
    # layout
    # ------------------------------------------------------------------

    def _build_top_bar(self):
        bar = ctk.CTkFrame(self, fg_color=_P['CARD'], corner_radius=0)
        bar.pack(fill='x')

        left = ctk.CTkFrame(bar, fg_color='transparent')
        left.pack(side='left', padx=16, pady=(14, 10))

        ctk.CTkLabel(
            left, text=_RECEIPT_ACRONYM,
            text_color=_P['ACCENT'], font=_font(18, 'bold'),
        ).pack(anchor='w')

        ctk.CTkLabel(
            left, text=_RECEIPT_EXPANDED,
            text_color=_P['MUTED'], font=_font(9),
        ).pack(anchor='w', pady=(2, 0))
        ctk.CTkLabel(
            left, text=brand.APP_BRAND_BYLINE,
            text_color=_P['MUTED'], font=_font(9),
        ).pack(anchor='w', pady=(2, 0))

        right = ctk.CTkFrame(bar, fg_color='transparent')
        right.pack(side='right', padx=12, pady=(14, 10))

        self._export_btn = ctk.CTkButton(
            right, text='Export Proof Pack', command=self._export_proof_pack,
            fg_color=_P['HEAD'], hover_color=_P['ACCENT_SOFT'],
            text_color=_P['TEXT'], font=_font(11), corner_radius=6,
            height=32,
        )
        self._export_btn.pack(side='left', padx=(0, 8))

        self._open_btn = ctk.CTkButton(
            right, text='Open Receipt', command=self._prompt_open,
            fg_color=_P['ACCENT'], hover_color=_P['ACCENT_SOFT'],
            text_color=_P['ON_ACCENT'], font=_font(11, 'bold'),
            corner_radius=6, height=32,
        )
        self._open_btn.pack(side='left')

    def _build_tabview(self):
        self._tabs = ctk.CTkTabview(
            self,
            fg_color=_P['CARD'],
            segmented_button_fg_color=_P['HEAD'],
            segmented_button_selected_color=_P['ACCENT'],
            segmented_button_unselected_color=_P['HEAD'],
            segmented_button_selected_hover_color=_P['ACCENT_SOFT'],
            text_color=_P['TEXT'],
        )
        self._tabs.pack(fill='both', expand=True, padx=16, pady=(8, 4))

        for name in ('Summary', 'Artifacts', 'Custody', 'Raw Receipt'):
            self._tabs.add(name)

        # --- Summary tab ---
        s = self._tabs.tab('Summary')
        self._sum_header = ctk.CTkLabel(
            s, text='No receipt loaded', text_color=_P['MUTED'],
            font=_font(13), anchor='w',
        )
        self._sum_header.pack(anchor='w', padx=16, pady=(16, 4))

        self._sum_stats = ctk.CTkFrame(s, fg_color=_P['BG'], corner_radius=8)
        self._sum_stats.pack(fill='x', padx=16, pady=(4, 12))
        self._sum_stats_labels: list[tuple[ctk.CTkLabel, ctk.CTkLabel]] = []

        self._sum_safety = ctk.CTkLabel(
            s, text='', text_color=_P['PROOF'], font=_font(11), anchor='w',
        )
        self._sum_safety.pack(anchor='w', padx=16, pady=(0, 8))

        self._sum_warnings = ctk.CTkFrame(s, fg_color='transparent')
        self._sum_warnings.pack(fill='x', padx=16)

        # --- Artifacts tab ---
        a = self._tabs.tab('Artifacts')
        self._art_frame = ctk.CTkScrollableFrame(a, fg_color=_P['CARD'])
        self._art_frame.pack(fill='both', expand=True, padx=0, pady=0)

        # --- Custody tab ---
        c_ = self._tabs.tab('Custody')

        self._cust_status_card = ctk.CTkFrame(c_, fg_color=_P['BG'], corner_radius=10)
        self._cust_status_card.pack(fill='x', padx=16, pady=(16, 8))

        self._cust_status_badge = ctk.CTkLabel(
            self._cust_status_card, text='No receipt loaded',
            text_color=_P['MUTED'], font=_font(14, 'bold'), anchor='w',
        )
        self._cust_status_badge.pack(anchor='w', padx=16, pady=(12, 4))

        self._cust_status_trust = ctk.CTkLabel(
            self._cust_status_card, text='',
            text_color=_P['PROOF'], font=_font(32, 'bold'), anchor='w',
        )
        self._cust_status_trust.pack(anchor='w', padx=16, pady=(0, 8))

        self._cust_status_explain = ctk.CTkLabel(
            self._cust_status_card, text='',
            text_color=_P['MUTED'], font=_font(11), anchor='w',
            wraplength=660, justify='left',
        )
        self._cust_status_explain.pack(anchor='w', padx=16, pady=(0, 12))

        # counts bar
        self._cust_counts_frame = ctk.CTkFrame(c_, fg_color=_P['CARD'])
        self._cust_counts_frame.pack(fill='x', padx=16, pady=(0, 4))
        self._cust_counts_labels: list[ctk.CTkLabel] = []

        # missing items section
        self._cust_missing_frame = ctk.CTkFrame(
            c_, fg_color=_P['BG'], corner_radius=8)
        self._cust_missing_frame.pack(fill='both', expand=True, padx=16, pady=(4, 4))

        self._cust_missing_list = ctk.CTkFrame(
            self._cust_missing_frame, fg_color='transparent')
        self._cust_missing_list.pack(fill='both', expand=True, padx=0, pady=(4, 0))

        # copy button
        btn_row = ctk.CTkFrame(c_, fg_color='transparent')
        btn_row.pack(fill='x', padx=16, pady=(4, 12))

        self._cust_copy_btn = ctk.CTkButton(
            btn_row, text='Copy Custody Summary', command=self._copy_custody,
            fg_color=_P['HEAD'], hover_color=_P['ACCENT_SOFT'],
            text_color=_P['TEXT'], font=_font(10), corner_radius=6,
            height=28,
        )
        self._cust_copy_btn.pack(side='left')

        # --- Raw Receipt tab ---
        r = self._tabs.tab('Raw Receipt')
        self._raw_frame = ctk.CTkFrame(r, fg_color=_P['PREVIEW'], corner_radius=8)
        self._raw_frame.pack(fill='both', expand=True, padx=8, pady=8)
        self._raw_text = tk.Text(
            self._raw_frame, wrap='word',
            font=('Consolas', 10),
            bg=_P['PREVIEW'], fg=_P['TEXT'],
            insertbackground=_P['TEXT'], relief='flat',
            padx=12, pady=10,
        )
        raw_scroll = ctk.CTkScrollbar(
            self._raw_frame, command=self._raw_text.yview)
        self._raw_text.configure(yscrollcommand=raw_scroll.set)
        self._raw_text.pack(side='left', fill='both', expand=True)
        raw_scroll.pack(side='right', fill='y')
        self._raw_text.insert('1.0', 'Open a receipt to view its raw content.')
        self._raw_text.configure(state='disabled')

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=_P['SIDEBAR_BG'], corner_radius=0, height=32)
        footer.pack(fill='x', side='bottom')
        footer.pack_propagate(False)

        self._status = ctk.CTkLabel(
            footer, text=_LOCAL_ONLY,
            text_color=_P['MUTED'], font=_font(9), anchor='w',
        )
        self._status.pack(side='left', padx=16, pady=6)

        self._trust_badge = ctk.CTkLabel(
            footer, text='', text_color=_P['PROOF'], font=_font(10, 'bold'),
            anchor='e',
        )
        self._trust_badge.pack(side='right', padx=16, pady=6)

    # ------------------------------------------------------------------
    # load and display
    # ------------------------------------------------------------------

    def load_receipt(self, path: str) -> None:
        """Load a receipt file, parse, validate, and refresh all views."""
        p = Path(path)
        if not p.is_file():
            self._state = ViewerState(error=f'File not found: {path}')
            self._render_error()
            return

        try:
            receipt = parse_file(p)
        except Exception as exc:
            self._state = ViewerState(error=f'Parse error: {exc}')
            self._render_error()
            return

        result = validate(receipt)
        self._state = ViewerState(
            receipt=receipt, result=result, file_path=str(p),
        )

        self.title(f'RECEIPT — {p.name}')
        self._status.configure(text=f'{p.name}  |  {_LOCAL_ONLY}')
        self._render_summary()
        self._render_artifacts()
        self._render_custody()
        self._render_raw()

        trust = self._state.trust_display
        self._trust_badge.configure(
            text=f'Trust: {trust}',
            text_color=_P['PROOF'] if trust == '100/100' else _P['DANGER'],
        )

    def _prompt_open(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title='Open Receipt',
            filetypes=[
                ('Cleanroom receipts', '*.cleanroom-receipt'),
                ('Legacy receipt text', '*.txt'),
                ('All files', '*.*'),
            ],
        )
        if path:
            self.load_receipt(path)

    # ------------------------------------------------------------------
    # summary tab
    # ------------------------------------------------------------------

    def _render_summary(self):
        receipt = self._state.receipt
        if receipt is None:
            return

        rtype = receipt.receipt_type.value.replace('_', ' ').title()
        self._sum_header.configure(text=f'{rtype} Receipt', text_color=_P['TEXT'])

        for lbl, val in self._sum_stats_labels:
            lbl.destroy()
            val.destroy()
        self._sum_stats_labels.clear()

        rows = [
            ('Date', receipt.created_at or 'Unknown'),
            ('Items', str(receipt.artifact_count)),
            ('Space', _human(receipt.total_bytes_claimed)),
            ('Producer', f'{receipt.producer_app} {receipt.producer_version}'.strip()),
        ]
        if receipt.legacy:
            rows.append(('Format', 'Legacy (.txt)'))

        for i, (label, value) in enumerate(rows):
            lbl = ctk.CTkLabel(
                self._sum_stats, text=label,
                text_color=_P['MUTED'], font=_font(10),
            )
            lbl.grid(row=i, column=0, sticky='w', padx=(16, 8), pady=4)
            val = ctk.CTkLabel(
                self._sum_stats, text=value,
                text_color=_P['TEXT'], font=_font(10, 'bold'),
            )
            val.grid(row=i, column=1, sticky='w', padx=(0, 16), pady=4)
            self._sum_stats_labels.append((lbl, val))

        safety = {
            ReceiptType.CLEANUP:
                'Nothing was deleted. Archived items remain in custody '
                'and can be restored.',
            ReceiptType.PREVIEW:
                'Preview only — no files were archived or deleted.',
            ReceiptType.PRUNE:
                'Archive-only removal. Original live files were not touched.',
            ReceiptType.UNKNOWN_LEGACY:
                'Partial receipt — some fields could not be parsed.',
        }.get(receipt.receipt_type, '')
        self._sum_safety.configure(text=safety)

        for w in self._sum_warnings.winfo_children():
            w.destroy()
        if receipt.warnings:
            ctk.CTkLabel(
                self._sum_warnings, text='Warnings',
                text_color=_P['MUTED'], font=_font(10, 'bold'),
            ).pack(anchor='w', padx=16)
            for w in receipt.warnings:
                ctk.CTkLabel(
                    self._sum_warnings, text=f'  {w}',
                    text_color=_P['MUTED'], font=_font(10),
                    anchor='w', justify='left',
                ).pack(anchor='w', padx=16)

    # ------------------------------------------------------------------
    # artifacts tab
    # ------------------------------------------------------------------

    def _render_artifacts(self):
        receipt = self._state.receipt
        if receipt is None:
            return

        for w in self._art_frame.winfo_children():
            w.destroy()

        artifacts = [a for a in receipt.artifacts
                     if a.archive_path and a.action != 'summary']
        if not artifacts:
            ctk.CTkLabel(
                self._art_frame,
                text='No individual artifact records in this receipt.',
                text_color=_P['MUTED'], font=_font(11),
            ).pack(padx=16, pady=16)
            return

        hdr = ctk.CTkFrame(self._art_frame, fg_color=_P['HEAD'])
        hdr.pack(fill='x', padx=4, pady=(4, 2))
        for col, w in (('Path', 360), ('Size', 90), ('Action', 90), ('Reason', 120)):
            ctk.CTkLabel(
                hdr, text=col, text_color=_P['MUTED'],
                font=_font(9, 'bold'), width=w, anchor='w',
            ).pack(side='left', padx=4, pady=4)

        for a in artifacts:
            row = ctk.CTkFrame(self._art_frame, fg_color=_P['BG'])
            row.pack(fill='x', padx=4, pady=1)
            ctk.CTkLabel(
                row, text=a.archive_path, text_color=_P['TEXT'],
                font=_font(10), width=360, anchor='w',
            ).pack(side='left', padx=4, pady=3)
            ctk.CTkLabel(
                row, text=_human(a.size_bytes), text_color=_P['MUTED'],
                font=_font(10), width=90, anchor='w',
            ).pack(side='left', padx=4, pady=3)
            ctk.CTkLabel(
                row, text=a.action, text_color=_P['MUTED'],
                font=_font(10), width=90, anchor='w',
            ).pack(side='left', padx=4, pady=3)
            ctk.CTkLabel(
                row, text=a.reason, text_color=_P['MUTED'],
                font=_font(10), width=120, anchor='w',
            ).pack(side='left', padx=4, pady=3)

    # ------------------------------------------------------------------
    # custody tab
    # ------------------------------------------------------------------

    _CUSTODY_COPY = {
        CustodyStatus.VERIFIED: (
            'Verified', 'Custody verified',
            'All referenced archive artifacts are present.',
            _P['PROOF'],
        ),
        CustodyStatus.GAPS_DETECTED: (
            'Gaps detected', 'Custody gaps detected',
            'Some referenced archive artifacts are missing. This usually '
            'means they were pruned, moved, or deleted outside the producer app.',
            _P['DANGER'],
        ),
        CustodyStatus.NO_ARTIFACT_PATHS: (
            'Partial receipt', 'Partial receipt',
            'This older receipt does not include enough structured '
            'artifact data for a full custody check.',
            _P['MUTED'],
        ),
        CustodyStatus.UNKNOWN: (
            'Unknown', 'Unknown',
            'Unable to determine custody status — no proof data available.',
            _P['MUTED'],
        ),
    }

    def _render_custody(self):
        receipt = self._state.receipt
        result = self._state.result
        if result is None or receipt is None:
            return

        is_pruned = receipt.receipt_type == ReceiptType.PRUNE
        status = result.custody_status
        trust = self._state.trust_display

        if is_pruned:
            badge = 'Pruned by receipt'
            title = 'Pruned by receipt'
            explain = (
                'This receipt records a prune action. Archived copies '
                'were permanently removed from the archive, so custody '
                'verification does not apply to pruned items.'
            )
            color = _P['MUTED']
        else:
            _, title, explain, color = self._CUSTODY_COPY.get(
                status, self._CUSTODY_COPY[CustodyStatus.UNKNOWN])
            badge = title

        self._cust_status_badge.configure(text=badge, text_color=color)
        self._cust_status_trust.configure(
            text=trust, text_color=color if trust != '100/100' else _P['PROOF'])
        self._cust_status_explain.configure(text=explain, text_color=_P['MUTED'])

        # counts
        for lbl in self._cust_counts_labels:
            lbl.destroy()
        self._cust_counts_labels.clear()

        if not is_pruned and result.total_count > 0:
            counts = ctk.CTkFrame(
                self._cust_counts_frame, fg_color='transparent')
            counts.pack(fill='x', padx=16, pady=8)
            self._cust_counts_labels.append(counts)

            for col, val, col_color in (
                ('Verified', str(result.verified_count), _P['PROOF']),
                ('Missing', str(result.missing_count),
                 _P['DANGER'] if result.missing_count > 0 else _P['MUTED']),
                ('Total', str(result.total_count), _P['TEXT']),
            ):
                ctk.CTkLabel(
                    counts, text=f'{col}: {val}',
                    text_color=col_color, font=_font(11, 'bold'),
                ).pack(side='left', padx=(0, 24))

        # missing items list
        for w in self._cust_missing_list.winfo_children():
            w.destroy()
        if result.errors:
            for e in result.errors:
                color = _P['DANGER'] if 'missing:' in e else _P['MUTED']
                ctk.CTkLabel(
                    self._cust_missing_list, text=e,
                    text_color=color, font=_font(10),
                    anchor='w', justify='left',
                ).pack(anchor='w', padx=12, pady=2)
        elif is_pruned:
            ctk.CTkLabel(
                self._cust_missing_list,
                text='No custody gaps — this is a prune receipt.',
                text_color=_P['MUTED'], font=_font(10),
                anchor='w', justify='left',
            ).pack(anchor='w', padx=12, pady=8)

    def _build_custody_summary_text(self) -> str:
        """Build a human-readable custody summary for clipboard."""
        state = self._state
        receipt = state.receipt
        result = state.result
        if result is None or receipt is None:
            return 'No receipt loaded.'

        status = result.custody_status
        is_pruned = receipt.receipt_type == ReceiptType.PRUNE
        trust = state.trust_display

        if is_pruned:
            return (
                f'RECEIPT Custody Summary\n'
                f'========================\n'
                f'Status:   Pruned by receipt\n'
                f'Trust:    {trust}\n'
                f'\n'
                f'This receipt records a prune action. Archived copies '
                f'were permanently removed from the archive.'
            )

        _, title, explain, _ = self._CUSTODY_COPY.get(
            status, self._CUSTODY_COPY[CustodyStatus.UNKNOWN])

        lines = [
            'RECEIPT Custody Summary',
            '========================',
            f'Status:   {title}',
            f'Trust:    {trust}',
        ]
        if result.total_count > 0:
            lines.append(f'Verified: {result.verified_count}/{result.total_count}')
            lines.append(f'Missing:  {result.missing_count}/{result.total_count}')
        lines.append('')
        lines.append(explain)
        if result.errors:
            lines.append('')
            for e in result.errors:
                lines.append(e)
        return '\n'.join(lines)

    def _copy_custody(self) -> None:
        text = self._build_custody_summary_text()
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
        except tk.TclError:
            pass  # clipboard unavailable — silently ignore

    def _export_proof_pack(self) -> None:
        """Export a local HTML proof pack from the currently loaded receipt."""
        receipt = self._state.receipt
        if receipt is None:
            return

        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            title='Export Proof Pack',
            defaultextension='.html',
            filetypes=[('HTML files', '*.html'), ('All files', '*.*')],
            initialfile=f'receipt-proof-pack-{receipt.receipt_type.value}.html',
        )
        if not path:
            return

        html_content = build_proof_pack_html(receipt, result=self._state.result)
        try:
            Path(path).write_text(html_content, encoding='utf-8')
        except OSError:
            pass  # silently skip write failures

    # ------------------------------------------------------------------
    # raw tab
    # ------------------------------------------------------------------

    def _render_raw(self):
        receipt = self._state.receipt
        if receipt is None:
            return

        self._raw_text.configure(state='normal')
        self._raw_text.delete('1.0', 'end')
        self._raw_text.insert('1.0', receipt.raw_text or '(empty receipt)')
        self._raw_text.configure(state='disabled')

    # ------------------------------------------------------------------
    # error state
    # ------------------------------------------------------------------

    def _render_error(self):
        self.title('RECEIPT — Error')
        self._status.configure(text=_LOCAL_ONLY)
        self._trust_badge.configure(text='')
        self._sum_header.configure(
            text=f'Error: {self._state.error}', text_color=_P['DANGER'])

    # ------------------------------------------------------------------
    # close behaviour
    # ------------------------------------------------------------------

    def set_on_close(self, callback: Callable[[], None]) -> None:
        self._on_close = callback

    def destroy(self) -> None:
        if self._on_close:
            self._on_close()
        super().destroy()
