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
