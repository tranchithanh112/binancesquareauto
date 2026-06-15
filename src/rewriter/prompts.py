"""
Prompt templates for the Claude Code CLI rewriter.

Vietnamese-only, human-voiced. The goal is to read like a real VN crypto
trader sharing on Binance Square — not an auto-generated news bot.
"""

# Shared voice rules injected into every template.
VOICE = """\
GIỌNG VĂN — BẮT BUỘC (đây là phần quan trọng nhất):
- Viết như một trader Việt THẬT đang chia sẻ trên Binance Square. Tự nhiên,
  đời thường, có cảm xúc và quan điểm cá nhân.
- Xưng "mình", gọi người đọc là "ae" (anh em). Văn nói, không trang trọng.
- TUYỆT ĐỐI KHÔNG: emoji làm tiêu đề mục (kiểu "📊 PHÂN TÍCH NHANH"), không
  bullet point cứng nhắc, không chia section máy móc, không bảng biểu.
- Lồng số liệu/giá vào câu văn tự nhiên (vd: "BTC về vùng 63k-58k mình gom
  dần", "SOL tầm 7x-5x là ngon"). KHÔNG viết "Support: $X / Resistance: $Y".
- Coin tag dạng $BTC, $SOL, $ETH lồng tự nhiên TRONG câu, không liệt kê cuối bài.
- Có quan điểm cá nhân RÕ: "mình nghĩ", "theo mình", "mình thì...". Hedge kiểu
  người thật, đừng kiểu "có thể tăng hoặc giảm".
- KHÔNG viết disclaimer kiểu "Đây là tin tức tổng hợp, không phải lời khuyên
  đầu tư" — nghe như bot. Nếu nhắc rủi ro thì nói kiểu người ("nhớ quản lý vốn
  nhé ae", "đừng full margin").
- KHÔNG ghi "Nguồn: ..." cứng. Nếu muốn dẫn thì nói tự nhiên trong câu ("theo
  tin từ {source} thì...").
- Tối đa 1 hashtag, chỉ khi thật tự nhiên. Thường thì khỏi.
- Kết bằng câu mời tương tác tự nhiên ("ae nghĩ sao?", "có gì hỏi mình bên
  dưới nhé", "ae đang hold con nào?").
- Số liệu phải thực tế, KHÔNG bịa giá viển vông. Không hype "x100".
- Viết liền mạch, KHÔNG sáo rỗng, không mở bài kiểu "Thị trường crypto hôm nay".
"""


SHORT_TEMPLATE = """\
Bạn viết một bài đăng Binance Square bằng TIẾNG VIỆT, dựa trên tin dưới đây.
Chỉ xuất ra khối định dạng yêu cầu, không giải thích, không hỏi lại.

{voice}

TIN NGUỒN
Nguồn: {source}
Tiêu đề: {title}
Nội dung: {content}
Coin liên quan: {coin_tags}

YÊU CẦU BÀI NÀY (tin tức + góc nhìn):
- Mở đầu bằng nhận định/cảm nhận cá nhân về tin này (không tóm tắt khô khan).
- Kể tin bằng giọng của mình, lồng số liệu quan trọng.
- Cho quan điểm: tin này tác động gì tới {coin_tags}, mình nhìn nhận sao.
- Nếu hợp lý, gợi ý vùng giá/hành động kiểu chia sẻ ("mình canh vào vùng...").
- Kết mời ae tương tác.
- Dài khoảng 600-900 ký tự. Mọi câu phải trọn vẹn.

ĐỊNH DẠNG (chỉ xuất đúng khối này)
---VI---
<bài tiếng Việt>
---END---
"""

SIGNAL_TEMPLATE = """\
Bạn viết một bài "nhận định nhanh" Binance Square bằng TIẾNG VIỆT, ngắn gọn,
dựa trên tin dưới. Chỉ xuất khối định dạng, không giải thích.

{voice}

TIN NGUỒN
Nguồn: {source}
Tiêu đề: {title}
Nội dung: {content}
Coin chính: {coin_tags}

YÊU CẦU (ngắn, sắc):
- 3-5 câu thôi. Một nhận định nhanh về {coin_tags} với số liệu thật từ tin.
- Kiểu "mình thấy $SOL đang test vùng 14x, volume tăng, ai cầm thì canh chốt
  bớt" — đời thường, có quan điểm.
- Kết bằng 1 câu mời ae ("ae tính sao con này?").
- Dưới 450 ký tự. Câu trọn vẹn.

ĐỊNH DẠNG (chỉ xuất đúng khối này)
---VI---
<bài tiếng Việt>
---END---
"""

POLL_TEMPLATE = """\
Bạn viết một bài hỏi ý kiến (poll) Binance Square bằng TIẾNG VIỆT để câu
tương tác, dựa trên tin dưới. Chỉ xuất khối định dạng.

{voice}

TIN NGUỒN
Nguồn: {source}
Tiêu đề: {title}
Nội dung: {content}
Coin chính: {coin_tags}

YÊU CẦU:
- 1-2 câu dẫn dắt tình huống về {coin_tags} với 1 con số cụ thể.
- 1 câu hỏi A/B tự nhiên kiểu trader hỏi nhau, không cần emoji 🟢🔴 cứng nhắc
  (vd: "Ae nghĩ $BTC tuần này phá 70k hay về test lại 58k? Cmt phát mình hóng").
- Dưới 400 ký tự. Câu trọn vẹn.

ĐỊNH DẠNG (chỉ xuất đúng khối này)
---VI---
<bài tiếng Việt>
---END---
"""

