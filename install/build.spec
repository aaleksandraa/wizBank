# PyInstaller spec (GUI exe)
block_cipher = None

a = Analysis(
    ['wizvod/main.py'],
    pathex=[],
    binaries=[],
    datas=[('wizvod/gui/assets/app_icon.ico', 'wizvod/gui/assets')],
    hiddenimports=['fitz'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='wizvod',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='wizvod/gui/assets/app_icon.ico'
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='wizvod'
)
