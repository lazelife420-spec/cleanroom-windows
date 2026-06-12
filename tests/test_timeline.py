"""Tests for Time Machine (day buckets + day rollback) and receipts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import receipts
import timeline


def entry(src, dest, when, reason='installer/archive', size=100, **extra):
    e = {'src': src, 'dest': dest, 'when': when, 'reason': reason, 'size': size}
    e.update(extra)
    return e


# ---------------------------------------------------------------------------
# build_timeline
# ---------------------------------------------------------------------------
def test_timeline_groups_by_day_newest_first(tmp_path):
    a = tmp_path / 'a.zip'
    b = tmp_path / 'b.zip'
    a.write_text('x')
    b.write_text('y')
    actions = [
        entry('C:\\dl\\a.zip', str(a), '2026-06-01T10:00:00', size=10),
        entry('C:\\dl\\b.zip', str(b), '2026-06-01T11:00:00', size=20),
        entry('C:\\dl\\c.zip', str(tmp_path / 'missing.zip'), '2026-06-05T09:00:00', size=5),
    ]
    buckets = timeline.build_timeline(actions)
    assert [b_['date'] for b_ in buckets] == ['2026-06-05', '2026-06-01']
    june1 = buckets[1]
    assert june1['count'] == 2
    assert june1['bytes'] == 30
    assert june1['restorable'] == 2
    june5 = buckets[0]
    assert june5['restorable'] == 0  # archived file is gone


def test_timeline_skips_restore_records_and_garbage():
    actions = [
        {'action': 'restore', 'src': 'a', 'dest': 'b', 'time': '2026-06-01T10:00:00'},
        {'no_src': True},
        'not-a-dict',
        entry('C:\\x', 'C:\\arch\\x', '2026-06-02T10:00:00'),
    ]
    buckets = timeline.build_timeline(actions)
    assert len(buckets) == 1
    assert buckets[0]['date'] == '2026-06-02'


def test_timeline_counts_reasons():
    actions = [
        entry('a', 'a2', '2026-06-01T10:00:00', reason='zero-byte'),
        entry('b', 'b2', '2026-06-01T10:01:00', reason='zero-byte'),
        entry('c', 'c2', '2026-06-01T10:02:00', reason='uninstall-leftover'),
    ]
    buckets = timeline.build_timeline(actions)
    assert buckets[0]['reasons']['zero-byte'] == 2
    assert buckets[0]['reasons']['uninstall-leftover'] == 1


# ---------------------------------------------------------------------------
# rollback_day
# ---------------------------------------------------------------------------
def test_rollback_day_restores_existing_entries(tmp_path):
    archived = tmp_path / 'arch' / 'f.txt'
    archived.parent.mkdir()
    archived.write_text('payload')
    original = tmp_path / 'home' / 'f.txt'
    actions = [
        entry(str(original), str(archived), '2026-06-01T10:00:00'),
        entry(str(tmp_path / 'never.txt'), str(tmp_path / 'gone.txt'), '2026-06-01T11:00:00'),
    ]
    bucket = timeline.build_timeline(actions)[0]

    import shutil

    def restore_fn(src, dest):
        Path(src).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(dest, src)
        return True, 'moved'

    restored, skipped, failed, msgs = timeline.rollback_day(bucket, restore_fn)
    assert (restored, skipped, failed) == (1, 1, 0)
    assert original.read_text() == 'payload'
    assert not archived.exists()


def test_rollback_day_reports_failures(tmp_path):
    archived = tmp_path / 'f.txt'
    archived.write_text('x')
    bucket = timeline.build_timeline(
        [entry('C:\\target\\f.txt', str(archived), '2026-06-01T10:00:00')])[0]
    restored, skipped, failed, msgs = timeline.rollback_day(
        bucket, lambda s, d: (False, 'simulated failure'))
    assert (restored, skipped, failed) == (0, 0, 1)
    assert msgs == ['simulated failure']


# ---------------------------------------------------------------------------
# receipts
# ---------------------------------------------------------------------------
def test_receipt_contains_summary_and_days_bought(tmp_path):
    moved = [
        entry('a', 'a2', '2026-06-01T10:00:00', reason='installer/archive', size=1024 ** 3),
        entry('b', 'b2', '2026-06-01T10:01:00', reason='zero-byte', size=0),
    ]
    path = receipts.write_receipt(moved, days_bought=12.4, receipt_dir=tmp_path)
    assert path.suffix == receipts.RECEIPT_EXT
    text = path.read_text(encoding='utf-8')
    assert 'CLEANROOM — RECEIPT' in text
    assert 'Items moved: 2' in text
    assert '1.0GB' in text
    assert '~12 extra days' in text
    assert 'installer/archive' in text
    assert 'Nothing was deleted' in text


def test_receipt_skips_empty_and_finds_latest(tmp_path):
    assert receipts.write_receipt([], receipt_dir=tmp_path) is None
    assert receipts.latest_receipt(tmp_path) is None

    from datetime import datetime
    p1 = receipts.write_receipt([entry('a', 'b', None)], receipt_dir=tmp_path,
                                now=datetime(2026, 6, 1, 10, 0, 0))
    p2 = receipts.write_receipt([entry('c', 'd', None)], receipt_dir=tmp_path,
                                now=datetime(2026, 6, 2, 10, 0, 0))
    assert receipts.latest_receipt(tmp_path) == p2
    assert p1.exists()


def test_receipt_pruning_caps_files(tmp_path):
    from datetime import datetime, timedelta
    start = datetime(2026, 1, 1, 0, 0, 0)
    for i in range(receipts.MAX_RECEIPTS + 5):
        receipts.write_receipt([entry('a', 'b', None)], receipt_dir=tmp_path,
                               now=start + timedelta(minutes=i))
    assert len(receipts.list_receipt_files(tmp_path)) == receipts.MAX_RECEIPTS
