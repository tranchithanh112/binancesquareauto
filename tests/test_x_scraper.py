from src.scraper.x_scraper import x_profile_recipe


def test_x_recipe_contains_handle_and_fallback():
    r = x_profile_recipe("elonmusk", max_posts=5)
    assert "elonmusk" in r["primary_url"]
    assert "nitter" in r["fallback_url"]
    assert "5" in r["instructions"]
    assert r["source"] == "x::elonmusk"
