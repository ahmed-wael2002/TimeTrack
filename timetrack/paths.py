"""Portable paths — data lives next to the exe (or the project root in source)."""

from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundled_path(*parts: str) -> Path:
    """Files packed into the exe (PyInstaller) or the source tree."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).joinpath(*parts)
    return app_dir().joinpath(*parts)


def icon_png() -> Path:
    return bundled_path("assets", "icon.png")


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
