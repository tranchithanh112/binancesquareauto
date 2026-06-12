import re
from difflib import SequenceMatcher
from unidecode import unidecode


_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")

# Stop words stripped from keyword signatures (English + common crypto filler).
_STOP = {
    "the", "and", "for", "that", "with", "from", "this", "after", "into",
    "over", "amid", "says", "said", "could", "will", "has", "have", "are",
    "was", "were", "its", "his", "her", "their", "they", "you", "your",
    "but", "not", "all", "new", "now", "may", "can", "out", "off", "per",
    "crypto", "market", "markets", "price", "prices", "news", "update",
    "report", "analyst", "analysts",
}

_MAG = {"million": 1_000_000, "billion": 1_000_000_000, "trillion": 1_000_000_000_000}


def normalize_title(title: str) -> str:
    s = unidecode(title).lower()
    s = _PUNCT_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _normalize_numbers(text: str) -> list[str]:
    """Pull out numeric tokens, canonicalizing $63K / 63,000 / 100 million
    so the same figure from two sources collides. Returns list of int-strings."""
    out: list[str] = []
    low = text.lower()
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*([kmbt])\b", low):
        num = float(m.group(1).replace(",", ""))
        mult = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}[m.group(2)]
        out.append(str(int(num * mult)))
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s+(million|billion|trillion)", low):
        num = float(m.group(1).replace(",", ""))
        out.append(str(int(num * _MAG[m.group(2)])))
    for m in re.finditer(r"\b(\d{1,3}(?:,\d{3})+|\d{4,})\b", text):
        out.append(str(int(m.group(1).replace(",", ""))))
    return out


def extract_keywords(title: str, content: str = "") -> set[str]:
    """Build a bag of significant tokens: words >=4 chars (minus stopwords)
    plus normalized numbers. Order-independent semantic fingerprint."""
    raw = f"{title} {content}"
    norm = normalize_title(raw)
    words = {w for w in norm.split()
             if len(w) >= 4 and w not in _STOP and not w.isdigit()}
    nums = set(_normalize_numbers(raw))
    return words | nums


def keyword_overlap(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two keyword sets."""
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def is_duplicate(*, url: str, title: str, existing_urls: set[str],
                 existing_titles: list[str], threshold: float,
                 content: str = "",
                 existing_signatures: list[set] | None = None,
                 kw_threshold: float = 0.5) -> tuple[bool, str]:
    """Dedup in three layers: exact URL, fuzzy title (SequenceMatcher), and
    keyword-signature overlap (catches the same event reported by two
    sources with reworded titles)."""
    if url in existing_urls:
        return True, "url"
    norm = normalize_title(title)
    for existing in existing_titles:
        ratio = SequenceMatcher(None, norm, existing).ratio()
        if ratio >= threshold:
            return True, "title"
    if existing_signatures:
        sig = extract_keywords(title, content)
        for ex_sig in existing_signatures:
            if keyword_overlap(sig, ex_sig) >= kw_threshold:
                return True, "semantic"
    return False, ""
