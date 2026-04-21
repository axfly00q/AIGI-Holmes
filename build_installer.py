#!/usr/bin/env python3
"""
build_installer.py  —  AIGI-Holmes one-click packaging script
==============================================================

Usage (from project root, inside the venv):

    python build_installer.py [--skip-inno] [--version 2.0.0]

Steps performed:
    1. Check environment (Python version, required tools, model file)
    2. Install / upgrade  pyinstaller  and  pyinstaller-hooks-contrib
    3. Run  pyinstaller AIGI_Holmes.spec -y  to produce  dist/AIGI-Holmes/
    4. (optional) Run  iscc installer.iss  to produce  dist/AIGI-Holmes-Setup-vX.Y.Z.exe
    5. Print a summary with file sizes and next-step instructions

Requirements:
    pip install -r requirements-app.txt
    pip install pyinstaller pyinstaller-hooks-contrib

For the Windows installer (step 4) you additionally need:
    Inno Setup 6.2+  from  https://jrsoftware.org/isdl.php
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROOT          = Path(__file__).parent.resolve()
SPEC_FILE     = ROOT / "AIGI_Holmes.spec"
ISS_FILE      = ROOT / "installer.iss"
DIST_DIR      = ROOT / "dist"
EXE_DIR       = DIST_DIR / "AIGI-Holmes"
MODEL_FILE    = ROOT / "finetuned_fake_real_resnet50.pth"
ICON_FILE     = ROOT / "asset" / "app.ico"

REQUIRED_PYTHON = (3, 9)
APP_VERSION     = "2.0.0"   # keep in sync with installer.iss #define AppVersion

# Common Inno Setup install locations
_LOCAL_PROGRAMS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")
INNO_CANDIDATES = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 6.2\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 6.3\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 6.4\ISCC.exe",
    os.path.join(_LOCAL_PROGRAMS, "Inno Setup 6", "ISCC.exe"),
    os.path.join(_LOCAL_PROGRAMS, "Inno Setup 6.7", "ISCC.exe"),
    # Inno Setup 6 installed per-user (LocalAppData\Programs)
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
]

# ---------------------------------------------------------------------------
# Color helpers (Windows 10+ supports ANSI; fall back to plain on older)
# ---------------------------------------------------------------------------
_USE_COLOR = (sys.platform == "win32" and
              os.environ.get("TERM_PROGRAM") != "dumb") or sys.platform != "win32"

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def green(t):  return _c(t, "32")
def yellow(t): return _c(t, "33")
def red(t):    return _c(t, "31")
def cyan(t):   return _c(t, "36")
def bold(t):   return _c(t, "1")

def _banner(title: str):
    bar = "=" * 60
    print(f"\n{cyan(bar)}")
    print(f"  {bold(title)}")
    print(f"{cyan(bar)}")

def _ok(msg):    print(f"  {green('✓')} {msg}")
def _warn(msg):  print(f"  {yellow('!')} {msg}")
def _fail(msg):  print(f"  {red('✗')} {msg}")
def _info(msg):  print(f"  {cyan('→')} {msg}")


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
def check_python():
    v = sys.version_info
    if v < REQUIRED_PYTHON:
        _fail(f"Python {'.'.join(map(str, REQUIRED_PYTHON))}+ required; "
              f"running {v.major}.{v.minor}.{v.micro}")
        sys.exit(1)
    _ok(f"Python {v.major}.{v.minor}.{v.micro}")


def check_model_file():
    if not MODEL_FILE.is_file():
        _fail(f"Model file not found: {MODEL_FILE}")
        _info("Download the model weights and place them in the project root.")
        sys.exit(1)
    size_mb = MODEL_FILE.stat().st_size / (1024 ** 2)
    _ok(f"Model file found ({size_mb:.1f} MB)")


def check_spec_and_iss():
    for f in [SPEC_FILE, ISS_FILE]:
        if not f.is_file():
            _fail(f"Missing required file: {f}")
            sys.exit(1)
        _ok(f"Found {f.name}")


def check_icon():
    if not ICON_FILE.is_file():
        _warn(f"App icon not found: {ICON_FILE}  (will use default PyInstaller icon)")
    else:
        _ok(f"App icon: {ICON_FILE}")


def find_inno() -> str | None:
    """Return path to ISCC.exe or None if not found."""
    # 1. Check PATH
    iscc = shutil.which("iscc") or shutil.which("ISCC")
    if iscc:
        return iscc
    # 2. Check common install locations
    for candidate in INNO_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Install / upgrade packaging tools
# ---------------------------------------------------------------------------
def ensure_pyinstaller():
    _info("Installing / upgrading pyinstaller …")
    _run([sys.executable, "-m", "pip", "install", "--upgrade",
          "pyinstaller>=6.0", "pyinstaller-hooks-contrib"],
         "pip install pyinstaller")
    _ok("pyinstaller ready")


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------
def _run(cmd: list, label: str, cwd: Path = ROOT) -> int:
    """Run a subprocess, stream output, return returncode."""
    print(f"\n{cyan('Running:')} {' '.join(str(c) for c in cmd)}\n")
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        _fail(f"{label} failed (exit code {result.returncode})")
        sys.exit(result.returncode)
    return result.returncode


def clean_build_artifacts():
    """Remove previous build/** and dist/ to ensure a clean output."""
    for path in [ROOT / "build", ROOT / "dist", ROOT / "__pycache__"]:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            _ok(f"Cleaned {path.relative_to(ROOT)}")


def run_pyinstaller():
    _banner("Step 1 / 2  —  PyInstaller (creating standalone EXE folder)")
    _info("This step bundles Python + all dependencies.")
    _info("First run can take 10-20 minutes (torch is large). Subsequent runs are faster.\n")

    t0 = time.monotonic()
    _run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "-y",
         "--log-level", "WARN"],
        "pyinstaller"
    )
    elapsed = time.monotonic() - t0

    if not (EXE_DIR / "AIGI-Holmes.exe").is_file():
        _fail(f"Expected EXE not found at {EXE_DIR / 'AIGI-Holmes.exe'}")
        sys.exit(1)

    folder_size = sum(f.stat().st_size for f in EXE_DIR.rglob("*") if f.is_file())
    _ok(f"EXE folder: {EXE_DIR}  ({folder_size / (1024**3):.2f} GB,  {elapsed:.0f}s)")


def run_inno(iscc_path: str, version: str):
    _banner("Step 2 / 2  —  Inno Setup (creating Windows installer)")
    _info(f"Using Inno Setup at: {iscc_path}")

    t0 = time.monotonic()
    _run([iscc_path, str(ISS_FILE)], "inno setup")
    elapsed = time.monotonic() - t0

    setup_exe = DIST_DIR / f"AIGI-Holmes-Setup-v{version}.exe"
    if setup_exe.is_file():
        size_mb = setup_exe.stat().st_size / (1024 ** 2)
        _ok(f"Installer: {setup_exe}  ({size_mb:.0f} MB,  {elapsed:.0f}s)")
    else:
        # Check for any Setup*.exe in dist/
        candidates = list(DIST_DIR.glob("AIGI-Holmes-Setup*.exe"))
        if candidates:
            f = candidates[0]
            size_mb = f.stat().st_size / (1024 ** 2)
            _ok(f"Installer: {f}  ({size_mb:.0f} MB,  {elapsed:.0f}s)")
        else:
            _warn("Installer EXE not found in dist/ — check Inno Setup output above.")


def print_summary(skip_inno: bool, inno_found: bool):
    _banner("Build Complete")

    exe_path = EXE_DIR / "AIGI-Holmes.exe"
    if exe_path.is_file():
        print(f"\n  {bold('Portable / green version')} (双击即用):")
        print(f"    {green(str(EXE_DIR))}")
        print(f"    → 将整个文件夹复制到目标电脑，双击 AIGI-Holmes.exe 启动")

    setup_candidates = list(DIST_DIR.glob("AIGI-Holmes-Setup*.exe"))
    if setup_candidates:
        f = setup_candidates[0]
        print(f"\n  {bold('Windows 安装包')} (向导安装 + 桌面快捷方式):")
        print(f"    {green(str(f))}")
        print(f"    → 分发此单文件安装程序，双击安装，桌面生成快捷方式")
    elif not skip_inno:
        if not inno_found:
            print(f"\n  {yellow('Windows 安装包未生成')} — Inno Setup 未找到。")
            print(f"  安装方法: https://jrsoftware.org/isdl.php")
            print(f"  安装后运行:  iscc installer.iss  或  python build_installer.py")

    print(f"""
  {cyan('系统要求 (目标电脑)')}:
    • Windows 10 build 17763 (1809) 或更新版本
    • Microsoft Edge WebView2 (Windows 10/11 已内置)
    • 首次启动约 15-20 秒 (加载 AI 模型)

  {cyan('CLIP 说明')}:
    • CLIP 零样本分类功能在首次使用时需要从网络下载 ViT-B/32 (~340 MB)
    • 如目标电脑无网络，该功能将优雅降级 (不影响核心 FAKE/REAL 检测)
    • 如需离线支持，请先在联网设备运行一次，CLIP 模型将缓存至 ~/.cache/clip/
""")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="AIGI-Holmes 一键打包脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--skip-clean",  action="store_true",
                        help="不清理之前的 build/ 目录（加快增量构建）")
    parser.add_argument("--skip-inno",   action="store_true",
                        help="跳过 Inno Setup 步骤，只生成绿色版 EXE 文件夹")
    parser.add_argument("--version",     default=APP_VERSION,
                        help=f"版本号 (默认: {APP_VERSION})")
    args = parser.parse_args()

    # Enable ANSI colors on Windows
    if sys.platform == "win32":
        os.system("color")

    _banner("AIGI-Holmes Packaging Script")
    print(f"  Project root : {ROOT}")
    print(f"  Python       : {sys.executable}")
    print(f"  Version      : {args.version}")
    print()

    # Pre-flight
    _banner("Pre-flight Checks")
    check_python()
    check_model_file()
    check_spec_and_iss()
    check_icon()

    inno_path = None if args.skip_inno else find_inno()
    if not args.skip_inno:
        if inno_path:
            _ok(f"Inno Setup found: {inno_path}")
        else:
            _warn("Inno Setup not found — will skip installer step.")
            _info("Get Inno Setup 6: https://jrsoftware.org/isdl.php")

    # Clean
    if not args.skip_clean:
        _banner("Cleaning Previous Build Artifacts")
        clean_build_artifacts()

    # PyInstaller
    run_pyinstaller()

    # Inno Setup
    if not args.skip_inno and inno_path:
        run_inno(inno_path, args.version)
    else:
        _info("Inno Setup step skipped.")

    # Summary
    print_summary(args.skip_inno, inno_path is not None)


if __name__ == "__main__":
    main()
