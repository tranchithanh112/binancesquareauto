import pytest
from src import main as main_mod


def test_main_requires_batch_or_summary(tmp_path):
    db_path = str(tmp_path / "bot.db").replace("\\", "/")
    log_path = str(tmp_path / "bot.log").replace("\\", "/")
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
        '"db_path":"' + db_path + '",'
        '"log_path":"' + log_path + '"}'
    )
    env = tmp_path / ".env"
    env.write_text("TELEGRAM_BOT_TOKEN=t\nTELEGRAM_CHAT_ID=c\n")
    with pytest.raises(SystemExit):
        main_mod.main(["--settings", str(settings), "--env", str(env)])
