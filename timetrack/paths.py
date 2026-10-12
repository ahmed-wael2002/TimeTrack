"""Portable paths — data lives next to the exe (or the project root in source)."""

from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    folder = app_dir() / "data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def database_path() -> Path:
    return data_dir() / "timetrack.db"


def exports_dir() -> Path:
    folder = app_dir() / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
