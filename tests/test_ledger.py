"""Unit tests for ledger.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ledger


def test_build_activity_feed_newest_first_and_present_flags(tmp_path):
    f = tmp_path / 'kept.bin'
    f.write_bytes(b'x')
    actions = [
        {'src': str(tmp_path / 'a'), 'dest': str(f), 'when': '2026-06-09T10:00:00',
         'reason': 'large-file', 'size': 10},
        {'src': str(tmp_path / 'gone'), 'dest': str(tmp_path / 'missing'), 'when': '2026-06-10T12:00:00',
         'reason': 'zero-byte', 'size': 5},
        {'action': 'restore', 'src': 'x', 'dest': 'y', 'when': '2026-06-10T13:00:00'},
    ]
    feed = ledger.build_activity_feed(actions)
    archival = [e for e in feed if e.get('kind') != 'restore']
    assert archival[0]['reason'] == 'zero-byte'
    assert archival[1]['reason'] == 'large-file'
    assert archival[0]['present'] is False
    assert archival[1]['present'] is True
    assert feed[0]['kind'] == 'restore'


def test_summarize_feed_and_trust_score():
    feed = [
        {'kind': 'file', 'present': True, 'size': 100, 'reason': 'a'},
        {'kind': 'file', 'present': True, 'size': 200, 'reason': 'a'},
        {'kind': 'file', 'present': False, 'size': 50, 'reason': 'b'},
        {'kind': 'restore', 'present': True, 'size': 0, 'reason': 'restore'},
    ]
    s = ledger.summarize_feed(feed)
    assert s['total_actions'] == 3
    assert s['present'] == 2
    assert s['restore_events'] == 1
    assert ledger.trust_score(2, 3) == 67
    assert ledger.trust_score(0, 0) == 100


def test_format_trust_score_display():
    assert ledger.format_trust_score_display(1182, 1182, 0) == '100/100'
    assert ledger.format_trust_score_display(1181, 1182, 1) == '99/100'
    assert ledger.format_trust_score_display(0, 0, 0) == '100/100'
