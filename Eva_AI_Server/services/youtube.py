"""
YouTube Data API v3 — search helper for roadmap resources.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


class YouTubeSearchFailed(Exception):
    """Raised when the YouTube API cannot be used (config, network, HTTP error). Empty search results do not raise."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


async def search_topic(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search YouTube for videos matching `query`.

    Returns up to `max_results` items:
      { "title", "url", "thumbnail", "channel" }

    Empty query → [].
    Successful HTTP 200 with no/invalid items → [].
    Missing key, transport errors, non-200, or bad JSON → YouTubeSearchFailed.
    """
    q = (query or "").strip()
    if not q:
        return []

    api_key = (settings.YOUTUBE_API_KEY or "").strip()
    if not api_key:
        raise YouTubeSearchFailed("YOUTUBE_API_KEY is not set — add it to your environment and try again.")

    n = max(1, min(int(max_results), 50))
    params = {
        "part": "snippet",
        "q": q,
        "type": "video",
        "maxResults": str(n),
        "order": "relevance",
        "key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(YOUTUBE_SEARCH_URL, params=params)
    except Exception as exc:  # noqa: BLE001
        logger.warning("YouTube HTTP error for query %r: %s", q[:80], exc)
        raise YouTubeSearchFailed(
            f"Could not reach YouTube (network or timeout). Underlying error: {exc}",
        ) from exc

    if response.status_code != 200:
        snippet = (response.text or "")[:400]
        logger.warning(
            "YouTube API status %s for query %r: %s",
            response.status_code,
            q[:80],
            snippet,
        )
        raise YouTubeSearchFailed(
            f"YouTube returned HTTP {response.status_code}. "
            f"Body (truncated): {snippet!r}",
            status_code=int(response.status_code),
        )

    try:
        payload: Dict[str, Any] = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("YouTube JSON decode error: %s", exc)
        raise YouTubeSearchFailed(f"Could not parse YouTube response as JSON: {exc}") from exc

    items = payload.get("items")
    if not isinstance(items, list):
        return []

    out: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        vid = (item.get("id") or {})
        if not isinstance(vid, dict):
            continue
        video_id = vid.get("videoId")
        if not video_id:
            continue
        snippet_d = item.get("snippet") or {}
        if not isinstance(snippet_d, dict):
            continue
        title = str(snippet_d.get("title") or "").strip()
        channel = str(snippet_d.get("channelTitle") or "").strip()
        thumbs = snippet_d.get("thumbnails") or {}
        thumb_url = ""
        if isinstance(thumbs, dict):
            high = thumbs.get("high") or thumbs.get("medium") or thumbs.get("default")
            if isinstance(high, dict):
                thumb_url = str(high.get("url") or "")
        out.append(
            {
                "title": title or "YouTube video",
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": thumb_url,
                "channel": channel,
            },
        )
        if len(out) >= n:
            break

    return out
