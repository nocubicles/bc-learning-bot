"""Simple validation engine for checking student answers against expected values."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Outcome of a student-answer check."""

    is_correct: bool
    feedback: str
    confidence: float  # 0.0 – 1.0


class ValidationEngine:
    """Check student answers using fuzzy keyword / substring matching.

    This does **not** call the Claude API — it relies entirely on simple
    string heuristics so it can run offline and cheaply.
    """

    def check_answer(
        self,
        student_answer: str,
        expected_answer: str,
        hints: list[str] | None = None,
    ) -> ValidationResult:
        """Compare *student_answer* to *expected_answer*.

        Strategy:
        1. Normalise both strings (lowercase, strip).
        2. Exact match → correct with confidence 1.0.
        3. Expected contained in student answer → correct, 0.9.
        4. Student answer contained in expected → correct, 0.8.
        5. Keyword overlap ≥ 60 % of expected keywords → correct, 0.7.
        6. Otherwise → incorrect.
        """
        if hints is None:
            hints = []

        norm_student = student_answer.strip().lower()
        norm_expected = expected_answer.strip().lower()

        # Exact match
        if norm_student == norm_expected:
            return ValidationResult(
                is_correct=True,
                feedback="Correct!",
                confidence=1.0,
            )

        # Expected is a substring of the student answer
        if norm_expected in norm_student:
            return ValidationResult(
                is_correct=True,
                feedback="Correct!",
                confidence=0.9,
            )

        # Student answer is a substring of expected
        if norm_student and norm_student in norm_expected:
            return ValidationResult(
                is_correct=True,
                feedback="Correct — though a bit brief.",
                confidence=0.8,
            )

        # Keyword overlap
        expected_keywords = set(self._extract_keywords(norm_expected))
        student_keywords = set(self._extract_keywords(norm_student))

        if expected_keywords:
            overlap = expected_keywords & student_keywords
            ratio = len(overlap) / len(expected_keywords)
            if ratio >= 0.6:
                return ValidationResult(
                    is_correct=True,
                    feedback="Looks correct!",
                    confidence=round(0.5 + ratio * 0.2, 2),
                )

        # Not matched
        hint_text = ""
        if hints:
            hint_text = f" Hint: {hints[0]}"
        return ValidationResult(
            is_correct=False,
            feedback=f"Not quite.{hint_text}",
            confidence=0.0,
        )

    def get_next_hint(
        self, hints: list[str], hints_given: int
    ) -> str | None:
        """Return the next hint, cycling through the list.

        Returns ``None`` when *hints* is empty.
        """
        if not hints:
            return None
        idx = hints_given % len(hints)
        return hints[idx]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Split text into meaningful keywords (drop very short words)."""
        return [w for w in text.split() if len(w) > 2]
