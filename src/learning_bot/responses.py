"""Structured response types for decoupling agent logic from presentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResponseType(str, Enum):
    """Types of responses the agent can produce."""

    ASSISTANT = "assistant"
    INFO = "info"
    SUCCESS = "success"
    ERROR = "error"
    HINT = "hint"
    STATUS = "status"
    EXPORT = "export"
    NOTES = "notes"
    HELP = "help"
    QUIT = "quit"


@dataclass
class ChatResponse:
    """Structured response from the agent, renderable by any frontend."""

    type: ResponseType
    content: str = ""
    status_table: list[dict] | None = None
    stats: dict | None = None
    current_module: str | None = None
    current_lesson: str | None = None
    export_format: str | None = None
    commands: list[dict] | None = None
    token_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict."""
        d: dict = {"type": self.type.value, "content": self.content}
        if self.status_table is not None:
            d["status_table"] = self.status_table
        if self.stats is not None:
            d["stats"] = self.stats
        if self.current_module is not None:
            d["current_module"] = self.current_module
        if self.current_lesson is not None:
            d["current_lesson"] = self.current_lesson
        if self.export_format is not None:
            d["export_format"] = self.export_format
        if self.commands is not None:
            d["commands"] = self.commands
        if self.token_count:
            d["token_count"] = self.token_count
        if self.input_tokens:
            d["input_tokens"] = self.input_tokens
        if self.output_tokens:
            d["output_tokens"] = self.output_tokens
        return d
