"""
Generate a 7-day price chart PNG from CoinGecko's free public API.
Used as a fallback cover image when the source article has no embedded
image (or to overlay extra visual punch on top of news).
"""
from __future__ import annotations
import os
import tempfile
from datetime import datetime
from typing import Optional

import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


COINGECKO_BASE = "https://api.coingecko.com/api/v3"

TICKER_TO_CG = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin",
    "ADA": "cardano", "AVAX": "avalanche-2", "LINK": "chainlink",
    "MATIC": "matic-network",
}


def _fetch_prices(coin_id: str, days: int = 7,
                  timeout: int = 30) -> tuple[Optional[list], Optional[str]]:
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
    try:
        resp = requests.get(url, params={"vs_currency": "usd", "days": days},
                            timeout=timeout,
                            headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException as e:
        return None, f"http error: {e}"
    if not resp.ok:
        return None, f"http {resp.status_code}"
    try:
        data = resp.json()
    except Exception as e:
        return None, f"json error: {e}"
    raw = data.get("prices") or []
    if not raw:
        return None, "empty prices array"
    out = [(datetime.utcfromtimestamp(ts / 1000), float(p)) for ts, p in raw]
    return out, None


def make_chart(ticker: str, *, days: int = 7,
               out_path: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Create a 7-day line chart PNG for `ticker`. Returns (path, error)."""
    coin_id = TICKER_TO_CG.get(ticker.upper())
    if not coin_id:
        return None, f"unsupported ticker {ticker}"

    prices, err = _fetch_prices(coin_id, days=days)
    if err:
        return None, err

    xs = [p[0] for p in prices]
    ys = [p[1] for p in prices]
    first, last = ys[0], ys[-1]
    change_pct = (last - first) / first * 100 if first else 0.0
    color = "#16c784" if change_pct >= 0 else "#ea3943"

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor("#0e0e10")
    ax.set_facecolor("#0e0e10")
    ax.plot(xs, ys, color=color, linewidth=2.2)
    ax.fill_between(xs, ys, min(ys), color=color, alpha=0.12)

    title = f"{ticker.upper()}/USD  ${last:,.2f}  ({change_pct:+.2f}% / {days}d)"
    ax.set_title(title, color="#ffffff", fontsize=14, pad=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(colors="#aaaaaa", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#333333")
    ax.grid(True, linestyle="--", alpha=0.18, color="#888888")

    if out_path is None:
        fd, out_path = tempfile.mkstemp(suffix=".png", prefix="bn_chart_")
        os.close(fd)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path, None
