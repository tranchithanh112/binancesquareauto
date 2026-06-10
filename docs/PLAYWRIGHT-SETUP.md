# Playwright Setup (First Run)

The bot uses Playwright with a persistent Chrome profile to scrape sites
Claude Code's MCP browser tools cannot reach (Reuters, CoinGecko, X) and to
post to Binance Square.

## Install

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

The profile is stored at `data/chrome_profile/` (created on first run,
git-ignored).

## First-time Binance Square login

Run the login helper:

```bash
python -c "from src.runners.playwright_post import open_browser_for_login; open_browser_for_login()"
```

A Chromium window opens at the Binance login page. Complete the login
(including 2FA), then close the window. Cookies are saved into the
persistent profile and reused on every later run.

## X / Nitter

Same idea — if you want logged-in X scraping, navigate to https://x.com in
the same profile and log in once. Otherwise the bot falls back to Nitter
mirrors (no login required).

## How the runners get used

```python
from src.runners.playwright_fetch import fetch_text
from src.runners.playwright_post import post_to_binance_square

text = fetch_text("https://www.coingecko.com/en/news")
# Claude session parses items from `text`, calls save_scraped(...)

status, err = post_to_binance_square(
    content_vi="...", content_en="...",
    coin_tags=["BTC", "ETH"], scheduled_iso="2026-06-09T08:30:00Z",
)
```
