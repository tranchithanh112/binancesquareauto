import re


COIN_MAP = {
    "BTC": [r"\bbitcoin\b", r"\bbtc\b"],
    "ETH": [r"\bethereum\b", r"\beth\b"],
    "SOL": [r"\bsolana\b", r"\bsol\b"],
    "BNB": [r"\bbnb\b", r"\bbinance coin\b"],
    "XRP": [r"\bxrp\b", r"\bripple\b"],
    "DOGE": [r"\bdoge\b", r"\bdogecoin\b"],
    "ADA": [r"\bada\b", r"\bcardano\b"],
    "AVAX": [r"\bavax\b", r"\bavalanche\b"],
    "LINK": [r"\blink\b", r"\bchainlink\b"],
    "MATIC": [r"\bmatic\b", r"\bpolygon\b"],
}

HIGH_IMPORTANCE_KEYWORDS = [
    r"\bfed\b", r"\bsec\b", r"\bsec approves\b", r"\bcpi\b", r"\brate cut\b",
    r"\brate hike\b", r"\betf approved\b", r"\bhack\b", r"\bdrains?\b",
    r"\bregulation\b", r"\bbanned?\b", r"\ball-?time high\b", r"\bath\b",
    r"\bhalving\b", r"\blawsuit\b", r"\bindictment\b",
]


def _count_mentions(ticker: str, text_l: str) -> int:
    total = 0
    for pat in COIN_MAP[ticker]:
        total += len(re.findall(pat, text_l))
    return total


def extract_coin_tags(text: str) -> list[str]:
    """Return coin tickers found in text, ORDERED by relevance (most
    mentioned first). Falls back to ['BTC'] only when nothing matches."""
    text_l = text.lower()
    scored: list[tuple[int, str]] = []
    for ticker in COIN_MAP:
        n = _count_mentions(ticker, text_l)
        if n:
            scored.append((n, ticker))
    if not scored:
        return ["BTC"]
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored]


def primary_coin(title: str, content: str) -> str | None:
    """Pick the single coin the article is actually ABOUT. Title mentions
    weigh 3x body mentions. Returns None when no coin clearly matches, so the
    caller can skip a misleading chart instead of defaulting to BTC."""
    title_l = (title or "").lower()
    body_l = (content or "").lower()
    best_ticker = None
    best_score = 0
    for ticker in COIN_MAP:
        score = _count_mentions(ticker, title_l) * 3 + _count_mentions(ticker, body_l)
        if score > best_score:
            best_score = score
            best_ticker = ticker
    return best_ticker


def classify_importance(text: str) -> str:
    text_l = text.lower()
    for pat in HIGH_IMPORTANCE_KEYWORDS:
        if re.search(pat, text_l):
            return "high"
    return "normal"
