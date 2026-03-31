# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hidden_imports = ['clr', 'clr_loader', 'pythonnet'] + collect_submodules('webview')

dts = [('logo.png', '.'), ('public/version.txt', '.'), ('papamonitor', 'papamonitor')]
dts += collect_data_files('clr_loader')
dts += collect_data_files('pythonnet')
dts += collect_data_files('webview')

a = Analysis(
    ['monitor.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('public/version.txt', '.'), ('papamonitor', 'papamonitor')],
    hiddenimports=[],
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
    upx=False,
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
