"""Application configuration and paths."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CURRICULUM_DIR = PROJECT_ROOT / "curriculum"
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Database
DB_DIR = Path(os.getenv("BCBOT_DB_DIR", Path.home() / ".bcbot"))
DB_PATH = Path(os.getenv("BCBOT_DB_PATH", DB_DIR / "learning_bot.db"))

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("BCBOT_MODEL", "claude-sonnet-4-5-20250929")
MAX_TOKENS = int(os.getenv("BCBOT_MAX_TOKENS", "4096"))

# Conversation window
MAX_CONTEXT_TOKENS = 30_000  # sliding window target
SUMMARY_RESERVE_TOKENS = 2_000  # reserved for progress summary in prompt

# Defaults
DEFAULT_STUDENT_NAME = "Student"
DEFAULT_CURRICULUM = "_trading_company.yaml"
