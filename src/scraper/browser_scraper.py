"""
Browser-driven scrape recipes. Claude session executes via MCP browser tools.
This module assembles instructions and persists results.
"""
from datetime import datetime, timezone
from src.db.models import Database


def reuters_recipe(url: str, max_articles: int) -> dict:
    return {
        "source": "reuters",
        "url": url,
        "max_articles": max_articles,
        "instructions": (
            "1. Navigate to the given Reuters cryptocurrency section URL.\n"
            "2. Take a snapshot and locate article cards on the page.\n"
            "3. For each of the first {n} cards, extract title, href, and "
            "summary (first paragraph of preview text).\n"
            "4. Return as a JSON list with keys: title, url, summary."
        ).format(n=max_articles),
    }


def coingecko_recipe(url: str, max_articles: int) -> dict:
    return {
        "source": "coingecko",
        "url": url,
        "max_articles": max_articles,
        "instructions": (
            "1. Navigate to CoinGecko news page.\n"
            "2. Snapshot and extract the top {n} news items.\n"
            "3. For each: title, href, and the first ~200 chars of preview.\n"
            "4. Return JSON list with keys: title, url, summary."
        ).format(n=max_articles),
    }


def google_news_recipe(query: str, max_articles: int) -> dict:
    return {
        "source": f"google_news::{query}",
        "url": f"https://news.google.com/search?q={query.replace(' ', '+')}",
        "max_articles": max_articles,
        "instructions": (
            "1. Navigate to Google News search URL.\n"
            "2. Snapshot and extract the top {n} article tiles.\n"
            "3. For each: title (visible heading), the outbound href (resolve "
            "any Google redirect), and the preview snippet.\n"
            "4. Return JSON list with keys: title, url, summary."
        ).format(n=max_articles),
    }


def save_scraped(db: Database, *, source: str, items: list[dict]) -> list[dict]:
    """Persist a list of {title, url, summary} dicts as articles.
    Skips ones already in DB (URL UNIQUE collision). Returns inserted rows."""
    inserted: list[dict] = []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for item in items:
        try:
            aid = db.insert_article(
                source=source,
                url=item["url"],
                title=item["title"],
                content=item.get("summary", ""),
                scraped_at=now_iso,
                importance="normal",
            )
            inserted.append({**item, "id": aid, "source": source})
        except Exception:
            continue
    return inserted
