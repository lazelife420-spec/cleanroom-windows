#!/usr/bin/env python3
"""High-performance scanning engine with parallel processing and memory optimization.

This module provides scalable file scanning for large directory trees (millions of
files). It combines SQLite-backed incremental state, thread/process parallelism,
memory-mapped hashing, and memory-pressure throttling so that repeated scans only
traverse changed files and hashing is bounded by available CPU and RAM.
"""
import gc
import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Tuple

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ScanOptions:
    """Configuration for a scan pass."""
    max_workers: int = 0
    memory_limit_mb: int = 512
    hash_chunk_size: int = 4 * 1024 * 1024
    mmap_threshold_bytes: int = 10 * 1024 * 1024
    batch_size: int = 1000
    incremental: bool = True
    force_rescan: bool = False
    progress_every: int = 1000

    def __post_init__(self):
        if self.max_workers <= 0:
            self.max_workers = min(32, (os.cpu_count() or 1) + 4)


class ScanState:
    """Persistent SQLite-backed incremental scan state.

    Stores the last known size, mtime, and optional hash for each scanned path.
    A file is considered "unchanged" only if both size and mtime match.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS scan_state (
        path TEXT PRIMARY KEY,
        size INTEGER NOT NULL,
        mtime REAL NOT NULL,
        hash TEXT,
        last_scan REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_scan_state_mtime ON scan_state(mtime);
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.execute('PRAGMA journal_mode=WAL')
            self._local.conn.execute('PRAGMA synchronous=NORMAL')
        return self._local.conn

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(self.SCHEMA)

    def known_paths(self) -> Dict[str, Tuple[int, float]]:
        """Return a mapping of path -> (size, mtime) for the last scan."""
        cur = self._conn().execute('SELECT path, size, mtime FROM scan_state')
        return {row[0]: (row[1], row[2]) for row in cur.fetchall()}

    def is_changed(self, path: str, size: int, mtime: float) -> bool:
        cur = self._conn().execute(
            'SELECT size, mtime FROM scan_state WHERE path = ?', (path,))
        row = cur.fetchone()
        return row is None or row[0] != size or row[1] != mtime

    def update(self, rows: Iterable[Tuple[str, int, float, Optional[str]]]):
        """Bulk update or insert scan state rows."""
        now = time.time()
        data = [(p, s, m, h, now) for p, s, m, h in rows]
        self._conn().executemany(
            'INSERT INTO scan_state (path, size, mtime, hash, last_scan) VALUES (?, ?, ?, ?, ?) '
            'ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime=excluded.mtime, '
            'hash=excluded.hash, last_scan=excluded.last_scan',
            data)
        self._conn().commit()

    def begin_scan(self):
        """Create a temporary table to record paths seen during this scan."""
        self._conn().execute('CREATE TEMPORARY TABLE IF NOT EXISTS current_paths (path TEXT PRIMARY KEY)')
        self._conn().execute('DELETE FROM current_paths')
        self._conn().commit()

    def record_current_paths(self, paths: Iterable[str]):
        """Record that a batch of paths was observed during the current scan."""
        data = [(p,) for p in paths]
        self._conn().executemany(
            'INSERT OR IGNORE INTO current_paths (path) VALUES (?)', data)
        self._conn().commit()

    def end_scan(self):
        """Remove state entries for paths not seen this scan and drop temp table."""
        self._conn().execute(
            'DELETE FROM scan_state WHERE path NOT IN (SELECT path FROM current_paths)')
        self._conn().execute('DROP TABLE IF EXISTS current_paths')
        self._conn().commit()

    def prune_orphans(self, current_paths: Iterable[str]):
        """Remove state entries for paths that no longer exist."""
        current = set(current_paths)
        cur = self._conn().execute('SELECT path FROM scan_state')
        orphans = [row[0] for row in cur.fetchall() if row[0] not in current]
        if orphans:
            self._conn().executemany(
                'DELETE FROM scan_state WHERE path = ?', [(p,) for p in orphans])
            self._conn().commit()

    def vacuum(self):
        self._conn().execute('VACUUM')


class MemoryGovernor:
    """Throttle work when memory pressure is high."""

    def __init__(self, limit_bytes: int, check_interval: float = 2.0):
        self.limit_bytes = limit_bytes
        self.check_interval = check_interval
        self._last_check = 0.0
        self._lock = threading.Lock()

    def _rss(self) -> int:
        try:
            return psutil.Process().memory_info().rss
        except Exception:
            return 0

    def check(self, force: bool = False) -> bool:
        """Return True if work should pause briefly to let memory settle."""
        now = time.time()
        with self._lock:
            if not force and now - self._last_check < self.check_interval:
                return False
            self._last_check = now
        if self._rss() > self.limit_bytes:
            gc.collect()
            return True
        return False

    def throttle(self):
        if self.check(force=True):
            time.sleep(0.5)
            gc.collect()


class PerformanceEngine:
    """High-performance, memory-aware file scanning engine."""

    def __init__(self, cache_dir: Optional[Path] = None, options: Optional[ScanOptions] = None):
        self.options = options or ScanOptions()
        self.cache_dir = cache_dir or Path('.scan_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_db = ScanState(self.cache_dir / 'scan_state.db')
        self.governor = MemoryGovernor(self.options.memory_limit_mb * 1024 * 1024)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _check_cancel(self) -> bool:
        return self._cancelled

    def _balance_directories(self, directories: List[str]) -> List[List[str]]:
        """Split directories into balanced chunks for worker threads."""
        n = len(directories)
        if n == 0:
            return []
        workers = min(self.options.max_workers, n)
        chunk_size = max(1, n // workers)
        chunks = []
        for i in range(0, n, chunk_size):
            chunks.append(directories[i:i + chunk_size])
        return chunks

    def _scan_directory_chunk(self, directories: List[str],
                              file_filter: Optional[Callable[[Dict], bool]]) -> List[Dict]:
        """Scan a chunk of directories and return a list of file records."""
        records = []
        for directory in directories:
            if self._check_cancel():
                break
            try:
                self._walk_directory(directory, file_filter, records)
            except Exception as e:
                logger.error(f"Error scanning directory {directory}: {e}")
            if self.governor.check():
                time.sleep(0.2)
        return records

    def _walk_directory(self, directory: str,
                        file_filter: Optional[Callable[[Dict], bool]],
                        records: List[Dict]):
        """Recursively walk a directory using os.scandir and append records."""
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if self._check_cancel():
                        return
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_file(follow_symlinks=False):
                            info = self._entry_to_info(entry)
                            if info is not None and (file_filter is None or file_filter(info)):
                                records.append(info)
                        elif entry.is_dir(follow_symlinks=False):
                            self._walk_directory(entry.path, file_filter, records)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass

    def _entry_to_info(self, entry: os.DirEntry) -> Optional[Dict]:
        try:
            stat = entry.stat(follow_symlinks=False)
            name = entry.name
            if '.' in name and not name.startswith('.'):
                extension = '.' + name.rsplit('.', 1)[-1].lower()
            else:
                extension = ''
            return {
                'path': entry.path,
                'name': name,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'extension': extension,
                'inode': stat.st_ino,
            }
        except (OSError, AttributeError):
            return None

    def _is_under_cache(self, path: str) -> bool:
        try:
            return Path(path).resolve().is_relative_to(self.cache_dir.resolve())
        except Exception:
            return False

    def parallel_scan_directories(self, directories: List[str],
                                  file_filter: Optional[Callable[[Dict], bool]] = None,
                                  progress_callback: Optional[Callable[[int, float], None]] = None
                                  ) -> Iterator[Dict]:
        """Yield file records from directories in parallel, streaming results."""
        directories = [d for d in directories if os.path.exists(d)]
        if not directories:
            return

        logger.info(f"Starting parallel scan of {len(directories)} directories with "
                    f"{self.options.max_workers} workers")

        def combined_filter(info: Dict) -> bool:
            if self._is_under_cache(info['path']):
                return False
            if file_filter is not None and not file_filter(info):
                return False
            return True

        chunks = self._balance_directories(directories)
        total_files = 0
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.options.max_workers) as executor:
            future_to_chunk = {
                executor.submit(self._scan_directory_chunk, chunk, combined_filter): chunk
                for chunk in chunks
            }

            for future in as_completed(future_to_chunk):
                if self._check_cancel():
                    break
                try:
                    for file_info in future.result():
                        yield file_info
                        total_files += 1
                        if (progress_callback and
                                total_files % self.options.progress_every == 0):
                            progress_callback(total_files, time.time() - start_time)
                        if self.governor.check():
                            time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error scanning chunk {future_to_chunk[future]}: {e}")

        logger.info(f"Parallel scan completed: {total_files} files in "
                    f"{time.time() - start_time:.2f}s")

    def incremental_scan(self, directories: List[str],
                         file_filter: Optional[Callable[[Dict], bool]] = None,
                         progress_callback: Optional[Callable[[int, float], None]] = None
                         ) -> Iterator[Dict]:
        """Yield only files that are new or changed since the last scan.

        State is persisted in a SQLite database so the engine can resume across
        process restarts. After the scan completes, the state table is updated and
        orphaned entries are removed.
        """
        if self.options.force_rescan:
            for item in self.parallel_scan_directories(directories, file_filter, progress_callback):
                yield item
            return

        self.state_db.begin_scan()
        current_batch = []
        changed = []
        unchanged_count = 0
        total_count = 0

        for info in self.parallel_scan_directories(directories, file_filter, progress_callback):
            path = info['path']
            size = info['size']
            mtime = info['modified']
            total_count += 1
            current_batch.append(path)

            if self.state_db.is_changed(path, size, mtime):
                changed.append((path, size, mtime, None))
                yield info
            else:
                unchanged_count += 1

            if len(changed) >= self.options.batch_size:
                self.state_db.update(changed)
                changed.clear()
                self.governor.throttle()

            if len(current_batch) >= self.options.batch_size:
                self.state_db.record_current_paths(current_batch)
                current_batch.clear()

        if changed:
            self.state_db.update(changed)
        if current_batch:
            self.state_db.record_current_paths(current_batch)

        self.state_db.end_scan()
        logger.info(f"Incremental scan: {unchanged_count} unchanged, "
                    f"{total_count - unchanged_count} changed")

    def batch_hash_files(self, file_paths: List[str],
                         progress_callback: Optional[Callable[[int, float], None]] = None
                         ) -> Iterator[Tuple[str, str]]:
        """Yield (path, sha256) pairs in batches with memory control."""
        processed = 0
        start_time = time.time()
        for i in range(0, len(file_paths), self.options.batch_size):
            batch = file_paths[i:i + self.options.batch_size]
            for path in batch:
                try:
                    h = self._calculate_hash(path)
                    yield (path, h)
                except Exception as e:
                    logger.error(f"Error hashing {path}: {e}")
                    yield (path, '')
                processed += 1
                if (progress_callback and
                        processed % self.options.progress_every == 0):
                    progress_callback(processed, time.time() - start_time)
            self.governor.throttle()

    def _calculate_hash(self, file_path: str) -> str:
        """Calculate SHA256 with memory-mapped I/O for large files."""
        h = hashlib.sha256()
        size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            if size > self.options.mmap_threshold_bytes:
                try:
                    import mmap
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        h.update(mm)
                    return h.hexdigest()
                except Exception:
                    pass
            chunk_size = self.options.hash_chunk_size
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def find_duplicates(self, file_paths: Optional[List[str]] = None,
                        file_records: Optional[List[Dict]] = None
                        ) -> Dict[str, List[str]]:
        """Find duplicate files using size + hash filtering."""
        if file_records is not None:
            records = file_records
        elif file_paths is not None:
            records = [{'path': p, 'size': os.path.getsize(p)} for p in file_paths]
        else:
            return {}

        size_groups: Dict[int, List[str]] = {}
        for rec in records:
            size = rec.get('size', 0)
            if size > 0:
                size_groups.setdefault(size, []).append(rec['path'])

        candidates = [p for paths in size_groups.values() if len(paths) > 1 for p in paths]
        logger.info(f"Hashing {len(candidates)} potential duplicates")

        hash_groups: Dict[str, List[str]] = {}
        for path, h in self.batch_hash_files(candidates):
            if h:
                hash_groups.setdefault(h, []).append(path)

        duplicates = {h: paths for h, paths in hash_groups.items() if len(paths) > 1}
        total = sum(len(v) for v in duplicates.values())
        logger.info(f"Found {len(duplicates)} duplicate groups with {total} files")
        return duplicates

    def get_performance_stats(self) -> Dict:
        try:
            proc = psutil.Process()
            mem = proc.memory_info()
            return {
                'memory_usage_mb': mem.rss / (1024 * 1024),
                'memory_percent': proc.memory_percent(),
                'cpu_percent': proc.cpu_percent(interval=0.1),
                'threads': proc.num_threads(),
                'max_workers': self.options.max_workers,
                'system_memory_gb': psutil.virtual_memory().total / (1024 ** 3),
                'state_db_size_mb': self.state_db.db_path.stat().st_size / (1024 * 1024)
                    if self.state_db.db_path.exists() else 0,
            }
        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}


class SmartCache:
    """TTL-based JSON cache for arbitrary scan results."""

    def __init__(self, cache_dir: Optional[Path] = None, max_age_hours: int = 24):
        self.cache_dir = cache_dir or Path('.scan_cache')
        self.max_age = timedelta(hours=max_age_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, directories: List[str], filters: Optional[Dict] = None) -> str:
        data = {'directories': sorted(str(d) for d in directories), 'filters': filters or {}}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def get(self, directories: List[str], filters: Optional[Dict] = None) -> Optional[List[Dict]]:
        cache_file = self.cache_dir / f"{self._key(directories, filters)}.json"
        if not cache_file.exists():
            return None
        try:
            age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if age > self.max_age:
                cache_file.unlink()
                return None
            return json.loads(cache_file.read_text(encoding='utf-8'))
        except Exception:
            return None

    def set(self, directories: List[str], results: List[Dict], filters: Optional[Dict] = None):
        cache_file = self.cache_dir / f"{self._key(directories, filters)}.json"
        try:
            cache_file.write_text(json.dumps(results), encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to cache results: {e}")

    def cleanup(self):
        cutoff = datetime.now() - self.max_age
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                if datetime.fromtimestamp(cache_file.stat().st_mtime) < cutoff:
                    cache_file.unlink()
            except Exception:
                pass


def clear_scan_cache(cache_dir: Path) -> None:
    """Remove the scan state database and any cached JSON files."""
    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        return
    for suffix in ('.db', '.db-shm', '.db-wal'):
        try:
            (cache_dir / f'scan_state{suffix}').unlink(missing_ok=True)
        except Exception:
            pass
    for cache_file in cache_dir.glob('*.json'):
        try:
            cache_file.unlink()
        except Exception:
            pass


def benchmark_scan(directories: List[str], iterations: int = 3,
                   options: Optional[ScanOptions] = None,
                   cache_dir: Optional[Path] = None) -> Dict:
    """Benchmark full and incremental scans across multiple iterations."""
    options = options or ScanOptions()
    engine = PerformanceEngine(cache_dir=cache_dir or Path('.scan_cache'), options=options)
    results = {
        'iterations': iterations,
        'directories': [str(d) for d in directories],
        'full_scan': [],
        'incremental_scan': [],
    }

    for i in range(iterations):
        # Force a full scan first.
        engine.options.force_rescan = True
        start = time.time()
        count = sum(1 for _ in engine.parallel_scan_directories(directories))
        results['full_scan'].append({
            'iteration': i + 1,
            'files': count,
            'time_s': time.time() - start,
            'files_per_second': count / (time.time() - start) if time.time() > start else 0,
        })

        # Then an incremental scan over the same tree.
        engine.options.force_rescan = False
        start = time.time()
        count = sum(1 for _ in engine.incremental_scan(directories))
        results['incremental_scan'].append({
            'iteration': i + 1,
            'files': count,
            'time_s': time.time() - start,
            'files_per_second': count / (time.time() - start) if time.time() > start else 0,
        })

    for key in ('full_scan', 'incremental_scan'):
        times = [r['time_s'] for r in results[key]]
        counts = [r['files'] for r in results[key]]
        results[f'{key}_avg_time_s'] = sum(times) / len(times) if times else 0
        results[f'{key}_avg_files_per_second'] = (
            sum(counts) / sum(times) if sum(times) else 0)
    return results


def print_benchmark(results: Dict):
    print("=" * 60)
    print("Performance Benchmark Results")
    print("=" * 60)
    print(f"Directories: {', '.join(results['directories'])}")
    print(f"Iterations: {results['iterations']}")
    print()
    print(f"Full scan average:        {results['full_scan_avg_time_s']:.2f}s  "
          f"({results['full_scan_avg_files_per_second']:.0f} files/s)")
    print(f"Incremental scan average: {results['incremental_scan_avg_time_s']:.2f}s  "
          f"({results['incremental_scan_avg_files_per_second']:.0f} files/s)")
    print()
    for key in ('full_scan', 'incremental_scan'):
        print(f"{key.replace('_', ' ').title()} details:")
        for r in results[key]:
            print(f"  Iteration {r['iteration']}: {r['files']} files in {r['time_s']:.2f}s")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='High-performance scan engine')
    parser.add_argument('--directories', nargs='+', default=['.'], help='Directories to scan')
    parser.add_argument('--benchmark', action='store_true', help='Run benchmark')
    parser.add_argument('--workers', type=int, default=0, help='Worker threads (0=auto)')
    parser.add_argument('--memory-limit', type=int, default=512, help='Memory limit in MB')
    parser.add_argument('--incremental', action='store_true', help='Use incremental scan')
    parser.add_argument('--force-rescan', action='store_true', help='Ignore incremental state')
    parser.add_argument('--find-duplicates', action='store_true', help='Find duplicate files')
    parser.add_argument('--cache-dir', default='.scan_cache', help='Cache directory')
    args = parser.parse_args()

    options = ScanOptions(
        max_workers=args.workers,
        memory_limit_mb=args.memory_limit,
        incremental=args.incremental,
        force_rescan=args.force_rescan,
    )
    engine = PerformanceEngine(cache_dir=Path(args.cache_dir), options=options)

    if args.benchmark:
        results = benchmark_scan(args.directories, options=options)
        print_benchmark(results)
        return

    scan_fn = engine.incremental_scan if args.incremental else engine.parallel_scan_directories
    file_count = 0
    records = []
    for info in scan_fn(args.directories):
        file_count += 1
        records.append(info)
        if file_count % 1000 == 0:
            print(f"Scanned {file_count} files...")
    print(f"Total files scanned: {file_count}")

    if args.find_duplicates:
        duplicates = engine.find_duplicates(file_records=records)
        print(f"Duplicate groups: {len(duplicates)}")
        for h, paths in duplicates.items():
            print(f"  {h[:16]}... ({len(paths)} files)")


if __name__ == '__main__':
    main()
