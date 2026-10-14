from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Optional

from timetrack.paths import bundled_path, icon_png
from timetrack.theme import FONT_UI, THEME

_ICON_FONTS = ("Segoe MDL2 Assets", "Segoe Fluent Icons")
_PLAY_GLYPH = "\uE768"
_PAUSE_GLYPH = "\uE769"
_STOP_GLYPH = "\uE71A"
_icon_font_family: Optional[str] = None
_icon_font_resolved = False
_app_icon_image: Optional[tk.PhotoImage] = None


def apply_window_icon(window: tk.Misc) -> None:
    """Use assets/icon.png for the window, taskbar, and child dialogs."""
    global _app_icon_image
    ico = bundled_path("assets", "icon.ico")
    if ico.exists():
        try:
            window.iconbitmap(str(ico))
        except tk.TclError:
            pass
    path = icon_png()
    if not path.exists():
        return
    try:
        if _app_icon_image is None:
            image = tk.PhotoImage(file=str(path))
            width = int(image.width())
            if width > 256:
                factor = max(1, round(width / 256))
                image = image.subsample(factor, factor)
            _app_icon_image = image
        window.iconphoto(True, _app_icon_image)
    except tk.TclError:
        return


def media_icon_font(size: int) -> Optional[tuple]:
    global _icon_font_family, _icon_font_resolved
    if not _icon_font_resolved:
        families = {name.lower() for name in tkfont.families()}
        _icon_font_family = next((name for name in _ICON_FONTS if name.lower() in families), None)
        _icon_font_resolved = True
    if not _icon_font_family:
        return None
    return (_icon_font_family, size)


def round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
    radius = min(radius, abs(x2 - x1) // 2, abs(y2 - y1) // 2)
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master,
        text: str,
        command: Optional[Callable] = None,
        width: int = 220,
        height: int = 44,
        radius: int = 22,
        bg: str = THEME.primary,
        fg: str = "#FFFFFF",
        hover: str = THEME.primary_dark,
        font: tuple = (FONT_UI, 11, "bold"),
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            bg=kwargs.pop("canvas_bg", THEME.bg),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            **kwargs,
        )
        self._text = text
        self._command = command
        self._width = width
        self._height = height
        self._radius = radius
        self._bg = bg
        self._fg = fg
        self._hover = hover
        self._font = font
        self._enabled = True
        self._shape = None
        self._label = None
        self._draw(bg)
        self.bind("<Enter>", lambda _e: self._draw(self._hover) if self._enabled else None)
        self.bind("<Leave>", lambda _e: self._draw(self._bg) if self._enabled else None)
        self.bind("<Button-1>", self._on_click)

    def set_text(self, text: str) -> None:
        self._text = text
        if self._label:
            self.itemconfigure(self._label, text=text)

    def set_command(self, command: Optional[Callable]) -> None:
        self._command = command

    def set_colors(self, bg: str, hover: str, fg: str = "#FFFFFF") -> None:
        self._bg, self._hover, self._fg = bg, hover, fg
        self._draw(bg)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw(self._bg if enabled else THEME.line)

    def _draw(self, fill: str) -> None:
        self.delete("all")
        self._shape = round_rect(self, 1, 1, self._width - 1, self._height - 1, self._radius, fill=fill, outline="")
        self._label = self.create_text(
            self._width / 2,
            self._height / 2,
            text=self._text,
            fill=self._fg if self._enabled else THEME.muted,
            font=self._font,
        )

    def _on_click(self, _event) -> None:
        if self._enabled and self._command:
            self._command()


