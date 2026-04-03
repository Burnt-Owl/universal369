"""
Scraper Agent — fetches headlines from sites with no RSS or paywalled RSS.

Called as the 4th source tier by news_agent.run() after NewsAPI, RSS, Reddit.
Outputs story dicts in the same format as all other sources.

Targets are configured in config.SCRAPE_TARGETS. Each target needs:
  name         — display name
  url          — homepage to scrape
  headline_sel — CSS selector for headline elements (h2, h3, or a tags)
  base_url     — used to resolve relative hrefs

Adding a new site: add an entry to SCRAPE_TARGETS in config.py.
No code changes needed here.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SCRAPE_TARGETS

# Browser-like headers — avoids the most common bot blocks
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
}

_MIN_HEADLINE_LEN = 20   # filter out nav links, labels, etc.
_MAX_SUMMARY_LEN = 400


def _get_href(el, base_url: str) -> str:
    """
    Extract href from an element.
    - If the element IS an <a>, use it directly.
    - Otherwise check parent <a> (headline inside link) or child <a>.
    Resolves relative paths against base_url.
    """
    if el.name == "a":
        href = el.get("href", "")
    else:
        anchor = el.find_parent("a") or el.find("a")
        href = anchor.get("href", "") if anchor else ""

    if href and not href.startswith("http"):
        href = urljoin(base_url, href)
    return href


def _get_summary(el) -> str:
    """
    Try to find a short summary near the headline element.
    Checks next sibling <p>, then any nearby <p>.
    Returns empty string if nothing useful found.
    """
    for candidate in [el.find_next_sibling("p"), el.find_next("p")]:
        if candidate:
            text = candidate.get_text(" ", strip=True)[:_MAX_SUMMARY_LEN]
            if len(text) > 30:
                return text
    return ""


def scrape_site(target: dict, max_items: int = 5) -> list[dict]:
    name = target["name"]
    url = target["url"]
    sel = target["headline_sel"]
    base_url = target.get("base_url", url)

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[scraper_agent] Fetch failed {name}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    elements = soup.select(sel)

    if not elements:
        # Fallback: try generic heading tags — catches JS-light sites with
        # simple markup but non-standard class names
        elements = soup.select("h2 a, h3 a")
        if elements:
            print(f"[scraper_agent] {name}: selector '{sel}' matched nothing, used fallback h2/h3 a")

    if not elements:
        print(f"[scraper_agent] {name}: no headlines found (may be JS-rendered)")
        return []

    stories = []
    seen: set[str] = set()

    for el in elements:
        headline = el.get_text(" ", strip=True)
        # Filter noise: too short, duplicates, or looks like a nav label
        if len(headline) < _MIN_HEADLINE_LEN or headline in seen:
            continue
        # Skip anything that looks like a category/tag label (all caps, no spaces)
        if re.match(r"^[A-Z\s&]+$", headline) and len(headline.split()) <= 3:
            continue
        seen.add(headline)

        href = _get_href(el, base_url)
        summary = _get_summary(el)

        stories.append({
            "source": name,
            "headline": headline,
            "summary": summary,
            "url": href,
            "published": "",
            "feed_type": "scrape",
        })

        if len(stories) >= max_items:
            break

    print(f"[scraper_agent] {name}: {len(stories)} stories")
    return stories


def fetch_all(max_per_site: int = 5) -> list[dict]:
    """Scrape all configured targets. Returns flat story list."""
    all_stories = []
    for target in SCRAPE_TARGETS:
        stories = scrape_site(target, max_items=max_per_site)
        all_stories.extend(stories)
        time.sleep(1.5)  # polite gap — avoids hammering sites back to back
    return all_stories


if __name__ == "__main__":
    # Quick test: run standalone and print results
    stories = fetch_all()
    print(f"\n--- {len(stories)} total scraped stories ---")
    for s in stories:
        print(f"\n[{s['source']}] {s['headline']}")
        if s["url"]:
            print(f"  {s['url']}")
        if s["summary"]:
            print(f"  {s['summary'][:100]}...")
