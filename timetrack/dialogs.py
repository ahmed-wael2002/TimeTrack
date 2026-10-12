from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable, Optional

from timetrack.database import Database, Project
from timetrack.export import export_project_sheet
from timetrack.formatting import format_duration_words, format_hms
from timetrack.theme import FONT_UI, THEME
from timetrack.widgets import RoundedButton


class Modal(tk.Toplevel):
    def __init__(self, master, title: str, width: int = 440, height: int = 320) -> None:
        super().__init__(master)
        self.title(title)
        self.configure(bg=THEME.surface)
        self.resizable(False, False)
        self.transient(master)
        self.result = None
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - width) // 2
        y = master.winfo_rooty() + (master.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.header = tk.Label(
            self,
            text=title,
            bg=THEME.surface,
            fg=THEME.text,
            font=(FONT_UI, 16, "bold"),
            anchor="w",
        )
        self.header.pack(fill="x", padx=24, pady=(22, 8))

    def close(self, result=None) -> None:
        self.result = result
        self.grab_release()
        self.destroy()


class TextPrompt(Modal):
    def __init__(
        self,
        master,
        title: str,
        message: str,
        placeholder: str = "",
        initial: str = "",
        multiline: bool = False,
        confirm: str = "Save",
        width: int = 460,
        height: int = 280,
    ) -> None:
        super().__init__(master, title, width=width, height=height)
        tk.Label(
            self,
            text=message,
            bg=THEME.surface,
            fg=THEME.muted,
            font=(FONT_UI, 10),
            wraplength=width - 48,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=24)

        self.var = tk.StringVar(value=initial)
        if multiline:
            wrap = tk.Frame(self, bg=THEME.line, padx=1, pady=1)
            wrap.pack(fill="both", expand=True, padx=24, pady=(12, 8))
            self.entry = tk.Text(
                wrap,
                height=6,
                font=(FONT_UI, 11),
                bg=THEME.bg,
                fg=THEME.text,
                relief="flat",
                wrap="word",
                insertbackground=THEME.primary,
            )
            self.entry.pack(fill="both", expand=True, padx=8, pady=8)
            if initial:
                self.entry.insert("1.0", initial)
            elif placeholder:
                self.entry.insert("1.0", placeholder)
                self.entry.configure(fg=THEME.muted)
                self.entry.bind("<FocusIn>", self._clear_placeholder)
            self.placeholder = placeholder
        else:
            wrap = tk.Frame(self, bg=THEME.line, padx=1, pady=1)
            wrap.pack(fill="x", padx=24, pady=(16, 8))
            self.entry = tk.Entry(
                wrap,
                textvariable=self.var,
                font=(FONT_UI, 12),
                bg=THEME.bg,
                fg=THEME.text,
                relief="flat",
                insertbackground=THEME.primary,
            )
            self.entry.pack(fill="x", padx=10, pady=10)
            self.placeholder = ""
            self.entry.focus_set()
            self.entry.bind("<Return>", lambda _e: self._confirm())

        actions = tk.Frame(self, bg=THEME.surface)
        actions.pack(fill="x", padx=24, pady=(8, 20))
        RoundedButton(
            actions,
            "Cancel",
            command=self.close,
            width=110,
            height=40,
            bg=THEME.primary_soft,
            hover="#D6E6FB",
            fg=THEME.primary,
            canvas_bg=THEME.surface,
        ).pack(side="right", padx=(8, 0))
        RoundedButton(
            actions,
            confirm,
            command=self._confirm,
            width=110,
            height=40,
            canvas_bg=THEME.surface,
        ).pack(side="right")

    def _clear_placeholder(self, _event) -> None:
        if self.entry.get("1.0", "end-1c") == self.placeholder:
            self.entry.delete("1.0", "end")
            self.entry.configure(fg=THEME.text)

    def _confirm(self) -> None:
        if isinstance(self.entry, tk.Text):
            value = self.entry.get("1.0", "end-1c").strip()
            if value == self.placeholder:
                value = ""
        else:
            value = self.var.get().strip()
        self.close(value)


class ProjectPicker(Modal):
    def __init__(self, master, db: Database, selected_id: Optional[int] = None) -> None:
        super().__init__(master, "Projects", width=460, height=520)
        self.db = db
        self.selected_id = selected_id
        tk.Label(
            self,
            text="Choose a project or create a new one.",
            bg=THEME.surface,
            fg=THEME.muted,
            font=(FONT_UI, 10),
            anchor="w",
        ).pack(fill="x", padx=24)

        actions = tk.Frame(self, bg=THEME.surface)
        actions.pack(fill="x", padx=24, pady=(10, 6))
        RoundedButton(
            actions,
            "+ New project",
            command=self._create,
            width=150,
            height=36,
            canvas_bg=THEME.surface,
        ).pack(side="left")

        list_wrap = tk.Frame(self, bg=THEME.line)
        list_wrap.pack(fill="both", expand=True, padx=24, pady=(8, 12))
        self.canvas = tk.Canvas(list_wrap, bg=THEME.bg, highlightthickness=0)
        scroll = tk.Scrollbar(list_wrap, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=THEME.bg)
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.refresh()

        footer = tk.Frame(self, bg=THEME.surface)
        footer.pack(fill="x", padx=24, pady=(0, 18))
        RoundedButton(
            footer,
            "Done",
            command=lambda: self.close(self.selected_id),
            width=120,
            height=40,
            canvas_bg=THEME.surface,
        ).pack(side="right")

    def refresh(self) -> None:
        for child in self.inner.winfo_children():
            child.destroy()
        projects = self.db.list_projects()
        if not projects:
            tk.Label(
                self.inner,
                text="No projects yet. Create your first one.",
                bg=THEME.bg,
                fg=THEME.muted,
                font=(FONT_UI, 10),
                pady=24,
            ).pack()
            return
        for project in projects:
            self._row(project)

    def _row(self, project: Project) -> None:
        selected = project.id == self.selected_id
        row = tk.Frame(self.inner, bg=THEME.surface, highlightthickness=1,
                       highlightbackground=THEME.primary if selected else THEME.line)
        row.pack(fill="x", padx=8, pady=6)
        body = tk.Frame(row, bg=THEME.surface)
        body.pack(fill="x", padx=12, pady=10)
        info = tk.Frame(body, bg=THEME.surface)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(
            info,
            text=project.name,
            bg=THEME.surface,
            fg=THEME.text,
            font=(FONT_UI, 11, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            info,
            text=f"{project.track_count} tracks · {format_duration_words(project.total_seconds)}",
            bg=THEME.surface,
            fg=THEME.muted,
            font=(FONT_UI, 9),
            anchor="w",
        ).pack(fill="x")
        btns = tk.Frame(body, bg=THEME.surface)
        btns.pack(side="right")
        self._tiny(btns, "Select", lambda p=project: self._select(p))
        self._tiny(btns, "Rename", lambda p=project: self._rename(p))
        self._tiny(btns, "Export", lambda p=project: self._export(p))
        self._tiny(btns, "Delete", lambda p=project: self._delete(p), danger=True)

    def _tiny(self, parent, text: str, command: Callable, danger: bool = False) -> None:
        fg = THEME.danger if danger else THEME.primary
        btn = tk.Label(parent, text=text, bg=THEME.surface, fg=fg, font=(FONT_UI, 8, "bold"), cursor="hand2", padx=6)
        btn.pack(side="left")
        btn.bind("<Button-1>", lambda _e: command())

    def _select(self, project: Project) -> None:
        self.close(project.id)

    def _create(self) -> None:
        dialog = TextPrompt(self, "New project", "Give this project a short name.", confirm="Create", height=220)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            project = self.db.create_project(dialog.result)
            self.selected_id = project.id
            self.refresh()
        except Exception as exc:
            messagebox.showerror("TimeTrack", str(exc), parent=self)

    def _rename(self, project: Project) -> None:
        dialog = TextPrompt(
            self, "Rename project", "Update the project title.", initial=project.name, confirm="Rename", height=220
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            self.db.rename_project(project.id, dialog.result)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("TimeTrack", str(exc), parent=self)

    def _delete(self, project: Project) -> None:
        if not messagebox.askyesno(
            "Delete project",
            f"Delete “{project.name}” and all of its tracks? This cannot be undone.",
            parent=self,
        ):
            return
        self.db.delete_project(project.id)
        if self.selected_id == project.id:
            self.selected_id = None
        self.refresh()

    def _export(self, project: Project) -> None:
        user = self.db.get_user_name()
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Export TrackSheet",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile=f"{project.name}_TrackSheet.xlsx",
        )
        if not dest:
            return
        path = export_project_sheet(self.db, project, user, dest=dest)
        messagebox.showinfo("Exported", f"TrackSheet saved to:\n{path}", parent=self)


class UserNameDialog(TextPrompt):
    def __init__(self, master, initial: str = "") -> None:
        super().__init__(
            master,
            "Welcome to TimeTrack",
            "What should we call you? This name appears on exported TrackSheets.",
            initial=initial,
            confirm="Continue",
            height=230,
        )


class OutputDialog(TextPrompt):
    def __init__(self, master, title: str, duration: str) -> None:
        super().__init__(
            master,
            "What did you ship?",
            f"“{title}” ran for {duration}. Capture the output of this track while it is still fresh.",
            placeholder="Key results, decisions, or next steps…",
            multiline=True,
            confirm="Save track",
            height=340,
        )


class TracksWindow(Modal):
    def __init__(self, master, db: Database, project: Project) -> None:
        super().__init__(master, f"{project.name} — tracks", width=640, height=520)
        self.header.configure(text=project.name)
        tk.Label(
            self,
            text=f"{project.track_count} tracks · {format_hms(project.total_seconds)} total",
            bg=THEME.surface,
            fg=THEME.muted,
            font=(FONT_UI, 10),
            anchor="w",
        ).pack(fill="x", padx=24)

        wrap = tk.Frame(self, bg=THEME.line)
        wrap.pack(fill="both", expand=True, padx=24, pady=12)
        canvas = tk.Canvas(wrap, bg=THEME.bg, highlightthickness=0)
        scroll = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=THEME.bg)
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=580)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        tracks = db.list_tracks(project.id)
        if not tracks:
            tk.Label(inner, text="No tracks yet.", bg=THEME.bg, fg=THEME.muted, font=(FONT_UI, 10), pady=28).pack()
        for track in tracks:
            card = tk.Frame(inner, bg=THEME.surface)
            card.pack(fill="x", padx=10, pady=6)
            top = tk.Frame(card, bg=THEME.surface)
            top.pack(fill="x", padx=12, pady=(10, 0))
            tk.Label(top, text=track.title, bg=THEME.surface, fg=THEME.text, font=(FONT_UI, 11, "bold"), anchor="w").pack(
                side="left", fill="x", expand=True
            )
            tk.Label(
                top,
                text=format_hms(track.duration_seconds),
                bg=THEME.surface,
                fg=THEME.primary,
                font=(FONT_UI, 11, "bold"),
            ).pack(side="right")
            tk.Label(
                card,
                text=f"{track.day_date}  ·  {track.start_time} – {track.end_time}",
                bg=THEME.surface,
                fg=THEME.muted,
                font=(FONT_UI, 9),
                anchor="w",
            ).pack(fill="x", padx=12)
            tk.Label(
                card,
                text=track.output or "No output recorded",
                bg=THEME.surface,
                fg=THEME.text if track.output else THEME.muted,
                font=(FONT_UI, 9),
                wraplength=540,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=12, pady=(4, 12))

        footer = tk.Frame(self, bg=THEME.surface)
        footer.pack(fill="x", padx=24, pady=(0, 18))
        RoundedButton(footer, "Close", command=self.close, width=110, height=40, canvas_bg=THEME.surface).pack(
            side="right"
        )
