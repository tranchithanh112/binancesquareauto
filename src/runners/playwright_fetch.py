"""
Generic Playwright-based page fetcher with persistent Chrome profile.
First run prompts user to log in to any sites that need auth (X, Nitter, etc.).
Subsequent runs reuse the profile and stay logged in.
"""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from playwright.sync_api import sync_playwright, Browser


DEFAULT_PROFILE_DIR = Path("data/chrome_profile")


@contextmanager
def browser_session(profile_dir: Path = DEFAULT_PROFILE_DIR,
                    headless: bool = False) -> Iterator[Browser]:
    """Yield a persistent Chromium context. Profile dir survives across runs."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            yield ctx
        finally:
            ctx.close()


def fetch_text(url: str, *, wait_selector: Optional[str] = None,
               timeout_ms: int = 30000,
               profile_dir: Path = DEFAULT_PROFILE_DIR) -> str:
    """Navigate to URL, return visible page text. Used for Reuters, CoinGecko,
    Google News, etc. Caller parses items from the returned text in-brain."""
    with browser_session(profile_dir=profile_dir) as ctx:
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=timeout_ms)
            except Exception:
                pass
        page.wait_for_timeout(2000)
        text = page.evaluate("() => document.body.innerText")
        return text or ""


def fetch_html(url: str, *, timeout_ms: int = 30000,
               profile_dir: Path = DEFAULT_PROFILE_DIR) -> str:
    """Return full rendered HTML — useful when caller needs links not text."""
    with browser_session(profile_dir=profile_dir) as ctx:
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2000)
        return page.content()
