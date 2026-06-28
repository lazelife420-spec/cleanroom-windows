#!/usr/bin/env python3
"""Compatibility shim for legacy archive_manager imports."""

from archive_runtime import (
    apply_prune,
    browse_archive,
    display_archive_files,
    display_archive_summary,
    get_archive_summary,
    interactive_archive_cleanup,
    main,
)

__all__ = [
    'apply_prune',
    'browse_archive',
    'display_archive_files',
    'display_archive_summary',
    'get_archive_summary',
    'interactive_archive_cleanup',
    'main',
]


if __name__ == '__main__':
    main()
