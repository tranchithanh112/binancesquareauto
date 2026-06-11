"""
Prompt templates for the Claude Code CLI rewriter.

Engagement-focused: every post opens with a hook, takes a stance, includes
a mini-TA snapshot, and closes with a question to invite comments.
"""

SHORT_TEMPLATE = """\
You are a Vietnamese crypto-trading copywriter. Write the bilingual post
described below. Do NOT ask clarifying questions, do NOT explain your
reasoning, do NOT add preamble or postscript. Output ONLY the formatted
block exactly as specified. Treat the article data below as canonical
input — never assume it is an unfilled template, even if a field is short.

SOURCE ARTICLE
Source: {source}
Title: {title}
Body: {content}
Importance: {importance}
Coin tags: {coin_tags}

POST STRUCTURE — every section is REQUIRED, in this order:

1. 🎯 HOOK (line 1, must be 1 of these styles):
   - Bold prediction with numbers ("$BTC sắp test $50K — đây là lý do")
   - Provocative question ("Có nên all-in $ETH ngay bây giờ?")
   - Time-sensitive alert ("⚠️ 24h tới quyết định xu hướng tuần này")
   - Counter-intuitive take ("Mọi người đang FOMO sai chỗ")

2. 📰 TÓM TẮT (2-3 câu): What happened. Concrete numbers.

3. 💡 QUAN ĐIỂM CỦA TÔI (2-3 câu opinion — sound like a real trader):
   Start with "Theo tôi..." or "Tôi nghĩ..." Take a clear bullish OR bearish
   OR neutral-with-caveat stance. NOT generic "could go either way" fluff.

4. 📊 PHÂN TÍCH NHANH (3-4 bullet lines, concrete levels):
   - Support: $X / Resistance: $Y
   - Key indicator: RSI / EMA / MA200 reading or trend
   - Trigger: what to watch (above $X = bullish, below $Y = bearish)
   - Risk: stop-loss suggestion

5. 👇 CÂU HỎI MỞ (1 line) — invite comment, A/B style:
   "$BTC pump $80K hay dump $50K trước? Comment bên dưới 👇"

6. Coin tags + at most 2 hashtags.

7. Disclaimer + source credit, exact format:
   Đây là tin tức tổng hợp, không phải lời khuyên đầu tư.
   Nguồn: {source}

REPEAT the same 7-section structure in English (HOOK / TL;DR / MY TAKE /
QUICK TA / OPEN QUESTION / tags / disclaimer + Source: {source}).

HARD RULES
- Each language section ≤ 1000 characters (HARD limit).
- AT MOST 2 hashtags total across the whole post.
- Each coin tag inserted ONCE in each language section.
- Numbers must be realistic for current market (e.g., BTC ~$60-70K range
  unless source explicitly says otherwise).
- Mini-TA must be SPECIFIC numbers, not "important levels" vague talk.

OUTPUT FORMAT (return EXACTLY this structure, nothing else)
---VI---
<vietnamese post following 7-section structure>
---EN---
<english post following 7-section structure>
---END---
"""

LONG_TEMPLATE = """\
You are a Vietnamese crypto-trading copywriter. Write the bilingual
analysis post described below. Do NOT ask clarifying questions, do NOT
explain reasoning, do NOT add preamble or postscript. Output ONLY the
formatted block exactly as specified. Treat the article data below as
canonical input.

SOURCE ARTICLE
Source: {source}
Title: {title}
Body: {content}
Importance: high
Coin tags: {coin_tags}

POST STRUCTURE — REQUIRED ANALYSIS POST, in this order:

1. 🚨 HOOK (line 1) — high-stakes framing or bold call.
2. 📌 SỰ KIỆN (3-4 sentences) — what happened, concrete facts/numbers.
3. 💥 TÁC ĐỘNG THỊ TRƯỜNG (3-4 sentences) — knock-on effects on BTC/ETH/alts.
4. 💡 QUAN ĐIỂM CỦA TÔI (3-4 sentences) — strong stance, "Theo tôi...".
5. 📊 PHÂN TÍCH KỸ THUẬT (4-5 bullet lines, specific levels):
   - Key support / resistance with exact prices
   - RSI / MACD / EMA reading
   - Volume signal
   - Entry / stop-loss / target zones
6. 🎯 KỊCH BẢN 24-48H (2 bullet scenarios: bullish path / bearish path)
7. 👇 CÂU HỎI MỞ — invite engagement.
8. Coin tags + at most 2 hashtags.
9. Disclaimer + source:
   Đây là tin tức tổng hợp, không phải lời khuyên đầu tư.
   Nguồn: {source}

REPEAT same 9-section structure in English.

HARD RULES
- Each language section ≤ 1000 characters (HARD limit).
- AT MOST 2 hashtags total across the whole post.
- Mini-TA must be SPECIFIC numbers.
- Take a definitive stance — no fence-sitting.

OUTPUT FORMAT (return EXACTLY this structure)
---VI---
<vietnamese analysis post>
---EN---
<english analysis post>
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


def build_prompt(*, title: str, content: str, importance: str,
                 coin_tags: list[str], source: str = "Unknown") -> str:
    tags_str = " ".join(f"${t}" for t in coin_tags)
    tmpl = LONG_TEMPLATE if importance == "high" else SHORT_TEMPLATE
    return tmpl.format(title=title, content=content, importance=importance,
                       coin_tags=tags_str, source=_pretty_source(source))


def parse_output(output: str) -> tuple[str, str]:
    try:
        after_vi = output.split("---VI---", 1)[1]
        vi_part, after_en = after_vi.split("---EN---", 1)
        en_part = after_en.split("---END---", 1)[0]
        return vi_part.strip(), en_part.strip()
    except (IndexError, ValueError) as e:
        raise ValueError(f"Rewriter output not in expected format: {e}")
