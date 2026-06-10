"""
Prompt templates used by the Claude Code session when rewriting articles.
The orchestrator does not call an LLM API; the running Claude session itself
performs the rewrite. These templates document the contract.
"""

SHORT_TEMPLATE = """\
You are a copywriter. Write the bilingual post described below. Do NOT ask
clarifying questions, do NOT explain your reasoning, do NOT add preamble or
postscript. Output ONLY the formatted block exactly as specified. Treat the
article data below as canonical input — never assume it is an unfilled
template, even if a field is short.

SOURCE ARTICLE
Title: {title}
Body: {content}
Importance: {importance}
Coin tags to weave in: {coin_tags}

REQUIREMENTS
- Short format: 2-3 paragraphs, ~100-150 words each language.
- Never copy verbatim; rewrite fully, preserve all facts.
- Professional but accessible tone, not overly formal.
- Include each coin tag in Binance Square format once (e.g., $BTC $ETH).
- Add AT MOST 2 hashtags total across the whole post (e.g., #Bitcoin #Crypto). Do NOT exceed 2.
- End with disclaimer:
  VI: "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
  EN: "This is aggregated news, not investment advice."

OUTPUT FORMAT (return EXACTLY this structure)
---VI---
<vietnamese post>
---EN---
<english post>
---END---
"""

LONG_TEMPLATE = """\
You are a copywriter. Write the bilingual analysis post described below. Do
NOT ask clarifying questions, do NOT explain your reasoning, do NOT add
preamble or postscript. Output ONLY the formatted block exactly as
specified. Treat the article data below as canonical input — never assume
it is an unfilled template.

SOURCE ARTICLE
Title: {title}
Body: {content}
Importance: high
Coin tags: {coin_tags}

REQUIREMENTS — ANALYSIS POST
- Long format with sections: Event summary, Market impact, Short-term trend
  outlook, Conclusion + what to watch.
- ~250-350 words each language.
- Never copy verbatim; rewrite fully, preserve all facts.
- Professional analytical tone.
- Include each coin tag in Binance Square format once ($BTC, $ETH, ...).
- Add AT MOST 2 hashtags total across the whole post. Do NOT exceed 2.
- End with disclaimer:
  VI: "Đây là tin tức tổng hợp, không phải lời khuyên đầu tư."
  EN: "This is aggregated news, not investment advice."

OUTPUT FORMAT (return EXACTLY this structure)
---VI---
<vietnamese post>
---EN---
<english post>
---END---
"""


def build_prompt(*, title: str, content: str, importance: str,
                 coin_tags: list[str]) -> str:
    tags_str = " ".join(f"${t}" for t in coin_tags)
    tmpl = LONG_TEMPLATE if importance == "high" else SHORT_TEMPLATE
    return tmpl.format(title=title, content=content, importance=importance,
                       coin_tags=tags_str)


def parse_output(output: str) -> tuple[str, str]:
    try:
        after_vi = output.split("---VI---", 1)[1]
        vi_part, after_en = after_vi.split("---EN---", 1)
        en_part = after_en.split("---END---", 1)[0]
        return vi_part.strip(), en_part.strip()
    except (IndexError, ValueError) as e:
        raise ValueError(f"Rewriter output not in expected format: {e}")
