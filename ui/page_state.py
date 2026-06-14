"""Shared page state model — one truthful state per page at a time."""
from __future__ import annotations

IDLE_READY = 'idle_ready'
LOADING = 'loading'
EMPTY_DONE = 'empty_done'
RESULTS_READY = 'results_ready'
RECEIPT_READY = 'receipt_ready'
ERROR = 'error'


def cleaner_page_state(
    *,
    loading: bool = False,
    error: str = '',
    count: int = 0,
    checked: int = 0,
    scan_done: bool = False,
    cached_count: int = 0,
) -> tuple[str, str, str, str]:
    """Return (state, hero_title, hero_subtitle, footer_status)."""
    if loading:
        return (
            LOADING,
            'Scanning…',
            'Reviewing configured folders for candidates.',
            'Scanning configured folders…',
        )
    if error:
        short = error if len(error) < 80 else error[:77] + '…'
        return (
            ERROR,
            'Scan failed',
            short,
            f'Scan failed: {short}',
        )
    effective = count if scan_done else cached_count
    had_scan = scan_done or cached_count > 0
    effective_checked = checked if scan_done else 0
    if effective > 0 and effective_checked > 0:
        return (
            RECEIPT_READY,
            'Receipt ready',
            f'{effective} candidate(s) · {effective_checked} checked · preview receipt before archive.',
            f'Receipt ready — {effective} candidate(s), {effective_checked} checked.',
        )
    if effective > 0:
        return (
            RESULTS_READY,
            'Review ready',
            f'{effective} candidate(s) — check items, then preview receipt.',
            f'Review ready — {effective} candidate(s) awaiting review.',
        )
    if had_scan:
        return (
            EMPTY_DONE,
            'Scan complete',
            'No cleanup candidates found in configured folders.',
            'Scan complete — no candidates found.',
        )
    return (
        IDLE_READY,
        'Ready to scan',
        'Scan configured folders — preview receipt before any archive.',
        'Ready to scan.',
    )


def home_page_state(
    *,
    loading: bool = False,
    error: str = '',
    count: int = 0,
    checked: int = 0,
    scan_done: bool = False,
    custody_missing: int = 0,
    cached_count: int = 0,
    phase: str | None = None,
) -> tuple[str, str, str, str]:
    """Return (state, hero_title, hero_subtitle, status_line)."""
    if loading:
        return (
            LOADING,
            'Scanning…',
            'Reviewing configured folders for cleanup candidates.',
            'Scanning configured folders…',
        )
    if error:
        short = error if len(error) < 80 else error[:77] + '…'
        return ERROR, 'Scan failed', short, f'Scan failed: {short}'
    if phase == 'archived':
        return (
            EMPTY_DONE,
            'Archive complete',
            'Cleanup archived — receipt saved on disk.',
            'Archive complete.',
        )
    effective = count if scan_done else cached_count
    had_scan = scan_done or cached_count > 0
    effective_checked = checked if scan_done else 0
    if effective > 0 and effective_checked > 0:
        return (
            RECEIPT_READY,
            'Receipt ready',
            f'{effective} candidate(s) ready — preview receipt, then archive.',
            f'Receipt ready — {effective} candidate(s), {effective_checked} checked.',
        )
    if effective > 0:
        return (
            RESULTS_READY,
            'Review ready',
            f'{effective} candidate(s) found — review on Cleaner before archive.',
            f'Review ready — {effective} candidate(s) awaiting review.',
        )
    if had_scan:
        return (
            EMPTY_DONE,
            'Scan complete',
            'No cleanup candidates in configured folders.',
            'Scan complete — no candidates found.',
        )
    if custody_missing:
        return (
            RESULTS_READY,
            'Custody review needed',
            f'{custody_missing} archived artifact(s) missing on disk.',
            f'{custody_missing} custody gap(s) — review Activity.',
        )
    return (
        IDLE_READY,
        'Ready to scan',
        'Archive-first cleanup with receipts.',
        'Ready to scan.',
    )
