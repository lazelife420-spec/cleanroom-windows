"""Bridge from Cleanroom to the optional standalone RECEIPT proof viewer.

Cleanroom never depends on RECEIPT existing. This module answers only two
questions — is RECEIPT available on this machine, and (if so) launch it
out-of-process on a receipt file. Every caller degrades cleanly to
Cleanroom's own in-app receipt viewer when RECEIPT is absent.

Local-only: this shells out to a local viewer process and nothing else. No
network, no account, no telemetry.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

# Standalone packaged viewer shipped beside a frozen Cleanroom, if/when it
# exists. Until it ships, frozen builds simply report "unavailable".
RECEIPT_EXE_NAME = 'RECEIPT.exe'
_RECEIPT_MODULE = 'receipt_desktop.app'


def _frozen() -> bool:
    return bool(getattr(sys, 'frozen', False))


def _standalone_exe() -> Path | None:
    """A sibling RECEIPT.exe next to the running executable, if present."""
    try:
        base = Path(sys.executable).resolve().parent
    except Exception:
        return None
    candidate = base / RECEIPT_EXE_NAME
    return candidate if candidate.is_file() else None


def _module_available() -> bool:
    """True when the receipt_desktop app module is importable (dev/source)."""
    try:
        return importlib.util.find_spec(_RECEIPT_MODULE) is not None
    except Exception:
        return False


def is_available() -> bool:
    """True when there is a way to launch RECEIPT on this machine.

    Supported deployments:
      * a standalone RECEIPT.exe shipped beside a frozen Cleanroom, or
      * the receipt_desktop module importable from source (dev runs).

    A frozen Cleanroom with no sibling exe reports False, so the optional
    "Open in RECEIPT" button stays hidden until RECEIPT actually ships.
    """
    if _standalone_exe() is not None:
        return True
    if not _frozen() and _module_available():
        return True
    return False


def _launch_plan(path: str):
    """Return (cmd, cwd) to launch RECEIPT out-of-process, or None.

    Prefers a standalone exe; falls back to the source module in dev runs.
    """
    exe = _standalone_exe()
    if exe is not None:
        return [str(exe), '--open', path], str(exe.parent)
    if not _frozen() and _module_available():
        repo_root = Path(__file__).resolve().parent
        return (
            [sys.executable, '-m', _RECEIPT_MODULE, '--open', path],
            str(repo_root),
        )
    return None


def open_receipt(path) -> tuple[bool, str]:
    """Launch RECEIPT on *path* out-of-process.

    Returns ``(ok, error)``. Never raises: Cleanroom must stay alive whatever
    happens here, and the caller falls back to the in-app viewer on failure.
    """
    p = Path(path)
    if not p.is_file():
        return False, 'Receipt file not found.'
    plan = _launch_plan(str(p))
    if plan is None:
        return False, 'RECEIPT is not available on this PC.'
    cmd, cwd = plan
    try:
        subprocess.Popen(cmd, cwd=cwd, close_fds=True)
    except Exception as exc:
        return False, f'Could not start RECEIPT: {exc}'
    return True, ''
