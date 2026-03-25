"""
News Agent — fetches top global stories from the past 24 hours.
Output: runs/YYYY-MM-DD/daily-brief.json
"""

import json
import time
import urllib.request
import xml.etree.ElementTree as ET
import requests
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


def _parse_rss_feed(xml_bytes: bytes, feed_url: str) -> list[dict]:
    """Parse RSS 2.0 or Atom feed from raw XML bytes."""
    ATOM = "http://www.w3.org/2005/Atom"
    root = ET.fromstring(xml_bytes)
    stories = []

    # Atom feed
    if root.tag == f"{{{ATOM}}}feed":
        feed_title = (root.findtext(f"{{{ATOM}}}title") or feed_url)
        for entry in root.findall(f"{{{ATOM}}}entry")[:5]:
            link_el = entry.find(f"{{{ATOM}}}link")
            stories.append({
                "source": feed_title,
                "headline": entry.findtext(f"{{{ATOM}}}title") or "",
                "summary": entry.findtext(f"{{{ATOM}}}summary") or "",
                "url": link_el.get("href", "") if link_el is not None else "",
                "published": entry.findtext(f"{{{ATOM}}}published") or "",
            })
    else:
        # RSS 2.0
        channel = root.find("channel") or root
        feed_title = channel.findtext("title") or feed_url
        for item in channel.findall("item")[:5]:
            stories.append({
                "source": feed_title,
                "headline": item.findtext("title") or "",
                "summary": item.findtext("description") or "",
                "url": item.findtext("link") or "",
                "published": item.findtext("pubDate") or "",
            })

    return stories


def fetch_rss() -> list[dict]:
    stories = []
    for feed_url in RSS_FEEDS:
        try:
            req = urllib.request.Request(
                feed_url,
                headers={"User-Agent": "ComedyFactory/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_bytes = resp.read()
            stories.extend(_parse_rss_feed(xml_bytes, feed_url))
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
