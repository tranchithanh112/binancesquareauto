from src.dedup.dedup import (
    normalize_title, is_duplicate, extract_keywords, keyword_overlap,
)


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


def test_extract_keywords_normalizes_numbers():
    kw = extract_keywords("Bitcoin tops $63K as Strategy adds $100 million")
    assert "63000" in kw
    assert "100000000" in kw
    assert "bitcoin" in kw
    assert "tops" in kw
    # stopwords filtered
    assert "the" not in kw and "and" not in kw


def test_keyword_overlap_same_event_different_titles():
    a = extract_keywords(
        "Bitcoin tops $63,000 as Strategy adds $100 million BTC")
    b = extract_keywords(
        "Strategy buys $100 million in Bitcoin, BTC price hits $63K")
    assert keyword_overlap(a, b) >= 0.5


def test_is_duplicate_semantic_catches_reworded():
    sig = extract_keywords(
        "Bitcoin tops $63,000 as Strategy adds $100 million BTC")
    dup, reason = is_duplicate(
        url="https://b/2",
        title="Strategy buys $100 million in Bitcoin, BTC price hits $63K",
        existing_urls=set(), existing_titles=[], threshold=0.8,
        content="", existing_signatures=[sig], kw_threshold=0.5,
    )
    assert dup is True
    assert reason == "semantic"


def test_is_duplicate_semantic_allows_distinct_events():
    sig = extract_keywords(
        "Bitcoin tops $63,000 as Strategy adds $100 million BTC")
    dup, _ = is_duplicate(
        url="https://b/3",
        title="Solana network outage halts trading for two hours",
        existing_urls=set(), existing_titles=[], threshold=0.8,
        content="", existing_signatures=[sig], kw_threshold=0.5,
    )
    assert dup is False
