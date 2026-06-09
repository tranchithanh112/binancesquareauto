"""
X/Twitter profile scrape recipes. Executed by Claude Code MCP browser tools.
Without authentication, X is heavily rate-limited — falls back to Nitter.
"""


def x_profile_recipe(handle: str, max_posts: int) -> dict:
    return {
        "source": f"x::{handle}",
        "primary_url": f"https://x.com/{handle}",
        "fallback_url": f"https://nitter.net/{handle}",
        "max_posts": max_posts,
        "instructions": (
            "1. Navigate to primary_url. If the page fails to load posts within "
            "8 seconds or shows a login wall, navigate to fallback_url.\n"
            "2. Snapshot the profile timeline.\n"
            "3. Extract the {n} most recent posts. Skip retweets/replies.\n"
            "4. For each: post text, post URL (full permalink), and timestamp.\n"
            "5. Return JSON list with keys: title (first 120 chars of text), "
            "url, summary (full text)."
        ).format(n=max_posts),
    }
