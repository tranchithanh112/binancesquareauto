"""
Binance Square posting via Playwright. Uses persistent Chrome profile.
First run: user must manually log in to https://www.binance.com/en/square
in the launched browser, then quit. Cookies persist.

Single browser session handles many posts (avoids profile-lock conflicts
that arise when launching multiple Chromium instances against the same
user_data_dir).
"""
from __future__ import annotations
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from src.runners.playwright_fetch import DEFAULT_PROFILE_DIR


BINANCE_SQUARE_URL = "https://www.binance.com/en/square"
BINANCE_SQUARE_CREATE_URL = BINANCE_SQUARE_URL  # back-compat alias
LOGIN_WALL_HINT = "login"
SCREENSHOTS_DIR = Path("data/screenshots")


def open_browser_for_login(profile_dir: Path = DEFAULT_PROFILE_DIR,
                            max_wait_seconds: int = 600) -> None:
    """Open a Chromium window at Binance login. Wait until user closes
    every tab or until max_wait_seconds elapses. Cookies persist."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        page.goto("https://accounts.binance.com/en/login", timeout=60000)
        print(f"Browser opened. Log in, then close the window. "
              f"Auto-close after {max_wait_seconds}s.", flush=True)
        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            try:
                if not ctx.pages:
                    break
                time.sleep(2)
            except Exception:
                break
        try:
            ctx.close()
        except Exception:
            pass


def _dump_screenshot(page, label: str) -> str:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = SCREENSHOTS_DIR / f"{ts}_{label}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception as e:
        return f"screenshot_failed:{e}"


def _post_one_on_page(page, *, post_id: int, content_vi: str,
                       content_en: str, coin_tags: list[str],
                       scheduled_iso: Optional[str]) -> tuple[str, Optional[str]]:
    """Post a single item on an already-open page within a logged-in
    persistent context. Returns (status, error_msg)."""
    body = f"{content_vi}\n\n---\n\n{content_en}"

    try:
        page.goto(BINANCE_SQUARE_URL, wait_until="domcontentloaded",
                  timeout=30000)
    except PWTimeout:
        return "failed", f"navigation timeout (screenshot={_dump_screenshot(page, f'p{post_id}_nav')})"

    page.wait_for_timeout(4000)
    if LOGIN_WALL_HINT in page.url.lower():
        return "failed", "not_logged_in"

    # Click compose. Compose CTA is a span outside any <button>; the
    # in-modal publish button wraps a similar span. Use :not(button > *)
    # so we don't grab the publish button when the modal is already open.
    compose_selectors = [
        'span[data-bn-type="text"].css-1c82c04:has-text("Post"):visible',
    ]
    opened = False
    for sel in compose_selectors:
        try:
            handles = page.query_selector_all(sel)
            for h in handles:
                # Skip ones whose parent is a <button> (that's the publish btn).
                tag = h.evaluate("el => el.parentElement && el.parentElement.tagName")
                if tag and tag.upper() == "BUTTON":
                    continue
                try:
                    h.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass
                h.click()
                opened = True
                break
            if opened:
                break
        except Exception:
            continue
    if not opened:
        return "failed", f"compose button not found (screenshot={_dump_screenshot(page, f'p{post_id}_compose')})"

    page.wait_for_timeout(2500)

    # Editor — observed: <div class="ProseMirror" contenteditable="true">
    editor_selectors = [
        '.ProseMirror[contenteditable="true"]',
        '.short-editor-content [contenteditable="true"]',
        'div[contenteditable="true"]',
    ]
    editor = None
    for sel in editor_selectors:
        try:
            editor = page.wait_for_selector(sel, timeout=5000)
            if editor:
                break
        except Exception:
            continue
    if editor is None:
        return "failed", f"editor not found (screenshot={_dump_screenshot(page, f'p{post_id}_editor')})"

    editor.click()
    page.wait_for_timeout(500)
    editor.type(body, delay=15)
    page.wait_for_timeout(1500)

    for ticker in coin_tags:
        page.keyboard.type(" ")
        page.keyboard.type(f"${ticker}", delay=40)
        page.wait_for_timeout(1500)
        try:
            suggestion = page.query_selector(
                f'[role="listbox"] >> text=/{ticker}/i'
            )
            if suggestion:
                suggestion.click()
        except Exception:
            pass
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

    # Scheduling lives behind a kebab/dropdown that exposes a
    # .menu-item containing "Schedule Post". For now, if scheduled_iso is
    # set but the schedule UI isn't reachable, ABORT to avoid accidental
    # immediate publish.
    if scheduled_iso:
        try:
            sched_item = page.query_selector(
                '.menu-item:has-text("Schedule Post")'
            )
            if sched_item is None:
                # Look for a kebab/more-actions trigger near the publish btn.
                kebab = None
                for sel in [
                    'button[aria-label*="More" i]',
                    'svg[viewBox="0 0 24 24"] >> nth=0',  # very loose
                ]:
                    try:
                        kebab = page.query_selector(sel)
                        if kebab:
                            kebab.click()
                            page.wait_for_timeout(800)
                            sched_item = page.query_selector(
                                '.menu-item:has-text("Schedule Post")'
                            )
                            if sched_item:
                                break
                    except Exception:
                        continue
            if sched_item is None:
                return "failed", (
                    f"schedule UI not found, refusing to publish immediately "
                    f"(screenshot={_dump_screenshot(page, f'p{post_id}_sched_missing')})"
                )
            sched_item.click()
            page.wait_for_timeout(1000)
            datetime_input = page.query_selector('input[type="datetime-local"]')
            if datetime_input:
                from datetime import datetime as _dt
                dt = _dt.fromisoformat(
                    scheduled_iso.replace("Z", "+00:00")
                ).astimezone()
                datetime_input.fill(dt.strftime("%Y-%m-%dT%H:%M"))
            confirm = page.query_selector('button:has-text("Confirm")')
            if confirm:
                confirm.click()
        except Exception as e:
            return "failed", (
                f"schedule UI: {e} "
                f"(screenshot={_dump_screenshot(page, f'p{post_id}_schedule')})"
            )
    else:
        # Immediate publish — Observed publish: <button class="inactive css-rjdb8p">
        # The button is "inactive" until content present; should be active by now.
        publish = page.query_selector('button.css-rjdb8p')
        if publish is None:
            publish = page.query_selector(
                'button:has(span.css-1c82c04:has-text("Post"))'
            )
        if publish is None:
            return "failed", (
                f"publish button not found "
                f"(screenshot={_dump_screenshot(page, f'p{post_id}_publish')})"
            )
        try:
            publish.click()
        except Exception as e:
            return "failed", f"publish click: {e}"

    page.wait_for_timeout(5000)
    try:
        editor_text_after = page.evaluate(
            "() => document.querySelector('.ProseMirror[contenteditable=\"true\"]')?.innerText || ''"
        ) or ""
    except Exception:
        editor_text_after = ""
    if not editor_text_after.strip():
        return "scheduled", None
    return "failed", (
        f"no success indicator "
        f"(screenshot={_dump_screenshot(page, f'p{post_id}_verify')})"
    )


def post_many_to_binance_square(items: list[dict],
                                 profile_dir: Path = DEFAULT_PROFILE_DIR,
                                 headless: bool = False
                                 ) -> list[tuple[int, str, Optional[str]]]:
    """Open ONE persistent Chromium session and post each item sequentially.
    Each item dict: post_id, content_vi, content_en, coin_tags, scheduled_iso.
    Returns list of (post_id, status, error_msg).
    """
    profile_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[int, str, Optional[str]]] = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            page = ctx.new_page()
            for item in items:
                try:
                    status, err = _post_one_on_page(
                        page,
                        post_id=item["post_id"],
                        content_vi=item["content_vi"],
                        content_en=item["content_en"],
                        coin_tags=item["coin_tags"],
                        scheduled_iso=item.get("scheduled_iso"),
                    )
                except Exception as e:
                    status, err = "failed", f"exception: {e}"
                results.append((item["post_id"], status, err))
                # Small pause between posts to avoid rate-limiting
                page.wait_for_timeout(3000)
        finally:
            try:
                ctx.close()
            except Exception:
                pass
    return results


def post_to_binance_square(*, content_vi: str, content_en: str,
                           coin_tags: list[str], scheduled_iso: Optional[str],
                           profile_dir: Path = DEFAULT_PROFILE_DIR,
                           headless: bool = False) -> tuple[str, Optional[str]]:
    """Single-post wrapper (legacy). Opens own browser context. Prefer
    post_many_to_binance_square for batches."""
    results = post_many_to_binance_square(
        [{
            "post_id": 0,
            "content_vi": content_vi,
            "content_en": content_en,
            "coin_tags": coin_tags,
            "scheduled_iso": scheduled_iso,
        }],
        profile_dir=profile_dir,
        headless=headless,
    )
    _, status, err = results[0]
    return status, err
