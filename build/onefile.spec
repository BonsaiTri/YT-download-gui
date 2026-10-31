# -*- mode: python ; coding: utf-8 -*-
"""Single-file build: one self-contained yt-dlp-gui.exe (no sibling folder).

PyInstaller unpacks to a temp dir at startup, so the bundled embeddable
Python and the yt-dlp engine ride along inside the exe and are found via
sys._MEIPASS (see ytdlp_gui/engine.py:_bundle_dir).

Build:  pyinstaller --noconfirm --clean build/onefile.spec
"""

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
STAGE = os.path.join(ROOT, "build", "onefile-stage")

a = Analysis(
    [os.path.join(ROOT, "yt_dlp_gui.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(STAGE, "python"), "python"),   # embeddable interpreter
        (os.path.join(STAGE, "yt-dlp"), "yt-dlp"),   # yt-dlp engine checkout
    ],
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
    name="yt-dlp-gui",
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
    icon=[os.path.join(ROOT, "build", "icon.ico")],
)
