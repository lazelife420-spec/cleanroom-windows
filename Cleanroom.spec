# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\KickA\\smart_clean_tool\\startup_manager_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\KickA\\smart_clean_tool\\assets\\brand\\cleanroom-icon.ico', '.'), ('C:\\Users\\KickA\\smart_clean_tool\\assets\\brand\\cleanroom-icon.png', '.'), ('C:\\Users\\KickA\\smart_clean_tool\\cleanup_config.yaml', '.'), ('C:\\Users\\KickA\\smart_clean_tool\\register_task.ps1', '.'), ('C:\\Users\\KickA\\smart_clean_tool\\run_scheduled.ps1', '.')],
    hiddenimports=['pystray', 'pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Cleanroom',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\KickA\\smart_clean_tool\\assets\\brand\\cleanroom-icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Cleanroom',
)
