"""Shared layout contract helpers."""
from ui.page_layout import (
    CONTENT_MAX_WIDTH,
    LAYOUT_MIN,
    classify_layout,
    sync_table_empty_view,
)


def test_classify_layout_modes():
    assert classify_layout(900, 600) == 'compact'
    assert classify_layout(1100, 700) == 'normal'
    assert classify_layout(1400, 800) == 'wide'
    assert classify_layout(1100, 700, scale=1.5) == 'compact'


def test_layout_constants():
    assert LAYOUT_MIN[0] >= 920
    assert CONTENT_MAX_WIDTH >= 1100


class _GridStub:
    def __init__(self):
        self.calls = []

    def grid(self, **kw):
        self.calls.append(('grid', kw))

    def grid_remove(self):
        self.calls.append(('grid_remove', {}))


def test_sync_table_empty_view_hides_table_when_empty():
    table, detail, empty = _GridStub(), _GridStub(), _GridStub()
    sync_table_empty_view(
        has_rows=False, table_card=table, detail_panel=detail, empty_panel=empty)
    assert ('grid_remove', {}) in table.calls
    assert ('grid_remove', {}) in detail.calls
    assert any(c[0] == 'grid' for c in empty.calls)
