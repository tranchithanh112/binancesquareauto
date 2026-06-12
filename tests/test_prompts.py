import random

from src.rewriter.prompts import (
    build_prompt, parse_output, parse_article,
    pick_post_type, content_type_for, build_typed_prompt, POST_TYPE_WEIGHTS,
)


def test_build_prompt_short_includes_title_and_tags():
    p = build_prompt(title="T", content="C", importance="normal", coin_tags=["BTC", "ETH"])
    assert "T" in p and "$BTC $ETH" in p and "HOOK" in p


def test_build_prompt_long_for_high_importance():
    p = build_prompt(title="T", content="C", importance="high", coin_tags=["BTC"])
    assert "ANALYSIS" in p


def test_parse_output_extracts_vi_and_en():
    raw = "intro---VI---\nXin chao\n---EN---\nHello\n---END---tail"
    vi, en = parse_output(raw)
    assert vi == "Xin chao"
    assert en == "Hello"


def test_parse_article_extracts_title_vi_en():
    raw = "x---TITLE---\nTieu de\n---VI---\nXin chao\n---EN---\nHello\n---END---y"
    title, vi, en = parse_article(raw)
    assert title == "Tieu de"
    assert vi == "Xin chao"
    assert en == "Hello"


def test_pick_post_type_returns_known_type():
    rng = random.Random(1)
    types = {t for t, _ in POST_TYPE_WEIGHTS}
    for _ in range(20):
        assert pick_post_type(rng) in types


def test_content_type_for_article_only_high_news_ta():
    assert content_type_for("news_ta", "high") == (2, True)
    assert content_type_for("news_ta", "normal") == (1, False)
    assert content_type_for("signal", "high") == (1, False)
    assert content_type_for("poll", "normal") == (1, False)


def test_build_typed_prompt_variants():
    base = dict(title="T", content="C", importance="normal", coin_tags=["SOL"])
    assert "signal" in build_typed_prompt(post_type="signal", **base).lower()
    assert "poll" in build_typed_prompt(post_type="poll", **base).lower()
    assert "hot take" in build_typed_prompt(post_type="hot_take", **base).lower()
    art = build_typed_prompt(post_type="news_ta", title="T", content="C",
                             importance="high", coin_tags=["BTC"])
    assert "---TITLE---" in art