class CircleIconButton(tk.Canvas):
    """Circular media control; icons are font glyphs so they stay sharp on HiDPI."""

    def __init__(
        self,
        master,
        diameter: int = 168,
        command: Optional[Callable] = None,
        canvas_bg: str = THEME.bg,
        role: str = "play",
    ) -> None:
        pad = 64 if role == "play" else 40
        super().__init__(
            master,
            width=diameter + pad,
            height=diameter + pad,
            bg=canvas_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.diameter = diameter
        self.command = command
        self.role = role
        self._mode = "idle"  # idle | running | paused
        self._pulse = 0.0
        self._pulse_dir = 1
        self._burst = 0.0
        self._bounce = 0.0
        self._anim_after = None
        self._hovered = False
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.draw()
        self._animate()

    def set_mode(self, mode: str, animate: bool = False) -> None:
        previous = self._mode
        self._mode = mode
        if animate:
            if mode == "running" and previous != "running":
                self._burst = 1.0
                self._bounce = 1.0
            elif mode == "idle":
                self._burst = 0.85
                self._bounce = 0.55
            elif mode == "paused":
                self._bounce = 0.4
        self.draw()

    def pop_in(self) -> None:
        self._burst = 0.7
        self._bounce = 1.0
        self.draw()

    def destroy(self) -> None:
        if self._anim_after:
            try:
                self.after_cancel(self._anim_after)
            except Exception:
                pass
        super().destroy()

    def _on_click(self, _event) -> None:
        if self.command:
            self.command()

    def _on_enter(self, _event) -> None:
        self._hovered = True
        self.draw()

    def _on_leave(self, _event) -> None:
        self._hovered = False
        self.draw()

    def _animate(self) -> None:
        moving = False
        if self.role == "play":
            speed = 0.045 if self._mode == "running" else 0.018
            self._pulse += speed * self._pulse_dir
            if self._pulse >= 1:
                self._pulse = 1
                self._pulse_dir = -1
            elif self._pulse <= 0:
                self._pulse = 0
                self._pulse_dir = 1
            moving = True
        if self._burst > 0.01:
            self._burst *= 0.86
            moving = True
        else:
            self._burst = 0.0
        if self._bounce > 0.01:
            self._bounce *= 0.78
            moving = True
        else:
            self._bounce = 0.0
        if moving or self.role == "play":
            self.draw()
        self._anim_after = self.after(32, self._animate)

    def draw(self) -> None:
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        cx, cy = w / 2, h / 2
        bounce = 1.0 + (0.08 * self._bounce)
        radius = (self.diameter / 2) * bounce
        hover_boost = 3 if self._hovered else 0
        is_stop = self.role == "stop"
        running = self._mode == "running" and not is_stop
        max_extra = max(4, (min(w, h) / 2) - radius - 2)
        ring_extra = min(max_extra, 8 + self._pulse * (14 if running else 7) + hover_boost)
        soft = THEME.danger_soft if is_stop else THEME.primary_soft
        ring_color = "#FECACA" if is_stop else (THEME.play_ring if self._mode != "paused" else "#BFDBFE")
        fill = THEME.danger if is_stop else THEME.primary

        if self._burst:
            burst_r = min(min(w, h) / 2 - 1, radius + 10 + self._burst * 18)
            self.create_oval(
                cx - burst_r,
                cy - burst_r,
                cx + burst_r,
                cy + burst_r,
                fill=soft,
                outline="",
            )

        self.create_oval(
            cx - radius - ring_extra,
            cy - radius - ring_extra,
            cx + radius + ring_extra,
            cy + radius + ring_extra,
            fill=soft,
            outline="",
        )
        self.create_oval(
            cx - radius - 6,
            cy - radius - 6,
            cx + radius + 6,
            cy + radius + 6,
            fill=ring_color,
            outline="",
        )
        self.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill=fill,
            outline="",
        )
        self._draw_icon(cx, cy, radius)

    def _draw_icon(self, cx: float, cy: float, radius: float) -> None:
        if self.role == "stop":
            glyph = _STOP_GLYPH
            font_size = max(16, int(radius * 0.72))
        elif self._mode == "running":
            glyph = _PAUSE_GLYPH
            font_size = max(28, int(radius * 0.62))
        else:
            glyph = _PLAY_GLYPH
            font_size = max(28, int(radius * 0.68))

        icon_font = media_icon_font(font_size)
        if icon_font:
            # Play glyphs sit optically left of center; nudge so they look balanced.
            x = cx + (radius * 0.04 if glyph == _PLAY_GLYPH else 0)
            self.create_text(x, cy, text=glyph, fill="#FFFFFF", font=icon_font)
            return

        if self.role == "stop":
            side = radius * 0.42
            round_rect(
                self,
                cx - side,
                cy - side,
                cx + side,
                cy + side,
                int(side * 0.28),
                fill="#FFFFFF",
                outline="",
            )
        elif self._mode == "running":
            bar_w = max(8, radius * 0.16)
            gap = radius * 0.16
            height = radius * 0.58
            self._round_bar(cx - gap - bar_w / 2, cy, bar_w, height)
            self._round_bar(cx + gap + bar_w / 2, cy, bar_w, height)
        else:
            size = radius * 0.55
            points = [
                cx - size * 0.22,
                cy - size * 0.48,
                cx - size * 0.22,
                cy + size * 0.48,
                cx + size * 0.58,
                cy,
            ]
            self.create_polygon(points, fill="#FFFFFF", outline="", joinstyle="round")

    def _round_bar(self, cx: float, cy: float, width: float, height: float) -> None:
        x1, y1 = cx - width / 2, cy - height / 2
        x2, y2 = cx + width / 2, cy + height / 2
        round_rect(self, x1, y1, x2, y2, int(width / 2), fill="#FFFFFF", outline="")


