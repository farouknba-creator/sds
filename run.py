"""
Top-level launcher for SDS Studio.

This file exists ONLY to make PyInstaller bundling work cleanly.
The actual application code lives in sds_studio/main.py, but that file
uses relative imports (`from .gui.main_window import ...`) which only
work when invoked as `python -m sds_studio.main`.

PyInstaller needs a top-level script (not a package __main__) as its entry
point. This launcher does a single absolute import and delegates to the
real main() function.

Run in dev:    python run.py
Packaged:      SDSStudio.exe (PyInstaller points at this file)
"""
from __future__ import annotations

import sys

# Absolute import - resolves correctly under PyInstaller
from sds_studio.main import main


if __name__ == "__main__":
    sys.exit(main())
