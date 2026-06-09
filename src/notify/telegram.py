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
        f"\U0001F4CA Binance Square Bot — {batch_name} batch {date_str}\n\n"
        f"✅ Posted: {posted}\n"
        f"❌ Failed: {failed}\n"
        f"⏭️ Skipped (dup): {skipped}\n"
        f"\U0001F504 Retry success: {retry_success}\n\n"
        f"\U0001F4F0 Sources: {sources}\n"
        f"⏰ Schedule window: {schedule_window}"
    )


def format_error_alert(*, date_str: str, time_str: str, message: str) -> str:
    return (
        f"\U0001F6A8 Bot Error — {date_str} {time_str}\n\n"
        f"{message}\n"
        f"Manual check required."
    )


def format_daily_summary(*, date_str: str, total: int, target: int, success: int,
                         failed: int, top_coins: list[tuple[str, int]]) -> str:
    coins = ", ".join(f"${ticker}({count})" for ticker, count in top_coins)
    return (
        f"\U0001F4C8 Daily Summary — {date_str}\n\n"
        f"Total posted: {total}/{target}\n"
        f"Success: {success}\n"
        f"Failed: {failed}\n"
        f"Top coins: {coins}"
    )
