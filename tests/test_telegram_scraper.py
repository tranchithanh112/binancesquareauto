from unittest.mock import patch
from src.scraper.telegram_scraper import _is_ad, scrape_channel


def test_is_ad_filters_promos():
    assert _is_ad("Đăng ký ngay khóa học VIP, hoa hồng hấp dẫn ref=abc123") is True
    assert _is_ad("Tham gia group t.me/+abcdefg để nhận tín hiệu") is True
    assert _is_ad("ngắn") is True
    assert _is_ad(
        "BOJ chính thức nâng lãi suất từ 0,75% lên 1,00%, cao nhất kể từ 1995, "
        "thị trường crypto phản ứng mạnh với BTC giảm về vùng 65k") is False


def test_scrape_channel_parses_messages():
    html = """
    <div class="tgme_widget_message" data-post="ThuanCapital/100">
      <div class="tgme_widget_message_text">Dòng tiền ETF Mỹ hôm nay BTC âm 64 triệu USD, ETH dương 22 triệu, thị trường giằng co quanh vùng giá hiện tại nhé ae</div>
      <a class="tgme_widget_message_date"><time datetime="2999-01-01T00:00:00+00:00"></time></a>
    </div>
    """
    class FakeResp:
        ok = True
        text = html
    with patch("src.scraper.telegram_scraper.requests.get", return_value=FakeResp()):
        items = scrape_channel("ThuanCapital", max_items=5, max_age_hours=10**9)
    assert len(items) == 1
    it = items[0]
    assert it["source"] == "tg::ThuanCapital"
    assert it["url"] == "https://t.me/ThuanCapital/100"
    assert "ETF" in it["content"]


def test_scrape_channel_skips_ads():
    html = """
    <div class="tgme_widget_message" data-post="c/1">
      <div class="tgme_widget_message_text">Đăng ký kênh VIP nhận tín hiệu, ref=xyz, hoa hồng khủng, link bio</div>
    </div>
    """
    class FakeResp:
        ok = True
        text = html
    with patch("src.scraper.telegram_scraper.requests.get", return_value=FakeResp()):
        items = scrape_channel("c", max_age_hours=10**9)
    assert items == []
