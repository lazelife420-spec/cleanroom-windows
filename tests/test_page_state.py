"""Page state helpers."""
from ui.page_state import (
    EMPTY_DONE,
    IDLE_READY,
    LOADING,
    RECEIPT_READY,
    RESULTS_READY,
    SCAN_STOPPED,
    cleaner_page_state,
    home_page_state,
)


def test_cleaner_idle_ready():
    state, hero, _, footer = cleaner_page_state()
    assert state == IDLE_READY
    assert hero == 'Ready to scan'
    assert footer == 'Ready to scan.'


def test_cleaner_loading():
    state, hero, _, footer = cleaner_page_state(loading=True)
    assert state == LOADING
    assert 'Scanning' in hero
    assert 'Scanning' in footer


def test_cleaner_loading_with_progress():
    state, hero, sub, footer = cleaner_page_state(
        loading=True,
        progress={
            'current_folder': r'C:\Downloads',
            'files_checked': 644,
            'candidates_found': 2,
            'reclaimable_label': '1.20MB',
            'elapsed_s': 12,
        },
    )
    assert state == LOADING
    assert 'Downloads' in sub
    assert '644' in footer
    assert '2 candidate' in footer


def test_cleaner_scan_stopped():
    state, hero, _, footer = cleaner_page_state(stopped=True)
    assert state == SCAN_STOPPED
    assert hero == 'Scan stopped'
    assert 'no cleanup' in footer.lower()


def test_home_scan_stopped():
    state, hero, _, status = home_page_state(stopped=True)
    assert state == SCAN_STOPPED
    assert 'Scan stopped' in hero
    assert 'no cleanup' in status.lower()


def test_cleaner_empty_after_scan():
    state, hero, _, footer = cleaner_page_state(scan_done=True, count=0)
    assert state == EMPTY_DONE
    assert hero == 'Scan complete'
    assert 'no candidates' in footer.lower()


def test_cleaner_receipt_ready():
    state, hero, _, footer = cleaner_page_state(count=5, checked=3, scan_done=True)
    assert state == RECEIPT_READY
    assert 'Receipt ready' in hero


def test_cleaner_review_ready_from_cache():
    state, hero, _, footer = cleaner_page_state(cached_count=2)
    assert state == RESULTS_READY
    assert hero == 'Review ready'
    assert '2 candidate' in footer


def test_home_empty_after_scan():
    state, hero, _, _ = home_page_state(scan_done=True)
    assert state == EMPTY_DONE
    assert hero == 'Scan complete'


def test_home_review_ready_from_cache():
    state, hero, _, status = home_page_state(cached_count=2)
    assert state == RESULTS_READY
    assert hero == 'Review ready'
    assert 'Review ready' in status


def test_home_archive_complete():
    state, hero, _, status = home_page_state(phase='archived')
    assert state == EMPTY_DONE
    assert hero == 'Archive complete'
    assert 'Archive complete' in status
