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
