"""
Application paths and config loading.

All file operations in SDS Studio resolve paths relative to one of three roots:
  - APP_ROOT  : the folder containing the executable (or the repo root in dev)
  - CONFIG_DIR: <APP_ROOT>/config
  - ASSETS_DIR: <APP_ROOT>/assets

This makes the app fully portable: copy the folder, paths still resolve.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml


def _app_root() -> Path:
    """
    Resolve the application root directory.

    When running from a PyInstaller bundle, sys.frozen is set and
    sys.executable points to the .exe. In dev mode, we use the
    location of this file (sds_studio/core/paths.py -> project root).
    """
    if getattr(sys, "frozen", False):
        # PyInstaller onedir: exe lives in APP_ROOT
        return Path(sys.executable).parent.resolve()
    # Dev mode: this file is at <repo>/sds_studio/core/paths.py
    return Path(__file__).resolve().parent.parent.parent


APP_ROOT = _app_root()
CONFIG_DIR = APP_ROOT / "config"
ASSETS_DIR = APP_ROOT / "assets"
LOGS_DIR = APP_ROOT / "logs"
INPUT_DIR = APP_ROOT / "input"
OUTPUT_DIR = APP_ROOT / "output"
REVIEW_DIR = APP_ROOT / "review_queue"


def ensure_dirs() -> None:
    """Create the working directories if missing."""
    for d in (CONFIG_DIR, ASSETS_DIR, LOGS_DIR, INPUT_DIR, OUTPUT_DIR, REVIEW_DIR):
        d.mkdir(parents=True, exist_ok=True)


def resolve_path(p: str | Path) -> Path:
    """
    Resolve a path that may be either absolute or relative to APP_ROOT.
    Used for logo paths, output dirs, etc.
    """
    p = Path(p)
    if p.is_absolute():
        return p
    return (APP_ROOT / p).resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=100)


# Config file paths
SETTINGS_FILE = CONFIG_DIR / "settings.yaml"
SUPPLIERS_FILE = CONFIG_DIR / "suppliers.yaml"
TEMPLATE_CONFIG_FILE = CONFIG_DIR / "template_config.yaml"
SCHEMA_FILE = CONFIG_DIR / "sds_schema.json"
