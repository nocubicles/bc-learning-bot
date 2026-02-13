"""Structured logging configuration for the BC Learning Bot."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from learning_bot.config import DB_DIR


def setup_logging(verbose: bool = False) -> None:
    """Configure file and console logging.

    Parameters
    ----------
    verbose:
        When ``True`` the console handler is set to DEBUG instead of WARNING.
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    log_file = DB_DIR / "bcbot.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # File handler — DEBUG level
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler — WARNING by default, DEBUG if verbose
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Avoid duplicate handlers on repeated calls
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)
