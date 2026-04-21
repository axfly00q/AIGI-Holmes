# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# AIGI_Holmes.spec  —  PyInstaller packaging configuration
# =============================================================================
#
# Usage (from project root in venv):
#     pyinstaller AIGI_Holmes.spec -y
#
# Output:
#     dist/AIGI-Holmes/AIGI-Holmes.exe   ← green portable folder build
#
# Requirements:
#     pip install pyinstaller pyinstaller-hooks-contrib
# =============================================================================

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# ---------------------------------------------------------------------------
# Project root — the directory containing this spec file
# ---------------------------------------------------------------------------
ROOT = Path(SPECPATH)

# ---------------------------------------------------------------------------
# Helper: turn list of Paths into PyInstaller (src, dst) tuples
# ---------------------------------------------------------------------------
def _dir_data(src_rel, dst_rel):
    """Return a list entry for datas: copy whole directory."""
    return (str(ROOT / src_rel), dst_rel)

# ---------------------------------------------------------------------------
# Data files to ship alongside the executable
# ---------------------------------------------------------------------------
extra_datas = [
    # ── Core ML models ──────────────────────────────────────────────────────
    _dir_data('finetuned_fake_real_resnet50.pth', '.'),

    # ── Web UI assets ────────────────────────────────────────────────────────
    _dir_data('templates',  'templates'),
    _dir_data('static',     'static'),

    # ── Application icon / branding ──────────────────────────────────────────
    _dir_data('asset',      'asset'),

    # ── CLIP Python package source (editable install — compile into bundle) ──
    # simple_tokenizer.py reads bpe vocab from the same directory as __file__
    # so we must land both the .py sources AND the data file in 'clip/' inside
    # _MEIPASS.
    _dir_data('CLIP/clip',  'clip'),

    # ── Default environment — users can edit after installation ─────────────
    _dir_data('.env.example', '.'),
]

# Collect Jinja2 templates bundled inside the package itself
extra_datas += collect_data_files('jinja2')
# Collect starlette's bundled static assets (exception pages, etc.)
extra_datas += collect_data_files('starlette')
# Collect certifi's CA bundle (used by httpx / requests)
extra_datas += collect_data_files('certifi')
# Collect jaraco namespace packages (required by pkg_resources runtime hook)
extra_datas += collect_data_files('jaraco.text')
extra_datas += collect_data_files('jaraco.functools')
extra_datas += collect_data_files('jaraco.context')
extra_datas += collect_data_files('jaraco.classes')

# ---------------------------------------------------------------------------
# Hidden imports
# (pyinstaller-hooks-contrib already has hooks for: torch, torchvision,
#  uvicorn, passlib, webview — so those are mostly auto-handled.
#  Everything below covers the remaining runtime-only imports.)
# ---------------------------------------------------------------------------
hidden = []

# ── FastAPI & Starlette ──────────────────────────────────────────────────────
hidden += collect_submodules('fastapi')
hidden += collect_submodules('starlette')

# ── SQLAlchemy 2 + async dialects ────────────────────────────────────────────
hidden += collect_submodules('sqlalchemy')
hidden += [
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.sqlite.aiosqlite',
    'sqlalchemy.ext.asyncio',
    'aiosqlite',
]

# ── Pydantic v2 / pydantic-settings ─────────────────────────────────────────
hidden += collect_submodules('pydantic')
hidden += collect_submodules('pydantic_settings')
hidden += ['pydantic_core']

# ── jose / JWT auth ───────────────────────────────────────────────────────────
hidden += [
    'jose',
    'jose.jwt',
    'jose.jws',
    'jose.jwk',
    'jose.jwe',
    'jose.utils',
    'jose.constants',
    'jose.exceptions',
    'jose.backends',
    'cryptography',
    'cryptography.hazmat.primitives.asymmetric.rsa',
    'cryptography.hazmat.primitives.asymmetric.ec',
    'cryptography.hazmat.backends.openssl',
]

# ── bcrypt / passlib ──────────────────────────────────────────────────────────
hidden += [
    'bcrypt',
    'passlib',
    'passlib.context',
    'passlib.handlers.bcrypt',
    'passlib.handlers.sha2_crypt',
]

# ── Multipart / file uploads ──────────────────────────────────────────────────
hidden += ['multipart', 'python_multipart']

# ── Jinja2 extensions ─────────────────────────────────────────────────────────
hidden += ['jinja2', 'jinja2.ext', 'markupsafe']

# ── HTTP clients ──────────────────────────────────────────────────────────────
hidden += ['httpx', 'httpcore', 'requests', 'urllib3', 'charset_normalizer']

