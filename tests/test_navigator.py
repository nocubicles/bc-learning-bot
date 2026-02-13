"""Tests for learning_bot.curriculum.navigator.CurriculumNavigator."""

from __future__ import annotations

import pytest

from learning_bot.curriculum.models import Curriculum
from learning_bot.curriculum.navigator import CurriculumNavigator


@pytest.fixture()
def nav(sample_curriculum: Curriculum) -> CurriculumNavigator:
    return CurriculumNavigator(sample_curriculum)


class TestGetCurrentLesson:
    def test_no_progress_returns_first_lesson(self, nav: CurriculumNavigator) -> None:
        result = nav.get_current_lesson([])
        assert result is not None
        module, lesson = result
        assert module.id == "mod1"
        assert lesson.id == "lesson_a"

    def test_first_completed_returns_second(self, nav: CurriculumNavigator) -> None:
        progress = [
            {"module_id": "mod1", "lesson_id": "lesson_a", "status": "completed"},
        ]
        result = nav.get_current_lesson(progress)
        assert result is not None
        _, lesson = result
        assert lesson.id == "lesson_b"

    def test_all_completed_returns_none(self, nav: CurriculumNavigator) -> None:
        progress = [
            {"module_id": "mod1", "lesson_id": "lesson_a", "status": "completed"},
            {"module_id": "mod1", "lesson_id": "lesson_b", "status": "completed"},
        ]
        result = nav.get_current_lesson(progress)
        assert result is None


class TestGetNextLesson:
    def test_next_after_first(self, nav: CurriculumNavigator) -> None:
        result = nav.get_next_lesson("mod1", "lesson_a")
        assert result is not None
        _, lesson = result
        assert lesson.id == "lesson_b"

    def test_next_after_last_is_none(self, nav: CurriculumNavigator) -> None:
        result = nav.get_next_lesson("mod1", "lesson_b")
        assert result is None


class TestCheckPrerequisites:
    def test_no_prerequisites_returns_true(self, nav: CurriculumNavigator) -> None:
        lesson_a = nav.get_lesson("mod1", "lesson_a")
        assert nav.check_prerequisites(lesson_a, []) is True

    def test_unmet_prerequisite_returns_false(self, nav: CurriculumNavigator) -> None:
        lesson_b = nav.get_lesson("mod1", "lesson_b")
        assert nav.check_prerequisites(lesson_b, []) is False

    def test_met_prerequisite_returns_true(self, nav: CurriculumNavigator) -> None:
        lesson_b = nav.get_lesson("mod1", "lesson_b")
        progress = [
            {"module_id": "mod1", "lesson_id": "lesson_a", "status": "completed"},
        ]
        assert nav.check_prerequisites(lesson_b, progress) is True


class TestGetProgressSummary:
    def test_empty_progress(self, nav: CurriculumNavigator) -> None:
        stats = nav.get_progress_summary([])
        assert stats["total_lessons"] == 2
        assert stats["completed"] == 0
        assert stats["percent_complete"] == 0.0

    def test_partial_progress(self, nav: CurriculumNavigator) -> None:
        progress = [
            {"module_id": "mod1", "lesson_id": "lesson_a", "status": "completed"},
        ]
        stats = nav.get_progress_summary(progress)
        assert stats["completed"] == 1
        assert stats["percent_complete"] == 50.0
