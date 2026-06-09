from datetime import datetime, timedelta, timezone
from src.db.models import Database


def cutoff_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def purge_old(db: Database, *, cutoff_iso: str) -> None:
    with db._conn() as c:
        c.execute("DELETE FROM dedup WHERE created_at < ?", (cutoff_iso,))
        c.execute(
            "DELETE FROM articles WHERE scraped_at < ? AND id NOT IN "
            "(SELECT article_id FROM posts WHERE posted_at >= ?)",
            (cutoff_iso, cutoff_iso),
        )
