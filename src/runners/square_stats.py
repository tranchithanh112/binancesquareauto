"""
Fetch engagement stats for a public Binance Square profile.

The profile page calls a public (no-auth) endpoint that returns each post
with viewCount / likeCount / commentCount / shareCount / reactions. We page
through it and hand back normalized dicts the caller matches by content id.

Endpoint (GET):
  /bapi/composite/v2/friendly/pgc/content/queryUserProfilePageContentsWithFilter
    ?targetSquareUid=<UID>&timeOffset=<cursor>&pageSize=<n>
"""
from __future__ import annotations
from typing import Iterator, Optional

import requests


PROFILE_CONTENTS_URL = (
    "https://www.binance.com/bapi/composite/v2/friendly/pgc/content/"
    "queryUserProfilePageContentsWithFilter"
)
SUCCESS_CODE = "000000"


def _headers() -> dict:
    return {"User-Agent": "Mozilla/5.0", "clienttype": "web"}


def _fetch_page(uid: str, time_offset: int, page_size: int,
                timeout: int) -> tuple[Optional[list], Optional[int], Optional[str]]:
    """Return (items, next_offset, error)."""
    params = {"targetSquareUid": uid, "timeOffset": time_offset,
              "pageSize": page_size}
    try:
        r = requests.get(PROFILE_CONTENTS_URL, params=params,
                         headers=_headers(), timeout=timeout)
    except requests.RequestException as e:
        return None, None, f"http error: {e}"
    try:
        js = r.json()
    except Exception as e:
        return None, None, f"json error (status {r.status_code}): {e}"
    if str(js.get("code")) != SUCCESS_CODE:
        return None, None, f"API code {js.get('code')}: {js.get('message')}"
    data = js.get("data")
    if isinstance(data, dict):
        items = (data.get("vos") or data.get("list")
                 or data.get("contents") or [])
    elif isinstance(data, list):
        items = data
    else:
        items = []
    if not items:
        return [], None, None
    last = items[-1]
    next_offset = (last.get("latestReleaseTime") or last.get("createTime")
                   or last.get("firstReleaseTime"))
    return items, next_offset, None


def _normalize(item: dict) -> dict:
    return {
        "binance_id": str(item.get("id")),
        "body": item.get("bodyTextOnly") or "",
        "title": item.get("title") or (item.get("bodyTextOnly") or "")[:60],
        "views": int(item.get("viewCount") or 0),
        "likes": int(item.get("likeCount") or 0),
        "comments": int(item.get("commentCount") or 0),
        "shares": int(item.get("shareCount") or 0),
        "reactions": int(item.get("totalReactionCount") or 0),
        "bookmarks": int(item.get("bookmarkCount") or 0),
    }


def iter_profile_stats(uid: str, *, max_pages: int = 10, page_size: int = 20,
                       timeout: int = 20) -> Iterator[dict]:
    """Yield normalized stat dicts for a profile, newest first."""
    time_offset = -1
    for _ in range(max_pages):
        items, next_offset, err = _fetch_page(uid, time_offset, page_size, timeout)
        if err:
            raise RuntimeError(err)
        if not items:
            return
        for it in items:
            yield _normalize(it)
        if not next_offset:
            return
        time_offset = next_offset
