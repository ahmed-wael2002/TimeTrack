from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional

from timetrack.paths import database_path


@dataclass
class Project:
    id: int
    name: str
    created_at: str
    last_tracked_at: Optional[str] = None
    track_count: int = 0
    total_seconds: float = 0.0


@dataclass
class Track:
    id: int
    project_id: int
    title: str
    day_date: str
    start_time: str
    end_time: str
    duration_seconds: float
    output: str
    created_at: str
    project_name: str = ""


class Database:
    def __init__(self, path=None) -> None:
        self.path = str(path or database_path())
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    day_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    output TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tracks_project ON tracks(project_id);
                CREATE INDEX IF NOT EXISTS idx_tracks_day ON tracks(day_date);
                """
            )

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_user_name(self) -> str:
        return self.get_setting("user_name", "")

    def set_user_name(self, name: str) -> None:
        self.set_setting("user_name", name.strip())

    def create_project(self, name: str) -> Project:
        name = name.strip()
        if not name:
            raise ValueError("Project name cannot be empty.")
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO projects (name, created_at) VALUES (?, ?)",
                (name, now),
            )
            project_id = int(cursor.lastrowid)
        return self.get_project(project_id)

    def rename_project(self, project_id: int, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Project name cannot be empty.")
        with self.connect() as conn:
            conn.execute("UPDATE projects SET name = ? WHERE id = ?", (name, project_id))

    def delete_project(self, project_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def get_project(self, project_id: int) -> Project:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT p.id, p.name, p.created_at,
                       MAX(t.created_at) AS last_tracked_at,
                       COUNT(t.id) AS track_count,
                       COALESCE(SUM(t.duration_seconds), 0) AS total_seconds
                FROM projects p
                LEFT JOIN tracks t ON t.project_id = p.id
                WHERE p.id = ?
                GROUP BY p.id
                """,
                (project_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"Project {project_id} not found.")
        return self._project_from_row(row)

    def list_projects(self) -> list[Project]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.name, p.created_at,
                       MAX(t.created_at) AS last_tracked_at,
                       COUNT(t.id) AS track_count,
                       COALESCE(SUM(t.duration_seconds), 0) AS total_seconds
                FROM projects p
                LEFT JOIN tracks t ON t.project_id = p.id
                GROUP BY p.id
                ORDER BY COALESCE(MAX(t.created_at), p.created_at) DESC, p.name COLLATE NOCASE
                """
            ).fetchall()
        return [self._project_from_row(row) for row in rows]

    def recent_projects(self, limit: int = 6) -> list[Project]:
        return self.list_projects()[:limit]

    def add_track(
        self,
        project_id: int,
        title: str,
        day_date: str,
        start_time: str,
        end_time: str,
        duration_seconds: float,
        output: str,
    ) -> Track:
        title = title.strip() or "Untitled track"
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tracks (
                    project_id, title, day_date, start_time, end_time,
                    duration_seconds, output, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    title,
                    day_date,
                    start_time,
                    end_time,
                    float(duration_seconds),
                    output.strip(),
                    now,
                ),
            )
            track_id = int(cursor.lastrowid)
        return self.get_track(track_id)

    def get_track(self, track_id: int) -> Track:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT t.*, p.name AS project_name
                FROM tracks t
                JOIN projects p ON p.id = t.project_id
                WHERE t.id = ?
                """,
                (track_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"Track {track_id} not found.")
        return self._track_from_row(row)

    def list_tracks(self, project_id: int) -> list[Track]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT t.*, p.name AS project_name
                FROM tracks t
                JOIN projects p ON p.id = t.project_id
                WHERE t.project_id = ?
                ORDER BY t.day_date DESC, t.start_time DESC, t.id DESC
                """,
                (project_id,),
            ).fetchall()
        return [self._track_from_row(row) for row in rows]

    def update_track_output(self, track_id: int, output: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE tracks SET output = ? WHERE id = ?",
                (output.strip(), track_id),
            )

    @staticmethod
    def _project_from_row(row: sqlite3.Row) -> Project:
        return Project(
            id=int(row["id"]),
            name=row["name"],
            created_at=row["created_at"],
            last_tracked_at=row["last_tracked_at"],
            track_count=int(row["track_count"] or 0),
            total_seconds=float(row["total_seconds"] or 0),
        )

    @staticmethod
    def _track_from_row(row: sqlite3.Row) -> Track:
        return Track(
            id=int(row["id"]),
            project_id=int(row["project_id"]),
            title=row["title"],
            day_date=row["day_date"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            duration_seconds=float(row["duration_seconds"]),
            output=row["output"] or "",
            created_at=row["created_at"],
            project_name=row["project_name"] if "project_name" in row.keys() else "",
        )
