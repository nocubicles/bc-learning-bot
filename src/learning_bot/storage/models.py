"""Data models for the storage layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


@dataclass
class Student:
    name: str
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_utcnow)
    preferences: dict = field(default_factory=dict)


@dataclass
class LessonProgress:
    student_id: str
    module_id: str
    lesson_id: str
    id: str = field(default_factory=_new_id)
    status: str = "not_started"  # not_started | in_progress | validated | completed
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str = ""


@dataclass
class ConversationMessage:
    student_id: str
    session_id: str
    role: str  # user | assistant | system
    content: str
    id: str = field(default_factory=_new_id)
    timestamp: datetime = field(default_factory=_utcnow)
    token_count: int = 0
