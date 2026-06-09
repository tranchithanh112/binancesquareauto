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
