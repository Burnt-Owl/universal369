"""
News Agent — fetches top global stories from the past 24 hours.
Output: runs/YYYY-MM-DD/daily-brief.json

Sources (in priority order):
  1. NewsAPI     — primary, structured, popularity-sorted
  2. RSS feeds   — broad mainstream + weird/offbeat tier
  3. Reddit RSS  — worldnews / nottheonion / todayilearned (comedy gold)
"""

import json
import re
import time
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    NEWS_API_KEY, NEWS_SOURCES, NEWS_MAX_STORIES,
    RSS_FEEDS, REDDIT_RSS_FEEDS,
    MAX_RETRIES, RETRY_DELAYS,
)
from scraper_agent import fetch_all as fetch_scrape

_USER_AGENT = "ComedyFactory/2.0 (automated comedy news aggregator)"

# feedparser sets its own UA header via the agent kwarg; for Reddit we need
# a descriptive string so requests aren't 429'd on the public RSS endpoint.
_REDDIT_AGENT = "ComedyFactory/2.0 anonymous RSS reader"


# ---------------------------------------------------------------------------
# NewsAPI
# ---------------------------------------------------------------------------

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
                    "feed_type": "newsapi",
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


# ---------------------------------------------------------------------------
# RSS / Atom (via feedparser)
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_feed(feed_url: str, max_items: int = 5, feed_type: str = "rss") -> list[dict]:
    """Parse any RSS 1.0/2.0, Atom, or Reddit feed via feedparser."""
    agent = _REDDIT_AGENT if feed_type == "reddit" else _USER_AGENT
    try:
        d = feedparser.parse(feed_url, agent=agent)
        # bozo=True means the feed was malformed, but entries may still be usable
        if d.bozo and not d.entries:
            print(f"[news_agent] Feed unparseable {feed_url}: {d.bozo_exception}")
            return []

        feed_title = d.feed.get("title", feed_url)
        stories = []
        for entry in d.entries[:max_items]:
            headline = _strip_html(entry.get("title", "")).strip()
            if not headline:
                continue
            summary = _strip_html(
                entry.get("summary", "") or entry.get("description", "")
            )[:500]
            stories.append({
                "source": feed_title,
                "headline": headline,
                "summary": summary,
                "url": entry.get("link", ""),
                "published": entry.get("published", ""),
                "feed_type": feed_type,
            })
        return stories
    except Exception as e:
        print(f"[news_agent] Feed failed {feed_url}: {e}")
        return []


def fetch_rss() -> list[dict]:
    stories = []
    for feed_url in RSS_FEEDS:
        fetched = _parse_feed(feed_url, max_items=5, feed_type="rss")
        stories.extend(fetched)
        if fetched:
            print(f"[news_agent]   RSS {feed_url}: {len(fetched)} stories")
    return stories


def fetch_reddit() -> list[dict]:
    stories = []
    for feed_url in REDDIT_RSS_FEEDS:
        fetched = _parse_feed(feed_url, max_items=5, feed_type="reddit")
        stories.extend(fetched)
        if fetched:
            print(f"[news_agent]   Reddit {feed_url}: {len(fetched)} stories")
        time.sleep(1)  # polite gap — Reddit public RSS rate-limits aggressively
    return stories


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _normalize(headline: str) -> str:
    """Lowercase, strip punctuation — for fuzzy dedup across sources."""
    return re.sub(r"[^a-z0-9 ]", "", headline.lower()).strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(run_dir: Path) -> Path:
    print("[news_agent] Fetching top global stories...")

    # 1. NewsAPI (primary)
    stories = fetch_newsapi(run_dir.name)
    print(f"[news_agent] NewsAPI: {len(stories)} stories")

    seen: set[str] = {_normalize(s["headline"]) for s in stories}
    cap = NEWS_MAX_STORIES * 2  # gather extras so brief_agent has choice

    # 2. RSS feeds (supplement / fallback)
    print("[news_agent] Fetching RSS feeds...")
    for story in fetch_rss():
        norm = _normalize(story["headline"])
        if norm not in seen and len(stories) < cap:
            stories.append(story)
            seen.add(norm)

    # 3. Reddit (comedy bonus)
    print("[news_agent] Fetching Reddit feeds...")
    for story in fetch_reddit():
        norm = _normalize(story["headline"])
        if norm not in seen and len(stories) < cap:
            stories.append(story)
            seen.add(norm)

    # 4. Scraped sites (Quanta, Nautilus, Gizmodo, Futurism, etc.)
    print("[news_agent] Scraping direct sources...")
    for story in fetch_scrape():
        norm = _normalize(story["headline"])
        if norm not in seen and len(stories) < cap:
            stories.append(story)
            seen.add(norm)

    stories = stories[:NEWS_MAX_STORIES]

    if not stories:
        raise RuntimeError("[news_agent] No stories found. Cannot continue.")

    by_type = {}
    for s in stories:
        by_type[s["feed_type"]] = by_type.get(s["feed_type"], 0) + 1
    print(f"[news_agent] Final mix: {by_type}")

    output = {
        "date": run_dir.name,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(stories),
        "stories": stories,
    }

    out_file = run_dir / "daily-brief.json"
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"[news_agent] Saved {len(stories)} stories → {out_file}")
    return out_file


if __name__ == "__main__":
    from datetime import date
    today = date.today().isoformat()
    run_dir = Path(__file__).parent.parent / "runs" / today
    run_dir.mkdir(parents=True, exist_ok=True)
    run(run_dir)
