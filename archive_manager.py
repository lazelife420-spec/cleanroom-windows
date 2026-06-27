#!/usr/bin/env python3
"""Archive management interface - browse, review, and clean archived files."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import archive_custody


def apply_prune(records, log_file, dry_run=False, receipt_dir=None, now=None):
    """Compatibility wrapper for legacy callers that still import archive_manager."""
    return archive_custody.apply_prune(
        records,
        log_file,
        receipt_dir=receipt_dir,
        dry_run=dry_run,
        now=now,
    )


def get_archive_summary(archive_dir: str, log_file: str = "cleanup_log.json") -> Dict:
    """Get comprehensive archive statistics."""
    archive_path = Path(archive_dir)
    log_path = Path(log_file)

    summary = {
        'archive_dir': str(archive_path),
        'archive_exists': archive_path.exists(),
        'archive_size_mb': 0,
        'file_count': 0,
        'oldest_file': None,
        'newest_file': None,
        'by_reason': {},
        'by_age': {'7_days': 0, '30_days': 0, '90_days': 0, 'older': 0},
        'large_files': [],
        'total_log_entries': 0
    }

    if not archive_path.exists():
        return summary

    # Calculate archive size and file count
    try:
        for file_path in archive_path.rglob('*'):
            if file_path.is_file():
                size = file_path.stat().st_size
                summary['archive_size_mb'] += size / (1024 * 1024)
                summary['file_count'] += 1

                # Track large files (>10MB)
                if size > 10 * 1024 * 1024:
                    summary['large_files'].append({
                        'path': str(file_path.relative_to(archive_path)),
                        'size_mb': size / (1024 * 1024),
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime)
                    })

                # Track age
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                age_days = (datetime.now() - mtime).days

                if not summary['oldest_file'] or mtime < summary['oldest_file']['modified']:
                    summary['oldest_file'] = {'path': str(file_path.relative_to(archive_path)), 'modified': mtime}
                if not summary['newest_file'] or mtime > summary['newest_file']['modified']:
                    summary['newest_file'] = {'path': str(file_path.relative_to(archive_path)), 'modified': mtime}

                if age_days <= 7:
                    summary['by_age']['7_days'] += 1
                elif age_days <= 30:
                    summary['by_age']['30_days'] += 1
                elif age_days <= 90:
                    summary['by_age']['90_days'] += 1
                else:
                    summary['by_age']['older'] += 1
    except Exception:
        pass

    # Analyze log entries for reason statistics
    try:
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
                if isinstance(log_data, list):
                    log_entries = log_data
                elif isinstance(log_data, dict) and 'actions' in log_data:
                    log_entries = log_data['actions']
                else:
                    log_entries = []

                summary['total_log_entries'] = len(log_entries)

                for entry in log_entries:
                    if entry.get('action') == 'prune':
                        continue  # Skip prune entries

                    reason = entry.get('reason', 'other')
                    dest = entry.get('dest', '')

                    # Only count if file is still in archive
                    if dest and Path(dest).exists():
                        summary['by_reason'][reason] = summary['by_reason'].get(reason, 0) + 1
    except Exception:
        pass

    # Sort large files by size
    summary['large_files'].sort(key=lambda x: x['size_mb'], reverse=True)

    return summary


def display_archive_summary(summary: Dict):
    """Display formatted archive summary."""
    print("\n" + "="*60)
    print("📦 ARCHIVE SUMMARY")
    print("="*60)

    if not summary['archive_exists']:
        print(f"❌ Archive directory not found: {summary['archive_dir']}")
        return

    print(f"📍 Location: {summary['archive_dir']}")
    print(f"📊 Total size: {summary['archive_size_mb']:.1f} MB")
    print(f"📁 File count: {summary['file_count']}")

    if summary['oldest_file']:
        print(f"🕐 Oldest file: {summary['oldest_file']['modified'].strftime('%Y-%m-%d')} ({summary['oldest_file']['path']})")
    if summary['newest_file']:
        print(f"🕑 Newest file: {summary['newest_file']['modified'].strftime('%Y-%m-%d')} ({summary['newest_file']['path']})")

    print("\n📈 BY AGE:")
    print(f"  • ≤ 7 days:  {summary['by_age']['7_days']} files")
    print(f"  • ≤ 30 days: {summary['by_age']['30_days']} files")
    print(f"  • ≤ 90 days: {summary['by_age']['90_days']} files")
    print(f"  • > 90 days:  {summary['by_age']['older']} files")

    if summary['by_reason']:
        print("\n🏷️  BY REASON:")
        for reason, count in sorted(summary['by_reason'].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {reason}: {count} files")

    if summary['large_files']:
        print("\n🔍 LARGE FILES (>10MB):")
        for i, file_info in enumerate(summary['large_files'][:5], 1):
            print(f"  {i}. {file_info['path']} ({file_info['size_mb']:.1f} MB)")
        if len(summary['large_files']) > 5:
            print(f"  ... and {len(summary['large_files']) - 5} more")


def browse_archive(archive_dir: str, filter_reason: str = None, limit: int = 50) -> List[Dict]:
    """Browse archived files with optional filtering."""
    archive_path = Path(archive_dir)
    if not archive_path.exists():
        print(f"❌ Archive directory not found: {archive_dir}")
        return []

    try:
        with open('cleanup_log.json', 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            if isinstance(log_data, list):
                log_entries = log_data
            elif isinstance(log_data, dict) and 'actions' in log_data:
                log_entries = log_data['actions']
            else:
                log_entries = []
    except Exception:
        print("❌ Could not read cleanup log")
        return []

    files = []
    for entry in log_entries:
        if entry.get('action') == 'prune':
            continue

        src = entry.get('src', '')
        dest = entry.get('dest', '')
        reason = entry.get('reason', 'other')
        size = entry.get('size', 0)
        when = entry.get('when', '')

        if not dest or not Path(dest).exists():
            continue

        if filter_reason and filter_reason.lower() not in reason.lower():
            continue

        files.append({
            'src': src,
            'dest': dest,
            'reason': reason,
            'size': size,
            'when': when,
            'age_days': (datetime.now() - datetime.fromisoformat(when.replace('Z', '+00:00'))).days if when else 0
        })

    # Sort by newest first
    files.sort(key=lambda x: x['when'], reverse=True)
    return files[:limit]


def display_archive_files(files: List[Dict], show_numbers: bool = True):
    """Display archived files in a formatted list."""
    if not files:
        print("📭 No files found in archive")
        return

    print(f"\n📋 ARCHIVED FILES (showing {len(files)} recent files):")
    print("-" * 80)

    for i, file_info in enumerate(files, 1):
        size_str = f"{file_info['size'] / (1024*1024):.1f} MB" if file_info['size'] > 1024*1024 else f"{file_info['size']} B"
        age_str = f"{file_info['age_days']}d ago" if file_info['age_days'] > 0 else "today"

        prefix = f"{i:2d}. " if show_numbers else "   "
        print(f"{prefix}📄 {Path(file_info['dest']).name}")
        print(f"     📍 {file_info['dest']}")
        print(f"     🏷️  {file_info['reason']} • 📏 {size_str} • 🕐 {age_str}")
        print(f"     🔄 Original: {file_info['src']}")
        print()


def interactive_archive_cleanup(archive_dir: str, log_file: str = "cleanup_log.json"):
    """Interactive archive cleanup with user prompts."""
    print("🧹 INTERACTIVE ARCHIVE CLEANUP")
    print("="*50)

    # Show summary
    summary = get_archive_summary(archive_dir, log_file)
    display_archive_summary(summary)

    if not summary['archive_exists'] or summary['file_count'] == 0:
        print("\n✨ Archive is already clean!")
        return

    # Load archive records for smart recommendations
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            actions = json.load(f)
            if isinstance(actions, list):
                log_actions = actions
            elif isinstance(actions, dict) and 'actions' in actions:
                log_actions = actions['actions']
            else:
                log_actions = []

        records = archive_custody.build_archive_records(log_actions)
        safe_files = archive_custody.filter_by_prune_rank(records, 'Safe to delete')
        review_files = archive_custody.filter_by_prune_rank(records, 'Review first')

        print("\n🤖 SMART RECOMMENDATIONS:")
        print(f"   ✅ Safe to delete: {len(safe_files)} files")
        print(f"   ⚠️  Review first: {len(review_files)} files")

    except Exception:
        safe_files = []
        review_files = []

    while True:
        print("\n🎯 CLEANUP OPTIONS:")
        print("1. 🗑️  Delete safe files (recommended)")
        print("2. 🔍 Browse all files")
        print("3. 📅 Delete files older than X days")
        print("4. 🏷️  Delete files by reason")
        print("5. 📊 Show detailed summary")
        print("6. 🚪 Exit")

        choice = input("\nSelect option (1-6): ").strip()

        if choice == '1':
            # Delete safe files
            if safe_files:
                print(f"\n📋 Files safe to delete ({len(safe_files)}):")
                display_archive_files([{'dest': r['dest'], 'src': r['src'], 'reason': r['reason'], 'size': r['size'], 'when': r['when'], 'age_days': (datetime.now() - datetime.fromisoformat(r['when'].replace('Z', '+00:00'))).days if r.get('when') else 0} for r in safe_files[:10]], show_numbers=False)

                if input(f"\n🗑️  Delete these {len(safe_files)} safe files? (y/N): ").lower() == 'y':
                    result = archive_custody.apply_prune(safe_files, log_file, dry_run=False)
                    print(f"✅ Deleted {len(result['pruned'])} files, freed {result['bytes_pruned'] / (1024*1024):.1f} MB")
            else:
                print("ℹ️  No files marked as safe to delete")

        elif choice == '2':
            # Browse files
            files = browse_archive(archive_dir, limit=20)
            display_archive_files(files)

            if files and input("\n🗑️  Delete any of these files? (y/N): ").lower() == 'y':
                try:
                    num = input("Enter file number to delete (or 'all'): ").strip()
                    if num.lower() == 'all':
                        selected = files
                    else:
                        idx = int(num) - 1
                        if 0 <= idx < len(files):
                            selected = [files[idx]]
                        else:
                            print("❌ Invalid file number")
                            continue

                    # Convert to archive_custody format
                    selected_records = [{'dest': f['dest'], 'src': f['src'], 'reason': f['reason'], 'size': f['size'], 'when': f['when']} for f in selected]
                    result = archive_custody.apply_prune(selected_records, log_file, dry_run=False)
                    print(f"✅ Deleted {len(result['pruned'])} files, freed {result['bytes_pruned'] / (1024*1024):.1f} MB")
                except ValueError:
                    print("❌ Invalid input")

        elif choice == '3':
            # Delete by age
            try:
                days = int(input("Delete files older than how many days? "))
                files = browse_archive(archive_dir)
                old_files = [f for f in files if f['age_days'] > days]

                if old_files:
                    print(f"\n📋 Files older than {days} days ({len(old_files)}):")
                    display_archive_files(old_files[:10], show_numbers=False)

                    if input(f"\n🗑️  Delete these {len(old_files)} old files? (y/N): ").lower() == 'y':
                        selected_records = [{'dest': f['dest'], 'src': f['src'], 'reason': f['reason'], 'size': f['size'], 'when': f['when']} for f in old_files]
                        result = archive_custody.apply_prune(selected_records, log_file, dry_run=False)
                        print(f"✅ Deleted {len(result['pruned'])} files, freed {result['bytes_pruned'] / (1024*1024):.1f} MB")
                else:
                    print(f"ℹ️  No files older than {days} days")
            except ValueError:
                print("❌ Invalid number")

        elif choice == '4':
            # Delete by reason
            files = browse_archive(archive_dir)
            reasons = sorted(set(f['reason'] for f in files))

            print("\n🏷️  Available reasons:")
            for i, reason in enumerate(reasons, 1):
                count = len([f for f in files if f['reason'] == reason])
                print(f"{i}. {reason} ({count} files)")

            try:
                choice = int(input("Select reason: ")) - 1
                if 0 <= choice < len(reasons):
                    selected_reason = reasons[choice]
                    reason_files = [f for f in files if f['reason'] == selected_reason]

                    print(f"\n📋 Files with reason '{selected_reason}' ({len(reason_files)}):")
                    display_archive_files(reason_files[:10], show_numbers=False)

                    if input(f"\n🗑️  Delete these {len(reason_files)} files? (y/N): ").lower() == 'y':
                        selected_records = [{'dest': f['dest'], 'src': f['src'], 'reason': f['reason'], 'size': f['size'], 'when': f['when']} for f in reason_files]
                        result = archive_custody.apply_prune(selected_records, log_file, dry_run=False)
                        print(f"✅ Deleted {len(result['pruned'])} files, freed {result['bytes_pruned'] / (1024*1024):.1f} MB")
                else:
                    print("❌ Invalid choice")
            except ValueError:
                print("❌ Invalid input")

        elif choice == '5':
            # Show detailed summary
            display_archive_summary(summary)

        elif choice == '6':
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Archive management interface')
    parser.add_argument('--archive', '-a', default='cleanup_archive', help='Archive directory path')
    parser.add_argument('--log', '-l', default='cleanup_log.json', help='Log file path')
    parser.add_argument('--summary', action='store_true', help='Show archive summary only')
    parser.add_argument('--browse', action='store_true', help='Browse archived files')
    parser.add_argument('--interactive', action='store_true', help='Interactive cleanup mode')
    parser.add_argument('--filter-reason', help='Filter files by reason')
    parser.add_argument('--limit', type=int, default=50, help='Limit number of files to show')

    args = parser.parse_args()

    if args.summary:
        summary = get_archive_summary(args.archive, args.log)
        display_archive_summary(summary)

    elif args.browse:
        files = browse_archive(args.archive, args.filter_reason, args.limit)
        display_archive_files(files)

    elif args.interactive:
        interactive_archive_cleanup(args.archive, args.log)

    else:
        # Default to interactive mode
        interactive_archive_cleanup(args.archive, args.log)


if __name__ == '__main__':
    main()
