from __future__ import annotations

from datetime import datetime, timedelta


def format_hms(total_seconds: float) -> str:
    seconds = max(0, int(total_seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_duration_words(total_seconds: float) -> str:
    seconds = max(0, int(total_seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_clock() -> str:
    return datetime.now().strftime("%H:%M:%S")


def now_display() -> str:
    return datetime.now().strftime("%A, %b %d")


def parse_iso_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def duration_from_clock(start: str, end: str, day: str) -> timedelta:
    start_dt = datetime.strptime(f"{day} {start}", "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(f"{day} {end}", "%Y-%m-%d %H:%M:%S")
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    return end_dt - start_dt
