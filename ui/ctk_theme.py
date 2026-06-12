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

TAB_CONTEXT = (
    {
        'title': 'Review',
        'description': 'Proof dashboard — see what needs attention before you archive anything.',
        'next': 'Open Cleaner → Scan, then Preview Receipt before Archive & Clean.',
    },
    {
        'title': 'Activity',
        'description': 'Cleanroom Activity Ledger — every archive-first move with timestamps and restore links.',
        'next': 'Pick an entry to verify custody or roll back a specific action.',
    },
    {
        'title': 'Startup',
        'description': 'Programs that run when Windows starts — folders, registry Run keys, and logon tasks.',
        'next': 'Use the filters below, select a row, then Enable or Disable in the detail panel.',
    },
    {
        'title': 'Cleaner',
        'description': 'Scan configured folders for old installers, temp files, and large reclaimable items.',
        'next': 'Scan Now → check candidates → Preview Receipt → Archive & Clean.',
    },
    {
        'title': 'Uninstaller',
        'description': 'Installed programs with optional leftover scan and force-remove for broken entries.',
        'next': 'Select a program → Uninstall, or scan for leftover folders to archive.',
    },
    {
        'title': 'Restore',
        'description': 'Bring files back from the archive using the cleanup log — nothing is permanently deleted.',
        'next': 'Select archived entries and click Restore Selected.',
    },
    {
        'title': 'Settings',
        'description': 'Scan paths, archive folder, age rules, and quick toggles — all stored locally.',
        'next': 'Adjust Quick settings, Save Settings, then re-scan on Cleaner.',
    },
)

STARTUP_FILTER_CONTEXT = {
    'All': (
        'Showing all sources',
        'Startup folders, Registry Run keys, scheduled logon tasks, and disabled backups.',
        'Click a row for the full command path; registry items can be disabled safely.',
    ),
    'Folders': (
        'Startup folder programs',
        'Shortcuts in shell:startup and shell:common startup — per-user and all-users.',
        'Remove unwanted shortcuts from the folder in Explorer, or disable registry entries instead.',
    ),
    'Registry': (
        'Registry Run keys',
        'HKCU/HKLM Run and RunOnce values that launch apps at sign-in.',
        'Select an entry → Disable Selected to back up the value and stop it from running.',
    ),
    'Tasks': (
        'Scheduled logon tasks',
        'Task Scheduler items triggered at user logon or system startup.',
        'Review the command column — disable via Task Scheduler if you do not recognize the task.',
    ),
    'Disabled': (
        'Disabled startup backups',
        'Registry Run values Cleanroom previously disabled — stored so you can re-enable.',
        'Select an entry → Re-enable Selected to restore the original Run key.',
    ),
}


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


def switch(master, text: str, variable, command=None, *, text_color: str,
           progress_color: str, button_color: str, button_hover_color: str,
           **kw) -> ctk.CTkSwitch:
    return ctk.CTkSwitch(
        master,
        text=text,
        variable=variable,
        command=command,
        text_color=text_color,
        font=font(11),
        progress_color=progress_color,
        button_color=button_color,
        button_hover_color=button_hover_color,
        **kw,
    )
