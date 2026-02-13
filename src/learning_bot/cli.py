"""Typer CLI application: start, status, jump, reset, web commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from learning_bot import config
from learning_bot.renderer import (
    print_completion_stats,
    print_error,
    print_info,
    print_status_table,
    print_success,
    print_welcome,
)

app = typer.Typer(
    name="bcbot",
    help="BC Learning Bot — Learn Business Central implementation with a senior consultant AI.",
    no_args_is_help=True,
)
console = Console()


def _setup_log() -> None:
    """Initialise structured logging (idempotent)."""
    from learning_bot.logging_config import setup_logging

    setup_logging()


def _init_components(student_name: str):
    """Initialize all components and return (db, student, session_id, nav, progress)."""
    from learning_bot.curriculum.loader import CurriculumLoader
    from learning_bot.curriculum.navigator import CurriculumNavigator
    from learning_bot.progress import ProgressTracker
    from learning_bot.session import SessionManager
    from learning_bot.storage.database import Database

    # Database
    config.DB_DIR.mkdir(parents=True, exist_ok=True)
    db = Database(config.DB_PATH)
    db.init_db()

    # Session
    session_mgr = SessionManager(db)
    session_info = session_mgr.start_session(student_name)
    student = db.get_student(session_info.student_id)
    session_id = session_info.session_id

    # Curriculum
    nav = None
    try:
        loader = CurriculumLoader()
        curriculum = loader.load_curriculum(config.CURRICULUM_DIR, config.DEFAULT_CURRICULUM)
        nav = CurriculumNavigator(curriculum)
    except Exception as e:
        print_info(f"Curriculum not loaded: {e}. Running in free-chat mode.")

    # Progress
    progress = ProgressTracker(db) if nav else None

    return db, student, session_id, nav, progress


@app.command()
def start(
    name: str = typer.Option(config.DEFAULT_STUDENT_NAME, "--name", "-n", help="Your name"),
) -> None:
    """Start a learning session with Rainer, your BC consultant."""
    _setup_log()
    if not config.ANTHROPIC_API_KEY:
        print_error(
            "ANTHROPIC_API_KEY not set. Create a .env file or set the environment variable.\n"
            "See .env.example for reference."
        )
        raise typer.Exit(1)

    db, student, session_id, nav, progress = _init_components(name)

    print_welcome(student.name)

    from learning_bot.agent import Agent

    agent = Agent(
        db=db,
        student_id=student.id,
        student_name=student.name,
        session_id=session_id,
        curriculum_nav=nav,
        progress_tracker=progress,
    )
    agent.start()


@app.command()
def status(
    name: str = typer.Option(config.DEFAULT_STUDENT_NAME, "--name", "-n", help="Student name"),
) -> None:
    """Show your learning progress."""
    _setup_log()
    db, student, _, nav, progress = _init_components(name)

    if not nav or not progress:
        print_info("No curriculum loaded.")
        raise typer.Exit(1)

    all_progress = progress.get_all_progress(student.id)
    stats = nav.get_progress_summary(all_progress)

    table_data = []
    for module in nav.curriculum.modules:
        for lesson in module.lessons:
            lesson_status = "not_started"
            for p in all_progress:
                if p.module_id == module.id and p.lesson_id == lesson.id:
                    lesson_status = p.status
                    break
            table_data.append({
                "module_id": module.id,
                "module_title": module.title,
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "status": lesson_status,
            })

    current = nav.get_current_lesson(all_progress)
    current_mod = current[0].id if current else None
    current_les = current[1].id if current else None

    print_status_table(table_data, current_mod, current_les)
    print_completion_stats(stats)


@app.command()
def jump(
    lesson: str = typer.Argument(help="Lesson ID to jump to (e.g., 'create_company')"),
    name: str = typer.Option(config.DEFAULT_STUDENT_NAME, "--name", "-n", help="Student name"),
) -> None:
    """Jump to a specific lesson."""
    _setup_log()
    db, student, _, nav, progress = _init_components(name)

    if not nav or not progress:
        print_error("No curriculum loaded.")
        raise typer.Exit(1)

    # Find the lesson
    found = False
    for module in nav.curriculum.modules:
        for les in module.lessons:
            if les.id == lesson:
                progress.start_lesson(student.id, module.id, les.id)
                print_success(f"Jumped to: {module.title} → {les.title}")
                found = True
                break
        if found:
            break

    if not found:
        print_error(f"Lesson '{lesson}' not found. Use 'bcbot status' to see available lessons.")
        raise typer.Exit(1)


@app.command()
def reset(
    name: str = typer.Option(config.DEFAULT_STUDENT_NAME, "--name", "-n", help="Student name"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Reset all progress."""
    _setup_log()
    if not confirm:
        confirm = typer.confirm("This will reset all your progress. Are you sure?")
        if not confirm:
            print_info("Cancelled.")
            raise typer.Exit()

    db, student, _, nav, progress = _init_components(name)
    if progress:
        progress.reset_progress(student.id)
    print_success("Progress has been reset.")


@app.command()
def web(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run the web server on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
) -> None:
    """Launch the web interface."""
    _setup_log()
    if not config.ANTHROPIC_API_KEY:
        print_error(
            "ANTHROPIC_API_KEY not set. Create a .env file or set the environment variable.\n"
            "See .env.example for reference."
        )
        raise typer.Exit(1)

    try:
        import uvicorn
    except ImportError:
        print_error(
            "Web dependencies not installed. Run:\n"
            "  pip install 'learning-bot[web]'\n"
            "or:\n"
            "  pip install fastapi uvicorn[standard]"
        )
        raise typer.Exit(1)

    print_info(f"Starting web interface at http://{host}:{port}")
    uvicorn.run("learning_bot.web:app", host=host, port=port, log_level="info")
