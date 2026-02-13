"""Shared test fixtures for the BC Learning Bot test suite."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from learning_bot.curriculum.models import (
    Curriculum,
    Lesson,
    Module,
    Task,
    ValidationQuestion,
)
from learning_bot.storage.database import Database
from learning_bot.storage.models import Student


# ---------------------------------------------------------------------------
# Temp database
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path: Path) -> Database:
    """Return an initialised Database backed by a temp file."""
    db = Database(tmp_path / "test.db")
    db.init_db()
    return db


# ---------------------------------------------------------------------------
# Sample student
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_student(tmp_db: Database) -> Student:
    """Create and return a persisted Student row."""
    student = Student(name="TestStudent")
    tmp_db.create_student(student)
    return student


# ---------------------------------------------------------------------------
# Sample (small) curriculum — 1 module, 2 lessons
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_curriculum() -> Curriculum:
    """Return a minimal Curriculum with 1 module and 2 lessons."""
    return Curriculum(
        id="test_curriculum",
        title="Test Curriculum",
        description="A tiny curriculum for unit tests.",
        company_name="Test Corp",
        modules=[
            Module(
                id="mod1",
                title="Module One",
                description="First module.",
                order=1,
                lessons=[
                    Lesson(
                        id="lesson_a",
                        title="Lesson A",
                        objectives=["Learn A"],
                        prerequisites=[],
                        tasks=[
                            Task(
                                id="task_a1",
                                title="Task A1",
                                instructions="Do task A1.",
                                config_data={"key": "value"},
                                validation_questions=[
                                    ValidationQuestion(
                                        question="What is the answer?",
                                        expected_answer="42",
                                        hints=["Think about the meaning of life."],
                                    )
                                ],
                            )
                        ],
                        validation_questions=[],
                        agent_context="Context for lesson A.",
                        estimated_duration="10 minutes",
                    ),
                    Lesson(
                        id="lesson_b",
                        title="Lesson B",
                        objectives=["Learn B"],
                        prerequisites=["lesson_a"],
                        tasks=[
                            Task(
                                id="task_b1",
                                title="Task B1",
                                instructions="Do task B1.",
                            )
                        ],
                        validation_questions=[],
                        agent_context="",
                        estimated_duration="5 minutes",
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Curriculum YAML fixtures (for loader tests)
# ---------------------------------------------------------------------------

@pytest.fixture()
def curriculum_dir(tmp_path: Path) -> Path:
    """Write a minimal valid curriculum to *tmp_path* and return the path."""
    manifest = tmp_path / "_trading_company.yaml"
    manifest.write_text(
        "id: test_curriculum\n"
        "title: Test Curriculum\n"
        "description: A tiny curriculum.\n"
        "company_name: Test Corp\n"
        "modules:\n"
        "  - dir: mod1\n"
        "    id: mod1\n"
        "    title: Module One\n"
        "    description: First module.\n"
        "    order: 1\n",
        encoding="utf-8",
    )

    mod_dir = tmp_path / "mod1"
    mod_dir.mkdir()
    lesson_file = mod_dir / "01_lesson_a.yaml"
    lesson_file.write_text(
        "id: lesson_a\n"
        "title: Lesson A\n"
        "objectives:\n"
        "  - Learn A\n"
        "prerequisites: []\n"
        "tasks:\n"
        "  - id: task_a1\n"
        "    title: Task A1\n"
        "    instructions: Do task A1.\n"
        "    validation_questions:\n"
        "      - question: What is the answer?\n"
        "        expected_answer: '42'\n"
        "        hints:\n"
        "          - Think about the meaning of life.\n"
        "validation_questions: []\n"
        "agent_context: Context for lesson A.\n"
        "estimated_duration: 10 minutes\n",
        encoding="utf-8",
    )

    lesson_file_b = mod_dir / "02_lesson_b.yaml"
    lesson_file_b.write_text(
        "id: lesson_b\n"
        "title: Lesson B\n"
        "objectives:\n"
        "  - Learn B\n"
        "prerequisites:\n"
        "  - lesson_a\n"
        "tasks:\n"
        "  - id: task_b1\n"
        "    title: Task B1\n"
        "    instructions: Do task B1.\n"
        "validation_questions: []\n"
        "agent_context: ''\n"
        "estimated_duration: 5 minutes\n",
        encoding="utf-8",
    )

    return tmp_path
