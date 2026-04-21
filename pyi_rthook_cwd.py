"""
PyInstaller runtime hook: pyi_rthook_cwd.py
-------------------------------------------
Executed by the PyInstaller bootloader *before* any application code.

When a user double-clicks the packaged AIGI-Holmes.exe (or a desktop
shortcut to it), Windows may set the initial working directory to
something unexpected — typically the user's home directory or the
shortcut's "Start in" path.

This hook pins the working directory to the folder that contains the
executable so that all relative paths used by the app (database URL,
model checkpoint, templates, etc.) resolve correctly.

We also add sys._MEIPASS to sys.path *early* so that the CLIP package
source (bundled as a plain data directory) is importable before the
normal import machinery kicks in.
"""

import os
import sys
from pathlib import Path

# 1. Fix working directory to the folder containing AIGI-Holmes.exe
if getattr(sys, 'frozen', False):
    _exe_dir = Path(sys.executable).parent
    os.chdir(_exe_dir)

# 2. Ensure _MEIPASS is in sys.path so bundled packages (e.g. clip/) are
#    importable even if the regular hook machinery hasn't run yet.
_meipass = getattr(sys, '_MEIPASS', None)
if _meipass and _meipass not in sys.path:
    sys.path.insert(0, _meipass)

# 3. Create a minimal .env in the exe dir if one doesn't exist yet,
#    so pydantic-settings doesn't emit a warning about missing env file.
#    .env.example is bundled inside _MEIPASS (the _internal directory),
#    while .env should live in _exe_dir (writable by the user).
if getattr(sys, 'frozen', False):
    _env_path = _exe_dir / '.env'
    _env_example = Path(_meipass) / '.env.example' if _meipass else None
    if _env_path and not _env_path.exists() and _env_example and _env_example.exists():
        try:
            import shutil
            shutil.copy(_env_example, _env_path)
        except Exception as _e:
            print(f"[RTHOOK] WARNING: Failed to copy .env.example -> .env: {_e}", flush=True)
