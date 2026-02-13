"""Jinja2 prompt builder for assembling the system prompt."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from learning_bot.config import PROMPTS_DIR


class PromptBuilder:
    """Assembles system prompts from Jinja2 templates."""

    def __init__(self, prompts_dir: Path = PROMPTS_DIR) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_system_prompt_parts(
        self,
        student_name: str,
        module: dict | None = None,
        lesson: dict | None = None,
        current_task: dict | None = None,
        task_index: int = 0,
        total_tasks: int = 0,
        progress_summary: dict | None = None,
    ) -> tuple[str, str]:
        """Build system prompt as (base_prompt, dynamic_prompt).

        base_prompt: stable persona text (cacheable across turns).
        dynamic_prompt: curriculum context + progress (changes per turn).
        """
        # Base persona (stable across turns)
        base_template = self.env.get_template("system_base.md.j2")
        base_prompt = base_template.render(student_name=student_name)

        # Dynamic parts
        dynamic_parts: list[str] = []

        if lesson:
            try:
                ctx_template = self.env.get_template("curriculum_context.md.j2")
                dynamic_parts.append(
                    ctx_template.render(
                        module=module or {},
                        lesson=lesson,
                        current_task=current_task,
                        task_index=task_index,
                        total_tasks=total_tasks,
                    )
                )
            except Exception:
                pass

        if progress_summary:
            try:
                prog_template = self.env.get_template("progress_context.md.j2")
                dynamic_parts.append(prog_template.render(**progress_summary))
            except Exception:
                pass

        dynamic_prompt = "\n\n---\n\n".join(dynamic_parts)
        return base_prompt, dynamic_prompt

    def build_system_prompt(
        self,
        student_name: str,
        module: dict | None = None,
        lesson: dict | None = None,
        current_task: dict | None = None,
        task_index: int = 0,
        total_tasks: int = 0,
        progress_summary: dict | None = None,
    ) -> str:
        """Build complete system prompt from templates (convenience wrapper)."""
        base, dynamic = self.build_system_prompt_parts(
            student_name=student_name,
            module=module,
            lesson=lesson,
            current_task=current_task,
            task_index=task_index,
            total_tasks=total_tasks,
            progress_summary=progress_summary,
        )
        if dynamic:
            return f"{base}\n\n---\n\n{dynamic}"
        return base

    def build_fallback_prompt(self, student_name: str) -> str:
        """Build a minimal prompt when templates aren't available."""
        return (
            f"You are Rainer, a senior Business Central consultant with 15+ years of experience. "
            f"You are patiently guiding {student_name}, a junior BC consultant, through implementing "
            f"a trading company called 'Nordic Traders ApS' in a Business Central cloud sandbox.\n\n"
            f"Be methodical, encouraging, and use proper BC terminology. Guide step-by-step. "
            f"Never do the work for the student — always explain and let them do it.\n\n"
            f"If the student asks off-topic questions, answer briefly then steer back to the curriculum.\n\n"
            f"Available slash commands the student can use:\n"
            f"/status — Show progress\n"
            f"/hint — Get a hint\n"
            f"/skip — Skip current task\n"
            f"/next — Next lesson\n"
            f"/export xml|json — Export config data\n"
            f"/notes <text> — Save a note\n"
            f"/help — Show commands\n"
            f"/quit — Exit"
        )
