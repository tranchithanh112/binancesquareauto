"""
AI illustration generator for post covers — replaces the boring price chart.

Uses Pollinations.ai (free, no API key): a GET to
https://image.pollinations.ai/prompt/<url-encoded prompt> returns a PNG.

The image prompt is written by Claude from the article so the picture
actually matches the news; falls back to a generic crypto-art prompt.
"""
from __future__ import annotations
import os
import random
import tempfile
from urllib.parse import quote
from typing import Optional

import requests


POLLINATIONS = "https://image.pollinations.ai/prompt/"

_STYLE = ("vibrant cinematic digital illustration, crypto finance theme, "
          "dramatic neon lighting, highly detailed, trending on artstation, "
          "NO text, NO words, NO letters, NO charts")


def build_image_prompt(title: str, coin: str, content: str,
                       claude_fn=None) -> str:
    """Ask Claude for a vivid English scene describing the news. Falls back to
    a generic crypto-art prompt if the call fails or no claude_fn given."""
    fallback = f"a powerful symbolic scene about {coin or 'cryptocurrency'} and the crypto market, {_STYLE}"
    if claude_fn is None:
        return fallback
    ask = (
        "Viết MỘT câu mô tả cảnh minh hoạ bằng TIẾNG ANH (dưới 25 từ) cho tin "
        "crypto dưới đây, để tạo ảnh AI. Chỉ tả CẢNH/HÌNH ẢNH ẩn dụ, KHÔNG chữ "
        "trong ảnh, KHÔNG biểu đồ. Chỉ xuất đúng câu đó, không giải thích.\n\n"
        f"Tiêu đề: {title}\nNội dung: {content[:400]}"
    )
    try:
        out, err = claude_fn(ask)
    except Exception:
        return fallback
    if err or not out:
        return fallback
    scene = out.strip().strip('"').splitlines()[0][:200]
    if len(scene) < 8:
        return fallback
    return f"{scene}, {_STYLE}"


def generate_image(prompt: str, *, width: int = 1024, height: int = 576,
                   timeout: int = 90,
                   out_path: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Render `prompt` via Pollinations, save PNG to a tempfile.
    Returns (path, error)."""
    if not prompt:
        return None, "empty prompt"
    seed = random.randint(1, 10_000_000)
    url = (f"{POLLINATIONS}{quote(prompt)}"
           f"?width={width}&height={height}&nologo=true&seed={seed}")
    try:
        resp = requests.get(url, timeout=timeout,
                            headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException as e:
        return None, f"http error: {e}"
    if not resp.ok or not resp.content:
        return None, f"http {resp.status_code}"
    ctype = resp.headers.get("Content-Type", "")
    if "image" not in ctype:
        return None, f"not an image ({ctype})"
    if out_path is None:
        fd, out_path = tempfile.mkstemp(suffix=".png", prefix="bn_ai_")
        os.close(fd)
    try:
        with open(out_path, "wb") as f:
            f.write(resp.content)
    except Exception as e:
        return None, f"write error: {e}"
    return out_path, None
