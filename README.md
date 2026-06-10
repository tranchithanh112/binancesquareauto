# Binance Square Bot

Fully-automated bilingual (VI/EN) news bot for Binance Square. Scrapes
crypto news, rewrites via Claude Code CLI (headless), downloads + uploads
cover image, posts via official Binance Square OpenAPI. Targets ~30-40
posts/day for referral commission.

## How it works

```
        ┌─────────────┐   ┌────────────────┐   ┌──────────────────┐
RSS  ──▶│  --scrape   │──▶│ --auto-rewrite │──▶│   --post-next    │
feeds   │ (persists   │   │ (Claude CLI    │   │ (Binance OpenAPI │
        │  articles)  │   │  + image)      │   │  /content/add)   │
        └─────────────┘   └────────────────┘   └──────────────────┘
              │                   │                     │
              └───────────────────┴────────────┐        │
                                               ▼        ▼
                                       ┌──────────────────┐
                                       │   SQLite queue   │
                                       │  (articles,      │
                                       │   posts)         │
                                       └──────────────────┘
                                               │
                                               ▼
                                       ┌──────────────────┐
                                       │   Telegram bot   │
                                       │   notifications  │
                                       └──────────────────┘
```

## Requirements

- Windows 10/11 + PowerShell
- Python 3.11+
- Claude Code CLI (`claude` on PATH) — Pro plan recommended
- Binance Square OpenAPI key from https://www.binance.com/square/creator-center/home
- Telegram bot (BotFather) + your chat ID (@userinfobot)

## Setup

1. `python -m venv .venv; .venv\Scripts\activate`
2. `python -m pip install -r requirements.txt`
3. Copy `config/.env.example` to `config/.env` and fill in:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   BINANCE_SQUARE_OPENAPI_KEY=...
   ```
4. Run tests: `python -m pytest -q`
5. Manual smoke test:
   ```powershell
   python -m src.main --scrape
   python -m src.main --auto-rewrite --max-rewrites 2
   python -m src.main --post-next
   ```

## Full automation (Windows Task Scheduler)

Open elevated PowerShell, then:

```powershell
.\scripts\setup-tasks.ps1
```

This registers four jobs:

| Task | Schedule | Action |
|------|----------|--------|
| `BinanceSquareBot-Scrape` | 06:00, 12:00, 18:00, 22:00 | RSS scrape + dedup + persist |
| `BinanceSquareBot-Rewrite` | 06:05, 12:05, 18:05, 22:05 | Claude CLI rewrite + image upload, persist as pending posts |
| `BinanceSquareBot-Post` | every 30 min, 06:00–23:30 | Pop oldest pending, post via Binance OpenAPI |
| `BinanceSquareBot-Summary` | 23:55 | Telegram daily summary |

To remove: `.\scripts\remove-tasks.ps1`

## CLI reference

| Flag | Purpose |
|------|---------|
| `--scrape` | RSS scrape only, dedup, persist new articles. Fast, safe to run often. |
| `--auto-rewrite [--max-rewrites N]` | For each unposted article: call `claude -p` for bilingual rewrite, download cover image, upload to Binance, insert as pending post. |
| `--post-next` | Pop oldest pending post, publish via Binance OpenAPI, record result, Telegram notify. |
| `--batch morning\|evening` | Legacy: emits a SESSION-PLAN for manual Claude session execution. Not used in full-auto mode. |
| `--summary` | Telegram daily summary digest. |

## Architecture

- **`src/main.py`** — orchestrator. Each CLI flag triggers a discrete pipeline step.
- **`src/db/models.py`** — SQLite schema (articles, posts, dedup tables).
- **`src/scraper/rss_scraper.py`** — CoinDesk + CoinTelegraph RSS feeds.
- **`src/dedup/dedup.py`** — URL exact + diacritic-aware fuzzy title match.
- **`src/rewriter/`** — prompt templates + coin tag / importance classifier.
- **`src/runners/claude_cli.py`** — headless `claude -p` wrapper.
- **`src/runners/binance_openapi.py`** — official Binance Square API client (text + image post).
- **`src/runners/image_utils.py`** — RSS-HTML image extraction + download.
- **`src/notify/telegram.py`** — bot notifications.

## Key behaviors

- **Bilingual VI + EN** every post.
- **Cover image** auto-pulled from RSS feed HTML when available.
- **Hashtag sanitizer** caps total `#tag` count to 2 (Binance API limit).
- **Coin tags** auto-extracted from content (`$BTC`, `$ETH`, ...).
- **Dedup**: exact URL + fuzzy title (Vietnamese diacritic stripped).
- **DB-backed queue**: scrape and post run independently; restart-safe.
- **Cron-spread posting**: 1 post every 30 min, looks natural, stays under 100 posts/day Binance limit.

## Files / paths

```
config/
  settings.json   # schedule + source URLs + dedup config
  .env            # secrets (gitignored)
data/
  bot.db          # SQLite (gitignored)
logs/
  bot.log         # rolling log (gitignored)
scripts/
  setup-tasks.ps1
  remove-tasks.ps1
src/                # application code
tests/              # 34 pytest tests
docs/
  SESSION-DRIVER.md           # legacy Claude-session-driven flow (kept for reference)
  PLAYWRIGHT-SETUP.md         # legacy Playwright path (not used in full-auto)
  superpowers/
    specs/...     # original design spec
    plans/...     # original implementation plan
```

## Troubleshooting

- **`API error [220094]: Hashtag count exceeds the allowed limit`** — sanitizer keeps first 2 only; if prompt still produces too many, tighten `src/rewriter/prompts.py`.
- **Claude refuses to rewrite** — happens when running inside the project dir (auto-loads CLAUDE.md). `claude_cli.rewrite()` already runs from a tempdir to avoid this.
- **Image download fails** — falls back to text-only post.
- **Telegram alerts not arriving** — check `BINANCE_SQUARE_OPENAPI_KEY` and `TELEGRAM_*` in `config/.env`; `--summary` sends a test message.

## Limits

- Binance: 100 posts/day, 400 uploads/day per account.
- Claude Pro: subject to fair-use limits — 30-40 calls/day to `claude -p` is well within budget.
