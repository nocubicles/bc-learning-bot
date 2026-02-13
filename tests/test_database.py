"""Tests for learning_bot.storage.database.Database."""

from __future__ import annotations

from pathlib import Path

import pytest

from learning_bot.storage.database import Database
from learning_bot.storage.models import ConversationMessage, LessonProgress, Student


# ---------------------------------------------------------------------------
# Student CRUD
# ---------------------------------------------------------------------------


class TestStudentCRUD:
    def test_create_and_get(self, tmp_db: Database) -> None:
        student = Student(name="Alice")
        tmp_db.create_student(student)

        fetched = tmp_db.get_student(student.id)
        assert fetched is not None
        assert fetched.name == "Alice"
        assert fetched.id == student.id

    def test_get_nonexistent_returns_none(self, tmp_db: Database) -> None:
        assert tmp_db.get_student("no-such-id") is None

    def test_get_or_create_creates(self, tmp_db: Database) -> None:
        student = tmp_db.get_or_create_student("Bob")
        assert student.name == "Bob"

        # Second call returns the same record
        same = tmp_db.get_or_create_student("Bob")
        assert same.id == student.id

    def test_get_or_create_is_idempotent(self, tmp_db: Database) -> None:
        s1 = tmp_db.get_or_create_student("Carol")
        s2 = tmp_db.get_or_create_student("Carol")
        assert s1.id == s2.id


# ---------------------------------------------------------------------------
# Progress CRUD
# ---------------------------------------------------------------------------


class TestProgressCRUD:
    def test_update_creates_then_updates(self, tmp_db: Database, sample_student: Student) -> None:
        sid = sample_student.id

        # First update creates the record
        progress = tmp_db.update_progress(sid, "m1", "l1", status="in_progress")
        assert progress.status == "in_progress"
        assert progress.started_at is not None

        # Second update modifies it
        progress = tmp_db.update_progress(sid, "m1", "l1", status="completed")
        assert progress.status == "completed"
        assert progress.completed_at is not None

    def test_get_progress(self, tmp_db: Database, sample_student: Student) -> None:
        sid = sample_student.id
        assert tmp_db.get_progress(sid, "m1", "l1") is None

        tmp_db.update_progress(sid, "m1", "l1", status="in_progress")
        p = tmp_db.get_progress(sid, "m1", "l1")
        assert p is not None
        assert p.status == "in_progress"

    def test_get_all_progress(self, tmp_db: Database, sample_student: Student) -> None:
        sid = sample_student.id
        tmp_db.update_progress(sid, "m1", "l1", status="in_progress")
        tmp_db.update_progress(sid, "m1", "l2", status="completed")

        all_p = tmp_db.get_all_progress(sid)
        assert len(all_p) == 2

    def test_update_notes(self, tmp_db: Database, sample_student: Student) -> None:
        sid = sample_student.id
        tmp_db.update_progress(sid, "m1", "l1", status="in_progress")
        tmp_db.update_progress(sid, "m1", "l1", notes="My first note")

        p = tmp_db.get_progress(sid, "m1", "l1")
        assert p is not None
        assert p.notes == "My first note"

    def test_reset_progress(self, tmp_db: Database, sample_student: Student) -> None:
        sid = sample_student.id
        tmp_db.update_progress(sid, "m1", "l1", status="completed")
        assert len(tmp_db.get_all_progress(sid)) == 1

        tmp_db.reset_progress(sid)
        assert len(tmp_db.get_all_progress(sid)) == 0


# ---------------------------------------------------------------------------
# Message storage / retrieval
# ---------------------------------------------------------------------------


class TestMessageStorage:
    def test_save_and_get(self, tmp_db: Database, sample_student: Student) -> None:
        sid = sample_student.id
        session = "sess-001"

        msg1 = ConversationMessage(student_id=sid, session_id=session, role="user", content="Hello")
        msg2 = ConversationMessage(student_id=sid, session_id=session, role="assistant", content="Hi there!")

        tmp_db.save_message(msg1)
        tmp_db.save_message(msg2)

        messages = tmp_db.get_messages(session)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"

    def test_get_messages_respects_limit(self, tmp_db: Database, sample_student: Student) -> None:
        sid = sample_student.id
        session = "sess-002"

        for i in range(10):
            tmp_db.save_message(
                ConversationMessage(student_id=sid, session_id=session, role="user", content=f"msg {i}")
            )

        messages = tmp_db.get_messages(session, limit=3)
        assert len(messages) == 3

    def test_token_count_stored(self, tmp_db: Database, sample_student: Student) -> None:
        sid = sample_student.id
        session = "sess-003"
        msg = ConversationMessage(
            student_id=sid, session_id=session, role="assistant", content="response", token_count=150
        )
        tmp_db.save_message(msg)

        messages = tmp_db.get_messages(session)
        assert messages[0].token_count == 150
