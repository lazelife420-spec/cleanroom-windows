# ruff: noqa: E402
import sys
from pathlib import Path

tests_dir = Path(__file__).resolve().parent
project_dir = tests_dir.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import recommendations as rec

GB = 1024 ** 3
MB = 1024 ** 2


def test_health_score_perfect_system():
    score = rec.compute_health_score(startup_count=0, cleanup_count=0, cleanup_bytes=0, restore_count=1)
    assert score == 100


def test_health_score_degrades_with_clutter():
    clean = rec.compute_health_score(startup_count=2, cleanup_count=0, restore_count=1)
    dirty = rec.compute_health_score(startup_count=20, cleanup_count=30, cleanup_bytes=6 * GB, restore_count=0)
    assert dirty < clean
    assert dirty >= 10  # floor


def test_health_score_floor():
    # Deductions are capped (40 + 30 + 10 + 5), so the worst possible score is 15.
    score = rec.compute_health_score(startup_count=1000, cleanup_count=1000, cleanup_bytes=100 * GB, restore_count=0)
    assert score == 15


def test_health_band_labels():
    assert rec.health_band(90)[1] == 'Excellent'
    assert rec.health_band(70)[1] == 'Good'
    assert rec.health_band(50)[1] == 'Fair'
    assert rec.health_band(20)[1] == 'Needs Attention'


def test_recommendations_clean_system():
    recs = rec.build_recommendations()
    titles = [r['title'] for r in recs]
    assert any('No cleanup candidates' in t for t in titles)
    assert any('System looks lean' in t for t in titles)
    # nothing actionable should be high severity
    assert all(r['severity'] == 'info' for r in recs)


def test_recommendations_severity_scales_with_size():
    small = rec.build_recommendations(cleanup_count=3, cleanup_bytes=10 * MB)
    medium = rec.build_recommendations(cleanup_count=3, cleanup_bytes=600 * MB)
    large = rec.build_recommendations(cleanup_count=3, cleanup_bytes=6 * GB)
    assert small[0]['severity'] == 'low'
    assert medium[0]['severity'] == 'medium'
    assert large[0]['severity'] == 'high'


def test_recommendations_registry_thresholds():
    none = rec.build_recommendations(registry_count=3)
    some = rec.build_recommendations(registry_count=8)
    heavy = rec.build_recommendations(registry_count=15)
    assert not any('startup' in r['title'].lower() and 'registry' in r['detail'].lower() for r in none if r['severity'] != 'info')
    assert any(r['severity'] == 'medium' and 'registry' in r['detail'].lower() for r in some)
    assert any(r['severity'] == 'high' and 'registry' in r['detail'].lower() for r in heavy)


def test_recommendations_reason_counts():
    recs = rec.build_recommendations(
        cleanup_count=5, cleanup_bytes=1 * MB,
        reason_counts={'large-file': 2, 'partial-download': 1})
    titles = ' | '.join(r['title'] for r in recs)
    assert 'large file' in titles.lower()
    assert 'partial download' in titles.lower()


def test_recommendations_sorted_by_severity():
    recs = rec.build_recommendations(
        folder_count=6, registry_count=15, cleanup_count=25,
        cleanup_bytes=6 * GB, restore_count=0)
    order = [rec.SEVERITY_ORDER[r['severity']] for r in recs]
    assert order == sorted(order)


def test_schedule_recommendation_when_many_candidates():
    recs = rec.build_recommendations(cleanup_count=25, cleanup_bytes=1 * MB)
    assert any('Schedule' in r['title'] for r in recs)
