from src.db.models import Database
from src.db.cleanup import purge_old


def test_purge_old_removes_records_older_than_cutoff(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    db.insert_dedup(url="https://old/1", title_normalized="old title",
                    created_at="2026-01-01T00:00:00Z")
    db.insert_article(source="x", url="https://old/1", title="old", content="c",
                      scraped_at="2026-01-01T00:00:00Z", importance="normal")
    db.insert_dedup(url="https://new/1", title_normalized="new title",
                    created_at="2026-06-07T00:00:00Z")
    db.insert_article(source="x", url="https://new/1", title="new", content="c",
                      scraped_at="2026-06-07T00:00:00Z", importance="normal")

    purge_old(db, cutoff_iso="2026-05-09T00:00:00Z")

    assert db.dedup_url_exists("https://old/1") is False
    assert db.dedup_url_exists("https://new/1") is True