CircleActionButton = CircleIconButton


class ProjectCard(tk.Frame):
    def __init__(
        self,
        master,
        title: str,
        subtitle: str,
        command: Optional[Callable] = None,
        selected: bool = False,
    ) -> None:
        super().__init__(master, bg=THEME.bg)
        self.command = command
        self.card = tk.Frame(self, bg=THEME.surface, highlightthickness=1, highlightbackground=THEME.line)
        self.card.pack(fill="x", padx=2, pady=4)
        inner = tk.Frame(self.card, bg=THEME.surface)
        inner.pack(fill="x", padx=16, pady=12)
        self.title_lbl = EllipsisLabel(
            inner,
            text=title,
            bg=THEME.surface,
            fg=THEME.text,
            font=(FONT_UI, 11, "bold"),
        )
        self.title_lbl.pack(fill="x")
        self.sub_lbl = tk.Label(
            inner,
            text=subtitle,
            bg=THEME.surface,
            fg=THEME.muted,
            font=(FONT_UI, 9),
            anchor="w",
        )
        self.sub_lbl.pack(fill="x", pady=(2, 0))
        self.set_selected(selected)
        for widget in (self, self.card, inner, self.title_lbl, self.sub_lbl):
            widget.bind("<Button-1>", self._click)
            widget.configure(cursor="hand2")

    def set_selected(self, selected: bool) -> None:
        color = THEME.primary if selected else THEME.line
        self.card.configure(highlightbackground=color, highlightthickness=2 if selected else 1)

    def _click(self, _event) -> None:
        if self.command:
            self.command()


class EllipsisLabel(tk.Label):
    """Single-line label that ellipsizes when the widget is narrower than the text."""

    def __init__(self, master, text: str = "", **kwargs) -> None:
        kwargs.setdefault("anchor", "w")
        kwargs.setdefault("justify", "left")
        super().__init__(master, text=text, **kwargs)
        self._full_text = text
        self.bind("<Configure>", self._fit)

    def set_text(self, text: str) -> None:
        self._full_text = text
        self._fit()

    def _fit(self, _event=None) -> None:
        width = self.winfo_width()
        if width <= 2:
            return
        font = tkfont.Font(font=self.cget("font"))
        fitted = _ellipsize(font, self._full_text, max(12, width - 4))
        if self.cget("text") != fitted:
            self.configure(text=fitted)


def _ellipsize(font: tkfont.Font, text: str, max_width: int) -> str:
    if font.measure(text) <= max_width:
        return text
    ellipsis = "…"
    if font.measure(ellipsis) > max_width:
        return ""
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if font.measure(text[:mid] + ellipsis) <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low] + ellipsis if low else ellipsis


class FadeFrame(tk.Frame):
    """Shows or hides a child block with a short height animation."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, bg=kwargs.get("bg", THEME.bg))
        self._visible = False
        self._after = None
        self._target_height = 0

    def fade_in(self) -> None:
        if self._visible:
            return
        self._visible = True
        self.pack(fill="x", padx=36, pady=(8, 0))
        self.update_idletasks()
        self._target_height = max(self.winfo_reqheight(), 1)
        self.pack_propagate(False)
        self.configure(height=1)
        self._step_in(1)

    def fade_out(self) -> None:
        self._visible = False
        if self._after:
            try:
                self.after_cancel(self._after)
            except Exception:
                pass
            self._after = None
        self.pack_propagate(True)
        self.pack_forget()

    def _step_in(self, height: int) -> None:
        if not self._visible:
            return
        if height >= self._target_height:
            self.pack_propagate(True)
            return
        nxt = min(self._target_height, height + max(8, self._target_height // 6))
        self.configure(height=nxt)
        self._after = self.after(16, lambda: self._step_in(nxt))
