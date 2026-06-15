"""Cleanroom receipt identity — titles, badges, and R.E.C.E.I.P.T. proof language."""
from __future__ import annotations

RECEIPT_ACRONYM = 'R.E.C.E.I.P.T.'
RECEIPT_EXPANDED = (
    'Record · Evidence · Custody · Event · Integrity · Proof · Timestamp'
)

# Known module/action pairs for receipt window titles.
RECEIPT_ACTIONS = {
    'cleaner_preview': ('Cleaner', 'Preview'),
    'cleaner_archive': ('Cleaner', 'Archive Action'),
    'archive_prune': ('Archive', 'Prune Action'),
    'force_remove_intent': ('Force Remove', 'Intent'),
    'force_remove_complete': ('Force Remove', 'Complete'),
    'startup_change': ('Startup', 'Change'),
    'explorer_menu': ('Explorer Menu', 'Change'),
    'registry_snapshot': ('Registry', 'Snapshot'),
    'latest': ('Cleanroom', 'Stored Receipt'),
    'proof_pack': ('Proof Pack', 'Export'),
}


def receipt_window_title(module: str, action: str) -> str:
    module = (module or 'Cleanroom').strip()
    action = (action or 'Receipt').strip()
    return f'Cleanroom Receipt — {module} {action}'


def receipt_badge(*, preview: bool = False, archived: bool = False, pruned: bool = False) -> str:
    if preview:
        return 'PREVIEW ONLY'
    if pruned:
        return 'PRUNE COMPLETE'
    if archived:
        return 'ARCHIVE COMPLETE'
    return ''


def classify_receipt_body(text: str) -> dict:
    body = text or ''
    upper = body.upper()
    if 'FORCE REMOVE' in upper and 'INTENT' in upper:
        return {'module': 'Force Remove', 'action': 'Intent', 'preview': False}
    if 'FORCE REMOVE' in upper or 'FORCE REMOVED' in upper:
        return {'module': 'Force Remove', 'action': 'Complete', 'archived': True}
    if 'PRUNE RECEIPT' in upper or 'ITEMS PRUNED' in upper:
        return {'module': 'Archive', 'action': 'Prune Action', 'pruned': True}
    if 'PREVIEW ONLY' in upper:
        return {'module': 'Cleaner', 'action': 'Preview', 'preview': True}
    if 'STARTUP' in upper and ('ENABLE' in upper or 'DISABLE' in upper):
        return {'module': 'Startup', 'action': 'Change'}
    if 'REGISTRY' in upper and 'SNAPSHOT' in upper:
        return {'module': 'Registry', 'action': 'Snapshot'}
    if 'EXPLORER' in upper or 'SHELL CONTEXT' in upper:
        return {'module': 'Explorer Menu', 'action': 'Change'}
    if 'ITEMS MOVED' in upper or 'SPACE MOVED' in upper:
        return {'module': 'Cleaner', 'action': 'Archive Action', 'archived': True}
    return {'module': 'Cleanroom', 'action': 'Receipt'}


def receipt_context(
    text: str = '',
    *,
    module: str | None = None,
    action: str | None = None,
    preview: bool = False,
    action_key: str | None = None,
) -> dict:
    if action_key and action_key in RECEIPT_ACTIONS:
        mod, act = RECEIPT_ACTIONS[action_key]
        module = module or mod
        action = action or act
    inferred = classify_receipt_body(text)
    module = module or inferred.get('module', 'Cleanroom')
    action = action or inferred.get('action', 'Receipt')
    is_preview = preview or bool(inferred.get('preview'))
    is_archived = bool(inferred.get('archived'))
    is_pruned = bool(inferred.get('pruned'))
    badge = receipt_badge(preview=is_preview, archived=is_archived, pruned=is_pruned)
    safety = ''
    if is_preview:
        safety = 'Preview only — no files were archived or deleted.'
    elif is_pruned:
        safety = 'Archive-only removal. Original live files were not touched.'
    elif is_archived:
        safety = (
            'Nothing was deleted. Archived items remain in custody and can be restored.'
        )
    return {
        'module': module,
        'action': action,
        'preview': is_preview,
        'archived': is_archived,
        'pruned': is_pruned,
        'title': receipt_window_title(module, action),
        'badge': badge,
        'safety': safety,
        'acronym': RECEIPT_ACRONYM,
        'expanded': RECEIPT_EXPANDED,
    }
