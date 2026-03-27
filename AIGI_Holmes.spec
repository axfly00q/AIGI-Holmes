# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for AIGI-Holmes desktop application.
#
# Build command (run from the repository root):
#   pyinstaller AIGI_Holmes.spec
#
# The resulting executable is written to dist/AIGI-Holmes/AIGI-Holmes.exe

import os
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "desktop_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Include the fine-tuned model weights
        (str(ROOT / "finetuned_fake_real_resnet50.pth"), "."),
        # Include the application icon
        (str(ROOT / "asset" / "app.ico"), "asset"),
    ],
    hiddenimports=[
        # Gradio and its ecosystem may need explicit hints
        "gradio",
        "gradio.components",
        "gradio.routes",
        "gradio.themes",
        # torchvision models
        "torchvision.models",
        "torchvision.transforms",
        # pywebview backends – include all so the right one is selected at runtime
        "webview.platforms.winforms",
        "webview.platforms.gtk",
        "webview.platforms.cocoa",
        # Other runtime imports
        "PIL",
        "requests",
        "ipaddress",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AIGI-Holmes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no console window for end users
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "asset" / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AIGI-Holmes",
)
