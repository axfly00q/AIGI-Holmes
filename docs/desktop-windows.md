# Running AIGI-Holmes as a Desktop Window (Windows)

This guide explains how to launch **AIGI-Holmes** as a standalone desktop window
instead of opening a browser manually.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or later |
| pip | bundled with Python |
| Windows | 10 / 11 (x64) |

> **Note:** The model file `finetuned_fake_real_resnet50.pth` must be present in
> the repository root before launching.

---

## 1. Install dependencies

```powershell
pip install -r requirements-app.txt
```

This installs Gradio, PyTorch, Torchvision, Pillow, Requests, **and pywebview**
(the lightweight embedded-browser library that provides the native window).

---

## 2. Launch the desktop window

```powershell
python desktop_app.py
```

What happens:

1. The Gradio server starts on `http://127.0.0.1:7860` in a background thread.
2. The launcher polls the server until it is ready (up to 60 s).
3. A native desktop window opens and loads the UI — no browser needed.

Closing the window shuts the application down completely.

---

## 3. Browser-only mode (unchanged)

The original browser-based launch still works:

```powershell
python app.py
```

Then open `http://127.0.0.1:7860` in any browser.

---

## 4. Packaging as a Windows executable (PyInstaller)

To distribute the app as a standalone `.exe`:

### 4a. Install PyInstaller

```powershell
pip install pyinstaller
```

### 4b. Build the executable

```powershell
pyinstaller --onefile --noconsole --name AIGI-Holmes desktop_app.py
```

| Flag | Purpose |
|---|---|
| `--onefile` | Bundle everything into a single `.exe` |
| `--noconsole` | Hide the console window on launch |
| `--name AIGI-Holmes` | Output filename |

The executable is written to `dist\AIGI-Holmes.exe`.

### 4c. Add an application icon (optional)

Place a 256 × 256 `.ico` file (e.g. `app.ico`) in the repository root, then:

```powershell
pyinstaller --onefile --noconsole --icon=app.ico --name AIGI-Holmes desktop_app.py
```

### 4d. Important: include the model file

PyInstaller does **not** automatically bundle data files.  Add the model to the
spec or pass `--add-data` on the command line:

```powershell
pyinstaller --onefile --noconsole --name AIGI-Holmes ^
    --add-data "finetuned_fake_real_resnet50.pth;." ^
    desktop_app.py
```

The semicolon (`;`) separates the source path from the destination folder inside
the bundle (`.` = root of the bundle).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ERROR: pywebview is not installed` | Missing dependency | `pip install pywebview` |
| Window opens but shows a blank page | Server still loading | Wait a few more seconds; increase `STARTUP_TIMEOUT` in `desktop_app.py` |
| `Port 7860 is already in use` | Another process owns the port | Stop the other process or change `PORT` in `desktop_app.py` |
| Model file not found | `.pth` missing | Copy `finetuned_fake_real_resnet50.pth` to the project root |
