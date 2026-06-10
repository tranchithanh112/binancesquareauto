"""One-off operational script.

Persist 6 hand-written bilingual rewrites for the 6 RSS articles already in
data/bot.db (id 1..6), then drive Playwright to schedule each post on
Binance Square. Run from the repo root with the Playwright Chromium profile
already logged into Binance (see docs/PLAYWRIGHT-SETUP.md).

Usage:
    python post_now.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

from src.config import load_config
from src.db.models import Database
from src.main import run_all_posts
from src.notify.telegram import send_message, format_batch_report
from src.poster.scheduler import compute_schedule_times
from zoneinfo import ZoneInfo


REWRITES = [
    {
        "article_id": 1,
        "coin_tags": ["BTC"],
        "content_vi": (
            "⚠️ Mặt tối của cơn sốt memecoin\n\n"
            "Báo cáo mới phơi bày những góc khuất rùng rợn của thị trường "
            "memecoin: từ hình xăm trên trán đến các thử thách rượu nguy hiểm "
            "để câu view. Người sáng tạo content đẩy giới hạn ngày càng xa "
            "nhằm pump giá token vô danh.\n\n"
            "Câu chuyện này nhắc nhở: memecoin là sòng bạc, không phải đầu tư. "
            "Nếu chơi, chỉ với số tiền sẵn sàng mất sạch. Bitcoin và các "
            "coin lớn vẫn là nền tảng an toàn hơn cho danh mục dài hạn.\n\n"
            "$BTC #Memecoin #CryptoNews\n\n"
            "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
        ),
        "content_en": (
            "⚠️ The dark side of the memecoin craze\n\n"
            "A new report exposes the disturbing underbelly of the memecoin "
            "market: forehead tattoos, dangerous alcohol dares — all used by "
            "creators to pump obscure tokens for clout and price action.\n\n"
            "Takeaway: memecoins are a casino, not an investment. If you "
            "play, only risk what you can afford to lose entirely. Bitcoin "
            "and majors remain a safer base for long-term portfolios.\n\n"
            "$BTC #Memecoin #CryptoNews\n\n"
            "This is aggregated news, not investment advice."
        ),
    },
    {
        "article_id": 2,
        "coin_tags": ["BTC"],
        "content_vi": (
            "📊 Quỹ research lớn gọi tên Hyperliquid là 'cơ hội hấp dẫn'\n\n"
            "Công ty nghiên cứu nổi tiếng — từng gây ra đợt bán tháo cổ phiếu "
            "AI — vừa công bố luận điểm bullish về Hyperliquid, đánh giá DEX "
            "perp này có cấu trúc doanh thu và tăng trưởng người dùng đáng "
            "chú ý.\n\n"
            "Hyperliquid đang dẫn đầu mảng perp DEX về volume. Nếu phân tích "
            "này lan truyền, dòng tiền có thể chuyển dịch mạnh sang HYPE. "
            "Theo dõi sát các kênh on-chain để bắt sớm.\n\n"
            "$BTC #Hyperliquid #DEX\n\n"
            "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
        ),
        "content_en": (
            "📊 Top research firm flags Hyperliquid as a 'compelling' idea\n\n"
            "The influential firm behind a recent AI-stock selloff has "
            "published a bullish thesis on Hyperliquid, citing the perp "
            "DEX's revenue mechanics and user growth as standout factors.\n\n"
            "Hyperliquid currently leads perp DEX volume. If this thesis "
            "spreads, capital could rotate hard into HYPE. Watch on-chain "
            "flows closely to catch the move early.\n\n"
            "$BTC #Hyperliquid #DEX\n\n"
            "This is aggregated news, not investment advice."
        ),
    },
    {
        "article_id": 3,
        "coin_tags": ["BTC"],
        "content_vi": (
            "🚀 Bitcoin vượt $63,000 — Strategy gom thêm $100 triệu BTC\n\n"
            "BTC bứt phá qua mốc $63K trong phiên Á. Cùng lúc, Strategy "
            "(MicroStrategy) thông báo mua thêm $100 triệu Bitcoin — củng cố "
            "vị thế treasury crypto lớn nhất thế giới.\n\n"
            "Động thái mua liên tục của Saylor + dòng tiền ETF tạo support "
            "vững cho Bitcoin. Nếu BTC giữ trên $62K, target tiếp theo là "
            "$68K. Quan sát volume xác nhận xu hướng.\n\n"
            "$BTC #Bitcoin #Strategy #MicroStrategy\n\n"
            "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
        ),
        "content_en": (
            "🚀 Bitcoin tops $63,000 as Strategy adds $100M in BTC\n\n"
            "BTC broke above $63K during the Asian session. At the same "
            "time, Strategy (MicroStrategy) announced another $100M Bitcoin "
            "purchase — reinforcing its position as the largest crypto "
            "treasury on the planet.\n\n"
            "Saylor's relentless buying plus steady ETF inflows are building "
            "a solid support floor. If BTC holds above $62K, the next "
            "target sits at $68K. Watch volume to confirm direction.\n\n"
            "$BTC #Bitcoin #Strategy #MicroStrategy\n\n"
            "This is aggregated news, not investment advice."
        ),
    },
    {
        "article_id": 4,
        "coin_tags": ["BTC"],
        "content_vi": (
            "💼 OpenAI nộp hồ sơ IPO bí mật tại Mỹ\n\n"
            "OpenAI xác nhận đã nộp hồ sơ IPO confidential lên SEC nhưng chưa "
            "quyết định ngày niêm yết. Đây là cột mốc lớn cho làn sóng AI và "
            "có thể tác động gián tiếp đến sentiment crypto.\n\n"
            "Lịch sử cho thấy IPO AI lớn thường hút vốn risk-on, kéo cả "
            "Bitcoin và altcoin theo. Nếu OpenAI niêm yết thành công, dòng "
            "tiền tech-crypto có thể bùng nổ trong Q4.\n\n"
            "$BTC #OpenAI #AI #IPO\n\n"
            "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
        ),
        "content_en": (
            "💼 OpenAI confidentially files for a US IPO\n\n"
            "OpenAI confirmed it has filed confidentially with the SEC for "
            "an IPO but has not yet decided on a launch date. This is a "
            "major milestone for the AI wave — with knock-on effects for "
            "crypto sentiment.\n\n"
            "History shows that large AI IPOs tend to attract risk-on "
            "capital, lifting both Bitcoin and altcoins. A successful "
            "OpenAI listing could trigger a tech-crypto money flow surge in "
            "Q4.\n\n"
            "$BTC #OpenAI #AI #IPO\n\n"
            "This is aggregated news, not investment advice."
        ),
    },
    {
        "article_id": 5,
        "coin_tags": ["BTC"],
        "content_vi": (
            "🏦 RWA tokenized tăng gần 600% — báo cáo Binance\n\n"
            "Tài sản thực được tokenize (RWA) đang bùng nổ: cổ phiếu, vàng và "
            "bất động sản trên blockchain tăng trưởng gần 600% dù thị "
            "trường crypto pullback. Ngân hàng và tổ chức bắt đầu adopt mạnh.\n\n"
            "RWA là narrative dài hạn ít người chú ý hiện tại nhưng có "
            "potential lớn. Các project leaders: Ondo, Maple, Centrifuge. "
            "Theo dõi để không bỏ lỡ sóng tokenization sắp tới.\n\n"
            "$BTC #RWA #Tokenization #Binance\n\n"
            "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
        ),
        "content_en": (
            "🏦 Tokenized RWAs surge nearly 600% — Binance report\n\n"
            "Real-world asset tokenization is booming: stocks, gold and "
            "real estate on chain are up close to 600% despite the broader "
            "crypto pullback. Banks and institutions are starting to embrace "
            "blockchain-based assets in earnest.\n\n"
            "RWA is a long-cycle narrative most retail ignores today but it "
            "carries serious upside. Watch project leaders: Ondo, Maple, "
            "Centrifuge. Don't miss the tokenization wave that's building.\n\n"
            "$BTC #RWA #Tokenization #Binance\n\n"
            "This is aggregated news, not investment advice."
        ),
    },
    {
        "article_id": 6,
        "coin_tags": ["BTC"],
        "content_vi": (
            "📉 'Luận điểm tốt nhất' để tích lũy Bitcoin xuất hiện\n\n"
            "Bitcoin RSI chạm mức thấp lịch sử, đồng thời whales tăng tốc "
            "tích lũy — tạo cơ hội mua thế hệ theo nhận định mới nhất từ "
            "analyst. Tuy vậy nhiều người vẫn dự BTC có thể tụt dưới $60,000 "
            "ngắn hạn.\n\n"
            "Chiến lược DCA (mua dần) ở vùng giá hiện tại được khuyến nghị "
            "hơn là all-in một lần. Quản trị rủi ro, set stop-loss rõ ràng. "
            "Cycle dài hạn vẫn rất bullish.\n\n"
            "$BTC #Bitcoin #DCA #Accumulation\n\n"
            "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
        ),
        "content_en": (
            "📉 'Best thesis' for accumulating Bitcoin emerges\n\n"
            "Bitcoin RSI is hitting historical lows while whales accelerate "
            "accumulation — creating a generational buying setup per a fresh "
            "analyst take. Even so, many still expect BTC to dip under "
            "$60,000 short term.\n\n"
            "DCA into current prices is generally a wiser play than going "
            "all-in. Manage risk, set clear stops. The long cycle remains "
            "decidedly bullish.\n\n"
            "$BTC #Bitcoin #DCA #Accumulation\n\n"
            "This is aggregated news, not investment advice."
        ),
    },
]


def main() -> int:
    cfg = load_config()
    db = Database(cfg.db_path)

    # First scheduled post 12 min from now (Binance needs a buffer); rest 20-30 min apart.
    base = datetime.now(timezone.utc).replace(microsecond=0, second=0) + timedelta(minutes=12)
    sched_dts = compute_schedule_times(
        base=base, count=len(REWRITES), min_minutes=20, max_minutes=30,
    )
    sched_iso = [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in sched_dts]

    # Persist rewrites
    post_ids: list[int] = []
    for r, sched in zip(REWRITES, sched_iso):
        pid = db.insert_post(
            article_id=r["article_id"], content_vi=r["content_vi"],
            content_en=r["content_en"], coin_tags=r["coin_tags"],
            format="short", batch="evening", scheduled_time=sched,
        )
        post_ids.append(pid)
        print(f"persisted post {pid} (article {r['article_id']}) scheduled {sched}")

    # Drive Playwright to post each
    print("\nLaunching Playwright to schedule posts on Binance Square...\n")
    counts = run_all_posts(db, post_ids)
    print(f"\nResult: {json.dumps(counts)}\n")

    # Telegram summary
    tz = ZoneInfo(cfg.schedule["timezone"])
    date_str = datetime.now(tz).strftime("%d/%m/%Y")
    msg = format_batch_report(
        batch_name="One-off test", date_str=date_str,
        posted=counts.get("scheduled", 0), failed=counts.get("failed", 0),
        skipped=0, retry_success=counts.get("retry_success", 0),
        per_source={"CoinDesk": 3, "CoinTelegraph": 3},
        schedule_window=f"{sched_iso[0]} - {sched_iso[-1]} UTC",
    )
    try:
        send_message(token=cfg.telegram_bot_token,
                     chat_id=cfg.telegram_chat_id, text=msg)
        print("Telegram report sent.")
    except Exception as e:
        print(f"Telegram send failed: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
