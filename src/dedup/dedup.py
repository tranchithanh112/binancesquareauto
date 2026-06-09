import re
from difflib import SequenceMatcher
from unidecode import unidecode


_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    s = unidecode(title).lower()
    s = _PUNCT_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def is_duplicate(*, url: str, title: str, existing_urls: set[str],
                 existing_titles: list[str], threshold: float) -> tuple[bool, str]:
    if url in existing_urls:
        return True, "url"
    norm = normalize_title(title)
    for existing in existing_titles:
        ratio = SequenceMatcher(None, norm, existing).ratio()
        if ratio >= threshold:
            return True, "title"
    return False, ""
