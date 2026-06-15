#!/usr/bin/env python3
"""Source launch tray/process lifecycle gate — subprocess init, shutdown, clean exit.

Verifies StartupManagerGUI can start tray wiring and exit without leaving the
active tray singleton set. Does not replace manual notification-area checks —
see docs/PR22-SIGNOFF.md.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LIFECYCLE = textwrap.dedent(
    '''
    import sys
    import time
    from pathlib import Path

    ROOT = Path(r"{root}")
    sys.path.insert(0, str(ROOT))

    from tkinter import messagebox
    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno', 'askokcancel'):
        if fn in ('askyesno', 'askokcancel'):
            setattr(messagebox, fn, lambda *a, **k: True)
        else:
            setattr(messagebox, fn, lambda *a, **k: None)

    import startup_manager_gui as gui
    from ui.tray import get_active_tray, shutdown_all_trays

    app = gui.StartupManagerGUI()
    deadline = time.time() + 15.0
    tray = None
    while time.time() < deadline:
        app.update_idletasks()
        app.update()
        tray = getattr(app, '_tray', None)
        if tray is not None and tray.is_running:
            break
        time.sleep(0.1)

    if tray is None or not tray.is_running:
        err = getattr(tray, 'last_error', '') if tray else 'tray never initialized'
        print('FAIL: tray not running:', err, file=sys.stderr)
        shutdown_all_trays()
        try:
            app.destroy()
        except Exception:
            pass
        sys.exit(1)

    app._shutdown_app(reason='process-gate')
    time.sleep(0.5)
    if get_active_tray() is not None:
        print('FAIL: active tray singleton still set after shutdown', file=sys.stderr)
        shutdown_all_trays()
        sys.exit(1)
    print('TRAY PROCESS GATE PASSED')
    '''
).format(root=str(ROOT).replace('\\', '\\\\'))


def main() -> None:
    proc = subprocess.run(
        [sys.executable, '-c', LIFECYCLE],
        cwd=str(ROOT),
        timeout=90,
        text=True,
        capture_output=True,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(proc.returncode or 1)
    raise SystemExit(0)


if __name__ == '__main__':
    main()
