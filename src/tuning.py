"""
Weekly self-tuning of post-type weights based on real engagement.

Weights live in data/tuning.json so the bot can adjust them over time
without code edits. pick_post_type() reads them; auto_tune() shifts weight
toward post types that earn more engagement and away from the weak ones,
keeping a small floor so every type keeps getting sampled (exploration).
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


TUNING_PATH = Path("data/tuning.json")
DEFAULT_WEIGHTS = {"news_ta": 50.0, "signal": 20.0, "poll": 15.0, "hot_take": 15.0}
MIN_W, MAX_W = 5.0, 60.0
STEP = 0.30          # max ±30% adjustment per week
KEEP_HISTORY = 12    # weeks


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


DEFAULT_STYLE = ""  # free-text guidance appended to the writing prompt


def load_style(path: Path | str = TUNING_PATH) -> str:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return str(d.get("style_hint") or DEFAULT_STYLE)
    except Exception:
        return DEFAULT_STYLE


def save_style(style_hint: str, path: Path | str = TUNING_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_all(path)
    data["style_hint"] = style_hint[:600]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fmt_posts(rows: list[dict]) -> str:
    out = []
    for r in rows:
        out.append(
            f"[{r.get('post_type')}] 👁{r.get('views')} ❤{r.get('likes')} "
            f"💬{r.get('comments')} 🔥{r.get('reactions')}\n{r.get('content_vi','')[:400]}"
        )
    return "\n---\n".join(out) if out else "(chưa có)"


def evolve_style(best: list[dict], worst: list[dict], current_hint: str,
                 claude_fn) -> str | None:
    """Ask the LLM to evolve a short Vietnamese style guideline based on which
    posts earned engagement and which flopped. Returns a new hint (≤ ~400
    chars) or None on failure. `claude_fn(prompt)->(output, err)`."""
    if not best:
        return None
    prompt = (
        "Bạn là chuyên gia tối ưu nội dung Binance Square tiếng Việt. Dưới đây là "
        "các bài ĐĂNG TỐT NHẤT và KÉM NHẤT của một tài khoản (kèm lượt xem/like/"
        "comment/reaction). Nhiệm vụ: rút ra MỘT đoạn hướng dẫn ngắn (tiếng Việt, "
        "dưới 400 ký tự) để bài sau viết hấp dẫn hơn — nói cụ thể về CẤU TRÚC, ĐỘ "
        "DÀI, VĂN PHONG, mở bài, cách câu tương tác. Chỉ nêu điều CỤ THỂ rút ra từ "
        "dữ liệu, không chung chung. KHÔNG giải thích, KHÔNG markdown.\n\n"
        f"HƯỚNG DẪN HIỆN TẠI: {current_hint or '(chưa có)'}\n\n"
        f"=== BÀI TỐT NHẤT ===\n{_fmt_posts(best)}\n\n"
        f"=== BÀI KÉM NHẤT ===\n{_fmt_posts(worst)}\n\n"
        "Xuất ĐÚNG khối này:\n---HINT---\n<đoạn hướng dẫn mới>\n---END---"
    )
    try:
        out, err = claude_fn(prompt)
    except Exception:
        return None
    if err or not out:
        return None
    try:
        hint = out.split("---HINT---", 1)[1].split("---END---", 1)[0].strip()
    except (IndexError, ValueError):
        return None
    return hint[:600] if hint else None


def load_weights(path: Path | str = TUNING_PATH) -> dict[str, float]:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        w = d.get("weights")
        if isinstance(w, dict) and w:
            return {k: float(v) for k, v in w.items()}
    except Exception:
        pass
    return dict(DEFAULT_WEIGHTS)


def _read_all(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(path: Path, weights: dict, entry: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_all(path)
    data["weights"] = weights
    hist = data.get("history", [])
    hist.append(entry)
    data["history"] = hist[-KEEP_HISTORY:]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def engagement_score(row: dict) -> float:
    """Score one post_type's average engagement. Comments/likes weigh far
    more than passive views (they're what actually signals reach)."""
    return (float(row.get("avg_views") or 0)
            + float(row.get("avg_likes") or 0) * 50
            + float(row.get("avg_comments") or 0) * 100
            + float(row.get("avg_reactions") or 0) * 30)


def _prev_avg_score(path: Path) -> float | None:
    data = _read_all(path)
    hist = data.get("history", [])
    if hist:
        return hist[-1].get("avg_score")
    return None


def auto_tune(by_type: list[dict], *, path: Path | str = TUNING_PATH) -> dict:
    """Adjust post-type weights from per-type engagement stats.
    `by_type` is db.stats_by_post_type() output. Returns a report dict."""
    path = Path(path)
    weights = load_weights(path)
    scores = {r["post_type"]: engagement_score(r)
              for r in by_type if r.get("post_type")}
    if not scores:
        return {"changed": False, "reason": "no stats yet", "weights": weights}

    avg = sum(scores.values()) / len(scores)
    new = dict(weights)
    for t, s in scores.items():
        cur = new.get(t, DEFAULT_WEIGHTS.get(t, 15.0))
        rel = (s - avg) / avg if avg > 0 else 0.0
        rel = max(-1.0, min(1.0, rel))
        adj = cur * (1 + STEP * rel)
        new[t] = max(MIN_W, min(MAX_W, adj))
    total = sum(new.values())
    if total > 0:
        new = {t: round(v / total * 100, 1) for t, v in new.items()}

    prev_avg = _prev_avg_score(path)
    improving = prev_avg is None or avg > prev_avg
    entry = {"at": _now_iso(), "avg_score": round(avg, 2),
             "scores": {k: round(v, 2) for k, v in scores.items()},
             "weights": new}
    _save(path, new, entry)
    return {
        "changed": True,
        "old": {k: round(v, 1) for k, v in weights.items()},
        "weights": new,
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "avg_score": round(avg, 2),
        "prev_avg_score": round(prev_avg, 2) if prev_avg is not None else None,
        "improving": improving,
    }
