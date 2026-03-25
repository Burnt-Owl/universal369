import os
from pathlib import Path
from dotenv import load_dotenv

# Load from secure vault first (~/.comedy-factory/.env), then fall back to local .env
_VAULT = Path.home() / ".comedy-factory" / ".env"
_LOCAL = Path(__file__).parent / ".env"

load_dotenv(_VAULT)    # secrets vault (outside repo, never committed)
load_dotenv(_LOCAL, override=False)  # local .env only fills gaps, never overwrites vault

# --- API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY", "")
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

# --- ElevenLabs Voice IDs ---
# Set these once you've created/selected the voices in ElevenLabs
RAVEN_VOICE_ID = os.getenv("RAVEN_VOICE_ID", "")  # e.g. "21m00Tcm4TlvDq8ikWAM"
JAX_VOICE_ID = os.getenv("JAX_VOICE_ID", "")      # e.g. "AZnzlk1XvdvUeBnXmlld"

# --- ElevenLabs Voice Settings ---
RAVEN_VOICE_SETTINGS = {
    "stability": 0.4,
    "similarity_boost": 0.85,
    "style": 0.6,
    "use_speaker_boost": True,
}
JAX_VOICE_SETTINGS = {
    "stability": 0.6,
    "similarity_boost": 0.85,
    "style": 0.4,
    "use_speaker_boost": True,
}

# --- Claude Model ---
CLAUDE_MODEL = "claude-sonnet-4-6"

# --- Paths ---
BASE_DIR = Path(__file__).parent
RUNS_DIR = BASE_DIR / "runs"
PROMPTS_FILE = BASE_DIR / "PROMPTS.md"
COUPLE_FILE = BASE_DIR / "COUPLE.md"

# --- News Sources ---
NEWS_SOURCES = [
    "bbc-news",
    "reuters",
    "associated-press",
    "the-guardian-uk",
    "npr",
]
NEWS_MAX_STORIES = 10

# --- Script Settings ---
SCRIPT_MAX_WORDS = 200
SCRIPT_MIN_WORDS = 120

# --- Video Settings ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 9:16 vertical
VIDEO_FPS = 30
VIDEO_FORMAT = "mp4"

# --- Retry Settings ---
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # seconds

# --- Review Gate ---
REVIEW_GATE_ENABLED = os.getenv("REVIEW_GATE_ENABLED", "false").lower() == "true"
REVIEW_GATE_TIMEOUT_MINS = 30
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
