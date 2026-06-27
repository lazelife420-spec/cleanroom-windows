#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def prune(archive_dir: Path, days: int, apply: bool):
    if not archive_dir.exists():
        print(f"Archive dir does not exist: {archive_dir}")
        return []
    cutoff = datetime.now() - timedelta(days=days)
    removed = []
    for p in archive_dir.rglob('*'):
        if p.is_file():
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime)
            except Exception:
                continue
            if mtime < cutoff:
                removed.append(str(p))
                if apply:
                    try:
                        p.unlink()
                    except Exception:
                        pass
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive', '-a', default=str(Path(__file__).parent / 'archive'), help='Archive dir')
    ap.add_argument('--days', type=int, default=90, help='Prune files older than this many days')
    ap.add_argument('--apply', action='store_true', help='Actually delete files')
    args = ap.parse_args()
    removed = prune(Path(args.archive), args.days, args.apply)
    print(f"Candidates to remove: {len(removed)}")
    for r in removed[:100]:
        print(r)

if __name__ == '__main__':
    main()
