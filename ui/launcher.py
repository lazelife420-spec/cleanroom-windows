"""Local-only launch splash — brief, proof-first, no network."""
from __future__ import annotations

import customtkinter as ctk

from ui.receipt_animation import animations_disabled

LAUNCH_STEPS = (
    'Archive-first mode is ON',
    'Loading startup entries…',
    'Preparing proof flow…',
    'Local-only — no cloud, no telemetry',
    'Ready.',
)


def run_launch_splash(
    master,
    *,
    title: str,
    tagline: str,
    colors: dict,
    logo_photo,
    on_complete,
    min_ms: int = 1200,
) -> None:
    """Show a centered splash, then call on_complete() after min_ms."""
    if animations_disabled():
        on_complete()
        return

    bg = colors.get('BG', '#1a1d24')
    card = colors.get('CARD_BG', '#262c36')
    accent = colors.get('ACCENT', '#3b82f6')
    text = colors.get('TEXT', '#e5e7eb')
    muted = colors.get('MUTED', '#9ca3af')
    border = colors.get('BORDER', '#39414e')

    splash = ctk.CTkToplevel(master)
    splash.overrideredirect(True)
    splash.configure(fg_color=bg)
    try:
        splash.attributes('-topmost', True)
        splash.attributes('-alpha', 0.0)
    except Exception:
        pass

    w, h = 440, 300
    master.update_idletasks()
    sw = master.winfo_screenwidth()
    sh = master.winfo_screenheight()
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2 - 24)
    splash.geometry(f'{w}x{h}+{x}+{y}')

    frame = ctk.CTkFrame(splash, fg_color=card, corner_radius=14,
                         border_width=1, border_color=border)
    frame.pack(fill='both', expand=True, padx=2, pady=2)

    if logo_photo is not None:
        ctk.CTkLabel(frame, image=logo_photo, text='').pack(pady=(28, 8))
        splash._logo_ref = logo_photo

    ctk.CTkLabel(frame, text=title, text_color=text,
                 font=ctk.CTkFont('Segoe UI', 22, 'bold')).pack()
    ctk.CTkLabel(frame, text=tagline, text_color=muted,
                 font=ctk.CTkFont('Segoe UI', 11)).pack(pady=(4, 16))

    status_var = ctk.StringVar(value=LAUNCH_STEPS[0])
    ctk.CTkLabel(frame, textvariable=status_var, text_color=accent,
                 font=ctk.CTkFont('Segoe UI', 11, 'bold')).pack(pady=(0, 10))

    bar = ctk.CTkProgressBar(frame, width=320, height=8,
                             progress_color=accent, fg_color=border)
    bar.pack(pady=(0, 8))
    bar.set(0.08)

    ctk.CTkLabel(frame, text='Scan  →  Preview  →  Archive  →  Restore',
                 text_color=muted, font=ctk.CTkFont('Segoe UI', 10)).pack(pady=(4, 20))

    step_idx = {'i': 0}
    progress = {'v': 0.08}
    done = {'called': False}

    def _finish():
        if done['called']:
            return
        done['called'] = True
        try:
            splash.destroy()
        except Exception:
            pass
        on_complete()

    def _fade_in(step=0):
        try:
            splash.attributes('-alpha', min(1.0, step / 8.0))
        except Exception:
            _tick()
            return
        if step < 8:
            splash.after(30, lambda: _fade_in(step + 1))
        else:
            _tick()

    def _fade_out(step=8):
        try:
            splash.attributes('-alpha', step / 8.0)
        except Exception:
            _finish()
            return
        if step > 0:
            splash.after(28, lambda: _fade_out(step - 1))
        else:
            _finish()

    def _tick():
        step_idx['i'] = min(step_idx['i'] + 1, len(LAUNCH_STEPS) - 1)
        status_var.set(LAUNCH_STEPS[step_idx['i']])
        progress['v'] = min(1.0, progress['v'] + 0.2)
        bar.set(progress['v'])
        if progress['v'] < 1.0 and not done['called']:
            splash.after(220, _tick)

    splash.after(min_ms, lambda: _fade_out() if not done['called'] else None)
    splash.after(60, _fade_in)
