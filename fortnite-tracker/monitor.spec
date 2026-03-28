# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['monitor.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('public/version.txt', '.')],
    hiddenimports=['papamonitor', 'papamonitor.constants', 'papamonitor.dashboard_ui', 'papamonitor.remote_settings', 'papamonitor.fortnite_detect', 'papamonitor.scheduler', 'papamonitor.tray_icon', 'papamonitor.instance_lock', 'papamonitor.paths', 'papamonitor.versioning', 'papamonitor.windows_admin'],
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
    a.binaries,
    a.datas,
    [],
    name='monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
