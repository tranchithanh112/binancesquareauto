from datetime import datetime, timezone, timedelta
import feedparser


def _is_fresh(published: datetime, *, max_age_hours: int,
              now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return (now - published) <= timedelta(hours=max_age_hours)


def scrape_rss(*, url: str, source_name: str, max_articles: int,
               max_age_hours: int) -> list[dict]:
    feed = feedparser.parse(url)
    results: list[dict] = []
    now = datetime.now(timezone.utc)
    for entry in feed.entries[:max_articles]:
        published_struct = getattr(entry, "published_parsed", None)
        if published_struct is None:
            continue
        published = datetime(*published_struct[:6], tzinfo=timezone.utc)
        if not _is_fresh(published, max_age_hours=max_age_hours, now=now):
            continue
        results.append({
            "source": source_name,
            "url": entry.link,
            "title": entry.title,
            "content": getattr(entry, "summary", ""),
            "scraped_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "published": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return results
