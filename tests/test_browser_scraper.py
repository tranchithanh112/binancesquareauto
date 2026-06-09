from src.db.models import Database
from src.scraper.browser_scraper import save_scraped, reuters_recipe


def test_recipe_includes_max_articles():
    r = reuters_recipe("https://reuters.com/x", max_articles=7)
    assert "7" in r["instructions"]
    assert r["source"] == "reuters"


def test_save_scraped_inserts_and_skips_duplicates(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    items = [
        {"title": "T1", "url": "https://r/1", "summary": "s1"},
        {"title": "T2", "url": "https://r/2", "summary": "s2"},
    ]
    inserted = save_scraped(db, source="reuters", items=items)
    assert len(inserted) == 2

    inserted2 = save_scraped(db, source="reuters", items=items)
    assert inserted2 == []
