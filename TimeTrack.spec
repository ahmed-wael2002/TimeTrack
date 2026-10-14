# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['openpyxl']
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('timetrack')


a = Analysis(
    ['E:/TimeTrack/main.py'],
    pathex=['E:/TimeTrack'],
    binaries=[],
    datas=[('E:/TimeTrack/assets/icon.png', 'assets'), ('E:/TimeTrack/assets/icon.ico', 'assets')],
    hiddenimports=hiddenimports,
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
    name='TimeTrack',
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
    icon=['E:/TimeTrack/assets/icon.ico'],
)
