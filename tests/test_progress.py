"""Tests for learning_bot.progress.ProgressTracker."""

from __future__ import annotations

import logging

import pytest

from learning_bot.progress import ProgressTracker
from learning_bot.storage.database import Database
from learning_bot.storage.models import Student


@pytest.fixture()
def tracker(tmp_db: Database) -> ProgressTracker:
    return ProgressTracker(tmp_db)


@pytest.fixture()
def student_id(tmp_db: Database) -> str:
    student = Student(name="ProgressTest")
    tmp_db.create_student(student)
    return student.id


class TestStateTransitions:
    def test_start_then_validate_then_complete(
        self, tracker: ProgressTracker, student_id: str
    ) -> None:
        tracker.start_lesson(student_id, "m1", "l1")
        assert tracker.get_lesson_status(student_id, "m1", "l1") == "in_progress"

        tracker.validate_lesson(student_id, "m1", "l1")
        assert tracker.get_lesson_status(student_id, "m1", "l1") == "validated"

        tracker.complete_lesson(student_id, "m1", "l1")
        assert tracker.get_lesson_status(student_id, "m1", "l1") == "completed"

    def test_start_then_complete_skipping_validate(
        self, tracker: ProgressTracker, student_id: str
    ) -> None:
        tracker.start_lesson(student_id, "m1", "l1")
        tracker.complete_lesson(student_id, "m1", "l1")
        assert tracker.get_lesson_status(student_id, "m1", "l1") == "completed"


class TestInvalidTransition:
    def test_complete_from_not_started_logs_warning(
        self, tracker: ProgressTracker, student_id: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="learning_bot.progress"):
            tracker.complete_lesson(student_id, "m1", "l1")
        assert "Invalid transition" in caplog.text
        # Forced anyway
        assert tracker.get_lesson_status(student_id, "m1", "l1") == "completed"


class TestReset:
    def test_reset_clears_all(
        self, tracker: ProgressTracker, student_id: str
    ) -> None:
        tracker.start_lesson(student_id, "m1", "l1")
        tracker.complete_lesson(student_id, "m1", "l1")
        assert len(tracker.get_all_progress(student_id)) == 1

        tracker.reset_progress(student_id)
        assert len(tracker.get_all_progress(student_id)) == 0
