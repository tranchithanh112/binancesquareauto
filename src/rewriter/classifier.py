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


def extract_coin_tags(text: str) -> list[str]:
    text_l = text.lower()
    found: list[str] = []
    for ticker, patterns in COIN_MAP.items():
        for pat in patterns:
            if re.search(pat, text_l):
                found.append(ticker)
                break
    if not found:
        return ["BTC"]
    return found


def classify_importance(text: str) -> str:
    text_l = text.lower()
    for pat in HIGH_IMPORTANCE_KEYWORDS:
        if re.search(pat, text_l):
            return "high"
    return "normal"
