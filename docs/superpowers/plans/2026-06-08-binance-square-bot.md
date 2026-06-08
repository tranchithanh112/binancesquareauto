# Binance Square Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bilingual (Vietnamese/English) Binance Square auto-posting bot that scrapes crypto news, rewrites it via Claude Code in-session, schedules 20-30 deduplicated posts per day in two batches, and reports results to Telegram.

**Architecture:** Python 3.11 project. SQLite for state and dedup. RSS feeds where available, browser scraping for the rest. Posting via Claude Code MCP browser tools against a manually logged-in Binance Square session. Two daily batches at 08:00 and 20:00 GMT+7 via Claude Code `/schedule`. Telegram bot notifies after each batch and daily summary.

**Tech Stack:** Python 3.11, SQLite (stdlib), `feedparser`, `requests`, `python-dotenv`, `unidecode`, `pytest` for tests, `difflib` (stdlib) for fuzzy matching.

---

## File Structure

```
BinanceSquare/
├── config/
│   ├── settings.json
│   └── .env.example
├── src/
│   ├── __init__.py
│   ├── config.py                # Loads settings.json + .env
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py            # Schema init + CRUD
│   │   └── cleanup.py           # Purge >30d records
│   ├── dedup/
│   │   ├── __init__.py
│   │   └── dedup.py             # URL exact + fuzzy title
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── rss_scraper.py       # CoinDesk, CoinTelegraph
│   │   ├── browser_scraper.py   # Reuters, CoinGecko, Google News (Claude-driven)
│   │   └── x_scraper.py         # X profiles (Claude-driven)
│   ├── rewriter/
│   │   ├── __init__.py
│   │   ├── prompts.py           # Prompt templates for Claude
│   │   └── classifier.py        # Importance + coin tag extraction
│   ├── poster/
│   │   ├── __init__.py
│   │   ├── binance_poster.py    # Step-by-step posting recipe (Claude-driven)
│   │   └── scheduler.py         # Compute per-post scheduled_time
│   ├── notify/
│   │   ├── __init__.py
│   │   └── telegram.py          # Send batch / alert / summary
│   └── main.py                  # Orchestrator entry point
├── tests/
│   ├── __init__.py
│   ├── test_dedup.py
│   ├── test_models.py
│   ├── test_cleanup.py
│   ├── test_scheduler.py
│   ├── test_classifier.py
│   ├── test_rss_scraper.py
│   ├── test_telegram.py
│   └── test_config.py
├── data/                        # bot.db lives here at runtime
├── logs/
├── requirements.txt
├── README.md
└── .gitignore
```

**Test boundary:** Browser-driven modules (`browser_scraper`, `x_scraper`, `poster.binance_poster`) and the orchestrator use Claude Code MCP browser tools at runtime — they are **Claude recipes**, not pure Python. Tests cover the pure logic (dedup, models, scheduler, classifier, RSS parsing, Telegram HTTP, config loader). Browser modules are documented step-by-step procedures the Claude session executes.

---

## Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `README.md`
- Create: `config/settings.json`
- Create: `config/.env.example`
- Create: `data/.gitkeep`
- Create: `logs/.gitkeep`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
feedparser==6.0.11
requests==2.32.3
python-dotenv==1.0.1
unidecode==1.3.8
pytest==8.3.3
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.pytest_cache/
data/*.db
data/*.db-journal
logs/*.log
config/.env
.venv/
```

- [ ] **Step 3: Create config/settings.json**

```json
{
  "schedule": {
    "morning_hour": 8,
    "evening_hour": 20,
    "post_interval_min": 20,
    "post_interval_max": 30,
    "posts_per_batch": 15,
    "timezone": "Asia/Ho_Chi_Minh"
  },
  "sources": {
    "coindesk_rss": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph_rss": "https://cointelegraph.com/rss",
    "reuters_url": "https://www.reuters.com/technology/cryptocurrency/",
    "coingecko_url": "https://www.coingecko.com/en/news",
    "google_news_queries": ["crypto regulation", "Fed rate decision", "SEC crypto"],
    "x_accounts": ["elonmusk", "saylor", "VitalikButerin", "cz_binance"]
  },
  "scrape": {
    "max_articles_per_source": 10,
    "max_age_hours": 12
  },
  "dedup": {
    "similarity_threshold": 0.8,
    "cleanup_days": 30
  },
  "db_path": "data/bot.db",
  "log_path": "logs/bot.log"
}
```

- [ ] **Step 4: Create config/.env.example**

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

- [ ] **Step 5: Create README.md**

```markdown
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
```

- [ ] **Step 6: Create empty `__init__.py` files and `.gitkeep` placeholders**

```
src/__init__.py        (empty)
tests/__init__.py      (empty)
data/.gitkeep          (empty)
logs/.gitkeep          (empty)
```

- [ ] **Step 7: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold project structure and config"
```

---

## Task 2: Config loader

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
import json
from pathlib import Path
import pytest
from src.config import load_config, Config


def test_load_config_reads_settings_and_env(tmp_path, monkeypatch):
    settings = {
        "schedule": {"morning_hour": 8, "evening_hour": 20, "post_interval_min": 20,
                     "post_interval_max": 30, "posts_per_batch": 15, "timezone": "Asia/Ho_Chi_Minh"},
        "sources": {"coindesk_rss": "https://x", "cointelegraph_rss": "https://y",
                    "reuters_url": "https://r", "coingecko_url": "https://c",
                    "google_news_queries": ["q1"], "x_accounts": ["a1"]},
        "scrape": {"max_articles_per_source": 10, "max_age_hours": 12},
        "dedup": {"similarity_threshold": 0.8, "cleanup_days": 30},
        "db_path": "data/bot.db",
        "log_path": "logs/bot.log"
    }
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))
    env_path = tmp_path / ".env"
    env_path.write_text("TELEGRAM_BOT_TOKEN=abc\nTELEGRAM_CHAT_ID=123\n")

    cfg = load_config(settings_path=settings_path, env_path=env_path)

    assert isinstance(cfg, Config)
    assert cfg.telegram_bot_token == "abc"
    assert cfg.telegram_chat_id == "123"
    assert cfg.schedule["morning_hour"] == 8
    assert cfg.sources["coindesk_rss"] == "https://x"
    assert cfg.db_path == "data/bot.db"


def test_load_config_missing_telegram_raises(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"schedule": {}, "sources": {}, "scrape": {}, "dedup": {},
                                          "db_path": "x", "log_path": "y"}))
    env_path = tmp_path / ".env"
    env_path.write_text("")
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        load_config(settings_path=settings_path, env_path=env_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Implement loader**

```python
# src/config.py
import json
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Config:
    schedule: dict
    sources: dict
    scrape: dict
    dedup: dict
    db_path: str
    log_path: str
    telegram_bot_token: str
    telegram_chat_id: str


def load_config(settings_path: Path | str = "config/settings.json",
                env_path: Path | str = "config/.env") -> Config:
    settings_path = Path(settings_path)
    env_path = Path(env_path)
    load_dotenv(env_path, override=True)

    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN missing in .env")
    if not chat:
        raise ValueError("TELEGRAM_CHAT_ID missing in .env")

    return Config(
        schedule=settings["schedule"],
        sources=settings["sources"],
        scrape=settings["scrape"],
        dedup=settings["dedup"],
        db_path=settings["db_path"],
        log_path=settings["log_path"],
        telegram_bot_token=token,
        telegram_chat_id=chat,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): add settings + env loader"
```

---

## Task 3: Database models

**Files:**
- Create: `src/db/__init__.py` (empty)
- Create: `src/db/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py
import json
from src.db.models import Database


def test_init_creates_tables(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    aid = db.insert_article(source="coindesk", url="https://x/1", title="t",
                            content="c", scraped_at="2026-06-08T01:00:00Z", importance="high")
    rows = db.list_articles_unposted()
    assert len(rows) == 1
    assert rows[0]["id"] == aid
    assert rows[0]["source"] == "coindesk"


def test_insert_post_and_update_status(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    aid = db.insert_article(source="reuters", url="https://r/1", title="t",
                            content="c", scraped_at="2026-06-08T01:00:00Z", importance="normal")
    pid = db.insert_post(article_id=aid, content_vi="vi", content_en="en",
                         coin_tags=["BTC"], format="short", batch="morning",
                         scheduled_time="2026-06-08T08:00:00Z")
    db.update_post_status(pid, status="posted", posted_at="2026-06-08T08:01:00Z")
    posts = db.list_posts_by_batch("morning")
    assert posts[0]["status"] == "posted"
    assert json.loads(posts[0]["coin_tags"]) == ["BTC"]


def test_dedup_insert_and_check(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    db.insert_dedup(url="https://x/1", title_normalized="bitcoin hits new high",
                    created_at="2026-06-08T01:00:00Z")
    assert db.dedup_url_exists("https://x/1") is True
    assert db.dedup_url_exists("https://x/2") is False
    titles = db.list_dedup_titles()
    assert "bitcoin hits new high" in titles
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement Database**

```python
# src/db/models.py
import json
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    importance TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    content_vi TEXT NOT NULL,
    content_en TEXT NOT NULL,
    coin_tags TEXT NOT NULL,
    format TEXT NOT NULL,
    status TEXT NOT NULL,
    scheduled_time TEXT,
    posted_at TEXT,
    error_msg TEXT,
    batch TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dedup (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title_normalized TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dedup_title ON dedup(title_normalized);
CREATE INDEX IF NOT EXISTS idx_posts_batch ON posts(batch);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    def insert_article(self, *, source: str, url: str, title: str, content: str,
                       scraped_at: str, importance: str) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO articles(source,url,title,content,scraped_at,importance) "
                "VALUES (?,?,?,?,?,?)",
                (source, url, title, content, scraped_at, importance),
            )
            return cur.lastrowid

    def list_articles_unposted(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT a.* FROM articles a "
                "LEFT JOIN posts p ON p.article_id = a.id "
                "WHERE p.id IS NULL ORDER BY a.scraped_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_post(self, *, article_id: int, content_vi: str, content_en: str,
                    coin_tags: list[str], format: str, batch: str,
                    scheduled_time: str | None = None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO posts(article_id,content_vi,content_en,coin_tags,format,"
                "status,scheduled_time,batch) VALUES (?,?,?,?,?,?,?,?)",
                (article_id, content_vi, content_en, json.dumps(coin_tags),
                 format, "pending", scheduled_time, batch),
            )
            return cur.lastrowid

    def update_post_status(self, post_id: int, *, status: str,
                           posted_at: str | None = None,
                           error_msg: str | None = None) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE posts SET status=?, posted_at=COALESCE(?,posted_at), "
                "error_msg=COALESCE(?,error_msg) WHERE id=?",
                (status, posted_at, error_msg, post_id),
            )

    def list_posts_by_batch(self, batch: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM posts WHERE batch=? ORDER BY scheduled_time", (batch,)
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_dedup(self, *, url: str, title_normalized: str, created_at: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO dedup(url,title_normalized,created_at) VALUES (?,?,?)",
                (url, title_normalized, created_at),
            )

    def dedup_url_exists(self, url: str) -> bool:
        with self._conn() as c:
            row = c.execute("SELECT 1 FROM dedup WHERE url=?", (url,)).fetchone()
            return row is not None

    def list_dedup_titles(self) -> list[str]:
        with self._conn() as c:
            rows = c.execute("SELECT title_normalized FROM dedup").fetchall()
            return [r["title_normalized"] for r in rows]

    def list_posts_for_summary(self, since_iso: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM posts WHERE posted_at >= ? OR scheduled_time >= ?",
                (since_iso, since_iso),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_failed_posts_by_batch(self, batch: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM posts WHERE batch=? AND status='failed'", (batch,)
            ).fetchall()
            return [dict(r) for r in rows]
```

- [ ] **Step 4: Create empty `src/db/__init__.py`**

Empty file.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 6: Commit**

```bash
git add src/db/ tests/test_models.py
git commit -m "feat(db): add SQLite schema and CRUD"
```

---

## Task 4: Dedup module

**Files:**
- Create: `src/dedup/__init__.py` (empty)
- Create: `src/dedup/dedup.py`
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_dedup.py
from src.dedup.dedup import normalize_title, is_duplicate


def test_normalize_strips_diacritics_punctuation_lowercase():
    assert normalize_title("Bitcoin Đạt Đỉnh Mới!") == "bitcoin dat dinh moi"
    assert normalize_title("BTC hits $100,000?") == "btc hits 100000"
    assert normalize_title("  Multiple   Spaces  ") == "multiple spaces"


def test_is_duplicate_exact_url():
    existing_urls = {"https://x/1"}
    existing_titles: list[str] = []
    dup, reason = is_duplicate(url="https://x/1", title="Anything",
                               existing_urls=existing_urls,
                               existing_titles=existing_titles, threshold=0.8)
    assert dup is True
    assert reason == "url"


def test_is_duplicate_fuzzy_title():
    existing_urls: set[str] = set()
    existing_titles = ["bitcoin hits new all time high"]
    dup, reason = is_duplicate(url="https://x/new",
                               title="Bitcoin Hits New All-Time High!",
                               existing_urls=existing_urls,
                               existing_titles=existing_titles, threshold=0.8)
    assert dup is True
    assert reason == "title"


def test_is_duplicate_distinct_title_passes():
    existing_urls: set[str] = set()
    existing_titles = ["bitcoin hits new all time high"]
    dup, _ = is_duplicate(url="https://x/new",
                          title="Ethereum upgrade ships successfully",
                          existing_urls=existing_urls,
                          existing_titles=existing_titles, threshold=0.8)
    assert dup is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dedup.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement dedup**

```python
# src/dedup/dedup.py
import re
from difflib import SequenceMatcher
from unidecode import unidecode


_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    s = unidecode(title).lower()
    s = _PUNCT_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def is_duplicate(*, url: str, title: str, existing_urls: set[str],
                 existing_titles: list[str], threshold: float) -> tuple[bool, str]:
    if url in existing_urls:
        return True, "url"
    norm = normalize_title(title)
    for existing in existing_titles:
        ratio = SequenceMatcher(None, norm, existing).ratio()
        if ratio >= threshold:
            return True, "title"
    return False, ""
```

- [ ] **Step 4: Create empty `src/dedup/__init__.py`**

Empty file.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_dedup.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 6: Commit**

```bash
git add src/dedup/ tests/test_dedup.py
git commit -m "feat(dedup): url and fuzzy title matching"
```

---

## Task 5: DB cleanup

**Files:**
- Create: `src/db/cleanup.py`
- Test: `tests/test_cleanup.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_cleanup.py
from src.db.models import Database
from src.db.cleanup import purge_old


def test_purge_old_removes_records_older_than_cutoff(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    db.insert_dedup(url="https://old/1", title_normalized="old title",
                    created_at="2026-01-01T00:00:00Z")
    db.insert_article(source="x", url="https://old/1", title="old", content="c",
                      scraped_at="2026-01-01T00:00:00Z", importance="normal")
    db.insert_dedup(url="https://new/1", title_normalized="new title",
                    created_at="2026-06-07T00:00:00Z")
    db.insert_article(source="x", url="https://new/1", title="new", content="c",
                      scraped_at="2026-06-07T00:00:00Z", importance="normal")

    purge_old(db, cutoff_iso="2026-05-09T00:00:00Z")

    assert db.dedup_url_exists("https://old/1") is False
    assert db.dedup_url_exists("https://new/1") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cleanup.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement cleanup**

```python
# src/db/cleanup.py
from datetime import datetime, timedelta, timezone
from src.db.models import Database


def cutoff_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def purge_old(db: Database, *, cutoff_iso: str) -> None:
    with db._conn() as c:
        c.execute("DELETE FROM dedup WHERE created_at < ?", (cutoff_iso,))
        c.execute(
            "DELETE FROM articles WHERE scraped_at < ? AND id NOT IN "
            "(SELECT article_id FROM posts WHERE posted_at >= ?)",
            (cutoff_iso, cutoff_iso),
        )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_cleanup.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/db/cleanup.py tests/test_cleanup.py
git commit -m "feat(db): cleanup old dedup and article records"
```

---

## Task 6: Post scheduler

**Files:**
- Create: `src/poster/__init__.py` (empty)
- Create: `src/poster/scheduler.py`
- Test: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_scheduler.py
from datetime import datetime
from src.poster.scheduler import compute_schedule_times


def test_compute_schedule_times_within_range():
    base = datetime(2026, 6, 8, 8, 0, 0)
    times = compute_schedule_times(base=base, count=5, min_minutes=20,
                                   max_minutes=30, seed=42)
    assert len(times) == 5
    assert times[0] == base
    for i in range(1, 5):
        delta = (times[i] - times[i - 1]).total_seconds() / 60
        assert 20 <= delta <= 30


def test_compute_schedule_times_deterministic_with_seed():
    base = datetime(2026, 6, 8, 8, 0, 0)
    a = compute_schedule_times(base=base, count=3, min_minutes=20, max_minutes=30, seed=1)
    b = compute_schedule_times(base=base, count=3, min_minutes=20, max_minutes=30, seed=1)
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement scheduler**

```python
# src/poster/scheduler.py
import random
from datetime import datetime, timedelta


def compute_schedule_times(*, base: datetime, count: int, min_minutes: int,
                           max_minutes: int, seed: int | None = None) -> list[datetime]:
    rng = random.Random(seed)
    times = [base]
    current = base
    for _ in range(count - 1):
        delta = rng.randint(min_minutes, max_minutes)
        current = current + timedelta(minutes=delta)
        times.append(current)
    return times
```

- [ ] **Step 4: Create empty `src/poster/__init__.py`**

Empty file.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/poster/ tests/test_scheduler.py
git commit -m "feat(poster): schedule time computation"
```

---

## Task 7: Classifier

**Files:**
- Create: `src/rewriter/__init__.py` (empty)
- Create: `src/rewriter/classifier.py`
- Test: `tests/test_classifier.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_classifier.py
from src.rewriter.classifier import extract_coin_tags, classify_importance


def test_extract_coin_tags_finds_known_tickers():
    text = "Bitcoin and Ethereum lead the rally; Solana follows."
    tags = extract_coin_tags(text)
    assert "BTC" in tags
    assert "ETH" in tags
    assert "SOL" in tags


def test_extract_coin_tags_dedups_and_uppercases():
    text = "btc btc ETH eth eth"
    tags = extract_coin_tags(text)
    assert tags.count("BTC") == 1
    assert tags.count("ETH") == 1


def test_extract_coin_tags_returns_btc_default_when_no_matches():
    tags = extract_coin_tags("Generic crypto market news with no specific coin mentioned.")
    assert tags == ["BTC"]


def test_classify_importance_high_keywords():
    assert classify_importance("Fed announces rate cut affecting markets") == "high"
    assert classify_importance("SEC approves Bitcoin spot ETF") == "high"
    assert classify_importance("Major hack drains $500M from protocol") == "high"


def test_classify_importance_normal_default():
    assert classify_importance("New partnership announced between project X and Y") == "normal"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_classifier.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement classifier**

```python
# src/rewriter/classifier.py
import re


COIN_MAP = {
    "BTC": [r"\bbitcoin\b", r"\bbtc\b"],
    "ETH": [r"\bethereum\b", r"\beth\b"],
    "SOL": [r"\bsolana\b", r"\bsol\b"],
    "BNB": [r"\bbnb\b", r"\bbinance coin\b"],
    "XRP": [r"\bxrp\b", r"\bripple\b"],
    "DOGE": [r"\bdoge\b", r"\bdogecoin\b"],
    "ADA": [r"\bada\b", r"\bcardano\b"],
    "AVAX": [r"\bavax\b", r"\bavalanche\b"],
    "LINK": [r"\blink\b", r"\bchainlink\b"],
    "MATIC": [r"\bmatic\b", r"\bpolygon\b"],
}

HIGH_IMPORTANCE_KEYWORDS = [
    r"\bfed\b", r"\bsec\b", r"\bsec approves\b", r"\bcpi\b", r"\brate cut\b",
    r"\brate hike\b", r"\betf approved\b", r"\bhack\b", r"\bdrains?\b",
    r"\bregulation\b", r"\bbanned?\b", r"\ball-?time high\b", r"\bath\b",
    r"\bhalving\b", r"\blawsuit\b", r"\bindictment\b",
]


def extract_coin_tags(text: str) -> list[str]:
    text_l = text.lower()
    found: list[str] = []
    for ticker, patterns in COIN_MAP.items():
        for pat in patterns:
            if re.search(pat, text_l):
                found.append(ticker)
                break
    if not found:
        return ["BTC"]
    return found


def classify_importance(text: str) -> str:
    text_l = text.lower()
    for pat in HIGH_IMPORTANCE_KEYWORDS:
        if re.search(pat, text_l):
            return "high"
    return "normal"
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_classifier.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add src/rewriter/ tests/test_classifier.py
git commit -m "feat(rewriter): coin tag extraction and importance classifier"
```

---

## Task 8: Rewriter prompts

**Files:**
- Create: `src/rewriter/prompts.py`
- Test: `tests/test_prompts.py`

- [ ] **Step 1: Implement prompts**

```python
# src/rewriter/prompts.py
"""
Prompt templates used by the Claude Code session when rewriting articles.
The orchestrator does not call an LLM API; the running Claude session itself
performs the rewrite. These templates document the contract.
"""

SHORT_TEMPLATE = """\
You are writing a Binance Square post in BOTH Vietnamese and English.

SOURCE ARTICLE
Title: {title}
Body: {content}
Importance: {importance}
Coin tags to weave in: {coin_tags}

REQUIREMENTS
- Short format: 2-3 paragraphs, ~100-150 words each language.
- Never copy verbatim; rewrite fully, preserve all facts.
- Professional but accessible tone, not overly formal.
- Append the coin tags in Binance Square format (e.g., $BTC $ETH).
- Add 2-3 trending hashtags (e.g., #Bitcoin #Crypto).
- End with disclaimer:
  VI: "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
  EN: "This is aggregated news, not investment advice."

OUTPUT FORMAT (return EXACTLY this structure)
---VI---
<vietnamese post>
---EN---
<english post>
---END---
"""

LONG_TEMPLATE = """\
You are writing a Binance Square ANALYSIS post in BOTH Vietnamese and English.

SOURCE ARTICLE
Title: {title}
Body: {content}
Importance: high
Coin tags: {coin_tags}

REQUIREMENTS
- Long format with sections: Event summary, Market impact, Short-term trend
  outlook, Conclusion + what to watch.
- ~250-350 words each language.
- Never copy verbatim; rewrite fully, preserve all facts.
- Professional analytical tone.
- Append coin tags in Binance Square format ($BTC, $ETH, ...).
- Add 3-4 trending hashtags.
- End with disclaimer:
  VI: "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
  EN: "This is aggregated news, not investment advice."

OUTPUT FORMAT (return EXACTLY this structure)
---VI---
<vietnamese post>
---EN---
<english post>
---END---
"""


def build_prompt(*, title: str, content: str, importance: str,
                 coin_tags: list[str]) -> str:
    tags_str = " ".join(f"${t}" for t in coin_tags)
    tmpl = LONG_TEMPLATE if importance == "high" else SHORT_TEMPLATE
    return tmpl.format(title=title, content=content, importance=importance,
                       coin_tags=tags_str)


def parse_output(output: str) -> tuple[str, str]:
    try:
        after_vi = output.split("---VI---", 1)[1]
        vi_part, after_en = after_vi.split("---EN---", 1)
        en_part = after_en.split("---END---", 1)[0]
        return vi_part.strip(), en_part.strip()
    except (IndexError, ValueError) as e:
        raise ValueError(f"Rewriter output not in expected format: {e}")
```

- [ ] **Step 2: Write parser tests**

```python
# tests/test_prompts.py
from src.rewriter.prompts import build_prompt, parse_output


def test_build_prompt_short_includes_title_and_tags():
    p = build_prompt(title="T", content="C", importance="normal", coin_tags=["BTC", "ETH"])
    assert "T" in p and "$BTC $ETH" in p and "Short format" in p


def test_build_prompt_long_for_high_importance():
    p = build_prompt(title="T", content="C", importance="high", coin_tags=["BTC"])
    assert "ANALYSIS" in p


def test_parse_output_extracts_vi_and_en():
    raw = "intro---VI---\nXin chao\n---EN---\nHello\n---END---tail"
    vi, en = parse_output(raw)
    assert vi == "Xin chao"
    assert en == "Hello"
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_prompts.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 4: Commit**

```bash
git add src/rewriter/prompts.py tests/test_prompts.py
git commit -m "feat(rewriter): prompt templates and output parser"
```

---

## Task 9: RSS scraper

**Files:**
- Create: `src/scraper/__init__.py` (empty)
- Create: `src/scraper/rss_scraper.py`
- Test: `tests/test_rss_scraper.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_rss_scraper.py
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from src.scraper.rss_scraper import scrape_rss, _is_fresh


def test_is_fresh_recent_passes():
    now = datetime.now(timezone.utc)
    assert _is_fresh(now, max_age_hours=12, now=now) is True


def test_is_fresh_old_filtered():
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=24)
    assert _is_fresh(old, max_age_hours=12, now=now) is False


def test_scrape_rss_returns_articles():
    fake_entry = type("E", (), {
        "title": "Bitcoin hits ATH",
        "link": "https://x/1",
        "summary": "BTC reaches new all-time high",
        "published_parsed": (2026, 6, 8, 0, 0, 0, 0, 0, 0),
    })()
    fake_feed = type("F", (), {"entries": [fake_entry]})()

    with patch("src.scraper.rss_scraper.feedparser.parse", return_value=fake_feed):
        out = scrape_rss(url="https://feed", source_name="coindesk",
                         max_articles=10, max_age_hours=24 * 365 * 10)
    assert len(out) == 1
    assert out[0]["source"] == "coindesk"
    assert out[0]["url"] == "https://x/1"
    assert out[0]["title"] == "Bitcoin hits ATH"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rss_scraper.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement RSS scraper**

```python
# src/scraper/rss_scraper.py
from datetime import datetime, timezone, timedelta
import feedparser


def _is_fresh(published: datetime, *, max_age_hours: int,
              now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return (now - published) <= timedelta(hours=max_age_hours)


def scrape_rss(*, url: str, source_name: str, max_articles: int,
               max_age_hours: int) -> list[dict]:
    feed = feedparser.parse(url)
    results: list[dict] = []
    now = datetime.now(timezone.utc)
    for entry in feed.entries[:max_articles]:
        published_struct = getattr(entry, "published_parsed", None)
        if published_struct is None:
            continue
        published = datetime(*published_struct[:6], tzinfo=timezone.utc)
        if not _is_fresh(published, max_age_hours=max_age_hours, now=now):
            continue
        results.append({
            "source": source_name,
            "url": entry.link,
            "title": entry.title,
            "content": getattr(entry, "summary", ""),
            "scraped_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "published": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return results
```

- [ ] **Step 4: Create empty `src/scraper/__init__.py`**

Empty file.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_rss_scraper.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 6: Commit**

```bash
git add src/scraper/__init__.py src/scraper/rss_scraper.py tests/test_rss_scraper.py
git commit -m "feat(scraper): RSS feed scraper with freshness filter"
```

---

## Task 10: Browser scraper recipe

**Files:**
- Create: `src/scraper/browser_scraper.py`
- Test: `tests/test_browser_scraper.py`

The module exposes structured recipes (instructions the Claude session executes via MCP browser tools) plus `save_scraped()` to persist results.

- [ ] **Step 1: Implement recipe + saver**

```python
# src/scraper/browser_scraper.py
"""
Browser-driven scrape recipes. Claude session executes via MCP browser tools.
This module assembles instructions and persists results.
"""
from datetime import datetime, timezone
from src.db.models import Database


def reuters_recipe(url: str, max_articles: int) -> dict:
    return {
        "source": "reuters",
        "url": url,
        "max_articles": max_articles,
        "instructions": (
            "1. Navigate to the given Reuters cryptocurrency section URL.\n"
            "2. Take a snapshot and locate article cards on the page.\n"
            "3. For each of the first {n} cards, extract title, href, and "
            "summary (first paragraph of preview text).\n"
            "4. Return as a JSON list with keys: title, url, summary."
        ).format(n=max_articles),
    }


def coingecko_recipe(url: str, max_articles: int) -> dict:
    return {
        "source": "coingecko",
        "url": url,
        "max_articles": max_articles,
        "instructions": (
            "1. Navigate to CoinGecko news page.\n"
            "2. Snapshot and extract the top {n} news items.\n"
            "3. For each: title, href, and the first ~200 chars of preview.\n"
            "4. Return JSON list with keys: title, url, summary."
        ).format(n=max_articles),
    }


def google_news_recipe(query: str, max_articles: int) -> dict:
    return {
        "source": f"google_news::{query}",
        "url": f"https://news.google.com/search?q={query.replace(' ', '+')}",
        "max_articles": max_articles,
        "instructions": (
            "1. Navigate to Google News search URL.\n"
            "2. Snapshot and extract the top {n} article tiles.\n"
            "3. For each: title (visible heading), the outbound href (resolve "
            "any Google redirect), and the preview snippet.\n"
            "4. Return JSON list with keys: title, url, summary."
        ).format(n=max_articles),
    }


def save_scraped(db: Database, *, source: str, items: list[dict]) -> list[dict]:
    """Persist a list of {title, url, summary} dicts as articles.
    Skips ones already in DB (URL UNIQUE collision). Returns inserted rows."""
    inserted: list[dict] = []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for item in items:
        try:
            aid = db.insert_article(
                source=source,
                url=item["url"],
                title=item["title"],
                content=item.get("summary", ""),
                scraped_at=now_iso,
                importance="normal",
            )
            inserted.append({**item, "id": aid, "source": source})
        except Exception:
            continue
    return inserted
```

- [ ] **Step 2: Write tests**

```python
# tests/test_browser_scraper.py
from src.db.models import Database
from src.scraper.browser_scraper import save_scraped, reuters_recipe


def test_recipe_includes_max_articles():
    r = reuters_recipe("https://reuters.com/x", max_articles=7)
    assert "7" in r["instructions"]
    assert r["source"] == "reuters"


def test_save_scraped_inserts_and_skips_duplicates(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    items = [
        {"title": "T1", "url": "https://r/1", "summary": "s1"},
        {"title": "T2", "url": "https://r/2", "summary": "s2"},
    ]
    inserted = save_scraped(db, source="reuters", items=items)
    assert len(inserted) == 2

    inserted2 = save_scraped(db, source="reuters", items=items)
    assert inserted2 == []
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_browser_scraper.py -v`
Expected: PASS, 2 tests.

- [ ] **Step 4: Commit**

```bash
git add src/scraper/browser_scraper.py tests/test_browser_scraper.py
git commit -m "feat(scraper): browser recipes and persistence"
```

---

## Task 11: X scraper recipe

**Files:**
- Create: `src/scraper/x_scraper.py`
- Test: `tests/test_x_scraper.py`

- [ ] **Step 1: Implement recipe**

```python
# src/scraper/x_scraper.py
"""
X/Twitter profile scrape recipes. Executed by Claude Code MCP browser tools.
Without authentication, X is heavily rate-limited — falls back to Nitter.
"""


def x_profile_recipe(handle: str, max_posts: int) -> dict:
    return {
        "source": f"x::{handle}",
        "primary_url": f"https://x.com/{handle}",
        "fallback_url": f"https://nitter.net/{handle}",
        "max_posts": max_posts,
        "instructions": (
            "1. Navigate to primary_url. If the page fails to load posts within "
            "8 seconds or shows a login wall, navigate to fallback_url.\n"
            "2. Snapshot the profile timeline.\n"
            "3. Extract the {n} most recent posts. Skip retweets/replies.\n"
            "4. For each: post text, post URL (full permalink), and timestamp.\n"
            "5. Return JSON list with keys: title (first 120 chars of text), "
            "url, summary (full text)."
        ).format(n=max_posts),
    }
```

- [ ] **Step 2: Smoke test**

```python
# tests/test_x_scraper.py
from src.scraper.x_scraper import x_profile_recipe


def test_x_recipe_contains_handle_and_fallback():
    r = x_profile_recipe("elonmusk", max_posts=5)
    assert "elonmusk" in r["primary_url"]
    assert "nitter" in r["fallback_url"]
    assert "5" in r["instructions"]
    assert r["source"] == "x::elonmusk"
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_x_scraper.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/scraper/x_scraper.py tests/test_x_scraper.py
git commit -m "feat(scraper): X profile recipe with Nitter fallback"
```

---

## Task 12: Telegram notifications

**Files:**
- Create: `src/notify/__init__.py` (empty)
- Create: `src/notify/telegram.py`
- Test: `tests/test_telegram.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_telegram.py
from unittest.mock import patch, MagicMock
from src.notify.telegram import send_message, format_batch_report, format_daily_summary


def test_send_message_posts_to_api():
    fake_response = MagicMock(status_code=200, json=lambda: {"ok": True})
    with patch("src.notify.telegram.requests.post", return_value=fake_response) as p:
        send_message(token="TKN", chat_id="123", text="hello")
        p.assert_called_once()
        args, kwargs = p.call_args
        assert "TKN" in args[0]
        assert kwargs["json"]["chat_id"] == "123"
        assert kwargs["json"]["text"] == "hello"


def test_format_batch_report_contains_counts():
    msg = format_batch_report(
        batch_name="Morning", date_str="08/06/2026",
        posted=12, failed=1, skipped=3, retry_success=1,
        per_source={"CoinDesk": 4, "Reuters": 3},
        schedule_window="08:00 - 12:30",
    )
    assert "12" in msg and "08/06/2026" in msg and "CoinDesk(4)" in msg


def test_format_daily_summary_lists_top_coins():
    msg = format_daily_summary(
        date_str="08/06/2026", total=25, target=30, success=23,
        failed=2, top_coins=[("BTC", 8), ("ETH", 5)],
    )
    assert "25/30" in msg
    assert "$BTC(8)" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_telegram.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement Telegram**

```python
# src/notify/telegram.py
import requests


API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(*, token: str, chat_id: str, text: str) -> None:
    url = API_BASE.format(token=token)
    resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Telegram send failed: {resp.status_code} {resp.text}")


def format_batch_report(*, batch_name: str, date_str: str, posted: int,
                        failed: int, skipped: int, retry_success: int,
                        per_source: dict[str, int], schedule_window: str) -> str:
    sources = ", ".join(f"{name}({count})" for name, count in per_source.items())
    return (
        f"📊 Binance Square Bot — {batch_name} batch {date_str}\n\n"
        f"✅ Posted: {posted}\n"
        f"❌ Failed: {failed}\n"
        f"⏭️ Skipped (dup): {skipped}\n"
        f"🔄 Retry success: {retry_success}\n\n"
        f"📰 Sources: {sources}\n"
        f"⏰ Schedule window: {schedule_window}"
    )


def format_error_alert(*, date_str: str, time_str: str, message: str) -> str:
    return (
        f"🚨 Bot Error — {date_str} {time_str}\n\n"
        f"{message}\n"
        f"Manual check required."
    )


def format_daily_summary(*, date_str: str, total: int, target: int, success: int,
                         failed: int, top_coins: list[tuple[str, int]]) -> str:
    coins = ", ".join(f"${ticker}({count})" for ticker, count in top_coins)
    return (
        f"📈 Daily Summary — {date_str}\n\n"
        f"Total posted: {total}/{target}\n"
        f"Success: {success}\n"
        f"Failed: {failed}\n"
        f"Top coins: {coins}"
    )
```

- [ ] **Step 4: Create empty `src/notify/__init__.py`**

Empty file.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_telegram.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 6: Commit**

```bash
git add src/notify/ tests/test_telegram.py
git commit -m "feat(notify): Telegram send + report formatting"
```

---

## Task 13: Binance Square poster recipe

**Files:**
- Create: `src/poster/binance_poster.py`
- Test: `tests/test_binance_poster.py`

- [ ] **Step 1: Implement helper**

```python
# src/poster/binance_poster.py
"""
Binance Square posting recipe. Claude session executes browser steps;
this module provides structured instructions and result recording.

Pre-condition: user is already logged into Binance Square in the Chrome
session bound to MCP browser tools.
"""
from src.db.models import Database


BINANCE_SQUARE_CREATE_URL = "https://www.binance.com/en/square/create"


def build_post_recipe(*, post_id: int, content_vi: str, content_en: str,
                      coin_tags: list[str], scheduled_iso: str) -> dict:
    body = f"{content_vi}\n\n---\n\n{content_en}"
    return {
        "post_id": post_id,
        "url": BINANCE_SQUARE_CREATE_URL,
        "body": body,
        "coin_tags": coin_tags,
        "scheduled_iso": scheduled_iso,
        "instructions": (
            f"1. Navigate to {BINANCE_SQUARE_CREATE_URL}.\n"
            "2. Wait until the create-post editor is visible. If a login wall "
            "appears, abort with status='failed' and error='not_logged_in'.\n"
            "3. Click into the editor and type the provided body text. Pause "
            "2-5 seconds between major actions.\n"
            f"4. For each ticker in {coin_tags}: type '$' + ticker, wait for the "
            "tag suggestion popup, click the matching suggestion so the symbol "
            "is inserted as a Binance Square coin tag (not plain text).\n"
            "5. Open the schedule control. Set the scheduled time to "
            f"{scheduled_iso} (converted to local time as the UI expects).\n"
            "6. Click the schedule/publish confirm button.\n"
            "7. Verify a success toast or that the editor clears. If neither "
            "appears within 10 seconds, treat as failed.\n"
            "8. Return status ('scheduled' or 'failed') and any error message."
        ),
    }


def record_post_result(db: Database, *, post_id: int, status: str,
                       posted_at: str | None = None,
                       error_msg: str | None = None) -> None:
    db.update_post_status(post_id, status=status, posted_at=posted_at,
                          error_msg=error_msg)
```

- [ ] **Step 2: Write tests**

```python
# tests/test_binance_poster.py
from src.db.models import Database
from src.poster.binance_poster import build_post_recipe, record_post_result


def test_build_recipe_combines_vi_and_en():
    r = build_post_recipe(post_id=1, content_vi="VI", content_en="EN",
                          coin_tags=["BTC"], scheduled_iso="2026-06-08T08:00:00Z")
    assert "VI" in r["body"] and "EN" in r["body"]
    assert "['BTC']" in r["instructions"]
    assert "2026-06-08T08:00:00Z" in r["instructions"]


def test_record_post_result_updates_status(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init_schema()
    aid = db.insert_article(source="x", url="https://x/1", title="t", content="c",
                            scraped_at="2026-06-08T01:00:00Z", importance="normal")
    pid = db.insert_post(article_id=aid, content_vi="vi", content_en="en",
                         coin_tags=["BTC"], format="short", batch="morning",
                         scheduled_time="2026-06-08T08:00:00Z")
    record_post_result(db, post_id=pid, status="failed", error_msg="UI changed")
    posts = db.list_posts_by_batch("morning")
    assert posts[0]["status"] == "failed"
    assert posts[0]["error_msg"] == "UI changed"
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_binance_poster.py -v`
Expected: PASS, 2 tests.

- [ ] **Step 4: Commit**

```bash
git add src/poster/binance_poster.py tests/test_binance_poster.py
git commit -m "feat(poster): Binance Square post recipe and result recorder"
```

---

## Task 14: Orchestrator entry point

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main.py`

`main.py` does the pure-Python work (load config, scrape RSS, dedup, persist, build recipes, send Telegram) and emits structured recipes the Claude session executes.

- [ ] **Step 1: Implement main**

```python
# src/main.py
import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import load_config
from src.db.models import Database
from src.db.cleanup import cutoff_iso, purge_old
from src.dedup.dedup import is_duplicate, normalize_title
from src.scraper.rss_scraper import scrape_rss
from src.scraper.browser_scraper import (
    reuters_recipe, coingecko_recipe, google_news_recipe,
)
from src.scraper.x_scraper import x_profile_recipe
from src.rewriter.prompts import build_prompt, parse_output
from src.rewriter.classifier import classify_importance, extract_coin_tags
from src.poster.scheduler import compute_schedule_times
from src.poster.binance_poster import build_post_recipe
from src.notify.telegram import (
    send_message, format_batch_report, format_daily_summary, format_error_alert,
)


def setup_logging(log_path: str) -> None:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def scrape_rss_sources(cfg) -> list[dict]:
    log = logging.getLogger("scrape_rss")
    all_items: list[dict] = []
    rss_sources = [
        ("coindesk", cfg.sources["coindesk_rss"]),
        ("cointelegraph", cfg.sources["cointelegraph_rss"]),
    ]
    for name, url in rss_sources:
        try:
            items = scrape_rss(url=url, source_name=name,
                               max_articles=cfg.scrape["max_articles_per_source"],
                               max_age_hours=cfg.scrape["max_age_hours"])
            log.info(f"RSS {name}: {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            log.error(f"RSS {name} failed: {e}")
    return all_items


def emit_browser_recipes(cfg) -> list[dict]:
    recipes: list[dict] = []
    n = cfg.scrape["max_articles_per_source"]
    recipes.append(reuters_recipe(cfg.sources["reuters_url"], max_articles=n))
    recipes.append(coingecko_recipe(cfg.sources["coingecko_url"], max_articles=n))
    for q in cfg.sources["google_news_queries"]:
        recipes.append(google_news_recipe(q, max_articles=n))
    for handle in cfg.sources["x_accounts"]:
        recipes.append(x_profile_recipe(handle, max_posts=n))
    return recipes


def dedup_and_persist(cfg, db: Database, items: list[dict]) -> tuple[int, int]:
    log = logging.getLogger("dedup")
    existing_urls: set[str] = set()
    existing_titles = db.list_dedup_titles()
    new_count = 0
    skipped = 0
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for item in items:
        dup, reason = is_duplicate(
            url=item["url"], title=item["title"],
            existing_urls=existing_urls, existing_titles=existing_titles,
            threshold=cfg.dedup["similarity_threshold"],
        )
        if dup:
            skipped += 1
            log.info(f"dedup skip ({reason}): {item['title'][:60]}")
            continue
        importance = classify_importance(f"{item['title']} {item.get('content','')}")
        try:
            db.insert_article(
                source=item["source"], url=item["url"], title=item["title"],
                content=item.get("content", ""), scraped_at=now_iso,
                importance=importance,
            )
        except Exception as e:
            log.warning(f"insert_article failed for {item['url']}: {e}")
            skipped += 1
            continue
        title_norm = normalize_title(item["title"])
        db.insert_dedup(url=item["url"], title_normalized=title_norm,
                        created_at=now_iso)
        existing_urls.add(item["url"])
        existing_titles.append(title_norm)
        new_count += 1
    return new_count, skipped


def build_rewrite_prompts(db: Database, limit: int) -> list[dict]:
    out: list[dict] = []
    articles = db.list_articles_unposted()[:limit]
    for a in articles:
        text = f"{a['title']} {a['content']}"
        coin_tags = extract_coin_tags(text)
        prompt = build_prompt(
            title=a["title"], content=a["content"],
            importance=a["importance"], coin_tags=coin_tags,
        )
        out.append({
            "article_id": a["id"],
            "importance": a["importance"],
            "coin_tags": coin_tags,
            "prompt": prompt,
        })
    return out


def persist_rewrites(db: Database, batch: str, *, rewrites: list[dict],
                     scheduled_times: list[str]) -> list[int]:
    """rewrites: [{article_id, coin_tags, importance, output}].
    scheduled_times: ISO strings, same length as rewrites.
    Returns list of post_ids."""
    post_ids: list[int] = []
    for r, sched_iso in zip(rewrites, scheduled_times):
        vi, en = parse_output(r["output"])
        fmt = "long" if r["importance"] == "high" else "short"
        pid = db.insert_post(
            article_id=r["article_id"], content_vi=vi, content_en=en,
            coin_tags=r["coin_tags"], format=fmt, batch=batch,
            scheduled_time=sched_iso,
        )
        post_ids.append(pid)
    return post_ids


def build_post_recipes(db: Database, post_ids: list[int]) -> list[dict]:
    recipes: list[dict] = []
    for pid in post_ids:
        with db._conn() as c:
            row = c.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
        coin_tags = json.loads(row["coin_tags"])
        recipes.append(build_post_recipe(
            post_id=pid, content_vi=row["content_vi"], content_en=row["content_en"],
            coin_tags=coin_tags, scheduled_iso=row["scheduled_time"],
        ))
    return recipes


def compute_batch_base(cfg, batch: str) -> datetime:
    tz = ZoneInfo(cfg.schedule["timezone"])
    now = datetime.now(tz)
    hour = cfg.schedule["morning_hour"] if batch == "morning" else cfg.schedule["evening_hour"]
    return now.replace(hour=hour, minute=0, second=0, microsecond=0)


def send_batch_report(cfg, db: Database, batch: str, *, new_count: int,
                       skipped: int, scheduled_post_ids: list[int],
                       window_str: str) -> None:
    posts = db.list_posts_by_batch(batch)
    sched_set = set(scheduled_post_ids)
    relevant = [p for p in posts if p["id"] in sched_set]
    posted = sum(1 for p in relevant if p["status"] == "scheduled")
    failed = sum(1 for p in relevant if p["status"] == "failed")
    per_source: Counter = Counter()
    with db._conn() as c:
        for p in relevant:
            row = c.execute("SELECT source FROM articles WHERE id=?",
                            (p["article_id"],)).fetchone()
            if row:
                per_source[row["source"]] += 1
    date_str = datetime.now(ZoneInfo(cfg.schedule["timezone"])).strftime("%d/%m/%Y")
    msg = format_batch_report(
        batch_name=batch.capitalize(), date_str=date_str,
        posted=posted, failed=failed, skipped=skipped, retry_success=0,
        per_source=dict(per_source), schedule_window=window_str,
    )
    try:
        send_message(token=cfg.telegram_bot_token, chat_id=cfg.telegram_chat_id, text=msg)
    except Exception as e:
        logging.getLogger("notify").error(f"Telegram send failed: {e}")


def send_summary(cfg, db: Database) -> None:
    tz = ZoneInfo(cfg.schedule["timezone"])
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_utc = today.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    posts = db.list_posts_for_summary(today_utc)
    success = sum(1 for p in posts if p["status"] in ("scheduled", "posted"))
    failed = sum(1 for p in posts if p["status"] == "failed")
    coins: Counter = Counter()
    for p in posts:
        for t in json.loads(p["coin_tags"]):
            coins[t] += 1
    top = coins.most_common(5)
    target = cfg.schedule["posts_per_batch"] * 2
    date_str = datetime.now(tz).strftime("%d/%m/%Y")
    msg = format_daily_summary(date_str=date_str, total=len(posts), target=target,
                                success=success, failed=failed, top_coins=top)
    send_message(token=cfg.telegram_bot_token, chat_id=cfg.telegram_chat_id, text=msg)


def emit_session_plan(plan: dict) -> None:
    print("---SESSION-PLAN-BEGIN---")
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    print("---SESSION-PLAN-END---")


def run_batch(batch: str, cfg, db: Database) -> dict:
    log = logging.getLogger("batch")
    log.info(f"Starting {batch} batch")

    rss_items = scrape_rss_sources(cfg)
    new_count, skipped = dedup_and_persist(cfg, db, rss_items)
    log.info(f"RSS dedup: {new_count} new, {skipped} skipped")

    browser_recipes = emit_browser_recipes(cfg)
    rewrite_prompts = build_rewrite_prompts(db, limit=cfg.schedule["posts_per_batch"])

    base = compute_batch_base(cfg, batch)
    sched_times = compute_schedule_times(
        base=base, count=max(len(rewrite_prompts), 1),
        min_minutes=cfg.schedule["post_interval_min"],
        max_minutes=cfg.schedule["post_interval_max"],
    )
    sched_iso = [t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                 for t in sched_times][:len(rewrite_prompts)]

    plan = {
        "batch": batch,
        "browser_scrape_recipes": browser_recipes,
        "rewrite_prompts": rewrite_prompts,
        "scheduled_times": sched_iso,
        "summary_so_far": {"rss_new": new_count, "rss_skipped": skipped},
    }
    emit_session_plan(plan)

    purge_old(db, cutoff_iso=cutoff_iso(cfg.dedup["cleanup_days"]))
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["morning", "evening"])
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--settings", default="config/settings.json")
    parser.add_argument("--env", default="config/.env")
    args = parser.parse_args(argv)

    cfg = load_config(settings_path=args.settings, env_path=args.env)
    setup_logging(cfg.log_path)
    db = Database(cfg.db_path)
    db.init_schema()

    if args.summary:
        send_summary(cfg, db)
        return 0

    if not args.batch:
        parser.error("--batch or --summary required")

    try:
        run_batch(args.batch, cfg, db)
        return 0
    except Exception as e:
        logging.getLogger("main").exception("batch failed")
        try:
            now = datetime.now(ZoneInfo(cfg.schedule["timezone"]))
            send_message(
                token=cfg.telegram_bot_token, chat_id=cfg.telegram_chat_id,
                text=format_error_alert(
                    date_str=now.strftime("%d/%m/%Y"),
                    time_str=now.strftime("%H:%M"),
                    message=f"Batch {args.batch} failed: {e}",
                ),
            )
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke test main argument parsing**

```python
# tests/test_main.py
import pytest
from src import main as main_mod


def test_main_requires_batch_or_summary(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        '{"schedule":{"morning_hour":8,"evening_hour":20,'
        '"post_interval_min":20,"post_interval_max":30,'
        '"posts_per_batch":15,"timezone":"Asia/Ho_Chi_Minh"},'
        '"sources":{"coindesk_rss":"x","cointelegraph_rss":"y",'
        '"reuters_url":"z","coingecko_url":"w",'
        '"google_news_queries":[],"x_accounts":[]},'
        '"scrape":{"max_articles_per_source":10,"max_age_hours":12},'
        '"dedup":{"similarity_threshold":0.8,"cleanup_days":30},'
        '"db_path":"' + str(tmp_path / "bot.db").replace("\\", "/") + '",'
        '"log_path":"' + str(tmp_path / "bot.log").replace("\\", "/") + '"}'
    )
    env = tmp_path / ".env"
    env.write_text("TELEGRAM_BOT_TOKEN=t\nTELEGRAM_CHAT_ID=c\n")
    with pytest.raises(SystemExit):
        main_mod.main(["--settings", str(settings), "--env", str(env)])
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_main.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat(main): orchestrator entry point with session plan emission"
```

---

## Task 15: Session driver doc

**Files:**
- Create: `docs/SESSION-DRIVER.md`

- [ ] **Step 1: Write session driver doc**

```markdown
# Session Driver — How Claude Executes a Batch

`python -m src.main --batch morning|evening` emits a JSON SESSION-PLAN to
stdout between `---SESSION-PLAN-BEGIN---` and `---SESSION-PLAN-END---`
markers. The running Claude Code session reads that plan and executes the
parts that need browser tools or in-session rewriting.

## Steps

### 1. Run the batch entry

```bash
python -m src.main --batch morning
```

Parse the SESSION-PLAN block from stdout. It contains:

- `browser_scrape_recipes`: `[{source, url, instructions, ...}]`
- `rewrite_prompts`: `[{article_id, importance, coin_tags, prompt}]`
- `scheduled_times`: ISO UTC strings

### 2. Execute browser scrape recipes

For each recipe in `browser_scrape_recipes`:

- Follow `instructions` using MCP browser tools (`browser_navigate`,
  `browser_snapshot`, `browser_evaluate`).
- Collect a list of `{title, url, summary}` dicts.
- Persist:

```python
from src.db.models import Database
from src.scraper.browser_scraper import save_scraped
db = Database("data/bot.db")
save_scraped(db, source=recipe["source"], items=collected_items)
```

### 3. Re-build rewrite prompts after browser scrape

Browser items added new unposted articles. Rebuild the prompt list:

```python
from src.config import load_config
from src.main import build_rewrite_prompts
cfg = load_config()
rewrite_prompts = build_rewrite_prompts(db, limit=cfg.schedule["posts_per_batch"])
```

### 4. Execute rewrite prompts

For each prompt:

- Read the `prompt` text.
- Rewrite the article in your own session, producing the exact
  `---VI--- ... ---EN--- ... ---END---` block.

```python
rewrites = [{"article_id": p["article_id"],
             "importance": p["importance"],
             "coin_tags": p["coin_tags"],
             "output": "<your full output>"} for p in rewrite_prompts]
```

- Persist:

```python
from src.main import persist_rewrites
post_ids = persist_rewrites(db, batch="morning",
                            rewrites=rewrites,
                            scheduled_times=plan["scheduled_times"])
```

### 5. Execute posting

```python
from src.main import build_post_recipes
recipes = build_post_recipes(db, post_ids)
```

For each recipe: follow `instructions` with browser tools. On success/fail:

```python
from src.poster.binance_poster import record_post_result
from datetime import datetime, timezone
record_post_result(db, post_id=recipe["post_id"],
                   status="scheduled",
                   posted_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
# or status="failed", error_msg="..."
```

### 6. Retry failed posts (end of batch)

```python
failed = db.list_failed_posts_by_batch("morning")
# Re-run posting steps for each.
```

### 7. Send batch report

```python
from src.main import send_batch_report
send_batch_report(cfg, db, "morning", new_count=N, skipped=S,
                  scheduled_post_ids=post_ids, window_str="08:00 - 12:30")
```

### 8. Daily summary

At 23:00 GMT+7:

```bash
python -m src.main --summary
```

## Failure handling

- Any per-post failure → log + skip, continue.
- End of batch → retry failed posts once.
- Whole-batch blocker (Binance Square unreachable, browser crash) →
  Telegram alert is sent by `main.py` exception handler.
```

- [ ] **Step 2: Commit**

```bash
git add docs/SESSION-DRIVER.md
git commit -m "docs: session driver guide for batch execution"
```

---

## Task 16: End-to-end smoke run (manual checkpoint)

- [ ] **Step 1: Install dependencies**

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

- [ ] **Step 2: Run all tests**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Copy .env and fill credentials**

```bash
copy config\.env.example config\.env
```

Edit `config/.env` with real `TELEGRAM_BOT_TOKEN` (from @BotFather) and
`TELEGRAM_CHAT_ID` (from @userinfobot).

- [ ] **Step 4: Dry-run RSS scrape + emit session plan**

```bash
python -m src.main --batch morning
```

Expected: `data/bot.db` created, `logs/bot.log` populated, SESSION-PLAN
block printed to stdout.

- [ ] **Step 5: Test Telegram channel**

```bash
python -m src.main --summary
```

Expected: Telegram bot sends daily-summary message (counts may be zero on
first run).

- [ ] **Step 6: Manually log in to Binance Square**

Open Chrome, navigate to `https://www.binance.com/en/square`, log in
fully. Keep this Chrome session active for the Claude session.

- [ ] **Step 7: Run full batch via Claude session**

Following `docs/SESSION-DRIVER.md`, execute one full batch end-to-end:
parse session plan, run browser scrapes, run rewrites, run posts, send
batch report.

- [ ] **Step 8: Verify on Binance Square**

Open Binance Square, check scheduled posts queue. Confirm posts queued
at expected times with correct coin tags.

- [ ] **Step 9: Set up cron**

```
/schedule cron "0 8 * * *"  python -m src.main --batch morning
/schedule cron "0 20 * * *" python -m src.main --batch evening
/schedule cron "0 23 * * *" python -m src.main --summary
```

- [ ] **Step 10: Final commit**

```bash
git add -A
git commit -m "chore: complete v1 smoke verification"
```

---

## Self-review notes

- ✅ Spec coverage: architecture, sources, rewriting, posting, DB, Telegram, project structure, execution model — all covered by tasks 1-16.
- ✅ No placeholders ("TBD", "TODO") in any task — all code is concrete.
- ✅ Type consistency: `Database` methods used in Tasks 10, 13, 14 match signatures from Task 3. `compute_schedule_times` consistent. `build_post_recipe` / `record_post_result` consistent between Tasks 13-14.
- ✅ Out-of-scope items from spec (auto-login, multi-account, images) deliberately absent.
- ✅ Risks (UI changes, X scraping, RSS stability) handled via Telegram alerts, browser-recipe abstraction, Nitter fallback, config-driven URLs.
- ✅ Date formats: ISO 8601 UTC consistently used (matches spec DB schema notes).
- ✅ Retry strategy ("skip + retry at end of batch") implemented via `list_failed_posts_by_batch` (Task 3) and Step 6 in SESSION-DRIVER.md (Task 15).
