"""
Binance Square OpenAPI client. Posts content via the official endpoint
(no UI automation). Endpoint + headers per the binance-skills-hub
square-post skill (lib.mjs).

Endpoint:    POST https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add
Headers:     X-Square-OpenAPI-Key, Content-Type, clienttype
Body (text): { "contentType": 1, "bodyTextOnly": "<text>" }
Success:     JSON with code "000000"; data may include id, shareLink, publishStatus.
"""
from __future__ import annotations
from typing import Optional

import requests


import re as _re

MAX_HASHTAGS = 2


def sanitize_hashtags(text: str, max_total: int = MAX_HASHTAGS) -> str:
    """Keep only the first `max_total` hashtags across the body; strip the rest."""
    seen = 0
    def _sub(m):
        nonlocal seen
        seen += 1
        return m.group(0) if seen <= max_total else ""
    out = _re.sub(r"#\w+", _sub, text)
    # Collapse double spaces left behind
    out = _re.sub(r" {2,}", " ", out)
    return out


V1_BASE = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi"
V2_BASE = "https://www.binance.com/bapi/composite/v2/public/pgc/openApi"
ADD_CONTENT_URL = f"{V1_BASE}/content/add"
PRESIGNED_URL = f"{V2_BASE}/image/presignedUrl"
IMAGE_STATUS_URL = f"{V2_BASE}/image/imageStatus"
SUCCESS_CODE = "000000"

CONTENT_TYPE_MAP = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
}


def _headers(api_key: str) -> dict:
    return {
        "X-Square-OpenAPI-Key": api_key,
        "Content-Type": "application/json",
        "clienttype": "binanceSkill",
    }


def _api(url: str, api_key: str, body: dict,
         timeout: int = 30) -> tuple[Optional[dict], Optional[str]]:
    """Call a Binance Square API endpoint. Returns (data, error_msg).
    Handles 504 on /content/add as success (per upstream skill behavior)."""
    try:
        resp = requests.post(url, json=body, headers=_headers(api_key),
                             timeout=timeout)
    except requests.RequestException as e:
        return None, f"http error: {e}"
    if url == ADD_CONTENT_URL and resp.status_code == 504:
        return {"id": None, "shareLink": None,
                "publishStatus": "success_without_post_id"}, None
    try:
        js = resp.json()
    except Exception as e:
        return None, f"non-json response (status {resp.status_code}): {e}"
    code = str(js.get("code", ""))
    if code == SUCCESS_CODE:
        return js.get("data") or {}, None
    msg = js.get("message") or js.get("messageDetail") or str(js)
    return None, f"API error [{code}]: {msg}"


def _prep_body(body_text: str) -> str:
    return sanitize_hashtags(body_text)


def post_text(*, api_key: str, body_text: str,
              timeout: int = 30) -> tuple[str, Optional[str], Optional[dict]]:
    """Publish a short text-only post."""
    if not api_key:
        return "failed", "missing api key", None
    data, err = _api(ADD_CONTENT_URL, api_key,
                     {"contentType": 1, "bodyTextOnly": _prep_body(body_text)},
                     timeout=timeout)
    if err:
        return "failed", err, None
    return "posted", None, data


def _content_type_for(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return CONTENT_TYPE_MAP.get(ext, "application/octet-stream")


def upload_image(*, api_key: str, image_path: str,
                 poll_interval: float = 3.0, max_polls: int = 10,
                 timeout: int = 60) -> tuple[Optional[str], Optional[str]]:
    """Upload one image to Binance Square storage. Returns (image_url, error)."""
    import os
    import time

    if not api_key:
        return None, "missing api key"
    if not os.path.isfile(image_path):
        return None, f"image not found: {image_path}"

    image_name = os.path.basename(image_path)
    data, err = _api(PRESIGNED_URL, api_key, {"imageName": image_name},
                     timeout=timeout)
    if err:
        return None, f"presignedUrl: {err}"
    presigned_url = data.get("presignedUrl")
    file_ticket = data.get("fileTicket")
    if not presigned_url or not file_ticket:
        return None, f"presignedUrl missing fields in: {data}"

    # PUT to S3
    try:
        with open(image_path, "rb") as f:
            put = requests.put(presigned_url, data=f.read(),
                               headers={"Content-Type": _content_type_for(image_path)},
                               timeout=timeout)
    except requests.RequestException as e:
        return None, f"S3 PUT error: {e}"
    if not put.ok:
        return None, f"S3 PUT failed: {put.status_code} {put.text[:200]}"

    # Poll status
    for _ in range(max_polls):
        data, err = _api(IMAGE_STATUS_URL, api_key, {"fileTicket": file_ticket},
                         timeout=timeout)
        if err:
            return None, f"imageStatus: {err}"
        status = data.get("status")
        if status == 1:
            url = data.get("imageUrl")
            if not url:
                return None, "imageStatus status=1 but no imageUrl"
            return url, None
        if status == 2:
            return None, f"image processing failed: {data.get('failedReason')}"
        time.sleep(poll_interval)
    return None, f"image poll timed out after {max_polls} retries"


def post_text_with_images(*, api_key: str, body_text: str,
                          image_paths: list[str],
                          timeout: int = 30) -> tuple[str, Optional[str], Optional[dict]]:
    """Upload images then publish. Returns (status, error, data)."""
    if not api_key:
        return "failed", "missing api key", None
    if not image_paths:
        return post_text(api_key=api_key, body_text=body_text, timeout=timeout)
    if len(image_paths) > 4:
        return "failed", "max 4 images", None
    image_urls: list[str] = []
    for p in image_paths:
        url, err = upload_image(api_key=api_key, image_path=p, timeout=timeout)
        if err:
            return "failed", f"upload {p}: {err}", None
        image_urls.append(url)
    return post_text_with_image_urls(
        api_key=api_key, body_text=body_text,
        image_urls=image_urls, timeout=timeout,
    )


def post_text_with_image_urls(*, api_key: str, body_text: str,
                              image_urls: list[str],
                              timeout: int = 30) -> tuple[str, Optional[str], Optional[dict]]:
    """Publish using already-uploaded Binance image URLs (no re-upload)."""
    if not api_key:
        return "failed", "missing api key", None
    if not image_urls:
        return post_text(api_key=api_key, body_text=body_text, timeout=timeout)
    if len(image_urls) > 4:
        return "failed", "max 4 images", None
    data, err = _api(ADD_CONTENT_URL, api_key, {
        "contentType": 1,
        "bodyTextOnly": _prep_body(body_text),
        "imageList": image_urls,
    }, timeout=timeout)
    if err:
        return "failed", err, None
    return "posted", None, data