HOTTAKE_TEMPLATE = """\
Bạn viết một "quan điểm mạnh" (hot take) Binance Square bằng TIẾNG VIỆT,
mời tranh luận, dựa trên tin dưới. Chỉ xuất khối định dạng.

{voice}

TIN NGUỒN
Nguồn: {source}
Tiêu đề: {title}
Nội dung: {content}
Coin chính: {coin_tags}

YÊU CẦU:
- 1 quan điểm mạnh, hơi ngược số đông, về {coin_tags} — neo vào 1 fact thật từ
  tin, KHÔNG bịa.
- 1-2 câu lý do tại sao mình nghĩ vậy.
- 1 câu thách thức nhẹ mời ae phản biện ("ae thấy mình sai chỗ nào cứ bem").
- Dưới 500 ký tự. Câu trọn vẹn.

ĐỊNH DẠNG (chỉ xuất đúng khối này)
---VI---
<bài tiếng Việt>
---END---
"""

ARTICLE_TEMPLATE = """\
Bạn viết một BÀI DÀI (article) Binance Square bằng TIẾNG VIỆT kèm tiêu đề,
dựa trên tin lớn dưới đây. Chỉ xuất khối định dạng, không giải thích.

{voice}

TIN NGUỒN
Nguồn: {source}
Tiêu đề: {title}
Nội dung: {content}
Coin liên quan: {coin_tags}

TIÊU ĐỀ: một tiêu đề tiếng Việt giật nhẹ, cụ thể với tin này (≤ 80 ký tự),
không bịa, không clickbait lố.

THÂN BÀI (giọng người, viết như chia sẻ thesis dài):
- Mở bằng cảm nhận/quan điểm cá nhân về sự kiện.
- Kể sự kiện + tác động tới thị trường bằng giọng của mình, lồng số liệu.
- Nêu rõ mình nghĩ gì, kịch bản ngắn hạn mình nghiêng về bên nào.
- Nếu hợp lý, chia sẻ vùng giá/chiến lược kiểu cá nhân.
- Kết mời ae thảo luận.
- Thân bài 900-1500 ký tự, liền mạch, câu trọn vẹn. KHÔNG section header emoji.

ĐỊNH DẠNG (chỉ xuất đúng khối này)
---TITLE---
<tiêu đề tiếng Việt>
---VI---
<thân bài tiếng Việt>
---END---
"""


def _pretty_source(source: str) -> str:
    mapping = {
        "coindesk": "CoinDesk", "cointelegraph": "CoinTelegraph",
        "reuters": "Reuters", "coingecko": "CoinGecko",
    }
    s = (source or "").lower().strip()
    if s in mapping:
        return mapping[s]
    if s.startswith("google_news::"):
        return "Google News"
    if s.startswith("x::"):
        handle = s.split("::", 1)[1]
        return f"X (@{handle})"
    return source or "Unknown"


# Rotation weights — user-approved mix.
POST_TYPE_WEIGHTS = [("news_ta", 50), ("signal", 20), ("poll", 15), ("hot_take", 15)]


def pick_post_type(rng=None) -> str:
    """Weighted random post type per the approved 50/20/15/15 mix."""
    import random
    r = rng or random
    types = [t for t, _ in POST_TYPE_WEIGHTS]
    weights = [w for _, w in POST_TYPE_WEIGHTS]
    return r.choices(types, weights=weights, k=1)[0]


def content_type_for(post_type: str, importance: str) -> tuple[int, bool]:
    """Return (binance_content_type, is_article). news_ta on a high-importance
    story renders as a contentType=2 article with title + cover; everything
    else is a contentType=1 short post."""
    if post_type == "news_ta" and importance == "high":
        return 2, True
    return 1, False


def build_typed_prompt(*, post_type: str, title: str, content: str,
                       importance: str, coin_tags: list[str],
                       source: str = "Unknown") -> str:
    tags_str = " ".join(f"${t}" for t in coin_tags)
    src = _pretty_source(source)
    if post_type == "signal":
        tmpl = SIGNAL_TEMPLATE
    elif post_type == "poll":
        tmpl = POLL_TEMPLATE
    elif post_type == "hot_take":
        tmpl = HOTTAKE_TEMPLATE
    elif post_type == "news_ta" and importance == "high":
        tmpl = ARTICLE_TEMPLATE
    else:
        tmpl = SHORT_TEMPLATE
    return tmpl.format(voice=VOICE, title=title, content=content,
                       importance=importance, coin_tags=tags_str, source=src)


def build_prompt(*, title: str, content: str, importance: str,
                 coin_tags: list[str], source: str = "Unknown") -> str:
    """Legacy entry — maps to the news_ta typed prompt."""
    return build_typed_prompt(
        post_type="news_ta", title=title, content=content,
        importance=importance, coin_tags=coin_tags, source=source,
    )


def parse_output(output: str) -> tuple[str, str]:
    """Parse ---VI--- ... ---END--- (VN-only). Returns (vi, "")."""
    try:
        after_vi = output.split("---VI---", 1)[1]
        vi_part = after_vi.split("---END---", 1)[0]
        vi_part = vi_part.split("---EN---", 1)[0]
        return vi_part.strip(), ""
    except (IndexError, ValueError) as e:
        raise ValueError(f"Rewriter output not in expected format: {e}")


def parse_article(output: str) -> tuple[str, str, str]:
    """Parse ---TITLE--- ... ---VI--- ... ---END--- (VN-only).
    Returns (title, vi, "")."""
    try:
        after_title = output.split("---TITLE---", 1)[1]
        title_part, after_vi = after_title.split("---VI---", 1)
        vi_part = after_vi.split("---END---", 1)[0]
        vi_part = vi_part.split("---EN---", 1)[0]
        return title_part.strip(), vi_part.strip(), ""
    except (IndexError, ValueError) as e:
        raise ValueError(f"Article output not in expected format: {e}")