# ── Redis (optional cache — app gracefully disables if unreachable) ───────────
hidden += ['redis', 'redis.asyncio']

# ── WebSocket implementations ─────────────────────────────────────────────────
hidden += ['websockets', 'websockets.legacy', 'websockets.legacy.server',
           'websockets.server', 'wsproto', 'h11']

# ── anyio async runtime ───────────────────────────────────────────────────────
hidden += collect_submodules('anyio')

# ── PIL / Pillow ──────────────────────────────────────────────────────────────
hidden += ['PIL', 'PIL.Image', 'PIL.ImageOps', 'PIL.ImageDraw',
           'PIL.ImageFilter', 'PIL.ImageFont', 'PIL.JpegImagePlugin',
           'PIL.PngImagePlugin', 'PIL.WebPImagePlugin', 'PIL.BmpImagePlugin']

# ── Numpy & scientific stack ──────────────────────────────────────────────────
hidden += ['numpy', 'numpy.core', 'numpy.lib', 'numpy.random']

# ── CLIP module (editable install) ────────────────────────────────────────────
hidden += ['clip', 'clip.clip', 'clip.model', 'clip.simple_tokenizer',
           'ftfy', 'ftfy.bad_codecs', 'regex', 'tqdm', 'tqdm.auto']

# ── Report generation ─────────────────────────────────────────────────────────
hidden += collect_submodules('reportlab')
hidden += ['openpyxl', 'openpyxl.styles', 'openpyxl.utils', 'openpyxl.workbook']

# ── Document extraction (PDF / Word) ─────────────────────────────────────────
hidden += ['fitz', 'docx', 'docx.oxml', 'docx.shared']

# ── Misc utilities ────────────────────────────────────────────────────────────
hidden += [
    'packaging', 'packaging.version',
    'email_validator',
    'typing_extensions',
    'exceptiongroup',
    'sniffio',
    'idna',
    'click',
    'dotenv',         # python-dotenv (used by pydantic-settings)
]

# ── setuptools / pkg_resources dependencies ─────────────────────────────────
# pkg_resources (runtime hook pyi_rth_pkgres) requires jaraco.text via
# setuptools → importlib.metadata → jaraco namespace chain.
# We MUST NOT exclude setuptools (see excludes list) and must collect
# all jaraco submodules + data files.
hidden += collect_submodules('jaraco')
hidden += [
    'jaraco', 'jaraco.classes', 'jaraco.context',
    'jaraco.functools', 'jaraco.text',
]
hidden += collect_submodules('importlib_metadata')
hidden += collect_submodules('pkg_resources')
hidden += ['pkg_resources', 'pkg_resources.extern']

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(ROOT / 'desktop_launcher.py')],
    pathex=[
        str(ROOT),
        str(ROOT / 'CLIP'),    # allows  `import clip`  to resolve
    ],
    binaries=[],
    datas=extra_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / 'pyi_rthook_cwd.py')],
    excludes=[
        # These are not used at runtime and are HUGE — skip them
        'tkinter', '_tkinter',
        'matplotlib', 'matplotlib.pyplot',
        'notebook', 'jupyter', 'jupyter_core', 'jupyter_client',
        'IPython',
        'scipy',
        'pandas',
        'sklearn', 'sklearn',
        'cv2',           # OpenCV (not used in this project)
        'PySide2', 'PySide6', 'PyQt5', 'PyQt6',   # Qt backends for pywebview — not used on Windows
        'gi',           # GTK
        # test / dev only
        'pytest', 'pip',
        # NOTE: do NOT exclude 'setuptools' — pkg_resources depends on it
        # brotlicffi conflicts with urllib3 (missing .error attribute) — exclude to avoid crash
        'brotlicffi', 'brotli',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------------------
# PYZ archive
# ---------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# EXE
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AIGI-Holmes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # ← no console window for end-users
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'asset' / 'app.ico'),
    # Human-readable version shown in Windows Explorer Properties
    version=None,
)

# ---------------------------------------------------------------------------
# COLLECT — assemble the final dist/AIGI-Holmes/ folder
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Never UPX-compress these — they have their own compression or
        # are loaded by the OS loader and must stay valid PE files.
        'vcruntime*.dll',
        'msvcp*.dll',
        'api-ms-win*.dll',
        'torch_*.pyd',
        # Torch / CUDA native libs — already internally compressed
        'torch*.dll',
        'fbgemm.dll',
        'libiomp5md.dll',
        'libomp*.dll',
        'cudart*.dll',
        'cublas*.dll',
        'cufft*.dll',
        # Other large native libs that UPX sometimes corrupts
        'python3*.dll',
        '_ssl.pyd',
    ],
    name='AIGI-Holmes',
)
