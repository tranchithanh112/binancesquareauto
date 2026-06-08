# Binance Square Auto-Posting Bot — Design Spec

**Date:** 2026-06-08
**Status:** Draft for review
**Author:** Brainstorm session with user

---

## Overview

An auto-posting bot that scrapes crypto news from trusted sources, rewrites content into bilingual Vietnamese/English posts using Claude Code, tags relevant coins (e.g., `$BTC`, `$ETH`) for Binance Square's built-in referral system, and schedules 20-30 posts per day across two batches. Runs via Claude Code's `/schedule` cron with browser automation against an already-logged-in Binance Square session. Sends Telegram notifications after each batch.

**Goal:** Daily referral commission revenue from Binance Square posts driven by high-quality, timely, deduplicated crypto news.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│             Claude Code + /schedule              │
│                                                  │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐  │
│  │  Scraper   │──▶│ Rewriter  │──▶│  Poster   │  │
│  │ (Browser+ │   │ (Claude)  │   │ (Browser) │  │
│  │   RSS)    │   │           │   │           │  │
│  └───────────┘   └───────────┘   └───────────┘  │
│       │               │               │          │
│       ▼               ▼               ▼          │
│  ┌─────────────────────────────────────────┐     │
│  │           SQLite DB                      │     │
│  │  - articles (raw scraped)                │     │
│  │  - posts (rewritten + posted)            │     │
│  │  - dedup (URL + normalized title)        │     │
│  └─────────────────────────────────────────┘     │
│                      │                           │
│                      ▼                           │
│              ┌──────────────┐                    │
│              │ Telegram Bot │                    │
│              │  (Reports)   │                    │
│              └──────────────┘                    │
└─────────────────────────────────────────────────┘
```

**Per-batch flow:**
1. Scraper opens browser / hits RSS, collects headlines + content from configured sources
2. Dedup check (exact URL + fuzzy title match) against SQLite
3. Claude rewrites new articles into Vietnamese + English, choosing short or long format based on importance
4. Poster opens Binance Square, schedules each post with 20-30 min spacing
5. Failed posts retried once at end of batch
6. Telegram report sent: success / fail / skip counts per source

**Run schedule:** 8h morning + 20h evening (GMT+7). Daily summary at 23h.

---

## News Sources

| Source | Type | Scrape method | Priority |
|--------|------|---------------|----------|
| CoinDesk | Crypto news | RSS + browser fallback | High |
| CoinTelegraph | Crypto news | RSS + browser fallback | High |
| CoinGecko | Trending coins | Browser scrape trending page | Medium |
| Reuters (Crypto) | Finance / regulation | Browser scrape | High |
| X / Twitter | Influencers (Elon Musk, MicroStrategy/Saylor, CZ, Vitalik) | Browser scrape profile pages | High |
| Google News | Political news affecting crypto | Browser search ("crypto regulation", "Fed rate", "SEC crypto") | Medium |

**Scrape strategy:**
- RSS first (CoinDesk, CoinTelegraph) — fastest, most stable
- Browser fallback when RSS unavailable or insufficient
- Cap: 10 latest articles per source
- Filter: only articles within last 12 hours

**Importance classification (auto):**
- **High** → long analysis format: Fed actions, SEC rulings, BTC ATH, major hacks, regulatory shifts
- **Normal** → short news format: minor pump/dump, partnerships, listings
- Claude judges per article during rewrite based on content

**Coin tag extraction:**
- Parse content for ticker symbols (BTC, ETH, SOL, etc.)
- Map to Binance Square `$TICKER` tag format

---

## Content Rewriting

Claude Code rewrites in-session — no external LLM API. Each raw article produces a single post containing Vietnamese + English versions.

**Short format (~80% of posts):**
```
[Catchy title]

[2-3 paragraphs summary, ~100-150 words]

[Tags: $BTC $ETH ...]

---

[English version - same structure]
```

**Long format (~20% of posts, high-importance only):**
```
[Title with relevant emoji]

