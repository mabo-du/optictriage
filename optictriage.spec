# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os

if sys.platform == 'win32':
    exiftool_path = 'bin/exiftool.exe'
elif sys.platform == 'darwin':
    exiftool_path = 'bin/exiftool_mac'
else:
    exiftool_path = 'bin/exiftool_linux'

a = Analysis(
    ['src/optictriage/app.py'],
    pathex=[],
    binaries=[(exiftool_path, 'bin')],
    datas=[],
    hiddenimports=['optictriage', 'psutil', 'numpy', 'shapely', 'pyproj', 'sqlalchemy', 'pandas'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='optictriage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, 
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='optictriage',
)
