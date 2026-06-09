from src.rewriter.classifier import extract_coin_tags, classify_importance


def test_extract_coin_tags_finds_known_tickers():
    text = "Bitcoin and Ethereum lead the rally; Solana follows."
    tags = extract_coin_tags(text)
    assert "BTC" in tags
    assert "ETH" in tags
    assert "SOL" in tags


def test_extract_coin_tags_dedups_and_uppercases():
    text = "btc btc ETH eth eth"
    tags = extract_coin_tags(text)
    assert tags.count("BTC") == 1
    assert tags.count("ETH") == 1


def test_extract_coin_tags_returns_btc_default_when_no_matches():
    tags = extract_coin_tags("Generic crypto market news with no specific coin mentioned.")
    assert tags == ["BTC"]


def test_classify_importance_high_keywords():
    assert classify_importance("Fed announces rate cut affecting markets") == "high"
    assert classify_importance("SEC approves Bitcoin spot ETF") == "high"
    assert classify_importance("Major hack drains $500M from protocol") == "high"


def test_classify_importance_normal_default():
    assert classify_importance("New partnership announced between project X and Y") == "normal"