[Event summary]
[Market impact analysis]
[Short-term trend outlook]
[Conclusion + what to watch]

[Tags: $BTC $ETH ...]

---

[English version - same structure]
```

**Rewrite rules:**
- Never copy verbatim — full rewrite, preserve facts
- Tone: professional but accessible, not overly formal
- Append trending hashtags (`#Bitcoin`, `#Crypto`, `#BullRun`...)
- Small disclaimer at end: "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư" / "This is aggregated news, not investment advice"
- Vary phrasing and angle across posts to avoid duplicate-content patterns

---

## Binance Square Posting

**Pre-condition:** User has manually logged into Binance Square in Chrome. Bot reuses the logged-in browser session via Claude Code's MCP browser tools.

**Per-post flow:**
1. Navigate to Binance Square create-post page
2. Paste rewritten content
3. Insert coin tags (`$BTC`, `$ETH`...) using Binance Square's tag UI
4. Set schedule time (post N: base_time + N * random(20, 30) minutes)
5. Click schedule / publish
6. Verify success
7. Log result to SQLite

**Schedule windows:**
- Morning batch (08:00 start): posts schedule 08:00 → ~12:30
- Evening batch (20:00 start): posts schedule 20:00 → ~00:30 next day
- Inter-post delay: random 20-30 min (avoid pattern detection)

**Error handling — Skip + retry strategy:**
- Per-post failure → log error, skip, continue to next
- End of batch → retry all failed posts once
- Still failing → log, include in Telegram report
- Whole-batch blocker (Binance Square down, browser crash) → abort, Telegram alert

**Anti-detection:**
- Random 2-5s delay between UI actions
- Use schedule posting (not instant) — more natural
- Vary post timing within configured range

---

## Database Schema (SQLite)

```sql
articles (
  id INTEGER PRIMARY KEY,
  source TEXT,                  -- 'coindesk', 'reuters', 'x_elonmusk', ...
  url TEXT UNIQUE,
  title TEXT,
  content TEXT,
  scraped_at DATETIME,          -- ISO 8601 UTC, e.g. '2026-06-08T01:00:00Z'
  importance TEXT               -- 'high' or 'normal'
)

posts (
  id INTEGER PRIMARY KEY,
  article_id INTEGER REFERENCES articles(id),
  content_vi TEXT,
  content_en TEXT,
  coin_tags TEXT,               -- JSON array, e.g. '["BTC","ETH"]'
  format TEXT,                  -- 'short' or 'long'
  status TEXT,                  -- 'pending','scheduled','posted','failed'
  scheduled_time DATETIME,      -- ISO 8601 UTC
  posted_at DATETIME,           -- ISO 8601 UTC
  error_msg TEXT,
  batch TEXT                    -- 'morning' or 'evening'
)

dedup (
  id INTEGER PRIMARY KEY,
  url TEXT UNIQUE,
  title_normalized TEXT,        -- lowercase, no diacritics, no punctuation
  created_at DATETIME           -- ISO 8601 UTC
)
```

**Dedup logic:**
1. Exact URL match against `dedup.url` → skip
2. Normalize title (lowercase, strip diacritics, strip punctuation), fuzzy match against `dedup.title_normalized` via similarity ratio > 0.8 → skip
3. Pass both → new article, insert into `dedup` + `articles`

**Cleanup:** Delete `dedup` and `articles` records older than 30 days (run at end of each batch).

---

## Telegram Notifications

Single Telegram bot (created via @BotFather), sends messages to user's chat ID. Credentials in `.env`.

**1. Batch report (after each batch):**
```
📊 Binance Square Bot — Morning batch 08/06/2026

✅ Posted: 12
❌ Failed: 1
⏭️ Skipped (dup): 3
🔄 Retry success: 1

📰 Sources: CoinDesk(4), Reuters(3), X(3), CoinTelegraph(2), CoinGecko(1)
⏰ Schedule window: 08:00 - 12:30
```

**2. Error alert (critical errors):**
```
🚨 Bot Error — 08/06/2026 08:15

Binance Square UI failed to load.
Retried once — still failing.
Manual check required.
```

