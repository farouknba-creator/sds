# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for SDS Studio - portable Windows build (onedir mode).

Usage:
    pyinstaller sds_studio.spec --clean --noconfirm

Output: dist/SDSStudio/SDSStudio.exe (+ supporting files)

The entire dist/SDSStudio/ folder is the portable app - zip it and ship.

Why run.py instead of sds_studio/main.py:
    sds_studio/main.py uses relative imports (`from .gui.main_window import ...`)
    which only work when invoked as `python -m sds_studio.main`. PyInstaller
    needs a top-level script as its entry point. run.py is a thin launcher
    that does an absolute import of sds_studio.main and delegates to it.

    This is the standard pattern for bundling Python packages with PyInstaller.
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# SPECPATH is a built-in variable in PyInstaller specs - it's the absolute
# path to the directory containing this .spec file. Using it makes the spec
# work regardless of the current working directory when pyinstaller is invoked.
SPEC_DIR = SPECPATH

block_cipher = None

# Collect PySide6 plugins (Qt platforms, styles, image formats, etc.)
pyside6_datas = collect_data_files("PySide6", include_py_files=False)

# Hidden imports - things PyInstaller's static analysis might miss.
# Note: not all of these need to be importable at build time - PyInstaller
# will warn if a hidden import can't be resolved, but the build still succeeds.
# The ones that aren't installed (e.g. pytesseract without the system binary)
# will just be skipped at runtime by the code that uses them.
hidden_imports = [
    "fitz",                       # PyMuPDF - module is actually `pymupdf`/`fitz`
    "pdfplumber",
    "pdfminer",
    "pdfminer.high_level",
    "reportlab",
    "reportlab.lib",
    "reportlab.platypus",
    "pytesseract",                # optional - OCR fallback
    "yaml",
    "pydantic",
]

# Optional AI providers - import guarded so missing deps won't break packaging
try:
    import importlib
    for mod in ("openai", "anthropic", "ollama"):
        try:
            importlib.import_module(mod)
            hidden_imports.append(mod)
        except ImportError:
            pass
except Exception:
    pass

# PyMuPDF 1.24+ exposes fitz via the `pymupdf` package - add both names
# so whichever is installed gets picked up.
try:
    import pymupdf  # noqa: F401
    hidden_imports.append("pymupdf")
except ImportError:
    pass

# Ensure the sds_studio package itself is bundled as a package
# (not just individual modules) so relative imports inside it work.
# This is what makes run.py's `from sds_studio.main import main` resolve.
hidden_imports += collect_submodules("sds_studio")

a = Analysis(
    [os.path.join(SPEC_DIR, "run.py")],          # absolute path to launcher
    pathex=[SPEC_DIR],                            # project root on sys.path
    binaries=[],
    datas=pyside6_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SDSStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                # GUI app - no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                    # add "assets/app.ico" once you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SDSStudio",
)
