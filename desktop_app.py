"""
AIGI-Holmes Desktop Launcher
Starts the Gradio web server in a background thread and opens a native
desktop window (via pywebview) that hosts the UI without requiring a browser.
"""

import sys
import threading
import time

import webview

# ---------------------------------------------------------------------------
# Port used by the Gradio server (must match app.py default)
# ---------------------------------------------------------------------------
PORT = 7860
SERVER_URL = f"http://127.0.0.1:{PORT}"


def _start_server() -> None:
    """Import and launch the Gradio app in-process."""
    # Import here so that PyInstaller can find the dependency at analysis time.
    import app as aigi_app  # noqa: F401 - side-effects: builds `demo`

    aigi_app.demo.launch(
        server_name="127.0.0.1",
        server_port=PORT,
        share=False,
        prevent_thread_lock=True,  # let the main thread drive the window
    )


def _wait_for_server(timeout: float = 30.0) -> bool:
    """Poll until the Gradio server responds or the timeout expires."""
    import urllib.request
    import urllib.error

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(SERVER_URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def main() -> None:
    # Start the server in a daemon thread so it shuts down with the process.
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    if not _wait_for_server():
        # Fallback: show an error dialog instead of silently failing.
        webview.create_window(
            "AIGI-Holmes — 启动失败",
            html="<h2 style='font-family:sans-serif;color:red'>服务启动超时，请重试。</h2>",
        )
        webview.start()
        sys.exit(1)

    window = webview.create_window(
        "AIGI-Holmes — 新闻图片 AI 生成检测",
        SERVER_URL,
        width=1100,
        height=780,
        resizable=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
