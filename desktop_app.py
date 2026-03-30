"""
AIGI-Holmes Desktop Launcher

Opens the Gradio web UI in a native desktop window using pywebview,
so the user does not need to manually open a browser.

Usage (Windows):
    python desktop_app.py

Requirements:
    pip install -r requirements-app.txt
"""

import os
import sys
import threading
import time
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# In windowed PyInstaller builds (console=False) sys.stdout / sys.stderr can
# be None, causing any print() call to raise AttributeError.  Redirect them
# to devnull so the rest of the startup code runs safely.
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST = "127.0.0.1"
PORT = 7860
URL = f"http://{HOST}:{PORT}"
WINDOW_TITLE = "AIGI-Holmes — 新闻图片 AI 生成检测"
STARTUP_TIMEOUT = 60  # seconds to wait for the server to become ready
POLL_INTERVAL = 0.5   # seconds between readiness checks


# ---------------------------------------------------------------------------
# Server readiness helper
# ---------------------------------------------------------------------------

def _wait_for_server(url: str, timeout: float, poll_interval: float) -> bool:
    """Poll *url* until it responds with HTTP 200 (or any non-connection-error
    status) or *timeout* seconds elapse.  Returns True when ready."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except urllib.error.HTTPError:
            # Any HTTP error means the server is up (Gradio may return 4xx
            # on some paths before the UI is fully loaded, but the port is open).
            return True
        except Exception:
            pass
        time.sleep(poll_interval)
    return False


# ---------------------------------------------------------------------------
# Flask server thread
# ---------------------------------------------------------------------------

def _run_flask_server() -> None:
    """Launch the Flask app in the background without blocking this thread."""
    # Import inside the function so the model loads on this thread, not the
    # main thread, which keeps pywebview's event loop responsive on Windows.
    from server import app  # noqa: PLC0415 – intentional late import
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # suppress Flask request logs
    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        use_reloader=False,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        import webview  # noqa: PLC0415 – optional dependency
    except ImportError:
        print(
            "ERROR: pywebview is not installed.\n"
            "Run:  pip install pywebview\n"
            "Then try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Start the Flask server in a daemon thread so it is automatically
    # stopped when the main (UI) thread exits.
    server_thread = threading.Thread(target=_run_flask_server, daemon=True, name="flask-server")
    server_thread.start()

    print(f"Waiting for server to start on {URL} …")
    ready = _wait_for_server(URL, timeout=STARTUP_TIMEOUT, poll_interval=POLL_INTERVAL)
    if not ready:
        print(
            f"ERROR: Server did not become ready within {STARTUP_TIMEOUT} s.\n"
            "Check that port 7860 is not already in use.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Server is ready — opening desktop window.")
    window = webview.create_window(
        title=WINDOW_TITLE,
        url=URL,
        width=1100,
        height=800,
        resizable=True,
        min_size=(800, 600),
    )
    # webview.start() blocks until the window is closed.
    webview.start()


if __name__ == "__main__":
    main()