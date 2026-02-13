"""Core agent loop: prompt assembly, Claude API calls, slash command handling."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import anthropic

from learning_bot import config
from learning_bot.persona import PromptBuilder
from learning_bot.responses import ChatResponse, ResponseType

if TYPE_CHECKING:
    from learning_bot.curriculum.loader import CurriculumLoader
    from learning_bot.curriculum.navigator import CurriculumNavigator
    from learning_bot.progress import ProgressTracker
    from learning_bot.storage.database import Database


_SLASH_COMMANDS = [
    {"command": "/status", "description": "Show your current progress"},
    {"command": "/hint", "description": "Get a hint for the current task"},
    {"command": "/skip", "description": "Skip the current task"},
    {"command": "/next", "description": "Move to the next lesson"},
    {"command": "/export xml", "description": "Export current config as RapidStart XML"},
    {"command": "/export json", "description": "Export current config as BC API JSON"},
    {"command": "/notes <text>", "description": "Save a note for the current lesson"},
    {"command": "/help", "description": "Show this help message"},
    {"command": "/quit", "description": "Exit the chat"},
]


class Agent:
    """Manages conversation with Claude, handles slash commands."""

    def __init__(
        self,
        db: Database,
        student_id: str,
        student_name: str,
        session_id: str,
        curriculum_nav: CurriculumNavigator | None = None,
        progress_tracker: ProgressTracker | None = None,
    ) -> None:
        self.db = db
        self.student_id = student_id
        self.student_name = student_name
        self.session_id = session_id
        self.nav = curriculum_nav
        self.progress = progress_tracker
        self.prompt_builder = PromptBuilder()
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.messages: list[dict] = []

    def _build_system_prompt(self) -> str:
        """Assemble the system prompt with current context."""
        module_dict = None
        lesson_dict = None
        current_task = None
        task_index = 0
        total_tasks = 0
        progress_summary = None

        if self.nav and self.progress:
            # Get current lesson from progress
            all_progress = self.progress.get_all_progress(self.student_id)
            lesson_info = self.nav.get_current_lesson(all_progress)

            if lesson_info:
                module, lesson = lesson_info
                module_dict = {
                    "id": module.id,
                    "title": module.title,
                    "description": module.description,
                }
                lesson_dict = {
                    "id": lesson.id,
                    "title": lesson.title,
                    "objectives": lesson.objectives,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "instructions": t.instructions,
                            "config_data": t.config_data,
                            "validation_questions": [
                                {"question": q.question, "expected_answer": q.expected_answer, "hints": q.hints}
                                for q in t.validation_questions
                            ],
                        }
                        for t in lesson.tasks
                    ],
                    "validation_questions": [
                        {"question": q.question, "expected_answer": q.expected_answer, "hints": q.hints}
                        for q in lesson.validation_questions
                    ],
                    "agent_context": lesson.agent_context,
                    "estimated_duration": lesson.estimated_duration,
                }
                total_tasks = len(lesson.tasks)
                if total_tasks > 0:
                    current_task = lesson_dict["tasks"][0]
                    task_index = 1

            progress_summary = self.nav.get_progress_summary(all_progress)
            progress_summary["student_name"] = self.student_name

        try:
            return self.prompt_builder.build_system_prompt(
                student_name=self.student_name,
                module=module_dict,
                lesson=lesson_dict,
                current_task=current_task,
                task_index=task_index,
                total_tasks=total_tasks,
                progress_summary=progress_summary,
            )
        except Exception:
            return self.prompt_builder.build_fallback_prompt(self.student_name)

    def _trim_messages(self) -> list[dict]:
        """Apply sliding window to keep messages under token budget."""
        # Rough estimate: 4 chars per token
        max_chars = config.MAX_CONTEXT_TOKENS * 4
        trimmed = []
        total_chars = 0

        for msg in reversed(self.messages):
            msg_chars = len(msg.get("content", ""))
            if total_chars + msg_chars > max_chars and trimmed:
                break
            trimmed.append(msg)
            total_chars += msg_chars

        return list(reversed(trimmed))

    def _load_history(self) -> None:
        """Load conversation history from database."""
        messages = self.db.get_messages(self.session_id, limit=100)
        self.messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role in ("user", "assistant")
        ]

    def chat(self, user_input: str) -> ChatResponse:
        """Process user input and return a structured ChatResponse."""
        # Check for slash commands
        if user_input.startswith("/"):
            return self._handle_slash_command(user_input)

        # Add user message
        self.messages.append({"role": "user", "content": user_input})
        from learning_bot.storage.models import ConversationMessage

        self.db.save_message(ConversationMessage(
            student_id=self.student_id,
            session_id=self.session_id,
            role="user",
            content=user_input,
        ))

        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Call Claude
        try:
            response = self.client.messages.create(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                system=system_prompt,
                messages=self._trim_messages(),
            )
            assistant_text = response.content[0].text
        except anthropic.APIError as e:
            # Remove the user message we just added since we failed
            self.messages.pop()
            return ChatResponse(type=ResponseType.ERROR, content=f"Claude API error: {e}")

        # Token counting
        token_count = 0
        if hasattr(response, "usage") and response.usage is not None:
            token_count = (
                getattr(response.usage, "input_tokens", 0)
                + getattr(response.usage, "output_tokens", 0)
            )

        # Save
        self.messages.append({"role": "assistant", "content": assistant_text})
        self.db.save_message(ConversationMessage(
            student_id=self.student_id,
            session_id=self.session_id,
            role="assistant",
            content=assistant_text,
            token_count=token_count,
        ))

        return ChatResponse(
            type=ResponseType.ASSISTANT,
            content=assistant_text,
            token_count=token_count,
        )

    def _handle_slash_command(self, command: str) -> ChatResponse:
        """Handle slash commands, returning a ChatResponse."""
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            return ChatResponse(
                type=ResponseType.HELP,
                content="Available commands:",
                commands=_SLASH_COMMANDS,
            )

        elif cmd == "/status":
            return self._cmd_status()

        elif cmd == "/hint":
            return self._cmd_hint()

        elif cmd == "/skip":
            return self._cmd_skip()

        elif cmd == "/next":
            return self._cmd_next()

        elif cmd == "/export":
            return self._cmd_export(arg.strip().lower() or "json")

        elif cmd == "/notes":
            return self._cmd_notes(arg)

        elif cmd == "/quit":
            return ChatResponse(type=ResponseType.QUIT, content="Goodbye! Your progress has been saved.")

        else:
            return ChatResponse(
                type=ResponseType.INFO,
                content=f"Unknown command: {cmd}. Type /help for available commands.",
            )

    def _cmd_status(self) -> ChatResponse:
        """Show progress status."""
        if not self.nav or not self.progress:
            return ChatResponse(type=ResponseType.INFO, content="No curriculum loaded.")

        all_progress = self.progress.get_all_progress(self.student_id)
        stats = self.nav.get_progress_summary(all_progress)

        # Build table data
        table_data = []
        for module in self.nav.curriculum.modules:
            for lesson in module.lessons:
                status = "not_started"
                for p in all_progress:
                    if p.module_id == module.id and p.lesson_id == lesson.id:
                        status = p.status
                        break
                table_data.append({
                    "module_id": module.id,
                    "module_title": module.title,
                    "lesson_id": lesson.id,
                    "lesson_title": lesson.title,
                    "status": status,
                })

        current_lesson = self.nav.get_current_lesson(all_progress)
        current_mod_id = current_lesson[0].id if current_lesson else None
        current_les_id = current_lesson[1].id if current_lesson else None

        return ChatResponse(
            type=ResponseType.STATUS,
            content="Learning Progress",
            status_table=table_data,
            stats=stats,
            current_module=current_mod_id,
            current_lesson=current_les_id,
        )

    def _cmd_hint(self) -> ChatResponse:
        """Get a hint for the current task."""
        if not self.nav or not self.progress:
            return ChatResponse(type=ResponseType.INFO, content="No curriculum loaded.")

        all_progress = self.progress.get_all_progress(self.student_id)
        lesson_info = self.nav.get_current_lesson(all_progress)
        if not lesson_info:
            return ChatResponse(type=ResponseType.INFO, content="No active lesson.")

        _, lesson = lesson_info
        # Find first task with validation questions that have hints
        for task in lesson.tasks:
            for vq in task.validation_questions:
                if vq.hints:
                    return ChatResponse(type=ResponseType.HINT, content=vq.hints[0])

        # Fall back to lesson-level hints
        for vq in lesson.validation_questions:
            if vq.hints:
                return ChatResponse(type=ResponseType.HINT, content=vq.hints[0])

        return ChatResponse(
            type=ResponseType.INFO,
            content="No hints available for this task. Try asking Rainer!",
        )

    def _cmd_skip(self) -> ChatResponse:
        """Skip the current task."""
        if not self.nav or not self.progress:
            return ChatResponse(type=ResponseType.INFO, content="No curriculum loaded.")

        all_progress = self.progress.get_all_progress(self.student_id)
        lesson_info = self.nav.get_current_lesson(all_progress)
        if not lesson_info:
            return ChatResponse(type=ResponseType.INFO, content="No active lesson to skip.")

        module, lesson = lesson_info
        self.progress.complete_lesson(self.student_id, module.id, lesson.id)

        advance_resp = self._advance_to_next()

        # Generate AI introduction for the new lesson
        intro = self.chat(
            "[The student just skipped the previous lesson. "
            "Please introduce the new current lesson and its first task.]"
        )
        intro.content = f"*Skipped: {lesson.title}*\n\n{intro.content}"
        return intro

    def _cmd_next(self) -> ChatResponse:
        """Move to next lesson, checking prerequisites on the target lesson."""
        if not self.nav or not self.progress:
            return ChatResponse(type=ResponseType.INFO, content="No curriculum loaded.")

        all_progress = self.progress.get_all_progress(self.student_id)
        lesson_info = self.nav.get_current_lesson(all_progress)
        if not lesson_info:
            return ChatResponse(type=ResponseType.INFO, content="No active lesson.")

        module, lesson = lesson_info
        self.progress.complete_lesson(self.student_id, module.id, lesson.id)

        advance_resp = self._advance_to_next(check_prerequisites=True)

        # Generate AI introduction for the new lesson
        intro = self.chat(
            "[The student just completed the previous lesson. "
            "Please introduce the new current lesson and its first task.]"
        )
        intro.content = f"*Completed: {lesson.title}*\n\n{intro.content}"
        return intro

    def _advance_to_next(self, check_prerequisites: bool = False) -> ChatResponse:
        """Advance to the next lesson and return info about it."""
        all_progress = self.progress.get_all_progress(self.student_id)
        next_info = self.nav.get_current_lesson(all_progress)
        if next_info:
            module, lesson = next_info
            if check_prerequisites and not self.nav.check_prerequisites(lesson, all_progress):
                missing = [
                    pre for pre in lesson.prerequisites
                    if pre not in {
                        getattr(p, "lesson_id", None) or (p.get("lesson_id") if isinstance(p, dict) else None)
                        for p in all_progress
                        if (getattr(p, "status", None) or (p.get("status") if isinstance(p, dict) else None)) == "completed"
                    }
                ]
                return ChatResponse(
                    type=ResponseType.INFO,
                    content=(
                        f"Prerequisites not met for '{lesson.title}'. "
                        f"Complete these lessons first: {', '.join(missing)}. "
                        f"Use /skip to override."
                    ),
                )
            self.progress.start_lesson(self.student_id, module.id, lesson.id)
            return ChatResponse(
                type=ResponseType.INFO,
                content=f"Now on: {module.title} \u2192 {lesson.title}",
            )
        else:
            return ChatResponse(
                type=ResponseType.SUCCESS,
                content="Congratulations! You've completed the entire curriculum!",
            )

    def _cmd_export(self, format_type: str) -> ChatResponse:
        """Export current lesson config data."""
        if not self.nav or not self.progress:
            return ChatResponse(type=ResponseType.INFO, content="No curriculum loaded.")

        all_progress = self.progress.get_all_progress(self.student_id)
        lesson_info = self.nav.get_current_lesson(all_progress)
        if not lesson_info:
            return ChatResponse(type=ResponseType.INFO, content="No active lesson.")

        _, lesson = lesson_info
        # Collect config data from all tasks
        config_data = {}
        for task in lesson.tasks:
            if task.config_data:
                config_data[task.id] = task.config_data

        if not config_data:
            return ChatResponse(type=ResponseType.INFO, content="No configuration data available for this lesson.")

        if format_type == "xml":
            try:
                from learning_bot.generators.rapidstart import RapidStartGenerator

                gen = RapidStartGenerator()
                xml_output = gen.generate_from_config_data(config_data)
                return ChatResponse(type=ResponseType.EXPORT, content=xml_output, export_format="xml")
            except ImportError:
                return ChatResponse(type=ResponseType.ERROR, content="RapidStart generator not available.")
        else:
            output = json.dumps(config_data, indent=2, ensure_ascii=False)
            return ChatResponse(type=ResponseType.EXPORT, content=output, export_format="json")

    def _cmd_notes(self, text: str) -> ChatResponse:
        """Save a note, or show all notes for the current lesson."""
        if not self.nav or not self.progress:
            if text:
                return ChatResponse(type=ResponseType.INFO, content="Note saved (no curriculum context).")
            else:
                return ChatResponse(type=ResponseType.INFO, content="No curriculum loaded.")

        all_progress = self.progress.get_all_progress(self.student_id)
        lesson_info = self.nav.get_current_lesson(all_progress)

        if not text:
            # Show notes for current lesson
            if not lesson_info:
                return ChatResponse(type=ResponseType.INFO, content="No active lesson.")
            module, lesson = lesson_info
            existing = self.db.get_progress(self.student_id, module.id, lesson.id)
            notes = existing.notes if existing else ""
            return ChatResponse(type=ResponseType.NOTES, content=notes or "")

        # Save a new note
        if lesson_info:
            module, lesson = lesson_info
            existing = self.db.get_progress(self.student_id, module.id, lesson.id)
            current_notes = existing.notes if existing else ""
            new_notes = f"{current_notes}\n- {text}".strip()
            self.db.update_progress(
                student_id=self.student_id,
                module_id=module.id,
                lesson_id=lesson.id,
                notes=new_notes,
            )
        return ChatResponse(type=ResponseType.SUCCESS, content="Note saved.")

    def initialize(self) -> ChatResponse | None:
        """Load history and auto-start first lesson. Returns a greeting response if new session."""
        self._load_history()

        # Auto-start first lesson if nothing in progress
        if self.nav and self.progress:
            all_progress = self.progress.get_all_progress(self.student_id)
            if not any(p.status in ("in_progress", "validated") for p in all_progress):
                lesson_info = self.nav.get_current_lesson(all_progress)
                if lesson_info:
                    module, lesson = lesson_info
                    if not self.nav.check_prerequisites(lesson, all_progress):
                        missing = [
                            pre for pre in lesson.prerequisites
                            if pre not in {
                                getattr(p, "lesson_id", None)
                                for p in all_progress
                                if getattr(p, "status", None) == "completed"
                            }
                        ]
                        return ChatResponse(
                            type=ResponseType.INFO,
                            content=(
                                f"Prerequisites not met for '{lesson.title}'. "
                                f"Complete these lessons first: {', '.join(missing)}. "
                                f"Use /skip to override."
                            ),
                        )
                    else:
                        self.progress.start_lesson(self.student_id, module.id, lesson.id)

        # If no history, send an initial greeting via Claude
        if not self.messages:
            return self.chat("Hello! I'm ready to start learning Business Central.")

        return None

    def start(self) -> None:
        """Start the interactive chat loop (legacy entry point for CLI)."""
        from learning_bot.renderer import get_input, print_info, print_response, print_success

        init_resp = self.initialize()
        if init_resp:
            _render_response_cli(init_resp)

        while True:
            user_input = get_input(self.student_name)
            if not user_input:
                continue

            resp = self.chat(user_input)
            if resp.type == ResponseType.QUIT:
                print_info(resp.content)
                break
            _render_response_cli(resp)


def _render_response_cli(response: ChatResponse) -> None:
    """Render a ChatResponse using the Rich CLI renderer."""
    from learning_bot.renderer import (
        print_completion_stats,
        print_error,
        print_export,
        print_hint,
        print_info,
        print_notes,
        print_response,
        print_slash_help,
        print_status_table,
        print_success,
    )

    if response.type == ResponseType.ASSISTANT:
        print_response(response.content)
    elif response.type == ResponseType.INFO:
        print_info(response.content)
    elif response.type == ResponseType.SUCCESS:
        print_success(response.content)
    elif response.type == ResponseType.ERROR:
        print_error(response.content)
    elif response.type == ResponseType.HINT:
        print_hint(response.content)
    elif response.type == ResponseType.STATUS:
        if response.status_table is not None:
            print_status_table(response.status_table, response.current_module, response.current_lesson)
        if response.stats is not None:
            print_completion_stats(response.stats)
    elif response.type == ResponseType.EXPORT:
        print_export(response.content, response.export_format or "json")
    elif response.type == ResponseType.NOTES:
        print_notes(response.content)
    elif response.type == ResponseType.HELP:
        print_slash_help()
    elif response.type == ResponseType.QUIT:
        print_info(response.content)
