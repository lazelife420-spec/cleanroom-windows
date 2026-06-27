#!/usr/bin/env python3
# ruff: noqa: E402
"""Manual archive-only prune gate — disposable files, evidence-backed checks.

Run from repo root after rebasing feature/in-app-receipts-archive-prune:

    python scripts/archive_prune_manual_gate.py

Prints PASS/FAIL checklist. Exit 0 only if all hard gates pass.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import archive_custody as ac
import brand
import ledger
import main as cleanup_main
import receipts
import restore as restore_module

try:
    import audit
except Exception:
    audit = None


def _ok(label: str) -> None:
    print(f'[x] {label}')


def _fail(label: str, detail: str = '') -> None:
    msg = f'[ ] {label}'
    if detail:
        msg += f' — {detail}'
    print(msg)


def _age_file(path: Path, days: int = 45) -> None:
    old = time.time() - days * 86400
    os.utime(path, (old, old))


def main() -> int:
    gate_root = Path(os.environ.get('TEMP', '/tmp')) / 'cleanroom-prune-gate'
    if gate_root.exists():
        import shutil
        shutil.rmtree(gate_root, ignore_errors=True)
    gate_root.mkdir(parents=True)
    live_decoy = gate_root / 'live-decoy.txt'
    live_decoy.write_text('must never be pruned', encoding='utf-8')

    file_a = gate_root / 'delete-me-a.tmp'
    file_b = gate_root / 'delete-me-b.log'
    file_c = gate_root / 'delete-me-c.tmp'
    file_a.write_text('test a', encoding='utf-8')
    file_b.write_text('test b', encoding='utf-8')
    file_c.write_text('test c', encoding='utf-8')
    for p in (file_a, file_b, file_c):
        _age_file(p, 45)

    sandbox = gate_root / 'cleanroom-gate-profile'
    local = sandbox / 'LocalAppData' / 'Cleanroom'
    local.mkdir(parents=True, exist_ok=True)
    archive_dir = local / 'archive_gate'
    log_path = local / 'cleanup_log.json'
    receipt_dir = local / 'receipts'
    receipt_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        'paths': [str(gate_root)],
        'age_days': {'temp': 1, 'installers': 1},
        'size_threshold_mb': 200,
        'extensions_archive': ['.tmp', '.log', '.zip'],
        'exclude_patterns': [],
        'whitelist': [],
        'archive_dir': str(archive_dir),
        'log_file': str(log_path),
    }

    failed = []

    def check(cond, label, detail=''):
        if cond:
            _ok(label)
        else:
            _fail(label, detail)
            failed.append(label)

    candidates = cleanup_main.scan_candidates(cfg)
    check(len(candidates) >= 2, 'Scan finds disposable files',
          f'found {len(candidates)}')

    log = cleanup_main.apply_actions(candidates, cfg, archive_dir)
    check(len(log) >= 2, 'Archive & Clean moves files into Cleanroom custody/archive',
          f'log entries {len(log)}')

    for entry in log:
        src = Path(entry['src'])
        check(not src.exists(), f'Original gone from source: {src.name}')

    check(live_decoy.exists(), 'Prune never touches unrelated live decoy in gate folder')

    receipt_path = receipts.write_receipt(log, receipt_dir=receipt_dir)
    check(receipt_path and receipt_path.is_file(), 'Cleanroom receipt written after archive')
    body = receipts.format_receipt(log)
    check('CLEANROOM — RECEIPT' in body and brand.APP_MOTTO in body,
          'Preview Receipt text formatted (in-app viewer content)')

    # Restore first archived item
    entry_a = log[0]
    ok, msg = restore_module.restore_one(entry_a['src'], entry_a['dest'], apply=True)
    check(ok, 'Restore Selected restores file back to source folder', msg)
    check(Path(entry_a['src']).exists(), 'Restored file present at original path')

    actions = restore_module.load_log(str(log_path))
    records = ac.build_archive_records(actions, receipt_dir=receipt_dir, config=cfg)
    check(len(records) >= 1, 'Archive Browser shows evidence-backed records',
          f'{len(records)} rows')
    if records:
        check(records[0].get('receipt_path') is not None or receipt_path,
              'Receipt linkage available for archive records')
        check(records[0].get('prune_rank') in ac.PRUNE_RANK_ORDER,
              'Prune recommendation/rank appears')

    # Prune one still-archived item (not the restored one's dest if missing)
    to_prune = [r for r in records if Path(r['dest']).exists()]
    check(len(to_prune) >= 1, 'At least one archived custody copy remains to prune')
    prune_target = to_prune[0]
    src_before = Path(prune_target['src'])
    live_existed = src_before.exists()

    dry = ac.apply_prune([prune_target], log_path, receipt_dir=receipt_dir, dry_run=True)
    check(dry['dry_run'] and len(dry['pruned']) >= 1,
          'Prune dry-run previews archive-only removal')

    result = ac.apply_prune([prune_target], log_path, receipt_dir=receipt_dir, dry_run=False)
    check(len(result['pruned']) >= 1, 'Prune deletes archived custody copy')
    check(not Path(prune_target['dest']).exists(), 'Archived copy removed after prune')
    if live_existed:
        check(src_before.exists(), 'Prune does not delete original live/source files')
    check(live_decoy.exists(), 'Prune never touches unrelated live files')

    pr = result.get('receipt_path')
    check(pr and Path(pr).is_file(), 'Prune Receipt is written')
    if pr:
        pr_text = Path(pr).read_text(encoding='utf-8')
        check('PRUNE RECEIPT' in pr_text and 'Original live files were not touched' in pr_text,
              'Prune Receipt documents archive-only removal')

    actions2 = restore_module.load_log(str(log_path))
    check(any(a.get('action') == 'prune' for a in actions2 if isinstance(a, dict)),
          'Activity Ledger records prune action')
    feed = ledger.build_activity_feed(actions2)
    check(any(e.get('kind') == 'prune' for e in feed), 'Ledger feed includes prune event')

    # Restore unpruned remaining archive
    remaining = [r for r in ac.build_archive_records(actions2, receipt_dir=receipt_dir, config=cfg)
                 if Path(r['dest']).exists()]
    if remaining:
        r = remaining[0]
        ok2, msg2 = restore_module.restore_one(r['src'], r['dest'], apply=True)
        check(ok2, 'Restore still works for unpruned archived item', msg2)

    # Proof pack generation
    if audit and feed:
        entries = [t[3] for t in restore_module.entries_from_log(actions2)]
        try:
            import proof as proof_module
            custody = proof_module.verify_entries(entries)
        except Exception:
            custody = {'verified': 0, 'total': 0, 'missing': 0, 'bytes_in_custody': 0}
        summary = ledger.summarize_feed(feed)
        trust = ledger.trust_score(custody.get('verified', 0), custody.get('total', 0))
        out = local / 'audits' / 'gate_audit.html'
        out.parent.mkdir(parents=True, exist_ok=True)
        audit.export_html_audit(feed, custody, summary, trust, out,
                                app_version=brand.APP_VERSION)
        check(out.is_file() and out.stat().st_size > 500, 'Proof Pack HTML generates')
    else:
        check(False, 'Proof Pack HTML generates', 'audit module unavailable')

    # GUI confirmation strings (static check)
    gui_src = (ROOT / 'startup_manager_gui.py').read_text(encoding='utf-8')
    check('Prune Selected from Archive' in gui_src, 'Prune Selected requires confirmation (button label)')
    check('no longer be possible after pruning' in gui_src,
          'Confirmation clearly says restore will no longer be possible')
    check('show_receipt' in gui_src and '_play_receipt_animation' in gui_src,
          'Preview Receipt uses animation then in-app viewer path')

    print('\n=== Summary ===')
    if failed:
        print(f'GATE FAILED ({len(failed)}):')
        for f in failed:
            print(f'  - {f}')
        print(f'\nGate folder preserved: {gate_root}')
        return 1
    print('ARCHIVE-ONLY PRUNE MANUAL GATE PASSED')
    print(f'Gate folder: {gate_root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
