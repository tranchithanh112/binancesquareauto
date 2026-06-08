# Binance Square Bot

Auto-posting bot for Binance Square. Scrapes crypto news, rewrites bilingual (VI/EN), schedules 20-30 posts/day in two batches.

## Setup

1. `python -m venv .venv && .venv\Scripts\activate`  (Windows) or `source .venv/bin/activate` (Linux/Mac)
2. `pip install -r requirements.txt`
3. Copy `config/.env.example` to `config/.env` and fill in Telegram credentials.
4. Manually log in to Binance Square in Chrome.
5. Run a batch manually: `python -m src.main --batch morning`

## Scheduling

Use Claude Code `/schedule`:
- `/schedule cron "0 8 * * *" python -m src.main --batch morning`
- `/schedule cron "0 20 * * *" python -m src.main --batch evening`
- `/schedule cron "0 23 * * *" python -m src.main --summary`

See `docs/superpowers/specs/2026-06-08-binance-square-bot-design.md` for full design.
