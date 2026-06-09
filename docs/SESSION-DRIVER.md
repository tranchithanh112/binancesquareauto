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
