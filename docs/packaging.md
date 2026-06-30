# Packaging Guide — AIGI-Holmes

This guide explains how to build a standalone Windows installer for
AIGI-Holmes so that end users can install and run the app **without needing
to install Python** on their machine.

---

## Overview

The packaging flow has two steps:

1. **PyInstaller** bundles the Python app and all its dependencies into a
   self-contained directory (`dist/AIGI-Holmes/`).
2. **Inno Setup** wraps that directory into a single-file Windows installer
   (`dist/AIGI-Holmes-Setup.exe`) that creates a desktop shortcut and
   supports standard install/uninstall.

The app itself runs as a **desktop window** (via
[pywebview](https://pywebview.app)) rather than opening a browser tab —
users see a dedicated application window.

---

## Prerequisites (developer machine)

| Tool | Version | Where to get it |
|------|---------|-----------------|
| Python | 3.10 + | <https://python.org> |
| PyInstaller | 6.x | `pip install pyinstaller` |
| pywebview | 5.x | `pip install pywebview` |
| Inno Setup | 6.x | <https://jrsoftware.org/isdl.php> |

Install the full application dependencies first:

```bash
pip install -r requirements-app.txt
pip install pyinstaller
```

> **Note:** PyTorch (`torch`, `torchvision`) can be large. Make sure your
> virtual environment has enough disk space (~3 GB+ including the model
> weights).

---

## Step 1 — Build the standalone executable

From the **repository root**, run:

```bash
pyinstaller AIGI_Holmes.spec
```

PyInstaller reads `AIGI_Holmes.spec` and produces:

```
dist/
  AIGI-Holmes/          ← folder with the .exe and all dependencies
    AIGI-Holmes.exe
    finetuned_fake_real_resnet50.pth
    asset/app.ico
    ...
```

> **Tip:** The first build can take several minutes because PyInstaller
> analyses all imports (including torch).

### Testing the executable

```bash
dist\AIGI-Holmes\AIGI-Holmes.exe
```

A desktop window should open and display the AIGI-Holmes UI after a few
seconds.

---

## Step 2 — Build the installer

Open **Inno Setup Compiler** (installed in the previous step) and compile
`installer.iss`, or run from the command line:

```bash
iscc installer.iss
```

The installer is written to:

```
dist/AIGI-Holmes-Setup.exe
```

### What the installer does

- Installs files to `%ProgramFiles%\AIGI-Holmes\`
- Creates a **Start Menu** shortcut
- Optionally creates a **Desktop shortcut** (checked by default)
- Adds an entry to *Add / Remove Programs* for clean uninstallation
- Offers to launch the app immediately after installation

---

## Desktop window launcher (`desktop_launcher.py`)

`desktop_launcher.py` is the entry point used by PyInstaller.  It:

1. Starts the **FastAPI backend** (`backend.main:app`) via uvicorn on
   `127.0.0.1:7860` as a subprocess.
2. Waits up to 60 seconds for the server to become available.
3. Opens a `pywebview` window that displays the full-featured web UI —
   no browser needed.

To run the desktop launcher directly (developer mode):

```bash
pip install pywebview
python desktop_launcher.py
```

---

## Application icon

The icon is located at `asset/app.ico`.  It is embedded in both the
executable and the installer.

To replace it with a custom icon, overwrite `asset/app.ico` with your own
`.ico` file (recommended sizes: 16×16, 32×32, 48×48, 256×256) before
running PyInstaller.

---

## Distributing the installer

After building, share `dist/AIGI-Holmes-Setup.exe` with end users.  They
need only:

1. Download `AIGI-Holmes-Setup.exe`.
2. Double-click and follow the wizard (Next → Next → Finish).
3. Use the desktop shortcut to launch the app.

No Python installation is required on the target machine.

> **Windows SmartScreen notice:** Because the installer is not code-signed,
> Windows may show a "Windows protected your PC" warning the first time it
> is run.  Click *More info → Run anyway* to proceed.  For a production
> release, consider obtaining a code-signing certificate.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Window shows "服务启动超时" | Server didn't start in 30 s | Check that `finetuned_fake_real_resnet50.pth` is present in the same folder as the `.exe` |
| `ModuleNotFoundError` at build time | Missing dependency | `pip install <package>` then rebuild |
| Installer complains about missing files | PyInstaller step not run yet | Run `pyinstaller AIGI_Holmes.spec` before `iscc installer.iss` |
| Large installer size | torch/torchvision bundled | This is expected (~1-2 GB); use a CPU-only torch wheel to reduce size |
