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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")           # Imagen backgrounds (free, per-episode)
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY", "")       # Character shots (optional, cached)
CANVA_ACCESS_TOKEN = os.getenv("CANVA_ACCESS_TOKEN", "")   # Thumbnail generation (optional)
CANVA_BRAND_TEMPLATE_ID = os.getenv("CANVA_BRAND_TEMPLATE_ID", "")  # optional Canva template
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
DID_API_KEY = os.getenv("DID_API_KEY", "")                # D-ID Talks API — talking head animation
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")          # Pexels stock video footage

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

# --- News Sources (NewsAPI) ---
NEWS_SOURCES = [
    "bbc-news",
    "reuters",
    "associated-press",
    "the-guardian-uk",
    "npr",
    "abc-news",
    "al-jazeera-english",
    "the-washington-post",
    "vice-news",
]
NEWS_MAX_STORIES = 15

# --- RSS Feeds (feedparser — fallback + supplement) ---
RSS_FEEDS = [
    # === World News ===
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.reuters.com/reuters/worldNews",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://abcnews.go.com/abcnews/topstories",
    "https://feeds.npr.org/1001/rss.xml",
    # === Weird/Offbeat (comedy-adjacent) ===
    "https://www.boingboing.net/feed",
    "https://www.vice.com/en/rss",
    # === Science & Curiosity ===
    "https://www.newscientist.com/section/news/feed/",
    "https://www.iflscience.com/feed/",
    "https://www.smithsonianmag.com/rss/latest_articles/",
    "https://www.sciencedaily.com/rss/all.xml",         # 50 items, peer-review summaries
    "https://www.nature.com/nature.rss",                # 80 items, RDF/RSS 1.0
    "https://feeds.arstechnica.com/arstechnica/science",
    "https://www.sci.news/feed",                        # 20 items, breaking bio/physics
    # === Space (Artemis II coverage live) ===
    "https://www.nasa.gov/rss/dyn/breaking_news.rss",
    "https://www.esa.int/rssfeed/Our_Activities/Space_Science",
    "https://www.space.com/feeds.xml",               # 30 items, real-time mission tracking
    # Note: NASA Earth Observatory redirects to non-RSS page — skip
    # Note: RSSHub (DIYgod/RSSHub) worth self-hosting on VPS for sources without native RSS.
    # Note: Crawl4AI (unclecode/crawl4ai) is the 2026 upgrade path for JS-rendered scraping —
    #       replaces BS4 for sites like Futurism. Requires Playwright. Add when pipeline needs it.
]

# --- Reddit RSS Feeds (comedy gold) ---
REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/worldnews/.rss",
    "https://www.reddit.com/r/nottheonion/.rss",    # real news that sounds fake
    "https://www.reddit.com/r/todayilearned/.rss",  # TIL — perfect for Jax moments
]

# --- Scrape Targets (sites with no/paywalled RSS — scraped directly) ---
SCRAPE_TARGETS = [
    {
        "name": "Quanta Magazine",
        "url": "https://www.quantamagazine.org/",
        "headline_sel": "h3 > a, h2 > a",
        "base_url": "https://www.quantamagazine.org",
    },
    {
        "name": "Nautilus",
        "url": "https://nautil.us/",
        "headline_sel": "h3 a",
        "base_url": "https://nautil.us",
    },
    {
        "name": "Gizmodo",
        "url": "https://gizmodo.com/",
        "headline_sel": "h2.typo-sofia-h5",  # headline sits inside parent <a>
        "base_url": "https://gizmodo.com",
    },
    {
        "name": "Futurism",
        "url": "https://futurism.com/",
        "headline_sel": "h3 > a",
        "base_url": "https://futurism.com",
    },
]

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
