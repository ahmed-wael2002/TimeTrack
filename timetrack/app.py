from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from timetrack.database import Database, Project
from timetrack.dialogs import OutputDialog, ProjectPicker, TracksWindow, UserNameDialog
from timetrack.formatting import format_duration_words, format_hms, now_clock, now_display
from timetrack.theme import FONT_DISPLAY, FONT_UI, THEME
from timetrack.timer_service import TimerService, TimerSnapshot
from timetrack.widgets import CircleActionButton, FadeFrame, ProjectCard, RoundedButton


class TimeTrackApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TimeTrack")
        self.configure(bg=THEME.bg)
        self.minsize(460, 720)
        self.geometry("520x800")
        self._enable_dpi()

        self.db = Database()
        self.timer = TimerService()
        self.timer.set_tick_callback(self._on_timer_thread)
        self.selected_project_id: Optional[int] = None
        self._title_shown = False

        self._build()
        self.after(80, self._startup)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<space>", self._on_space)
        self.focus_set()

    def _enable_dpi(self) -> None:
        if sys.platform == "win32":
            try:
                from ctypes import windll

                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                try:
                    windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
        try:
            self.tk.call("tk", "scaling", 1.15)
        except Exception:
            pass

    def _build(self) -> None:
        top = tk.Frame(self, bg=THEME.bg)
        top.pack(fill="x", padx=28, pady=(22, 0))

        brand = tk.Frame(top, bg=THEME.bg)
        brand.pack(side="left")
        tk.Label(brand, text="TimeTrack", bg=THEME.bg, fg=THEME.primary, font=(FONT_DISPLAY, 20, "bold")).pack(
            anchor="w"
        )
        self.date_label = tk.Label(brand, text=now_display(), bg=THEME.bg, fg=THEME.muted, font=(FONT_UI, 9))
        self.date_label.pack(anchor="w")

        tools = tk.Frame(top, bg=THEME.bg)
        tools.pack(side="right")
        self._ghost_btn(tools, "Tracks", self._open_tracks).pack(side="left", padx=4)
        self._ghost_btn(tools, "User", self._edit_user).pack(side="left", padx=4)

        hero = tk.Frame(self, bg=THEME.bg)
        hero.pack(fill="both", expand=True, pady=(8, 0))

        self.status_label = tk.Label(
            hero, text="Ready when you are", bg=THEME.bg, fg=THEME.muted, font=(FONT_UI, 11)
        )
        self.status_label.pack(pady=(12, 0))

        self.clock_label = tk.Label(
            hero, text="00:00:00", bg=THEME.bg, fg=THEME.text, font=(FONT_DISPLAY, 36, "bold")
        )
        self.clock_label.pack(pady=(4, 8))

        self.play = CircleActionButton(hero, diameter=168, command=self._toggle_play, canvas_bg=THEME.bg)
        self.play.pack()

        self.title_wrap = FadeFrame(hero, bg=THEME.bg)
        tk.Label(
            self.title_wrap,
            text="What are you working on?",
            bg=THEME.bg,
            fg=THEME.muted,
            font=(FONT_UI, 9),
        ).pack(anchor="w")
        field = tk.Frame(self.title_wrap, bg=THEME.line, padx=1, pady=1)
        field.pack(fill="x", pady=(6, 0))
        self.title_var = tk.StringVar()
        self.title_entry = tk.Entry(
            field,
            textvariable=self.title_var,
            font=(FONT_UI, 13),
            bg=THEME.surface,
            fg=THEME.text,
            relief="flat",
            insertbackground=THEME.primary,
            justify="center",
        )
        self.title_entry.pack(fill="x", ipady=10, padx=1, pady=1)

        controls = tk.Frame(hero, bg=THEME.bg)
        controls.pack(pady=(16, 0))
        self.stop_btn = RoundedButton(
            controls,
            "Stop & save",
            command=self._stop_track,
            width=160,
            height=42,
            bg=THEME.danger,
            hover="#BE123C",
            canvas_bg=THEME.bg,
        )

        project_bar = tk.Frame(self, bg=THEME.bg)
        project_bar.pack(fill="x", padx=28, pady=(4, 8))
        self.project_btn = RoundedButton(
            project_bar,
            "Select project",
            command=self._pick_project,
            width=250,
            height=44,
            bg=THEME.surface,
            hover=THEME.primary_soft,
            fg=THEME.primary,
            canvas_bg=THEME.bg,
        )
        self.project_btn.pack()

        recent_header = tk.Frame(self, bg=THEME.bg)
        recent_header.pack(fill="x", padx=32, pady=(8, 0))
        tk.Label(
            recent_header,
            text="Recently tracked",
            bg=THEME.bg,
            fg=THEME.text,
            font=(FONT_UI, 11, "bold"),
            anchor="w",
        ).pack(side="left")
        self._ghost_btn(recent_header, "Manage", self._pick_project).pack(side="right")

        self.recent = tk.Frame(self, bg=THEME.bg)
        self.recent.pack(fill="both", expand=True, padx=28, pady=(4, 18))

        self.hint = tk.Label(
            self,
            text="Space starts or pauses  ·  timer keeps running in the background",
            bg=THEME.bg,
            fg=THEME.muted,
            font=(FONT_UI, 8),
        )
        self.hint.pack(pady=(0, 14))

    def _ghost_btn(self, parent, text: str, command) -> tk.Label:
        btn = tk.Label(parent, text=text, bg=THEME.bg, fg=THEME.primary, font=(FONT_UI, 9, "bold"), cursor="hand2")
        btn.bind("<Button-1>", lambda _e: command())
        return btn

    def _startup(self) -> None:
        if not self.db.get_user_name():
            dialog = UserNameDialog(self)
            self.wait_window(dialog)
            if dialog.result:
                self.db.set_user_name(dialog.result)
        self._refresh_projects()
        self._tick_date()

    def _tick_date(self) -> None:
        self.date_label.configure(text=now_display())
        self.after(30_000, self._tick_date)

    def _refresh_projects(self) -> None:
        for child in self.recent.winfo_children():
            child.destroy()
        projects = self.db.recent_projects()
        if self.selected_project_id:
            try:
                selected = self.db.get_project(self.selected_project_id)
                self.project_btn.set_text(selected.name)
                self.project_btn.set_colors(THEME.primary_soft, "#D6E6FB", THEME.primary)
            except KeyError:
                self.selected_project_id = None
        if not self.selected_project_id:
            self.project_btn.set_text("Select project")
            self.project_btn.set_colors(THEME.surface, THEME.primary_soft, THEME.primary)

        if not projects:
            tk.Label(
                self.recent,
                text="Create a project to start tracking your time.",
                bg=THEME.bg,
                fg=THEME.muted,
                font=(FONT_UI, 10),
            ).pack(pady=16)
            return
        for project in projects:
            subtitle = f"{format_duration_words(project.total_seconds)} · {project.track_count} tracks"
            card = ProjectCard(
                self.recent,
                project.name,
                subtitle,
                command=lambda p=project: self._select_project(p.id),
                selected=project.id == self.selected_project_id,
            )
            card.pack(fill="x")

    def _select_project(self, project_id: int) -> None:
        if self.timer.is_active() and project_id != self.selected_project_id:
            messagebox.showinfo("TimeTrack", "Stop the current track before switching projects.")
            return
        self.selected_project_id = project_id
        self._refresh_projects()

    def _pick_project(self) -> None:
        if self.timer.is_active():
            messagebox.showinfo("TimeTrack", "Stop the current track before changing projects.")
            return
        dialog = ProjectPicker(self, self.db, self.selected_project_id)
        self.wait_window(dialog)
        if dialog.result:
            self.selected_project_id = dialog.result
        self._refresh_projects()

    def _current_project(self) -> Optional[Project]:
        if not self.selected_project_id:
            return None
        try:
            return self.db.get_project(self.selected_project_id)
        except KeyError:
            self.selected_project_id = None
            return None

    def _ensure_project(self) -> Optional[Project]:
        project = self._current_project()
        if project:
            return project
        self._pick_project()
        return self._current_project()

    def _toggle_play(self) -> None:
        if not self.timer.is_active():
            if not self._ensure_project():
                return
            self.timer.start()
            self._show_title()
            self.stop_btn.pack()
            self.play.set_mode("running")
            self.status_label.configure(text="Tracking — stay in flow")
            self.title_entry.focus_set()
            return
        if self.timer.is_paused():
            self.timer.resume()
            self.play.set_mode("running")
            self.status_label.configure(text="Tracking — stay in flow")
        else:
            self.timer.pause()
            self.play.set_mode("paused")
            self.status_label.configure(text="Paused")

    def _show_title(self) -> None:
        if not self._title_shown:
            self.title_wrap.fade_in()
            self._title_shown = True

    def _hide_title(self) -> None:
        self.title_wrap.fade_out()
        self._title_shown = False
        self.title_var.set("")

    def _stop_track(self) -> None:
        if not self.timer.is_active():
            return
        snapshot = self.timer.stop()
        if snapshot.elapsed_seconds < 1:
            self._reset_ui()
            return
        title = self.title_var.get().strip() or "Untitled track"
        dialog = OutputDialog(self, title, format_hms(snapshot.elapsed_seconds))
        self.wait_window(dialog)
        output = dialog.result if dialog.result is not None else ""
        project = self._current_project()
        if not project:
            messagebox.showerror("TimeTrack", "The selected project is no longer available.")
            self._reset_ui()
            return
        self.db.add_track(
            project_id=project.id,
            title=title,
            day_date=snapshot.day_date,
            start_time=snapshot.start_clock,
            end_time=now_clock(),
            duration_seconds=snapshot.elapsed_seconds,
            output=output,
        )
        self._reset_ui()
        self._refresh_projects()

    def _reset_ui(self) -> None:
        self.timer.reset()
        self.play.set_mode("idle")
        self.clock_label.configure(text="00:00:00")
        self.status_label.configure(text="Ready when you are")
        self.stop_btn.pack_forget()
        self._hide_title()

    def _on_timer_thread(self, snapshot: TimerSnapshot) -> None:
        try:
            self.after(0, lambda s=snapshot: self._apply_snapshot(s))
        except tk.TclError:
            pass

    def _apply_snapshot(self, snapshot: TimerSnapshot) -> None:
        if not self.winfo_exists() or not snapshot.running:
            return
        self.clock_label.configure(text=snapshot.display)
        if snapshot.paused:
            self.status_label.configure(text="Paused")
        else:
            self.status_label.configure(text="Tracking — stay in flow")

    def _open_tracks(self) -> None:
        project = self._ensure_project()
        if not project:
            return
        dialog = TracksWindow(self, self.db, project)
        self.wait_window(dialog)

    def _edit_user(self) -> None:
        dialog = UserNameDialog(self, initial=self.db.get_user_name())
        self.wait_window(dialog)
        if dialog.result:
            self.db.set_user_name(dialog.result)

    def _on_space(self, event) -> None:
        if event.widget == self.title_entry:
            return
        self._toggle_play()
        return "break"

    def _on_close(self) -> None:
        if self.timer.is_active():
            if not messagebox.askyesno(
                "TimeTrack",
                "A track is still running. Stop and save it before closing?",
            ):
                return
            self._stop_track()
            if self.timer.is_active():
                return
        self.timer.shutdown()
        self.destroy()


def main() -> None:
    app = TimeTrackApp()
    app.mainloop()
