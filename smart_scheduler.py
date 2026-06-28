#!/usr/bin/env python3
"""Compatibility shim for legacy smart_scheduler entrypoints."""

from legacy.smart_cleaner.smart_scheduler import SmartScheduler, main

__all__ = ['SmartScheduler', 'main']


if __name__ == '__main__':
    main()
