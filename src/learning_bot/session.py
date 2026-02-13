"""Session management for the learning bot."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from .storage.database import Database

log = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    session_id: str
    student_id: str
    student_name: str


class SessionManager:
    """Creates and tracks a single learning session."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._current: SessionInfo | None = None

    def start_session(self, student_name: str) -> SessionInfo:
        student = self._db.get_or_create_student(student_name)
        session_id = str(uuid4())
        self._current = SessionInfo(
            session_id=session_id,
            student_id=student.id,
            student_name=student.name,
        )
        log.info("Session %s started for student %s (%s)", session_id, student.name, student.id)
        return self._current

    def get_current_session(self) -> SessionInfo | None:
        return self._current
