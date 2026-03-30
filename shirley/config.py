import os
from pathlib import Path
from dotenv import load_dotenv

# Load from secure vault first, then fall back to local .env
_VAULT = Path.home() / ".comedy-factory" / ".env"
_LOCAL = Path(__file__).parent / ".env"

load_dotenv(_VAULT)
load_dotenv(_LOCAL, override=False)

# --- API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Claude Model ---
CLAUDE_MODEL = "claude-sonnet-4-6"

# --- Paths ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TASKS_FILE = DATA_DIR / "tasks.json"
SCHEDULE_DIR = DATA_DIR / "schedule"
NOTES_DIR = DATA_DIR / "notes"
HISTORY_FILE = DATA_DIR / "history.json"
COMEDY_FACTORY_DIR = BASE_DIR.parent / "comedy-factory"

# --- Settings ---
MAX_HISTORY_TURNS = 20
TIMEZONE = os.getenv("SHIRLEY_TIMEZONE", "UTC")

# --- Retry Settings ---
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]


def ensure_data_dirs():
    """Create data directories on first run."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCHEDULE_DIR.mkdir(exist_ok=True)
    NOTES_DIR.mkdir(exist_ok=True)
