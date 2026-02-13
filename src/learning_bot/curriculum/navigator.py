"""Curriculum navigation — lookups, ordering, prerequisite checks."""

from __future__ import annotations

from learning_bot.curriculum.models import Curriculum, Lesson, Module


def _get(obj, key: str):
    """Get attribute from dict or object."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


class CurriculumNavigator:
    """Provides lookup and traversal over a loaded :class:`Curriculum`."""

    def __init__(self, curriculum: Curriculum) -> None:
        self.curriculum = curriculum
        # Build indexes for fast lookup
        self._modules: dict[str, Module] = {m.id: m for m in curriculum.modules}
        self._lessons: dict[tuple[str, str], Lesson] = {}
        for module in curriculum.modules:
            for lesson in module.lessons:
                self._lessons[(module.id, lesson.id)] = lesson

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_module(self, module_id: str) -> Module:
        """Return a module by id, or raise ``KeyError``."""
        try:
            return self._modules[module_id]
        except KeyError:
            raise KeyError(f"Module not found: {module_id!r}")

    def get_lesson(self, module_id: str, lesson_id: str) -> Lesson:
        """Return a lesson by (module_id, lesson_id), or raise ``KeyError``."""
        try:
            return self._lessons[(module_id, lesson_id)]
        except KeyError:
            raise KeyError(
                f"Lesson not found: module={module_id!r}, lesson={lesson_id!r}"
            )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def get_current_lesson(
        self, progress_list: list,
    ) -> tuple[Module, Lesson] | None:
        """Return the first incomplete lesson based on *progress_list*.

        *progress_list* is a list of objects or dicts with ``module_id``,
        ``lesson_id``, ``status``.  A lesson is considered complete when
        its status is ``"completed"``.

        Returns ``None`` when the entire curriculum is finished.
        """
        completed = {
            (_get(p, "module_id"), _get(p, "lesson_id"))
            for p in progress_list
            if _get(p, "status") == "completed"
        }
        for module in self.curriculum.modules:
            for lesson in module.lessons:
                if (module.id, lesson.id) not in completed:
                    return module, lesson
        return None

    def get_next_lesson(
        self, module_id: str, lesson_id: str
    ) -> tuple[Module, Lesson] | None:
        """Return the lesson after the one identified by the ids.

        Searches within the same module first, then moves to the next
        module.  Returns ``None`` if the given lesson is the very last.
        """
        found = False
        for module in self.curriculum.modules:
            for lesson in module.lessons:
                if found:
                    return module, lesson
                if module.id == module_id and lesson.id == lesson_id:
                    found = True
        return None

    # ------------------------------------------------------------------
    # Prerequisites
    # ------------------------------------------------------------------

    def check_prerequisites(
        self, lesson: Lesson, progress_list: list,
    ) -> bool:
        """Return ``True`` if all prerequisites for *lesson* are met.

        Prerequisites are stored as lesson ids.  We check that each one
        appears in *progress_list* with status ``"completed"``.
        """
        if not lesson.prerequisites:
            return True
        completed_ids = {
            _get(p, "lesson_id")
            for p in progress_list
            if _get(p, "status") == "completed"
        }
        return all(pre in completed_ids for pre in lesson.prerequisites)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_progress_summary(self, progress_list: list) -> dict:
        """Return an overview dict with completion stats.

        Keys: ``total_lessons``, ``completed``, ``in_progress``,
        ``not_started``, ``percent_complete``, ``current_module``,
        ``current_lesson``.
        """
        total = sum(len(m.lessons) for m in self.curriculum.modules)
        completed = sum(
            1 for p in progress_list if _get(p, "status") == "completed"
        )
        in_progress = sum(
            1 for p in progress_list if _get(p, "status") == "in_progress"
        )
        not_started = total - completed - in_progress

        current = self.get_current_lesson(progress_list)
        current_module = current[0].title if current else None
        current_lesson = current[1].title if current else None

        return {
            "total_lessons": total,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": max(not_started, 0),
            "percent_complete": round(completed / total * 100, 1) if total else 0.0,
            "current_module": current_module,
            "current_lesson": current_lesson,
        }
