from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from timetrack.theme import FONT_UI, THEME


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


class CircleActionButton(tk.Canvas):
    def __init__(
        self,
        master,
        diameter: int = 168,
        command: Optional[Callable] = None,
        canvas_bg: str = THEME.bg,
    ) -> None:
        super().__init__(
            master,
            width=diameter + 36,
            height=diameter + 36,
            bg=canvas_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.diameter = diameter
        self.command = command
        self._mode = "idle"  # idle | running | paused
        self._pulse = 0.0
        self._pulse_dir = 1
        self._anim_after = None
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._hovered = False
        self.draw()
        self._animate()

    def set_mode(self, mode: str) -> None:
        self._mode = mode
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
        speed = 0.045 if self._mode == "running" else 0.018
        self._pulse += speed * self._pulse_dir
        if self._pulse >= 1:
            self._pulse = 1
            self._pulse_dir = -1
        elif self._pulse <= 0:
            self._pulse = 0
            self._pulse_dir = 1
        self.draw()
        self._anim_after = self.after(40, self._animate)

    def draw(self) -> None:
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        cx, cy = w / 2, h / 2
        radius = self.diameter / 2
        hover_boost = 3 if self._hovered else 0
        ring_extra = 8 + self._pulse * (14 if self._mode == "running" else 7) + hover_boost
        ring_color = THEME.play_ring if self._mode != "paused" else "#FECACA"
        fill = THEME.primary if self._mode != "paused" else THEME.danger
        if self._mode == "paused":
            fill = THEME.primary

        self.create_oval(
            cx - radius - ring_extra,
            cy - radius - ring_extra,
            cx + radius + ring_extra,
            cy + radius + ring_extra,
            fill=THEME.primary_soft,
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

        if self._mode == "running":
            bar_w, gap = 14, 12
            self.create_round_bar(cx - gap - bar_w / 2, cy, bar_w, 48)
            self.create_round_bar(cx + gap + bar_w / 2, cy, bar_w, 48)
        else:
            size = 42
            points = [
                cx - size * 0.28,
                cy - size * 0.48,
                cx - size * 0.28,
                cy + size * 0.48,
                cx + size * 0.52,
                cy,
            ]
            self.create_polygon(points, fill="#FFFFFF", outline="", smooth=False)

    def create_round_bar(self, cx: float, cy: float, width: float, height: float) -> None:
        x1, y1 = cx - width / 2, cy - height / 2
        x2, y2 = cx + width / 2, cy + height / 2
        r = width / 2
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill="#FFFFFF", outline="")
        self.create_oval(x1, y1, x1 + width, y1 + width, fill="#FFFFFF", outline="")
        self.create_oval(x1, y2 - width, x1 + width, y2, fill="#FFFFFF", outline="")
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill="#FFFFFF", outline="")


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
        self.title_lbl = tk.Label(
            inner,
            text=title,
            bg=THEME.surface,
            fg=THEME.text,
            font=(FONT_UI, 11, "bold"),
            anchor="w",
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


class FadeFrame(tk.Frame):
    """Shows or hides a child block with a short height animation."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, bg=kwargs.get("bg", THEME.bg))
        self._visible = False
        self._after = None

    def fade_in(self) -> None:
        if self._visible:
            return
        self._visible = True
        self.pack(fill="x", padx=36, pady=(8, 0))

    def fade_out(self) -> None:
        self._visible = False
        self.pack_forget()
