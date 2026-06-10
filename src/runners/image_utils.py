"""
Image extraction + download for use as Binance Square post covers.

RSS feeds (CoinTelegraph etc.) embed primary images in HTML content.
This module pulls the first <img src> and downloads it to a tempfile.
"""
from __future__ import annotations
import os
import re
import tempfile
from typing import Optional

import requests
from bs4 import BeautifulSoup


_IMG_TAG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)


def extract_image_url(html: str) -> Optional[str]:
    """Return first <img src> URL found in HTML, or None."""
    if not html:
        return None
    m = _IMG_TAG_RE.search(html)
    if m:
        return m.group(1)
    try:
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    except Exception:
        pass
    return None


def download_to_temp(url: str, *, timeout: int = 30) -> tuple[Optional[str], Optional[str]]:
    """Download image URL to a tempfile. Returns (path, error)."""
    if not url:
        return None, "empty url"
    try:
        resp = requests.get(url, timeout=timeout, stream=True,
                            headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException as e:
        return None, f"download error: {e}"
    if not resp.ok:
        return None, f"download HTTP {resp.status_code}"
    ext = ".jpg"
    ct = resp.headers.get("Content-Type", "").lower()
    if "png" in ct:
        ext = ".png"
    elif "webp" in ct:
        ext = ".webp"
    elif "gif" in ct:
        ext = ".gif"
    else:
        path_lower = url.lower().split("?", 1)[0]
        for candidate in (".png", ".webp", ".gif", ".jpeg", ".jpg"):
            if path_lower.endswith(candidate):
                ext = ".jpg" if candidate == ".jpeg" else candidate
                break
    fd, path = tempfile.mkstemp(suffix=ext, prefix="bn_img_")
    try:
        with os.fdopen(fd, "wb") as f:
            for chunk in resp.iter_content(8192):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        try:
            os.unlink(path)
        except Exception:
            pass
        return None, f"write error: {e}"
    return path, None
