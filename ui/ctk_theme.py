"""CustomTkinter polish helpers — palette-aware, fully local."""
from __future__ import annotations

import customtkinter as ctk

LOCAL_ONLY_TEXT = (
    'Cleanroom is local-only. No account, no cloud, no telemetry, '
    'no uploaded file lists, and no remote cleanup logic. Receipts, archives, '
    'ledgers, proof packs, and settings stay on this machine.'
)

PROOF_FLOW_TEXT = 'Scan  →  Preview Receipt  →  Archive & Clean  →  Restore'

ARCHIVE_BANNER_TEXT = (
    'Archive-first mode is ON — Cleanroom moves files to archive before any removal.'
)


def appearance_for_palette(theme_name: str) -> str:
    return 'light' if theme_name == 'light' else 'dark'


def sync_appearance(theme_name: str) -> None:
    ctk.set_appearance_mode(appearance_for_palette(theme_name))
    ctk.set_default_color_theme('green')


def font(size: int, weight: str = 'normal') -> ctk.CTkFont:
    return ctk.CTkFont(family='Segoe UI', size=size, weight=weight)


def frame(master, fg_color: str, *, corner_radius: int = 0, **kw) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, fg_color=fg_color, corner_radius=corner_radius, **kw)


def label(master, text: str, *, text_color: str, font_size: int = 11,
          weight: str = 'normal', **kw) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        master, text=text, text_color=text_color,
        font=font(font_size, weight), **kw)


def button(master, text: str, command, *, fg_color: str, hover_color: str,
           text_color: str, primary: bool = False, width: int | None = None,
           **kw) -> ctk.CTkButton:
    opts = dict(
        text=text,
        command=command,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=text_color,
        font=font(11, 'bold' if primary else 'normal'),
        corner_radius=6,
    )
    if width is not None:
        opts['width'] = width
    opts.update(kw)
    return ctk.CTkButton(master, **opts)
