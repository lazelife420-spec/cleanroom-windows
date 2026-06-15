"""RECEIPT Desktop — launchable proof viewer entry point.

Usage::

    python -m receipt_desktop.app
    python -m receipt_desktop.app --open C:\\path\\receipt.cleanroom-receipt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from receipt_desktop.viewer import ReceiptViewerApp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog='receipt-desktop',
        description='RECEIPT Desktop — local-only proof viewer',
    )
    p.add_argument(
        '--open', dest='receipt_path',
        help='Path to a .cleanroom-receipt or legacy .txt receipt file',
    )
    return p.parse_args(argv)


def open_receipt_standalone(path: str) -> int:
    """Open a receipt file in the RECEIPT viewer.  Returns exit code."""
    p = Path(path)
    if not p.is_file():
        print(f'RECEIPT: file not found — {path}')
        return 1

    app = ReceiptViewerApp(receipt_path=path)
    app.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    app = ReceiptViewerApp(receipt_path=args.receipt_path)
    app.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
