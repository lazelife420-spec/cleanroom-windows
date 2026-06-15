"""Receipt identity classification."""
from ui.receipt_identity import receipt_context, receipt_window_title


def test_preview_receipt_title():
    body = '*** PREVIEW ONLY ***\nItems moved: 0'
    ctx = receipt_context(body, action_key='cleaner_preview')
    assert ctx['title'] == 'Cleanroom Receipt — Cleaner Preview'
    assert ctx['preview'] is True
    assert ctx['badge'] == 'PREVIEW ONLY'


def test_archive_receipt_title():
    body = 'Items moved: 3\nSpace moved: 1.2MB'
    ctx = receipt_context(body)
    assert 'Archive' in ctx['title']
    assert ctx['archived'] is True


def test_window_title_format():
    assert receipt_window_title('Force Remove', 'Intent') == (
        'Cleanroom Receipt — Force Remove Intent'
    )
