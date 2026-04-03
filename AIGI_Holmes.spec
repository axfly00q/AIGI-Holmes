# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for AIGI-Holmes desktop application.
#
# Build command (run from the repository root):
#   pyinstaller AIGI_Holmes.spec
#
# The resulting executable is written to dist/AIGI-Holmes/AIGI-Holmes.exe

import os
import site
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "desktop_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
    (str(ROOT / "finetuned_fake_real_resnet50.pth"), "."),
    (str(ROOT / "asset" / "app.ico"), "asset"),
],
    hiddenimports=[
        # Gradio and its ecosystem
        "gradio",
        "gradio.components",
        "gradio.components.base",
        "gradio.routes",
        "gradio.themes",
        "gradio.themes.base",
        "gradio.themes.utils",
        "gradio.blocks",
        "gradio.interface",
        "gradio.helpers",
        "gradio.processing_utils",
        "gradio.utils",
        # gradio_client (bundled with Gradio 4.x)
        "gradio_client",
        "gradio_client.utils",
        # ASGI stack Gradio relies on
        "fastapi",
        "fastapi.staticfiles",
        "fastapi.responses",
        "starlette",
        "starlette.routing",
        "starlette.responses",
        "starlette.staticfiles",
        "starlette.middleware",
        "starlette.middleware.cors",
        # uvicorn (Gradio's HTTP server)
        "uvicorn",
        "uvicorn.main",
        "uvicorn.config",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # pydantic (FastAPI / Gradio data validation)
        "pydantic",
        "pydantic.v1",
        # anyio (async I/O used by Starlette / FastAPI)
        "anyio",
        "anyio.from_thread",
        "anyio._backends._asyncio",
        # HTTP stack
        "httpx",
        "httpcore",
        "h11",
        # File uploads
        "python_multipart",
        "multipart",
        # Async file I/O used by Gradio
        "aiofiles",
        "aiofiles.os",
        # WebSocket support
        "websockets",
        "websockets.legacy",
        "websockets.legacy.server",
        # Templating
        "markupsafe",
        "jinja2",
        # torch and torchvision
        "torch",
        "torch.nn",
        "torchvision.models",
        "torchvision.transforms",
        # pywebview — Windows backends (pywebview 4.x layout)
        "webview",
        "webview.platforms",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        # pythonnet required by pywebview WinForms/EdgeChromium backends
        "clr",
        "clr_loader",
        # Other runtime imports
        "PIL",
        "PIL.Image",
        "requests",
        "ipaddress",
        "io",
        "packaging",
        "packaging.version",
        "orjson",
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
    console=False,         # hide console window for end users
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
