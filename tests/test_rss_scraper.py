from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from src.scraper.rss_scraper import scrape_rss, _is_fresh


def test_is_fresh_recent_passes():
    now = datetime.now(timezone.utc)
    assert _is_fresh(now, max_age_hours=12, now=now) is True


def test_is_fresh_old_filtered():
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=24)
    assert _is_fresh(old, max_age_hours=12, now=now) is False


def test_scrape_rss_returns_articles():
    fake_entry = type("E", (), {
        "title": "Bitcoin hits ATH",
        "link": "https://x/1",
        "summary": "BTC reaches new all-time high",
        "published_parsed": (2026, 6, 8, 0, 0, 0, 0, 0, 0),
    })()
    fake_feed = type("F", (), {"entries": [fake_entry]})()

    with patch("src.scraper.rss_scraper.feedparser.parse", return_value=fake_feed):
        out = scrape_rss(url="https://feed", source_name="coindesk",
                         max_articles=10, max_age_hours=24 * 365 * 10)
    assert len(out) == 1
    assert out[0]["source"] == "coindesk"
    assert out[0]["url"] == "https://x/1"
    assert out[0]["title"] == "Bitcoin hits ATH"
