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


async def search_topic(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search YouTube for videos matching `query`.

    Returns up to `max_results` items:
      { "title", "url", "thumbnail", "channel" }

    Never raises; returns [] on missing key, HTTP errors, or malformed JSON.
    """
    q = (query or "").strip()
    if not q:
        return []

    api_key = (settings.YOUTUBE_API_KEY or "").strip()
    if not api_key:
        logger.warning("YOUTUBE_API_KEY is not set; skipping YouTube search")
        return []

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
        return []

    if response.status_code != 200:
        logger.warning(
            "YouTube API status %s for query %r: %s",
            response.status_code,
            q[:80],
            (response.text or "")[:300],
        )
        return []

    try:
        payload: Dict[str, Any] = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("YouTube JSON decode error: %s", exc)
        return []

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
        snippet = item.get("snippet") or {}
        if not isinstance(snippet, dict):
            continue
        title = str(snippet.get("title") or "").strip()
        channel = str(snippet.get("channelTitle") or "").strip()
        thumbs = snippet.get("thumbnails") or {}
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
