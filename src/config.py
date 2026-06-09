import json
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import dotenv_values


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

    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)

    # If the .env file exists, read from it directly; otherwise fall back to process env.
    if env_path.exists():
        env_values = dotenv_values(env_path)
        token = env_values.get("TELEGRAM_BOT_TOKEN")
        chat = env_values.get("TELEGRAM_CHAT_ID")
    else:
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
