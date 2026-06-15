from src.runners.square_stats import _normalize
from src.db.models import Database


def test_normalize_extracts_engagement():
    item = {
        "id": 12345, "title": "Hello", "bodyTextOnly": "body text",
        "viewCount": 347, "likeCount": 6, "commentCount": 2,
        "shareCount": 1, "totalReactionCount": 6, "bookmarkCount": 3,
    }
    n = _normalize(item)
    assert n["binance_id"] == "12345"
    assert n["views"] == 347
    assert n["likes"] == 6
    assert n["comments"] == 2
    assert n["reactions"] == 6
    assert n["bookmarks"] == 3


def test_upsert_stats_and_aggregate(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    aid = db.insert_article(source="coindesk", url="https://x/1", title="t",
                            content="c", scraped_at="2026-06-12T00:00:00Z",
                            importance="normal")
    pid = db.insert_post(article_id=aid, content_vi="vi", content_en="en",
                         coin_tags=["BTC"], format="short", batch="auto",
                         post_type="signal", content_type=1)
    db.set_binance_id(pid, "999")
    db.upsert_stats(binance_id="999", post_id=pid, views=200, likes=5,
                    comments=1, shares=0, reactions=5, bookmarks=2,
                    collected_at="2026-06-12T01:00:00Z")
    db.upsert_stats(binance_id="999", post_id=pid, views=300, likes=8,
                    comments=2, shares=1, reactions=8, bookmarks=3,
                    collected_at="2026-06-12T02:00:00Z")
    agg = db.stats_by_post_type()
    assert len(agg) == 1
    assert agg[0]["post_type"] == "signal"
    assert agg[0]["avg_views"] == 300


def test_find_unmatched_post_by_body(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    aid = db.insert_article(source="x", url="https://x/2", title="t",
                            content="c", scraped_at="2026-06-12T00:00:00Z",
                            importance="normal")
    pid = db.insert_post(article_id=aid,
                         content_vi="Bitcoin vuot moc 63000 hom nay",
                         content_en="en", coin_tags=["BTC"], format="short",
                         batch="auto")
    db.update_post_status(pid, status="posted", posted_at="2026-06-12T01:00:00Z")
    m = db.find_unmatched_post_by_body(
        "Bitcoin vuot moc 63000 hom nay --- Bitcoin tops 63000 today")
    assert m is not None and m["post_id"] == pid
    assert db.find_unmatched_post_by_body("Totally different content") is None