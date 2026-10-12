from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    bg: str = "#F7FAFD"
    surface: str = "#FFFFFF"
    primary: str = "#1E6FE8"
    primary_dark: str = "#1558C0"
    primary_soft: str = "#E8F1FD"
    accent: str = "#3B82F6"
    text: str = "#1E293B"
    muted: str = "#64748B"
    line: str = "#E2E8F0"
    danger: str = "#E11D48"
    danger_soft: str = "#FFE4EA"
    success: str = "#0F9F6E"
    shadow: str = "#D6E4F5"
    play_inner: str = "#1E6FE8"
    play_ring: str = "#93C5FD"


THEME = Theme()

FONT_UI = "Segoe UI"
FONT_DISPLAY = "Segoe UI Semibold"
