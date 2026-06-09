from src.db.models import Database
from src.poster.binance_poster import build_post_recipe, record_post_result


def test_build_recipe_combines_vi_and_en():
    r = build_post_recipe(post_id=1, content_vi="VI", content_en="EN",
                          coin_tags=["BTC"], scheduled_iso="2026-06-08T08:00:00Z")
    assert "VI" in r["body"] and "EN" in r["body"]
    assert "['BTC']" in r["instructions"]
    assert "2026-06-08T08:00:00Z" in r["instructions"]


def test_record_post_result_updates_status(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    aid = db.insert_article(source="x", url="https://x/1", title="t", content="c",
                            scraped_at="2026-06-08T01:00:00Z", importance="normal")
    pid = db.insert_post(article_id=aid, content_vi="vi", content_en="en",
                         coin_tags=["BTC"], format="short", batch="morning",
                         scheduled_time="2026-06-08T08:00:00Z")
    record_post_result(db, post_id=pid, status="failed", error_msg="UI changed")
    posts = db.list_posts_by_batch("morning")
    assert posts[0]["status"] == "failed"
    assert posts[0]["error_msg"] == "UI changed"