**3. Daily summary (23:00):**
```
📈 Daily Summary — 08/06/2026

Total posted: 25/30
Success: 23
Failed: 2
Top coins: $BTC(8), $ETH(5), $SOL(3)
```

---

## Project Structure

```
BinanceSquare/
├── config/
│   ├── settings.json
│   └── .env
├── src/
│   ├── scraper/
│   │   ├── rss_scraper.py
│   │   ├── browser_scraper.py
│   │   └── x_scraper.py
│   ├── rewriter/
│   │   └── prompts.py
│   ├── poster/
│   │   └── binance_poster.py
│   ├── dedup/
│   │   └── dedup.py
│   ├── notify/
│   │   └── telegram.py
│   ├── db/
│   │   ├── models.py
│   │   └── cleanup.py
│   └── main.py
├── data/
│   └── bot.db
├── logs/
│   └── bot.log
├── requirements.txt
└── README.md
```

**`config/settings.json`:**
```json
{
  "schedule": {
    "morning_hour": 8,
    "evening_hour": 20,
    "post_interval_min": 20,
    "post_interval_max": 30,
    "posts_per_batch": 15
  },
  "sources": {
    "coindesk_rss": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph_rss": "https://cointelegraph.com/rss",
    "reuters_url": "https://www.reuters.com/technology/cryptocurrency/",
    "coingecko_url": "https://www.coingecko.com/en/news",
    "x_accounts": ["elonmusk", "saylor", "VitalikButerin", "cz_binance"]
  },
  "scrape": {
    "max_articles_per_source": 10,
    "max_age_hours": 12
  },
  "dedup": {
    "similarity_threshold": 0.8,
    "cleanup_days": 30
  }
}
```

**Tech stack:**
- Python 3.11+
- SQLite (stdlib)
- `feedparser` — RSS parsing
- `difflib` (stdlib) — fuzzy title matching
- `requests` — Telegram API calls
- Browser automation via Claude Code MCP browser tools (no separate Playwright install needed)

---

## Execution Model

**Scheduling:** Claude Code `/schedule` cron jobs (preferred):
```
/schedule cron "0 8 * * *"  run-batch-morning
/schedule cron "0 20 * * *" run-batch-evening
/schedule cron "0 23 * * *" send-daily-summary
```

**Entry point `src/main.py`:**
1. Parse args: `--batch morning|evening` or `--summary`
2. Load config
3. Scrape all sources (parallel where possible)
4. Dedup against DB
5. Claude rewrites each new article in-session
6. Open Binance Square browser session
7. Schedule each post with random inter-post delay
8. Retry failed posts at end of batch
9. Update DB statuses
10. Send Telegram batch report
11. Run DB cleanup

**Failure modes:**
- Source scrape fail → skip source, use remaining sources to fill `posts_per_batch`
- Insufficient new articles → post whatever is available, note in Telegram report
- Binance Square unavailable → abort batch, send Telegram error alert
- Telegram send fail → log locally, do not block batch

---

## Out of Scope (v1)

- Auto-login (manual login required)
- Multi-account support
- Image / chart attachments
- A/B testing post formats
- Analytics on which posts drive most referral commission
- Web dashboard for monitoring

These may be addressed in v2 once v1 is operational.

---

## Open Questions / Risks

1. **Binance Square ToS** — auto-posting may violate ToS. Risk of account ban. User accepts this risk.
2. **UI changes** — Binance Square frontend changes will break the poster. Mitigation: clear error logs + Telegram alerts so user can patch quickly.
3. **X/Twitter scraping** — without login, X scraping is rate-limited and unreliable. May need to fall back to RSS aggregators (e.g., Nitter) or skip X source.
4. **RSS source URL stability** — RSS feed URLs may change. Monitor + update config when broken.

---

## Success Criteria

v1 lands when: bot can run a morning batch end-to-end, post 10+ scheduled articles to Binance Square, dedupe correctly across batches, and send a Telegram report. Two consecutive successful days = ready for daily operation.
