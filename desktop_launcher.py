"""
AIGI-Holmes Desktop Application Launcher

Starts the FastAPI/uvicorn backend in a daemon thread, then opens a
pywebview desktop window (or falls back to the system browser).

Usage:
    python desktop_launcher.py
"""

import os
import socket
import sys
import threading
import time
import urllib.request
import urllib.error
import atexit
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Redirect stdout/stderr to a log file in frozen (windowed) builds.
#    In windowed mode the process has no console – all print() output would
#    be lost.  We always redirect in frozen mode so we can debug issues.
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _log_file = Path(os.environ.get("TEMP", ".")) / "AIGI-Holmes.log"
    _log_fp = open(_log_file, "a", encoding="utf-8")
    sys.stdout = _log_fp
    sys.stderr = _log_fp

# ---------------------------------------------------------------------------
# 2. Fix working directory.
#    When a user double-clicks the EXE (or a shortcut), Windows may set the
#    working directory to something unexpected (e.g. C:\Windows\System32).
#    We pin the cwd to the directory that contains the EXE so that relative
#    paths in the app (e.g. "sqlite:///./aigi_holmes.db") resolve correctly.
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _exe_dir = Path(sys.executable).parent
    os.chdir(_exe_dir)
    print(f"[INIT] CWD fixed to: {_exe_dir}", flush=True)

# ---------------------------------------------------------------------------
# 3. Load .env into os.environ BEFORE importing any backend module.
#    pydantic-settings BaseSettings only reads declared fields — anything not
#    declared (e.g. SERPER_API_KEY) is ignored.  load_dotenv() populates
#    os.environ so that os.getenv("SERPER_API_KEY") works everywhere.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_file = Path(os.getcwd()) / ".env"
    # Frozen app: if .env doesn't exist yet, copy from .env.example in _MEIPASS
    if not _env_file.exists():
        _meipass_dir = getattr(sys, "_MEIPASS", None)
        if _meipass_dir:
            _example = Path(_meipass_dir) / ".env.example"
            if _example.exists():
                import shutil as _shutil
                _shutil.copy(_example, _env_file)
                print(f"[INIT] Created .env from .env.example", flush=True)
    if _env_file.exists():
        _load_dotenv(_env_file, override=False)
        print(f"[INIT] Loaded .env from: {_env_file}", flush=True)
    else:
        print(f"[INIT] WARNING: .env not found at {_env_file}", flush=True)
except Exception as _dotenv_err:
    print(f"[INIT] WARNING: load_dotenv failed: {_dotenv_err}", flush=True)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST            = "127.0.0.1"
_PORT_BASE      = 7860
_PORT_RANGE     = 10          # try 7860 … 7869
WINDOW_TITLE    = "AIGI-Holmes — 新闻图片 AI 生成检测"
STARTUP_TIMEOUT = 90    # seconds to wait for the server
POLL_INTERVAL   = 0.5   # seconds between readiness checks

_uvicorn_server = None  # uvicorn.Server instance (for graceful shutdown)
PORT            = _PORT_BASE   # will be updated by _find_free_port()
URL             = f"http://{HOST}:{PORT}"


def _find_free_port(start: int, count: int) -> int:
    """Return the first free TCP port in [start, start+count)."""
    for p in range(start, start + count):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((HOST, p))
                return p
            except OSError:
                continue
    raise OSError(
        f"No free port found in range {start}–{start + count - 1}. "
        "Close other applications and try again."
    )


def _show_error(title: str, message: str) -> None:
    """Show a Windows MessageBox (works in windowed/frozen mode)."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR
    except Exception:
        pass  # non-Windows or ctypes unavailable


def _show_status_window(url: str) -> None:
    """Show a small tkinter status window.  Blocks until the user closes it."""
    try:
        import tkinter as tk

        root = tk.Tk()
        root.title("AIGI-Holmes")
        root.geometry("420x160")
        root.resizable(False, False)
        root.configure(bg="#1a1a2e")

        # Center on screen
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - 420) // 2
        y = (sh - 160) // 2
        root.geometry(f"420x160+{x}+{y}")

        tk.Label(
            root, text="AIGI-Holmes  正在运行",
            font=("Microsoft YaHei UI", 13, "bold"),
            fg="#e0e0e0", bg="#1a1a2e",
        ).pack(pady=(20, 4))

        tk.Label(
            root, text=f"已在浏览器中打开：{url}",
            font=("Microsoft YaHei UI", 9),
            fg="#aaaacc", bg="#1a1a2e",
        ).pack()

        tk.Label(
            root, text="关闭此窗口即可退出程序",
            font=("Microsoft YaHei UI", 8),
            fg="#666688", bg="#1a1a2e",
        ).pack(pady=(2, 0))

        btn = tk.Button(
            root, text="退出程序",
            font=("Microsoft YaHei UI", 9),
            bg="#e05050", fg="white",
            relief="flat", padx=12, pady=4,
            command=root.destroy,
            cursor="hand2",
        )
        btn.pack(pady=12)

        root.mainloop()
        print("[SHUTDOWN] Status window closed", flush=True)
    except Exception as e:
        # tkinter unavailable — keep the process alive via sleep loop
        print(f"[WARNING] tkinter unavailable ({e}), falling back to sleep loop", flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[SHUTDOWN] Interrupted by user", flush=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_server(url: str, timeout: float, poll: float) -> bool:
    """Poll *url* until it responds or *timeout* seconds elapse."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except urllib.error.HTTPError:
            return True     # server replied (even with an error) → it's up
        except Exception:
            pass
        time.sleep(poll)
    return False


