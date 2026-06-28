#!/usr/bin/env python3
"""Compatibility shim for legacy smart_config imports."""

from cleanup_profiles import CleanupRule, LearningData, Profile, SmartConfig, main

__all__ = ['CleanupRule', 'LearningData', 'Profile', 'SmartConfig', 'main']


if __name__ == '__main__':
    main()
