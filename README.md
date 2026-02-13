# BC Learning Bot

A senior consultant chatbot that teaches Business Central implementation step by step. Powered by Claude, it guides you through setting up a trading company — from initial setup through chart of accounts, master data, purchasing, sales, inventory, and financial reporting.

## Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

```bash
# Clone and enter the project
cd learning_bot

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package
pip install -e ".[dev]"

# Configure your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Usage

Always activate the virtual environment first:

```bash
source .venv/bin/activate
```

### CLI (terminal)

```bash
bcbot start --name "Villem"     # Start a learning session
bcbot status --name "Villem"    # View your progress
bcbot jump create_company -n "Villem"  # Jump to a specific lesson
bcbot reset --name "Villem" -y  # Reset all progress
```

Inside the chat session, use slash commands:

| Command | Description |
|---------|-------------|
| `/status` | Show your current progress |
| `/hint` | Get a hint for the current task |
| `/skip` | Skip the current task |
| `/next` | Move to the next lesson |
| `/export json` | Export current config as BC API JSON |
| `/export xml` | Export current config as RapidStart XML |
| `/notes <text>` | Save a note for the current lesson |
| `/help` | Show available commands |
| `/quit` | Exit the chat |

### Web interface

```bash
bcbot web                       # Start at http://127.0.0.1:8000
bcbot web --port 3000           # Custom port
bcbot web --host 0.0.0.0       # Expose to network
```

Open the URL in your browser, enter your name, and start learning.

## Configuration

Environment variables (set in `.env` or your shell):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `BCBOT_MODEL` | `claude-sonnet-4-5-20250929` | Claude model to use |
| `BCBOT_MAX_TOKENS` | `4096` | Max tokens per response |
| `BCBOT_DB_PATH` | `~/.bcbot/learning_bot.db` | SQLite database path |

## Running tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```
