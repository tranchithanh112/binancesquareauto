from src.rewriter.prompts import build_prompt, parse_output


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
