import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

CFG = Path(__file__).parent / 'cleanup_config.yaml'

MESSAGE = (
    "Cleanroom can optionally record anonymous local usage events to help improve reliability.\n"
    "No personal files or contents leave this PC. Data stays local unless you opt in to sharing.\n\n"
    "Enable local diagnostics logging (usage_log.json)?"
)


def set_telemetry(enable: bool):
    # Prefer importing the helper to avoid subprocess overhead; fall back to subprocess
    try:
        from enable_telemetry import main as _et_main
        # ensure module uses same config file as the GUI (optional)
        try:
            import enable_telemetry as _et_mod
            _et_mod.CFG = CFG
        except Exception:
            pass
        rc = _et_main(enable=bool(enable))
        return rc == 0
    except Exception:
        proc = subprocess.run([sys.executable, str(Path(__file__).parent / 'enable_telemetry.py'), 'true' if enable else 'false'], capture_output=True, text=True)
        return proc.returncode == 0


def on_enable():
    ok = set_telemetry(True)
    if ok:
        messagebox.showinfo('Diagnostics', 'Local diagnostics logging enabled.')
    else:
        messagebox.showerror('Diagnostics', 'Failed to update configuration.')
    root.destroy()


def on_disable():
    ok = set_telemetry(False)
    if ok:
        messagebox.showinfo('Diagnostics', 'Local diagnostics logging disabled.')
    else:
        messagebox.showerror('Diagnostics', 'Failed to update configuration.')
    root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    if messagebox.askyesno('Cleanroom — Diagnostics', MESSAGE):
        on_enable()
    else:
        on_disable()
