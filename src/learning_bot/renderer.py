"""Rich console output for the learning bot."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_welcome(student_name: str) -> None:
    """Print welcome banner."""
    console.print(
        Panel(
            f"[bold blue]Welcome to the BC Learning Bot, {student_name}![/]\n\n"
            "I'm [bold]Rainer[/], your senior Business Central consultant.\n"
            "I'll guide you through implementing a trading company step by step.\n\n"
            "[dim]Type your message and press Enter to chat.\n"
            "Type /help for available commands, or /quit to exit.[/]",
            title="[bold]BC Learning Bot[/]",
            border_style="blue",
        )
    )


def print_response(text: str) -> None:
    """Render assistant response as markdown."""
    console.print()
    console.print(Markdown(text))
    console.print()


def print_status_table(
    progress: list[dict],
    current_module: str | None = None,
    current_lesson: str | None = None,
) -> None:
    """Print progress status table."""
    table = Table(title="Learning Progress", border_style="blue")
    table.add_column("Module", style="cyan")
    table.add_column("Lesson", style="white")
    table.add_column("Status", justify="center")

    status_icons = {
        "not_started": "[dim]Not Started[/]",
        "in_progress": "[yellow]In Progress[/]",
        "validated": "[blue]Validated[/]",
        "completed": "[green]Completed[/]",
    }

    for item in progress:
        is_current = (
            item.get("module_id") == current_module
            and item.get("lesson_id") == current_lesson
        )
        marker = " [bold yellow]◄[/]" if is_current else ""
        table.add_row(
            item.get("module_title", item.get("module_id", "")),
            item.get("lesson_title", item.get("lesson_id", "")) + marker,
            status_icons.get(item.get("status", "not_started"), item.get("status", "")),
        )

    console.print(table)


def print_completion_stats(stats: dict) -> None:
    """Print completion statistics."""
    pct = stats.get("percent_complete", stats.get("completion_percentage", 0))
    bar_filled = int(pct / 5)
    bar_empty = 20 - bar_filled
    bar = f"[green]{'█' * bar_filled}[/][dim]{'░' * bar_empty}[/]"

    total = stats.get("total_lessons", 0)
    completed = stats.get("completed", stats.get("completed_lessons", 0))

    console.print(
        Panel(
            f"Progress: {bar} {pct:.0f}%\n"
            f"Lessons: {completed}/{total}  |  "
            f"Current: {stats.get('current_module', 'N/A')} → {stats.get('current_lesson', 'N/A')}",
            title="[bold]Progress Summary[/]",
            border_style="green",
        )
    )


def print_notes(notes: str) -> None:
    """Display saved notes in a styled Rich panel."""
    if not notes or not notes.strip():
        console.print(Panel("[dim]No notes saved for this lesson yet.[/]",
                            title="[bold]Notes[/]", border_style="magenta"))
        return
    console.print(Panel(notes.strip(), title="[bold]Notes[/]", border_style="magenta"))


def print_hint(hint: str) -> None:
    """Print a hint in a styled panel."""
    console.print(Panel(hint, title="[bold yellow]Hint[/]", border_style="yellow"))


def print_export(content: str, format_type: str) -> None:
    """Print exported content."""
    lang = "xml" if format_type == "xml" else "json"
    console.print(Panel(content, title=f"[bold]Export ({format_type.upper()})[/]", border_style="cyan"))


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[bold red]Error:[/] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[blue]ℹ[/] {message}")


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/] {message}")


def print_slash_help() -> None:
    """Print available slash commands."""
    table = Table(title="Available Commands", border_style="blue")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")

    commands = [
        ("/status", "Show your current progress"),
        ("/hint", "Get a hint for the current task"),
        ("/skip", "Skip the current task"),
        ("/next", "Move to the next lesson"),
        ("/export xml", "Export current config as RapidStart XML"),
        ("/export json", "Export current config as BC API JSON"),
        ("/notes <text>", "Save a note for the current lesson"),
        ("/help", "Show this help message"),
        ("/quit", "Exit the chat"),
    ]
    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


def get_input(prompt: str = "You") -> str:
    """Get user input with styled prompt."""
    try:
        return console.input(f"[bold green]{prompt}[/] > ").strip()
    except (EOFError, KeyboardInterrupt):
        return "/quit"
