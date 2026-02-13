"""Pydantic v2 models for the BC Learning Bot curriculum."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ValidationQuestion(BaseModel):
    """A question used to verify the student completed a task correctly."""

    question: str
    expected_answer: str
    hints: list[str] = Field(default_factory=list)


class Task(BaseModel):
    """A single hands-on task within a lesson."""

    id: str
    title: str
    instructions: str
    config_data: dict = Field(default_factory=dict)
    validation_questions: list[ValidationQuestion] = Field(default_factory=list)


class Lesson(BaseModel):
    """A lesson containing one or more tasks."""

    id: str
    title: str
    objectives: list[str]
    prerequisites: list[str] = Field(default_factory=list)
    tasks: list[Task]
    validation_questions: list[ValidationQuestion] = Field(default_factory=list)
    agent_context: str = ""
    estimated_duration: str = ""


class Module(BaseModel):
    """A module grouping related lessons in order."""

    id: str
    title: str
    description: str = ""
    order: int
    lessons: list[Lesson]


class Curriculum(BaseModel):
    """Top-level curriculum definition."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    description: str
    company_name: str
    modules: list[Module]
