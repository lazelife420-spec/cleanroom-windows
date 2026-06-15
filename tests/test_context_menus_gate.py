"""Tests for context-menu and consolidation gate scripts."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_gate(name: str) -> subprocess.CompletedProcess:
    script = ROOT / 'scripts' / name
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_context_menu_gate_passes():
    r = _run_gate('context_menu_gate.py')
    assert r.returncode == 0, r.stdout + r.stderr


def test_receipt_identity_gate_passes():
    r = _run_gate('receipt_identity_gate.py')
    assert r.returncode == 0, r.stdout + r.stderr


def test_archive_loading_truth_gate_passes():
    r = _run_gate('archive_loading_truth_gate.py')
    assert r.returncode == 0, r.stdout + r.stderr


def test_scan_state_consolidation_gate_passes():
    r = _run_gate('scan_state_consolidation_gate.py')
    assert r.returncode == 0, r.stdout + r.stderr
