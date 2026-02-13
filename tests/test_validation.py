"""Tests for learning_bot.validation.ValidationEngine."""

from __future__ import annotations

from learning_bot.validation import ValidationEngine, ValidationResult


class TestExactMatch:
    def test_exact_match(self) -> None:
        engine = ValidationEngine()
        result = engine.check_answer("42", "42", [])
        assert result.is_correct is True
        assert result.confidence == 1.0

    def test_exact_match_with_whitespace(self) -> None:
        engine = ValidationEngine()
        result = engine.check_answer("  42  ", "42", [])
        assert result.is_correct is True
        assert result.confidence == 1.0


class TestFuzzyMatch:
    def test_case_insensitive(self) -> None:
        engine = ValidationEngine()
        result = engine.check_answer("Nordic Traders ApS", "nordic traders aps", [])
        assert result.is_correct is True

    def test_student_answer_contains_expected(self) -> None:
        engine = ValidationEngine()
        result = engine.check_answer(
            "I see Nordic Traders ApS in the list",
            "Nordic Traders ApS",
            [],
        )
        assert result.is_correct is True
        assert result.confidence >= 0.8


class TestKeywordMatching:
    def test_keyword_overlap_passes(self) -> None:
        engine = ValidationEngine()
        result = engine.check_answer(
            "Create New with No Data option selected",
            "Create New - No Data",
            [],
        )
        assert result.is_correct is True

    def test_no_overlap_fails(self) -> None:
        engine = ValidationEngine()
        result = engine.check_answer("something else entirely", "Create New - No Data", [])
        assert result.is_correct is False

    def test_feedback_includes_hint_on_failure(self) -> None:
        engine = ValidationEngine()
        result = engine.check_answer("wrong", "right", ["Try again!"])
        assert result.is_correct is False
        assert "Try again!" in result.feedback


class TestHintCycling:
    def test_first_hint(self) -> None:
        engine = ValidationEngine()
        hints = ["Hint 1", "Hint 2", "Hint 3"]
        assert engine.get_next_hint(hints, 0) == "Hint 1"

    def test_second_hint(self) -> None:
        engine = ValidationEngine()
        hints = ["Hint 1", "Hint 2", "Hint 3"]
        assert engine.get_next_hint(hints, 1) == "Hint 2"

    def test_wraps_around(self) -> None:
        engine = ValidationEngine()
        hints = ["Hint 1", "Hint 2"]
        assert engine.get_next_hint(hints, 2) == "Hint 1"
        assert engine.get_next_hint(hints, 3) == "Hint 2"

    def test_empty_hints_returns_none(self) -> None:
        engine = ValidationEngine()
        assert engine.get_next_hint([], 0) is None
