"""
News Agent — fetches top global stories from the past 24 hours.
Output: runs/YYYY-MM-DD/daily-brief.json
"""

import json
import time
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import NEWS_API_KEY, NEWS_SOURCES, NEWS_MAX_STORIES, MAX_RETRIES, RETRY_DELAYS


RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.reuters.com/reuters/worldNews",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.theguardian.com/world/rss",
]


def fetch_newsapi(run_date: str) -> list[dict]:
    if not NEWS_API_KEY:
        return []

    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "sources": ",".join(NEWS_SOURCES),
        "from": yesterday,
        "language": "en",
        "sortBy": "popularity",
        "pageSize": NEWS_MAX_STORIES,
        "apiKey": NEWS_API_KEY,
    }

    for attempt, delay in enumerate(RETRY_DELAYS + [None], 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            return [
                {
                    "source": a["source"]["name"],
                    "headline": a["title"],
                    "summary": a.get("description") or "",
                    "url": a["url"],
                    "published": a.get("publishedAt", ""),
                }
                for a in articles
                if a.get("title") and "[Removed]" not in a.get("title", "")
            ]
        except Exception as e:
            if delay is None:
                print(f"[news_agent] NewsAPI failed after {attempt} attempts: {e}")
                return []
            print(f"[news_agent] NewsAPI attempt {attempt} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
    return []


def fetch_rss() -> list[dict]:
    stories = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                published = entry.get("published_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                stories.append({
                    "source": feed.feed.get("title", feed_url),
                    "headline": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "url": entry.get("link", ""),
                    "published": entry.get("published", ""),
                })
        except Exception as e:
            print(f"[news_agent] RSS feed {feed_url} failed: {e}")

    return stories


def run(run_dir: Path) -> Path:
    print("[news_agent] Fetching top global stories...")

    stories = fetch_newsapi(run_dir.name)
    if len(stories) < 5:
        rss_stories = fetch_rss()
        # Deduplicate by headline
        existing_headlines = {s["headline"] for s in stories}
        stories += [s for s in rss_stories if s["headline"] not in existing_headlines]

    stories = stories[:NEWS_MAX_STORIES]

    if not stories:
        raise RuntimeError("[news_agent] No stories found. Cannot continue.")

    output = {
        "date": run_dir.name,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(stories),
        "stories": stories,
    }

    out_file = run_dir / "daily-brief.json"
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"[news_agent] Saved {len(stories)} stories to {out_file}")
    return out_file


if __name__ == "__main__":
    from datetime import date
    today = date.today().isoformat()
    run_dir = Path(__file__).parent.parent / "runs" / today
    run_dir.mkdir(parents=True, exist_ok=True)
    run(run_dir)
