# Performance Engine Guide

The `performance_engine.py` module provides a scalable, high-performance file scanner for Cleanroom. It is designed for directory trees containing millions of files and supports parallel scanning, incremental re-scanning, memory-aware throttling, and duplicate detection.

## Features

- **Parallel directory scanning**: Uses a thread pool to scan multiple directories concurrently, bounded by CPU count.
- **Incremental scanning**: Persists file size and modification time in a SQLite database so unchanged files are skipped on subsequent runs.
- **Memory-aware throttling**: Monitors process RSS and pauses work when a configured memory limit is approached.
- **Fast duplicate detection**: Groups files by size first, then hashes only size collisions.
- **Memory-mapped hashing**: Large files are hashed via `mmap` to reduce read overhead.
- **Benchmarking**: Built-in `benchmark_scan()` compares full vs. incremental scan speed.

## Usage

### Standalone CLI

Run from the project root:

```bash
# Parallel scan of the current directory
python performance_engine.py --directories .

# Incremental scan (only changed files after the first run)
python performance_engine.py --directories . --incremental

# Find duplicate files
python performance_engine.py --directories . --find-duplicates

# Benchmark full vs incremental scans
python performance_engine.py --directories . --benchmark

# Tune workers and memory limit
python performance_engine.py --directories . --workers 8 --memory-limit 1024
```

### Python API

```python
from pathlib import Path
from performance_engine import PerformanceEngine, ScanOptions

options = ScanOptions(
    max_workers=8,
    memory_limit_mb=1024,
    incremental=True,
)
engine = PerformanceEngine(cache_dir=Path('.scan_cache'), options=options)

for file_info in engine.incremental_scan(['C:/Users/me/Downloads']):
    print(file_info['path'], file_info['size'])

# Find duplicates among discovered records
duplicates = engine.find_duplicates(file_records=list(engine.parallel_scan_directories(['.'])))
```

## Configuration

`ScanOptions` controls all behavior:

| Option | Default | Description |
|--------|---------|-------------|
| `max_workers` | `0` (auto) | Thread pool size. Auto = `min(32, cpu_count + 4)`. |
| `memory_limit_mb` | `512` | Soft memory limit; scanning pauses briefly when exceeded. |
| `hash_chunk_size` | `4 MiB` | Chunk size used when hashing files without mmap. |
| `mmap_threshold_bytes` | `10 MiB` | Files larger than this use memory-mapped hashing. |
| `batch_size` | `1000` | Number of incremental state rows updated per batch. |
| `incremental` | `True` | Enable incremental scan state persistence. |
| `force_rescan` | `False` | Ignore persisted state and scan every file. |
| `progress_every` | `1000` | Number of files between progress callback invocations. |

## How Incremental Scanning Works

1. The first scan records every file's path, size, and modification time in `scan_state.db` inside the configured cache directory.
2. On the next run, each discovered file is compared against the database. If size and mtime match, the file is skipped.
3. Changed or new files are yielded and their state is updated in batches.
4. Deleted files remain in the database until the next completed scan, when orphaned entries are removed automatically.

The cache directory is automatically excluded from scanning so internal state files are never treated as user files.

## Benchmarking

Use the built-in benchmark to compare full and incremental scans:

```python
from performance_engine import benchmark_scan, print_benchmark

results = benchmark_scan(['C:/Users/me/Downloads', 'C:/Temp'], iterations=3)
print_benchmark(results)
```

Example output:

```text
============================================================
Performance Benchmark Results
============================================================
Directories: C:/Users/me/Downloads, C:/Temp
Iterations: 3

Full scan average:        12.34s  (85432 files/s)
Incremental scan average:  1.23s  (854320 files/s)

Full scan details:
  Iteration 1: 1054213 files in 12.50s
  Iteration 2: 1054213 files in 12.10s
  Iteration 3: 1054213 files in 12.41s
Incremental scan details:
  Iteration 1: 0 files in 1.20s
  Iteration 2: 0 files in 1.25s
  Iteration 3: 0 files in 1.23s
```

## Memory Optimization Tips

1. **Reduce `batch_size`** if you see memory spikes during the first scan. The default `1000` is suitable for most systems.
2. **Lower `memory_limit_mb`** on constrained machines or raise it when scanning extremely large files.
3. **Avoid scanning the cache directory** as a root. The engine automatically excludes its own cache, but pointing a root directly at it wastes time.
4. **Use incremental mode** for scheduled runs. Most files do not change between runs, so only metadata is traversed.
5. **Limit duplicate hashing** by passing pre-filtered records to `find_duplicates()` instead of all discovered files.

## Integration with main.py

The engine can be used as a faster scan backend for `main.py`. A `scan_candidates_fast()` helper applies the same candidate rules as the default scanner but uses parallel directory enumeration and incremental state. Enable it via the config key `performance_scan: true` or the CLI flag `--fast-scan`.

When enabled, the GUI (`startup_manager_gui.py`) will also use the fast scanner. Per-folder skipping (the UI's "Stop Scan" folder feature) is supported by filtering files against the skip list in the parallel worker; this is slightly less efficient than the standard scanner's folder-before-entry skip, but it lets the GUI benefit from incremental state and parallelism.

The GUI also exposes a **Run Benchmark…** button in **Settings → Advanced → Performance scanner** that compares a full scan against an incremental scan over the configured folders, and a **Clear Cache** button that resets the incremental scan state so the next scan starts fresh.

Example configuration snippet in `cleanup_config.yaml`:

```yaml
paths:
  - C:/Users/me/Downloads
  - C:/Users/me/AppData/Local/Temp
performance_scan: true
performance:
  max_workers: 8
  memory_limit_mb: 1024
  incremental: true
```

## Example Use Cases

### Daily scheduled cleanup with incremental scan

```bash
python main.py --config cleanup_config.yaml --fast-scan --apply
```

### One-time duplicate cleanup on a large download folder

```bash
python performance_engine.py --directories C:/Users/me/Downloads --find-duplicates
```

### Benchmark before enabling in production

```bash
python performance_engine.py --directories C:/Users/me/Downloads C:/Temp --benchmark --workers 8
```

## File Reference

- `performance_engine.py` — engine implementation and CLI.
- `tests/test_performance_engine.py` — unit tests for scanning, hashing, incremental state, and caching.
- `docs/PERFORMANCE_ENGINE.md` — this guide.
