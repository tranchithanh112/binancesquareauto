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

# Keyword -> visual scene + mood. Matched against title+content (English or
# Vietnamese keywords) so the cover reflects the news tone — no LLM call.
_THEMES = [
    (("etf", "inflow", "institution", "blackrock", "quỹ"),
     "institutional money flowing into glowing futuristic vaults, bullish optimism"),
    (("hack", "exploit", "breach", "drain", "stolen", "rug", "tấn công"),
     "shattered coin among dark debris, red alarm glow, security breach"),
    (("surge", "rally", "soar", "ath", "all-time high", "pump", "breakout",
      "bứt phá", "tăng mạnh", "bùng nổ"),
     "a rocket blasting upward through clouds, green bullish energy, euphoria"),
    (("crash", "plunge", "dump", "selloff", "liquidation", "fear", "lao dốc",
      "giảm mạnh", "sập"),
     "coins tumbling down a stormy red descent, fear and volatility"),
    (("sec", "regulation", "lawsuit", "ban", "court", "ruling", "pháp lý",
      "quy định", "kiện"),
     "a courthouse with digital scales of justice over a glowing coin, serious tone"),
    (("whale", "wallet", "withdraw", "accumulat", "cá voi"),
     "a giant whale silhouette gliding over an ocean of glowing coins, ominous"),
    (("fed", "rate", "cpi", "inflation", "boj", "macro", "lãi suất", "vĩ mô"),
     "a global financial skyline with glowing economic data streams, tense macro mood"),
    (("halving", "upgrade", "mainnet", "launch", "ra mắt"),
     "a futuristic ceremony unveiling a radiant coin, milestone energy"),
]


def _theme_for(text: str) -> str:
    low = (text or "").lower()
    for keys, scene in _THEMES:
        if any(k in low for k in keys):
            return scene
    return "an epic symbolic crypto market scene, dynamic energy"


def build_image_prompt(title: str, coin: str, content: str,
                       claude_fn=None) -> str:
    """Build an English image prompt from the news WITHOUT an LLM call:
    pick a visual theme by keyword + the subject coin. claude_fn is accepted
    for backward compatibility but ignored (cost-saving)."""
    scene = _theme_for(f"{title} {content}")
    subj = coin or "cryptocurrency"
    return f"a symbolic scene about {subj} cryptocurrency, {scene}, {_STYLE}"


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
