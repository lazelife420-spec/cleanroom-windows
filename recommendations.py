#!/usr/bin/env python3
"""Pure, headless recommendation and health-score engine for Cleanroom.

Kept free of any GUI imports so it can be unit-tested without a display.
"""

GB = 1024 ** 3
MB = 1024 ** 2

# Order used when sorting recommendations for display.
SEVERITY_ORDER = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}

SEVERITY_COLORS = {
    'high': '#D62828',
    'medium': '#F0A500',
    'low': '#2563EB',
    'info': '#6B7280',
}


def compute_health_score(startup_count=0, cleanup_count=0, cleanup_bytes=0, restore_count=0):
    """Return a 10-100 health score from current system stats."""
    score = 100
    score -= min(40, cleanup_count * 2)
    score -= min(30, startup_count)
    if cleanup_bytes >= 5 * GB:
        score -= 10
    elif cleanup_bytes >= 1 * GB:
        score -= 5
    if restore_count == 0:
        score -= 5
    return max(10, score)


def health_band(score):
    """Return (hex_color, label) describing the score band."""
    if score >= 80:
        return ('#1F8A70', 'Excellent')
    if score >= 60:
        return ('#F0A500', 'Good')
    if score >= 40:
        return ('#F47835', 'Fair')
    return ('#D62828', 'Needs Attention')


def _human_size(n):
    value = float(n)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if value < 1024:
            return f"{value:.2f}{unit}"
        value /= 1024
    return f"{value:.2f}PB"


def build_recommendations(folder_count=0, registry_count=0, cleanup_count=0,
                          cleanup_bytes=0, restore_count=0, reason_counts=None):
    """Build a sorted list of recommendation dicts.

    Each dict has keys: severity ('high'|'medium'|'low'|'info'), title, detail.
    reason_counts may map cleanup reasons (e.g. 'large-file') to counts.
    """
    recs = []
    reason_counts = reason_counts or {}
    startup_count = folder_count + registry_count

    if cleanup_count > 0:
        if cleanup_bytes >= 5 * GB:
            sev = 'high'
        elif cleanup_bytes >= 500 * MB:
            sev = 'medium'
        else:
            sev = 'low'
        recs.append({
            'severity': sev,
            'title': f'Archive {cleanup_count} reviewed candidate(s)',
            'detail': (f'Reclaim {_human_size(cleanup_bytes)} by moving reviewed files into custody. '
                       'Nothing is deleted — every move is logged and restorable.'),
        })
    else:
        recs.append({
            'severity': 'info',
            'title': 'No cleanup candidates found',
            'detail': 'Your configured folders look clean. Re-scan periodically to keep it that way.',
        })

    large = reason_counts.get('large-file', 0)
    if large:
        recs.append({
            'severity': 'medium',
            'title': f'{large} large file(s) detected',
            'detail': 'Review big, old files first — they reclaim the most space per item.',
        })

    partial = reason_counts.get('partial-download', 0)
    if partial:
        recs.append({
            'severity': 'low',
            'title': f'{partial} abandoned partial download(s)',
            'detail': 'Unfinished .crdownload files are safe to archive.',
        })

    if registry_count > 12:
        recs.append({
            'severity': 'high',
            'title': 'Heavy registry startup load',
            'detail': f'{registry_count} registry autoruns found. Disable entries you do not need to speed up boot.',
        })
    elif registry_count > 6:
        recs.append({
            'severity': 'medium',
            'title': 'Review registry startup entries',
            'detail': f'{registry_count} registry autoruns found. Trimming a few can improve boot time.',
        })

    if folder_count > 4:
        recs.append({
            'severity': 'medium',
            'title': 'Crowded startup folder',
            'detail': f'{folder_count} startup folder shortcuts found. Check for bulky or duplicate launchers.',
        })

    if cleanup_count >= 20:
        recs.append({
            'severity': 'medium',
            'title': 'Schedule automatic cleanup',
            'detail': 'Reviewed files are accumulating — schedule regular archive runs to keep custody current.',
        })

    if restore_count == 0:
        recs.append({
            'severity': 'info',
            'title': 'No restore history yet',
            'detail': 'Archived files will appear in the Restore tab after your first cleanup.',
        })

    if startup_count == 0 and cleanup_count == 0:
        recs.append({
            'severity': 'info',
            'title': 'System looks lean',
            'detail': 'Nothing actionable right now. Nice work.',
        })

    recs.sort(key=lambda r: SEVERITY_ORDER.get(r['severity'], 99))
    return recs
