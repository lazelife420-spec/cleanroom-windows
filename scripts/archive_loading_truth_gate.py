#!/usr/bin/env python3
"""Gate: archive footer has single writer set; no ready text while loading."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUI = (ROOT / 'startup_manager_gui.py').read_text(encoding='utf-8')

FOOTER_WRITERS = (
    '_set_archive_footer_loading',
    '_set_archive_footer_ready',
    '_set_archive_footer_empty',
    '_set_archive_footer_error',
)


def main() -> int:
    failed = []
    for fn in FOOTER_WRITERS:
        if f'def {fn}' not in GUI:
            failed.append(f'missing {fn}')
    if '_archive_loaded = True' in GUI:
        # Must not set loaded before tree populate completes in refresh done callback
        done_block = GUI.split('def refresh_archive_browser', 1)[-1].split('def _update_archive_stat_cards', 1)[0]
        if '_archive_loaded = True' in done_block.split('def done(result, err):', 1)[-1].split('self._run_bg', 1)[0]:
            failed.append('refresh_archive_browser done() sets _archive_loaded before populate')
    if 'status_lbl=self.archive_status_lbl' in GUI.split('_apply_archive_view_filters', 1)[-1][:1200]:
        failed.append('_apply_archive_view_filters still passes archive_status_lbl to chunked populate')
    if '_archive_restore_btn' not in GUI:
        failed.append('restore button not tracked separately from bulk archive actions')
    if failed:
        print('archive_loading_truth_gate: FAIL')
        for line in failed:
            print(f'  - {line}')
        return 1
    print('archive_loading_truth_gate: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
