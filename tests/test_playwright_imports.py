"""Smoke test — make sure the Playwright runner modules import cleanly."""
import importlib


def test_playwright_fetch_imports():
    mod = importlib.import_module("src.runners.playwright_fetch")
    assert hasattr(mod, "fetch_text")
    assert hasattr(mod, "fetch_html")
    assert hasattr(mod, "browser_session")


def test_playwright_post_imports():
    mod = importlib.import_module("src.runners.playwright_post")
    assert hasattr(mod, "post_to_binance_square")
    assert hasattr(mod, "open_browser_for_login")
    assert mod.BINANCE_SQUARE_URL == "https://www.binance.com/en/square"
