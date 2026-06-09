from src.dedup.dedup import normalize_title, is_duplicate


def test_normalize_strips_diacritics_punctuation_lowercase():
    assert normalize_title("Bitcoin Đạt Đỉnh Mới!") == "bitcoin dat dinh moi"
    assert normalize_title("BTC hits $100,000?") == "btc hits 100000"
    assert normalize_title("  Multiple   Spaces  ") == "multiple spaces"


def test_is_duplicate_exact_url():
    existing_urls = {"https://x/1"}
    existing_titles: list[str] = []
    dup, reason = is_duplicate(url="https://x/1", title="Anything",
                               existing_urls=existing_urls,
                               existing_titles=existing_titles, threshold=0.8)
    assert dup is True
    assert reason == "url"


def test_is_duplicate_fuzzy_title():
    existing_urls: set[str] = set()
    existing_titles = ["bitcoin hits new all time high"]
    dup, reason = is_duplicate(url="https://x/new",
                               title="Bitcoin Hits New All-Time High!",
                               existing_urls=existing_urls,
                               existing_titles=existing_titles, threshold=0.8)
    assert dup is True
    assert reason == "title"


def test_is_duplicate_distinct_title_passes():
    existing_urls: set[str] = set()
    existing_titles = ["bitcoin hits new all time high"]
    dup, _ = is_duplicate(url="https://x/new",
                          title="Ethereum upgrade ships successfully",
                          existing_urls=existing_urls,
                          existing_titles=existing_titles, threshold=0.8)
    assert dup is False
