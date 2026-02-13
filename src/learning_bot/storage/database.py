"""SQLite database for student progress and conversation history."""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import ConversationMessage, LessonProgress, Student

log = logging.getLogger(__name__)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS students (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    preferences TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    id           TEXT PRIMARY KEY,
    student_id   TEXT NOT NULL REFERENCES students(id),
    module_id    TEXT NOT NULL,
    lesson_id    TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'not_started',
    started_at   TEXT,
    completed_at TEXT,
    notes        TEXT NOT NULL DEFAULT '',
    UNIQUE(student_id, module_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id          TEXT PRIMARY KEY,
    student_id  TEXT NOT NULL REFERENCES students(id),
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_progress_student
    ON lesson_progress(student_id);
CREATE INDEX IF NOT EXISTS idx_messages_session
    ON conversation_messages(session_id, timestamp);
"""


def _to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _from_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class Database:
    """Thin wrapper around SQLite for student/progress/conversation storage."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Connection helper
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_db(self) -> None:
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
        log.info("Database initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # Students
    # ------------------------------------------------------------------

    def create_student(self, student: Student) -> Student:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO students (id, name, created_at, preferences) VALUES (?, ?, ?, ?)",
                (student.id, student.name, _to_iso(student.created_at), json.dumps(student.preferences)),
            )
        return student

    def get_student(self, student_id: str) -> Student | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if row is None:
            return None
        return Student(
            id=row["id"],
            name=row["name"],
            created_at=_from_iso(row["created_at"]),  # type: ignore[arg-type]
            preferences=json.loads(row["preferences"]),
        )

    def get_or_create_student(self, name: str) -> Student:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM students WHERE name = ?", (name,)).fetchone()
            if row is not None:
                return Student(
                    id=row["id"],
                    name=row["name"],
                    created_at=_from_iso(row["created_at"]),  # type: ignore[arg-type]
                    preferences=json.loads(row["preferences"]),
                )
            student = Student(name=name)
            conn.execute(
                "INSERT INTO students (id, name, created_at, preferences) VALUES (?, ?, ?, ?)",
                (student.id, student.name, _to_iso(student.created_at), json.dumps(student.preferences)),
            )
        return student

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def get_progress(self, student_id: str, module_id: str, lesson_id: str) -> LessonProgress | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM lesson_progress WHERE student_id = ? AND module_id = ? AND lesson_id = ?",
                (student_id, module_id, lesson_id),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_progress(row)

    def update_progress(
        self,
        student_id: str,
        module_id: str,
        lesson_id: str,
        *,
        status: str | None = None,
        notes: str | None = None,
    ) -> LessonProgress:
        existing = self.get_progress(student_id, module_id, lesson_id)
        if existing is None:
            progress = LessonProgress(student_id=student_id, module_id=module_id, lesson_id=lesson_id)
        else:
            progress = existing

        if status is not None:
            progress.status = status
        if notes is not None:
            progress.notes = notes

        now = datetime.now(timezone.utc)
        if progress.status == "in_progress" and progress.started_at is None:
            progress.started_at = now
        if progress.status == "completed" and progress.completed_at is None:
            progress.completed_at = now

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO lesson_progress (id, student_id, module_id, lesson_id, status, started_at, completed_at, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(student_id, module_id, lesson_id)
                   DO UPDATE SET status=excluded.status, started_at=excluded.started_at,
                                 completed_at=excluded.completed_at, notes=excluded.notes""",
                (
                    progress.id,
                    progress.student_id,
                    progress.module_id,
                    progress.lesson_id,
                    progress.status,
                    _to_iso(progress.started_at),
                    _to_iso(progress.completed_at),
                    progress.notes,
                ),
            )
        return progress

    def get_all_progress(self, student_id: str) -> list[LessonProgress]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM lesson_progress WHERE student_id = ? ORDER BY module_id, lesson_id",
                (student_id,),
            ).fetchall()
        return [self._row_to_progress(r) for r in rows]

    def reset_progress(self, student_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM lesson_progress WHERE student_id = ?", (student_id,))

    @staticmethod
    def _row_to_progress(row: sqlite3.Row) -> LessonProgress:
        return LessonProgress(
            id=row["id"],
            student_id=row["student_id"],
            module_id=row["module_id"],
            lesson_id=row["lesson_id"],
            status=row["status"],
            started_at=_from_iso(row["started_at"]),
            completed_at=_from_iso(row["completed_at"]),
            notes=row["notes"],
        )

    # ------------------------------------------------------------------
    # Conversation messages
    # ------------------------------------------------------------------

    def save_message(self, message: ConversationMessage) -> ConversationMessage:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO conversation_messages
                   (id, student_id, session_id, role, content, timestamp, token_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    message.id,
                    message.student_id,
                    message.session_id,
                    message.role,
                    message.content,
                    _to_iso(message.timestamp),
                    message.token_count,
                ),
            )
        return message

    def get_messages(self, session_id: str, limit: int = 100) -> list[ConversationMessage]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM conversation_messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def get_recent_messages(self, session_id: str, max_tokens: int) -> list[ConversationMessage]:
        """Return the most recent messages that fit within *max_tokens*."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM conversation_messages WHERE session_id = ? ORDER BY timestamp DESC",
                (session_id,),
            ).fetchall()

        messages: list[ConversationMessage] = []
        total = 0
        for row in rows:
            if total + row["token_count"] > max_tokens:
                break
            messages.append(self._row_to_message(row))
            total += row["token_count"]

        messages.reverse()
        return messages

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> ConversationMessage:
        return ConversationMessage(
            id=row["id"],
            student_id=row["student_id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            timestamp=_from_iso(row["timestamp"]),  # type: ignore[arg-type]
            token_count=row["token_count"],
        )
