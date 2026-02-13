"""YAML-based curriculum loader with Pydantic validation."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from learning_bot.curriculum.models import Curriculum, Lesson, Module

logger = logging.getLogger(__name__)


class CurriculumLoadError(Exception):
    """Raised when curriculum files cannot be loaded or validated."""


class CurriculumLoader:
    """Loads a curriculum from a directory of YAML files.

    Expected layout::

        curriculum/
            _trading_company.yaml   # manifest
            01_initial_setup/
                01_company_setup.yaml
                02_fiscal_year.yaml
            02_chart_of_accounts/
                01_coa_overview.yaml
                ...
    """

    def load_curriculum(
        self,
        curriculum_dir: str | Path,
        manifest_file: str = "_trading_company.yaml",
    ) -> Curriculum:
        """Load and validate an entire curriculum from *curriculum_dir*.

        Parameters
        ----------
        curriculum_dir:
            Root directory containing the manifest and module sub-directories.
        manifest_file:
            Name of the YAML manifest inside *curriculum_dir*.

        Returns
        -------
        Curriculum
            A fully validated curriculum object.
        """
        curriculum_dir = Path(curriculum_dir)
        manifest_path = curriculum_dir / manifest_file

        if not manifest_path.exists():
            raise CurriculumLoadError(
                f"Manifest not found: {manifest_path}"
            )

        raw_manifest = self._read_yaml(manifest_path)
        if not isinstance(raw_manifest, dict):
            raise CurriculumLoadError(
                f"Manifest must be a YAML mapping, got {type(raw_manifest).__name__}"
            )

        modules = self._load_modules(curriculum_dir, raw_manifest)
        raw_manifest["modules"] = modules

        try:
            return Curriculum.model_validate(raw_manifest)
        except ValidationError as exc:
            raise CurriculumLoadError(
                f"Curriculum validation failed:\n{exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_modules(
        self, curriculum_dir: Path, manifest: dict
    ) -> list[dict]:
        """Load module directories listed in the manifest."""
        raw_modules: list[dict] = manifest.get("modules", [])
        loaded: list[dict] = []

        for mod_entry in raw_modules:
            mod_dir_name = mod_entry.get("directory") or mod_entry.get("dir")
            if not mod_dir_name:
                raise CurriculumLoadError(
                    f"Module entry missing 'directory' or 'dir' key: {mod_entry}"
                )

            mod_dir = curriculum_dir / mod_dir_name
            if not mod_dir.is_dir():
                raise CurriculumLoadError(
                    f"Module directory not found: {mod_dir}"
                )

            lessons = self._load_lessons(mod_dir)
            mod_data = {k: v for k, v in mod_entry.items() if k not in ("directory", "dir")}
            mod_data["lessons"] = lessons
            loaded.append(mod_data)

        return loaded

    def _load_lessons(self, module_dir: Path) -> list[dict]:
        """Load all lesson YAML files from a module directory, sorted by name."""
        yaml_files = sorted(module_dir.glob("*.yaml"))
        if not yaml_files:
            logger.warning("No lesson files found in %s", module_dir)
            return []

        lessons: list[dict] = []
        for path in yaml_files:
            raw = self._read_yaml(path)
            if not isinstance(raw, dict):
                raise CurriculumLoadError(
                    f"Lesson file must be a YAML mapping: {path}"
                )
            try:
                lesson = Lesson.model_validate(raw)
            except ValidationError as exc:
                raise CurriculumLoadError(
                    f"Lesson validation failed in {path}:\n{exc}"
                ) from exc
            lessons.append(lesson.model_dump())
        return lessons

    @staticmethod
    def _read_yaml(path: Path) -> dict | list | None:
        """Read and parse a single YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise CurriculumLoadError(
                f"YAML parse error in {path}: {exc}"
            ) from exc
        except OSError as exc:
            raise CurriculumLoadError(
                f"Cannot read {path}: {exc}"
            ) from exc
