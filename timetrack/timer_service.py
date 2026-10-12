from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from timetrack.formatting import format_hms, now_clock, today_iso


@dataclass
class TimerSnapshot:
    running: bool
    paused: bool
    elapsed_seconds: float
    day_date: str
    start_clock: str
    display: str


class TimerService:
    """Wall-clock timer that keeps counting while the window is minimized."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._paused = False
        self._start_monotonic = 0.0
        self._pause_started = 0.0
        self._paused_total = 0.0
        self._day_date = ""
        self._start_clock = ""
        self._tick_callback: Optional[Callable[[TimerSnapshot], None]] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def set_tick_callback(self, callback: Callable[[TimerSnapshot], None]) -> None:
        self._tick_callback = callback

    def start(self) -> None:
        with self._lock:
            if self._running and not self._paused:
                return
            if self._running and self._paused:
                self._paused_total += time.monotonic() - self._pause_started
                self._paused = False
                return
            self._running = True
            self._paused = False
            self._paused_total = 0.0
            self._start_monotonic = time.monotonic()
            self._day_date = today_iso()
            self._start_clock = now_clock()
        self._ensure_thread()

    def pause(self) -> None:
        with self._lock:
            if not self._running or self._paused:
                return
            self._paused = True
            self._pause_started = time.monotonic()

    def resume(self) -> None:
        self.start()

    def stop(self) -> TimerSnapshot:
        snapshot = self.snapshot()
        with self._lock:
            self._running = False
            self._paused = False
        return snapshot

    def reset(self) -> None:
        with self._lock:
            self._running = False
            self._paused = False
            self._paused_total = 0.0
            self._day_date = ""
            self._start_clock = ""

    def is_active(self) -> bool:
        with self._lock:
            return self._running

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    def snapshot(self) -> TimerSnapshot:
        with self._lock:
            elapsed = 0.0
            if self._running:
                now = time.monotonic()
                paused_extra = (now - self._pause_started) if self._paused else 0.0
                elapsed = now - self._start_monotonic - self._paused_total - paused_extra
            return TimerSnapshot(
                running=self._running,
                paused=self._paused,
                elapsed_seconds=max(0.0, elapsed),
                day_date=self._day_date,
                start_clock=self._start_clock,
                display=format_hms(elapsed),
            )

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _ensure_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="TimeTrackTimer", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            snapshot = self.snapshot()
            callback = self._tick_callback
            if callback:
                try:
                    callback(snapshot)
                except Exception:
                    pass
            if not snapshot.running:
                break
            time.sleep(0.2)
