"""Student progress tracking — state machine over lesson statuses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from learning_bot.storage.database import Database
    from learning_bot.storage.models import LessonProgress

logger = logging.getLogger(__name__)

# Valid status transitions
_VALID_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"in_progress"},
    "not_started": {"in_progress"},
    "in_progress": {"validated", "completed"},
    "validated": {"completed"},
    "completed": set(),  # terminal
}


class ProgressError(Exception):
    """Raised on invalid progress transitions."""


class ProgressTracker:
    """State-machine that tracks per-lesson progress for a student."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def start_lesson(
        self, student_id: str, module_id: str, lesson_id: str
    ) -> None:
        """Mark a lesson as *in_progress*."""
        self._transition(student_id, module_id, lesson_id, "in_progress")

    def validate_lesson(
        self, student_id: str, module_id: str, lesson_id: str
    ) -> None:
        """Mark a lesson as *validated* (quiz/check passed)."""
        self._transition(student_id, module_id, lesson_id, "validated")

    def complete_lesson(
        self, student_id: str, module_id: str, lesson_id: str
    ) -> None:
        """Mark a lesson as *completed*."""
        self._transition(student_id, module_id, lesson_id, "completed")

    def get_lesson_status(
        self, student_id: str, module_id: str, lesson_id: str
    ) -> str | None:
        """Return the current status string, or ``None`` if not started."""
        row = self.db.get_progress(student_id, module_id, lesson_id)
        return row.status if row else None

    def get_all_progress(self, student_id: str) -> list[LessonProgress]:
        """Return all progress records for a student."""
        return self.db.get_all_progress(student_id)

    def get_completion_stats(self, student_id: str) -> dict:
        """Return a dict with counts and percentages."""
        rows = self.db.get_all_progress(student_id)
        completed = sum(1 for r in rows if r.status == "completed")
        in_progress = sum(1 for r in rows if r.status == "in_progress")
        validated = sum(1 for r in rows if r.status == "validated")
        total = len(rows)

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "validated": validated,
            "percent_complete": round(completed / total * 100, 1) if total else 0.0,
        }

    def reset_progress(self, student_id: str) -> None:
        """Reset all progress for a student."""
        self.db.reset_progress(student_id)

    def _transition(
        self,
        student_id: str,
        module_id: str,
        lesson_id: str,
        new_status: str,
    ) -> None:
        """Apply a status transition, enforcing the state machine."""
        current = self.get_lesson_status(student_id, module_id, lesson_id)
        allowed = _VALID_TRANSITIONS.get(current, set())

        if new_status not in allowed:
            logger.warning(
                "Invalid transition %s -> %s for %s/%s, forcing",
                current, new_status, module_id, lesson_id,
            )

        self.db.update_progress(
            student_id=student_id,
            module_id=module_id,
            lesson_id=lesson_id,
            status=new_status,
        )
        logger.debug(
            "Progress %s/%s: %s -> %s", module_id, lesson_id, current, new_status
        )
