"""Page state helpers."""
from ui.page_state import (
    EMPTY_DONE,
    ERROR,
    IDLE_READY,
    LOADING,
    RECEIPT_READY,
    RESULTS_READY,
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
