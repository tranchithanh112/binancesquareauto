"""
Scrape a public Telegram channel via its web preview (t.me/s/<channel>).
No login, no bot, no API key — just HTML. Filters ads/promos and stale posts.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup


# Promo / ad signals — skip messages that look like self-promotion or spam.
_AD_PATTERNS = [
    r"ref=", r"/join\?", r"\bairdrop\b", r"khuyến mãi", r"ưu đãi", r"giảm giá",
    r"đăng ký ngay", r"nhận thưởng", r"link dưới", r"link bio", r"code\s*:",
    r"mã giới thiệu", r"hoa hồng", r"khóa học", r"\bvip\b", r"group vip",
    r"\bcourse\b", r"đăng ký kênh", r"contact admin", r"liên hệ admin",
    r"quảng cáo", r"tài trợ", r"sponsor", r"\bpartner\b",
]
_AD_RE = re.compile("|".join(_AD_PATTERNS), re.IGNORECASE)
_TME_INVITE_RE = re.compile(r"t\.me/(joinchat|\+)")


def _is_ad(text: str) -> bool:
    if _AD_RE.search(text):
        return True
    if _TME_INVITE_RE.search(text):
        return True
    if len(text.strip()) < 60:
        return True
    letters = sum(c.isalpha() for c in text)
    if letters < 40:
        return True
    return False


def _parse_time(msg) -> Optional[datetime]:
    t = msg.select_one("a.tgme_widget_message_date time[datetime]")
    if t and t.get("datetime"):
        try:
            return datetime.fromisoformat(t["datetime"]).astimezone(timezone.utc)
        except Exception:
            return None
    return None


def scrape_channel(channel: str, *, max_items: int = 15, max_age_hours: int = 24,
                   timeout: int = 20) -> list[dict]:
    """Return recent non-ad messages from a public channel as article dicts."""
    url = f"https://t.me/s/{channel}"
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return []
    if not r.ok:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    now = datetime.now(timezone.utc)
    out: list[dict] = []
    for msg in reversed(soup.select("div.tgme_widget_message")):
        text_el = msg.select_one("div.tgme_widget_message_text")
        if not text_el:
            continue
        text = text_el.get_text(" ", strip=True)
        if not text or _is_ad(text):
            continue
        published = _parse_time(msg)
        if published and (now - published) > timedelta(hours=max_age_hours):
            continue
        post_id = msg.get("data-post")
        link = f"https://t.me/{post_id}" if post_id else url
        out.append({
            "source": f"tg::{channel}",
            "url": link,
            "title": text[:80],
            "content": text,
            "scraped_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        if len(out) >= max_items:
            break
    return out
