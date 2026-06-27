"""Tests for performance_engine.py — parallel scanning, incremental state, and hashing."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import performance_engine as pe


def test_scan_options_auto_workers():
    opts = pe.ScanOptions(max_workers=0)
    assert opts.max_workers > 0


def test_parallel_scan_finds_files(tmp_path):
    engine = pe.PerformanceEngine(cache_dir=tmp_path / 'cache')
    (tmp_path / 'a.txt').write_text('hello')
    (tmp_path / 'sub').mkdir(parents=True)
    (tmp_path / 'sub' / 'b.txt').write_text('world')

    results = list(engine.parallel_scan_directories([str(tmp_path)]))
    paths = {r['path'] for r in results}
    assert str(tmp_path / 'a.txt') in paths
    assert str(tmp_path / 'sub' / 'b.txt') in paths


def test_incremental_scan_skips_unchanged_files(tmp_path):
    cache_dir = tmp_path / 'cache'
    engine = pe.PerformanceEngine(cache_dir=cache_dir)
    f = tmp_path / 'file.txt'
    f.write_text('v1')

    first = list(engine.incremental_scan([str(tmp_path)]))
    assert len(first) == 1

    second = list(engine.incremental_scan([str(tmp_path)]))
    assert len(second) == 0

    f.write_text('v2')
    third = list(engine.incremental_scan([str(tmp_path)]))
    assert len(third) == 1


def test_force_rescan_returns_all_files(tmp_path):
    engine = pe.PerformanceEngine(cache_dir=tmp_path / 'cache')
    (tmp_path / 'x.txt').write_text('x')
    list(engine.incremental_scan([str(tmp_path)]))

    engine.options.force_rescan = True
    results = list(engine.incremental_scan([str(tmp_path)]))
    assert len(results) == 1


def test_batch_hash_files(tmp_path):
    engine = pe.PerformanceEngine(cache_dir=tmp_path / 'cache')
    f1 = tmp_path / 'a.txt'
    f2 = tmp_path / 'b.txt'
    f1.write_text('same')
    f2.write_text('same')
    f3 = tmp_path / 'c.txt'
    f3.write_text('different')

    hashes = dict(engine.batch_hash_files([str(f1), str(f2), str(f3)]))
    assert hashes[str(f1)] == hashes[str(f2)]
    assert hashes[str(f1)] != hashes[str(f3)]


def test_find_duplicates_by_records(tmp_path):
    engine = pe.PerformanceEngine(cache_dir=tmp_path / 'cache')
    f1 = tmp_path / 'a.txt'
    f2 = tmp_path / 'b.txt'
    f3 = tmp_path / 'c.txt'
    f1.write_text('duplicate')
    f2.write_text('duplicate')
    f3.write_text('unique')

    records = [
        {'path': str(f1), 'size': f1.stat().st_size},
        {'path': str(f2), 'size': f2.stat().st_size},
        {'path': str(f3), 'size': f3.stat().st_size},
    ]
    duplicates = engine.find_duplicates(file_records=records)
    assert len(duplicates) == 1
    group = list(duplicates.values())[0]
    assert sorted(group) == sorted([str(f1), str(f2)])


def test_smart_cache_ttl(tmp_path):
    cache_dir = tmp_path / 'cache'
    cache = pe.SmartCache(cache_dir=cache_dir, max_age_hours=24)
    dirs = [str(tmp_path)]
    cache.set(dirs, [{'path': 'x'}])
    assert cache.get(dirs) == [{'path': 'x'}]

    # Force a stale entry by back-dating the cache file.
    key = cache._key(dirs)
    cache_file = cache_dir / f"{key}.json"
    old_mtime = time.time() - 3600 * 25
    import os
    os.utime(cache_file, (old_mtime, old_mtime))
    assert cache.get(dirs) is None


def test_memory_governor_detects_pressure(tmp_path):
    import psutil
    governor = pe.MemoryGovernor(
        limit_bytes=psutil.Process().memory_info().rss + 1024 * 1024 * 1024)
    assert governor.check(force=True) is False

    governor_small = pe.MemoryGovernor(limit_bytes=1)
    assert governor_small.check(force=True) is True


def test_performance_stats(tmp_path):
    engine = pe.PerformanceEngine(cache_dir=tmp_path / 'cache')
    stats = engine.get_performance_stats()
    assert 'memory_usage_mb' in stats
    assert 'max_workers' in stats


def test_progress_callback(tmp_path):
    engine = pe.PerformanceEngine(cache_dir=tmp_path / 'cache')
    (tmp_path / 'a.txt').write_text('a')
    (tmp_path / 'b.txt').write_text('b')

    progress = []

    def cb(count, elapsed):
        progress.append((count, elapsed))

    engine.options.progress_every = 1
    list(engine.parallel_scan_directories([str(tmp_path)], progress_callback=cb))
    assert len(progress) >= 2


def test_cancel_scan(tmp_path):
    engine = pe.PerformanceEngine(cache_dir=tmp_path / 'cache')
    for i in range(10):
        (tmp_path / f'{i}.txt').write_text('x')

    engine.cancel()
    results = list(engine.parallel_scan_directories([str(tmp_path)]))
    assert len(results) < 10


def test_benchmark_scan(tmp_path):
    for i in range(5):
        (tmp_path / f'{i}.txt').write_text('x')
    results = pe.benchmark_scan([str(tmp_path)], iterations=2, cache_dir=tmp_path / 'cache')
    assert 'full_scan' in results
    assert 'incremental_scan' in results
    assert len(results['full_scan']) == 2
    assert len(results['incremental_scan']) == 2
    assert results['full_scan_avg_time_s'] >= 0
    assert results['incremental_scan_avg_time_s'] >= 0
    assert results['full_scan'][0]['files'] == 5


def test_clear_scan_cache(tmp_path):
    cache_dir = tmp_path / 'cache'
    cache_dir.mkdir()
    (cache_dir / 'scan_state.db').write_text('db')
    (cache_dir / 'scan_state.db-shm').write_text('shm')
    (cache_dir / 'scan_state.db-wal').write_text('wal')
    (cache_dir / 'some_key.json').write_text('json')
    (cache_dir / 'keep.txt').write_text('keep')

    pe.clear_scan_cache(cache_dir)
    assert not (cache_dir / 'scan_state.db').exists()
    assert not (cache_dir / 'scan_state.db-shm').exists()
    assert not (cache_dir / 'scan_state.db-wal').exists()
    assert not (cache_dir / 'some_key.json').exists()
    assert (cache_dir / 'keep.txt').exists()
