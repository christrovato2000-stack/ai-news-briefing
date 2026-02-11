"""
News aggregator module - fetches AI and tech news from multiple sources.
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
import re

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _age_days(published_parsed) -> float:
    """Return how many days ago a feedparser time struct is."""
    if not published_parsed:
        return 0.0
    pub_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - pub_dt).total_seconds() / 86400


def _fetch_feed(url: str, max_age_days: int = 7, limit: int = 20) -> list[dict]:
    """Parse an RSS/Atom feed and return recent entries."""
    try:
        feed = feedparser.parse(url)
        if feed.bozo and feed.bozo_exception:
            logger.warning("Feed parse warning for %s: %s", url, feed.bozo_exception)
        items = []
        for entry in feed.entries[:limit * 2]:
            age = _age_days(getattr(entry, "published_parsed", None))
            if age > max_age_days:
                continue
            items.append({
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "summary": _clean_html(entry.get("summary", entry.get("description", ""))),
                "published": entry.get("published", ""),
                "source": feed.feed.get("title", url),
            })
            if len(items) >= limit:
                break
        logger.info("Fetched %d items from %s", len(items), url)
        return items
    except Exception as exc:
        logger.error("Error fetching feed %s: %s", url, exc)
        return []


def _clean_html(raw: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()[:600]


# ---------------------------------------------------------------------------
# Hacker News
# ---------------------------------------------------------------------------

def fetch_hackernews(max_age_days: int = 7, limit: int = 30) -> list[dict]:
    """Fetch top AI/tech stories from Hacker News Algolia API."""
    logger.info("Fetching Hacker News stories…")
    keywords = [
        "artificial intelligence", "machine learning", "LLM", "GPT", "Claude",
        "OpenAI", "Anthropic", "deep learning", "neural network", "AI",
        "robotics", "autonomous", "transformer", "diffusion", "model",
    ]
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    cutoff_ts = int(cutoff.timestamp())

    results: list[dict] = []
    seen: set[str] = set()

    for kw in keywords[:6]:  # limit API calls
        try:
            url = (
                "https://hn.algolia.com/api/v1/search?"
                f"query={requests.utils.quote(kw)}"
                f"&tags=story"
                f"&numericFilters=created_at_i>{cutoff_ts},points>10"
                f"&hitsPerPage=15"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                if story_url in seen:
                    continue
                seen.add(story_url)
                results.append({
                    "title": hit.get("title", "").strip(),
                    "url": story_url,
                    "summary": f"HN points: {hit.get('points', 0)} | comments: {hit.get('num_comments', 0)}",
                    "published": hit.get("created_at", ""),
                    "source": "Hacker News",
                })
        except Exception as exc:
            logger.error("HN fetch error for '%s': %s", kw, exc)
        time.sleep(0.3)

    # Sort by points proxy (embedded in summary) isn't ideal, just return as-is
    logger.info("Fetched %d unique HN stories", len(results))
    return results[:limit]


# ---------------------------------------------------------------------------
# ArXiv
# ---------------------------------------------------------------------------

def fetch_arxiv(max_age_days: int = 7, limit: int = 20) -> list[dict]:
    """Fetch recent AI papers from ArXiv RSS feeds."""
    logger.info("Fetching ArXiv papers…")
    feeds = [
        ("https://rss.arxiv.org/rss/cs.AI", "ArXiv cs.AI"),
        ("https://rss.arxiv.org/rss/cs.LG", "ArXiv cs.LG"),
        ("https://rss.arxiv.org/rss/cs.CL", "ArXiv cs.CL"),
    ]
    all_items: list[dict] = []
    seen: set[str] = set()
    for feed_url, label in feeds:
        for item in _fetch_feed(feed_url, max_age_days=max_age_days, limit=15):
            if item["url"] not in seen:
                item["source"] = label
                all_items.append(item)
                seen.add(item["url"])
    logger.info("Fetched %d ArXiv papers", len(all_items))
    return all_items[:limit]


# ---------------------------------------------------------------------------
# TechCrunch AI
# ---------------------------------------------------------------------------

def fetch_techcrunch(max_age_days: int = 7, limit: int = 15) -> list[dict]:
    """Fetch AI news from TechCrunch RSS."""
    logger.info("Fetching TechCrunch AI…")
    items = _fetch_feed(
        "https://techcrunch.com/feed/",
        max_age_days=max_age_days,
        limit=40,
    )
    ai_keywords = {
        "ai", "artificial intelligence", "machine learning", "openai", "anthropic",
        "google deepmind", "llm", "chatgpt", "claude", "gemini", "gpt",
        "deep learning", "neural", "robot", "automation", "generative",
    }
    filtered = [
        i for i in items
        if any(kw in i["title"].lower() or kw in i["summary"].lower() for kw in ai_keywords)
    ]
    logger.info("Fetched %d TechCrunch AI items", len(filtered))
    return filtered[:limit]


# ---------------------------------------------------------------------------
# The Verge
# ---------------------------------------------------------------------------

def fetch_verge(max_age_days: int = 7, limit: int = 15) -> list[dict]:
    """Fetch AI coverage from The Verge RSS."""
    logger.info("Fetching The Verge AI…")
    items = _fetch_feed(
        "https://www.theverge.com/rss/index.xml",
        max_age_days=max_age_days,
        limit=60,
    )
    ai_keywords = {
        "ai", "artificial intelligence", "openai", "anthropic", "chatgpt",
        "claude", "gemini", "llm", "machine learning", "deep learning",
        "robot", "automation", "generative", "gpt", "neural",
    }
    filtered = [
        i for i in items
        if any(kw in i["title"].lower() or kw in i["summary"].lower() for kw in ai_keywords)
    ]
    logger.info("Fetched %d Verge AI items", len(filtered))
    return filtered[:limit]


# ---------------------------------------------------------------------------
# MIT Technology Review
# ---------------------------------------------------------------------------

def fetch_mit_tech_review(max_age_days: int = 7, limit: int = 10) -> list[dict]:
    """Fetch AI stories from MIT Technology Review RSS."""
    logger.info("Fetching MIT Tech Review…")
    items = _fetch_feed(
        "https://www.technologyreview.com/feed/",
        max_age_days=max_age_days,
        limit=30,
    )
    ai_keywords = {
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "neural", "llm", "robot", "automation", "generative", "openai",
        "anthropic", "chatgpt", "algorithm",
    }
    filtered = [
        i for i in items
        if any(kw in i["title"].lower() or kw in i["summary"].lower() for kw in ai_keywords)
    ]
    logger.info("Fetched %d MIT Tech Review items", len(filtered))
    return filtered[:limit]


# ---------------------------------------------------------------------------
# VentureBeat AI
# ---------------------------------------------------------------------------

def fetch_venturebeat(max_age_days: int = 7, limit: int = 15) -> list[dict]:
    """Fetch AI stories from VentureBeat RSS."""
    logger.info("Fetching VentureBeat AI…")
    items = _fetch_feed(
        "https://venturebeat.com/feed/",
        max_age_days=max_age_days,
        limit=40,
    )
    ai_keywords = {
        "ai", "artificial intelligence", "machine learning", "llm", "generative",
        "openai", "anthropic", "deep learning", "neural", "robot", "gpt",
        "chatgpt", "claude", "gemini", "automation",
    }
    filtered = [
        i for i in items
        if any(kw in i["title"].lower() or kw in i["summary"].lower() for kw in ai_keywords)
    ]
    logger.info("Fetched %d VentureBeat items", len(filtered))
    return filtered[:limit]


# ---------------------------------------------------------------------------
# Wired AI
# ---------------------------------------------------------------------------

def fetch_wired(max_age_days: int = 7, limit: int = 10) -> list[dict]:
    """Fetch AI stories from Wired RSS."""
    logger.info("Fetching Wired AI…")
    items = _fetch_feed(
        "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss",
        max_age_days=max_age_days,
        limit=20,
    )
    logger.info("Fetched %d Wired AI items", len(items))
    return items[:limit]


# ---------------------------------------------------------------------------
# Main aggregation entry point
# ---------------------------------------------------------------------------

def aggregate_news(max_age_days: int = 7) -> list[dict]:
    """
    Aggregate AI & tech news from all sources.
    Returns a deduplicated list of news items sorted with most recent first.
    """
    logger.info("Starting news aggregation (last %d days)…", max_age_days)

    fetchers = [
        fetch_hackernews,
        fetch_arxiv,
        fetch_techcrunch,
        fetch_verge,
        fetch_mit_tech_review,
        fetch_venturebeat,
        fetch_wired,
    ]

    all_items: list[dict] = []
    seen_titles: set[str] = set()

    for fetcher in fetchers:
        try:
            items = fetcher(max_age_days=max_age_days)
            for item in items:
                title_key = item["title"].lower().strip()
                if title_key and title_key not in seen_titles:
                    seen_titles.add(title_key)
                    all_items.append(item)
        except Exception as exc:
            logger.error("Fetcher %s failed: %s", fetcher.__name__, exc)

    logger.info("Aggregated %d unique stories total", len(all_items))
    return all_items
