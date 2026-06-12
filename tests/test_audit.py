"""Unit tests for audit.py HTML export."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import audit


def test_export_html_audit_contains_proof_sections(tmp_path):
    feed = [{'when': '2026-06-10T12:00:00', 'reason': 'large-file', 'src': 'C:\\a',
             'size': 1024, 'present': True, 'kind': 'file'}]
    custody = {'verified': 1, 'total': 1, 'missing': 0, 'bytes_in_custody': 1024, 'missing_items': []}
    summary = {'total_actions': 1, 'present': 1, 'missing': 0, 'bytes_moved': 1024,
               'reasons': Counter({'large-file': 1}), 'restore_events': 0}
    out = tmp_path / 'audit.html'
    audit.export_html_audit(feed, custody, summary, 100, out)
    html = out.read_text(encoding='utf-8')
    assert 'CUSTODY VERIFIED' in html
    assert 'Trust score' in html
    assert 'large-file' in html
    assert 'C:\\a' in html or 'C:&#92;a' in html or 'C:\\\\a' in html


def test_proof_pack_trust_score_caps_when_items_missing(tmp_path):
    feed = []
    custody = {
        'verified': 1181,
        'total': 1182,
        'missing': 1,
        'bytes_in_custody': 0,
        'missing_items': ['missing-item'],
    }
    summary = {
        'total_actions': 1182,
        'present': 1181,
        'missing': 1,
        'bytes_moved': 0,
        'reasons': Counter(),
        'restore_events': 0,
    }
    out = tmp_path / 'audit-gaps.html'
    audit.export_html_audit(feed, custody, summary, 100, out)
    html = out.read_text(encoding='utf-8')
    assert 'GAPS DETECTED' in html
    assert 'Missing from archive</span>' in html
    assert '>1</b><span>Missing from archive</span>' in html
    assert '1181/1182' in html
    assert 'Trust score: <strong>100/100</strong>' not in html
    assert 'Trust score: <strong>99/100</strong>' in html


def test_proof_pack_trust_score_perfect_when_nothing_missing(tmp_path):
    feed = []
    custody = {
        'verified': 1182,
        'total': 1182,
        'missing': 0,
        'bytes_in_custody': 0,
        'missing_items': [],
    }
    summary = {
        'total_actions': 1182,
        'present': 1182,
        'missing': 0,
        'bytes_moved': 0,
        'reasons': Counter(),
        'restore_events': 0,
    }
    out = tmp_path / 'audit-clean.html'
    audit.export_html_audit(feed, custody, summary, 100, out)
    html = out.read_text(encoding='utf-8')
    assert 'CUSTODY VERIFIED' in html
    assert 'Trust score: <strong>100/100</strong>' in html
    assert '1182/1182' in html