def _cleanup():
    """Tell uvicorn to shut down gracefully when the process exits."""
    global _uvicorn_server
    if _uvicorn_server is not None:
        try:
            _uvicorn_server.should_exit = True
        except Exception:
            pass


atexit.register(_cleanup)


# ---------------------------------------------------------------------------
# Backend thread
#
# KEY INSIGHT: In a PyInstaller frozen executable sys.executable IS the
# bundled EXE, not a Python interpreter.  Spawning a subprocess with
# sys.executable and uvicorn args just launches a second copy of the app.
#
# The correct approach is to run uvicorn.Server inside a daemon *thread*
# in the same process.  uvicorn creates its own asyncio event loop, so
# there are no conflicts with pywebview (which runs on the main thread).
# ---------------------------------------------------------------------------

def _run_backend():
    """Blocking call that runs the uvicorn server.  Meant for a daemon thread."""
    global _uvicorn_server
    try:
        import uvicorn
        # Import the FastAPI app object directly instead of passing a string.
        # String-based import ("backend.main:app") also works, but using the
        # object is more reliable in frozen environments.
        from backend.main import app as fastapi_app

        config = uvicorn.Config(
            app=fastapi_app,
            host=HOST,
            port=PORT,
            log_level="warning",
        )
        _uvicorn_server = uvicorn.Server(config)
        _uvicorn_server.run()
    except Exception:
        import traceback
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    global PORT, URL
    # ── Find a free port ───────────────────────────────────────────────────
    try:
        PORT = _find_free_port(_PORT_BASE, _PORT_RANGE)
    except OSError as exc:
        _show_error("AIGI-Holmes 启动失败", str(exc))
        sys.exit(1)
    URL = f"http://{HOST}:{PORT}"

    print(f"[STARTUP] AIGI-Holmes Desktop Application", flush=True)
    print(f"[STARTUP] Python    : {sys.executable}", flush=True)
    print(f"[STARTUP] Frozen    : {getattr(sys, 'frozen', False)}", flush=True)
    print(f"[STARTUP] CWD       : {os.getcwd()}", flush=True)
    if getattr(sys, "frozen", False):
        print(f"[STARTUP] _MEIPASS  : {sys._MEIPASS}", flush=True)

    # ── Start backend in a daemon thread ───────────────────────────────────
    print(f"[STARTUP] Starting backend on {URL} …", flush=True)
    backend_thread = threading.Thread(target=_run_backend, daemon=True, name="uvicorn")
    backend_thread.start()

    # ── Wait until the server responds ────────────────────────────────────
    print(f"[STARTUP] Waiting for server (timeout={STARTUP_TIMEOUT}s) …", flush=True)
    if not _wait_for_server(URL, STARTUP_TIMEOUT, POLL_INTERVAL):
        log_path = Path(os.environ.get("TEMP", ".")) / "AIGI-Holmes.log"
        msg = (
            f"服务器在 {STARTUP_TIMEOUT} 秒内未能启动。\n\n"
            f"可能原因：\n"
            f"  • AI 模型加载失败（首次启动约需 15–30 秒）\n"
            f"  • 缺少 Visual C++ 运行库\n\n"
            f"详细日志：{log_path}"
        )
        _show_error("AIGI-Holmes 启动失败", msg)
        sys.exit(1)

    print(f"[STARTUP] Server is ready at {URL}", flush=True)

    # ── Open in system browser (supports native file downloads) ────────────
    import webbrowser
    webbrowser.open(URL)
    print(f"[INFO] Opened system browser at {URL}", flush=True)

    # ── Show a minimal status window so users can quit cleanly ─────────────
    _show_status_window(URL)


if __name__ == "__main__":
    main()
