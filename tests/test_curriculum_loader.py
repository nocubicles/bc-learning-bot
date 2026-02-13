"""Tests for learning_bot.curriculum.loader.CurriculumLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from learning_bot.curriculum.loader import CurriculumLoadError, CurriculumLoader


class TestLoadValidCurriculum:
    def test_loads_successfully(self, curriculum_dir: Path) -> None:
        loader = CurriculumLoader()
        curriculum = loader.load_curriculum(curriculum_dir, "_trading_company.yaml")

        assert curriculum.id == "test_curriculum"
        assert len(curriculum.modules) == 1
        assert curriculum.modules[0].id == "mod1"
        assert len(curriculum.modules[0].lessons) == 2

    def test_lesson_fields(self, curriculum_dir: Path) -> None:
        loader = CurriculumLoader()
        curriculum = loader.load_curriculum(curriculum_dir, "_trading_company.yaml")
        lesson_a = curriculum.modules[0].lessons[0]

        assert lesson_a.id == "lesson_a"
        assert lesson_a.title == "Lesson A"
        assert lesson_a.objectives == ["Learn A"]
        assert len(lesson_a.tasks) == 1
        assert lesson_a.tasks[0].validation_questions[0].expected_answer == "42"


class TestLoadMissingFile:
    def test_missing_manifest_raises(self, tmp_path: Path) -> None:
        loader = CurriculumLoader()
        with pytest.raises(CurriculumLoadError, match="Manifest not found"):
            loader.load_curriculum(tmp_path, "_nonexistent.yaml")

    def test_missing_module_dir_raises(self, tmp_path: Path) -> None:
        manifest = tmp_path / "_trading_company.yaml"
        manifest.write_text(
            "id: x\ntitle: X\ndescription: X\ncompany_name: X\n"
            "modules:\n  - dir: missing_dir\n    id: m\n    title: M\n    order: 1\n",
            encoding="utf-8",
        )
        loader = CurriculumLoader()
        with pytest.raises(CurriculumLoadError, match="Module directory not found"):
            loader.load_curriculum(tmp_path, "_trading_company.yaml")


class TestValidationErrors:
    def test_bad_yaml_raises(self, tmp_path: Path) -> None:
        manifest = tmp_path / "_trading_company.yaml"
        manifest.write_text(
            "id: x\ntitle: X\ndescription: X\ncompany_name: X\n"
            "modules:\n  - dir: mod\n    id: m\n    title: M\n    order: 1\n",
            encoding="utf-8",
        )
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        (mod_dir / "01_bad.yaml").write_text(
            "id: bad\ntitle: Bad\n",  # missing required fields
            encoding="utf-8",
        )
        loader = CurriculumLoader()
        with pytest.raises(CurriculumLoadError, match="validation failed"):
            loader.load_curriculum(tmp_path, "_trading_company.yaml")
