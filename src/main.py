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
