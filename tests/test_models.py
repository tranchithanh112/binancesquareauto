import json
from src.db.models import Database


def test_init_creates_tables(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    aid = db.insert_article(source="coindesk", url="https://x/1", title="t",
                            content="c", scraped_at="2026-06-08T01:00:00Z", importance="high")
    rows = db.list_articles_unposted()
    assert len(rows) == 1
    assert rows[0]["id"] == aid
    assert rows[0]["source"] == "coindesk"


def test_insert_post_and_update_status(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    aid = db.insert_article(source="reuters", url="https://r/1", title="t",
                            content="c", scraped_at="2026-06-08T01:00:00Z", importance="normal")
    pid = db.insert_post(article_id=aid, content_vi="vi", content_en="en",
                         coin_tags=["BTC"], format="short", batch="morning",
                         scheduled_time="2026-06-08T08:00:00Z")
    db.update_post_status(pid, status="posted", posted_at="2026-06-08T08:01:00Z")
    posts = db.list_posts_by_batch("morning")
    assert posts[0]["status"] == "posted"
    assert json.loads(posts[0]["coin_tags"]) == ["BTC"]


def test_dedup_insert_and_check(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    db.insert_dedup(url="https://x/1", title_normalized="bitcoin hits new high",
                    created_at="2026-06-08T01:00:00Z")
    assert db.dedup_url_exists("https://x/1") is True
    assert db.dedup_url_exists("https://x/2") is False
    titles = db.list_dedup_titles()
    assert "bitcoin hits new high" in titles
