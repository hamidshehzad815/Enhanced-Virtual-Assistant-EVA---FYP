"""
YouTube Data API v3 — search helper for roadmap resources.

Fetches candidate videos, ranks by view count, returns top N.
Rotates through multiple API keys when daily quota is exceeded.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# Search broader, then pick highest-view videos (avoids low-view junk).
SEARCH_CANDIDATE_POOL = 25

_QUOTA_ERROR_REASONS = frozenset(
    {
        "quotaExceeded",
        "dailyLimitExceeded",
        "userRateLimitExceeded",
    },
)


class YouTubeSearchFailed(Exception):
    """Raised when the YouTube API cannot be used (config, network, HTTP error). Empty search results do not raise."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def resolve_youtube_api_keys(api_keys: Optional[Sequence[str]] = None) -> List[str]:
    """Normalize API keys: explicit list, then YOUTUBE_API_KEYS env, then YOUTUBE_API_KEY."""
    if api_keys:
        keys = [str(k).strip() for k in api_keys if str(k).strip()]
        if keys:
            return keys

    import os

    multi = (os.getenv("YOUTUBE_API_KEYS") or "").strip()
    if multi:
        keys = [part.strip() for part in multi.split(",") if part.strip()]
        if keys:
            return keys

    single = (settings.YOUTUBE_API_KEY or "").strip()
    return [single] if single else []


def _is_quota_exceeded(status_code: int, payload: Any) -> bool:
    if status_code != 403:
        return False
    if not isinstance(payload, dict):
        return False
    err = payload.get("error")
    if not isinstance(err, dict):
        return False
    errors = err.get("errors")
    if not isinstance(errors, list):
        return False
    for item in errors:
        if isinstance(item, dict) and item.get("reason") in _QUOTA_ERROR_REASONS:
            return True
    message = str(err.get("message") or "").lower()
    return "quota" in message or "exceeded" in message


async def _http_get_json(
    client: httpx.AsyncClient,
    url: str,
    params: Dict[str, str],
) -> tuple[int, Any, str]:
    try:
        response = await client.get(url, params=params)
    except Exception as exc:  # noqa: BLE001
        logger.warning("YouTube HTTP error for %s: %s", url, exc)
        raise YouTubeSearchFailed(
            f"Could not reach YouTube (network or timeout). Underlying error: {exc}",
        ) from exc

    text = response.text or ""
    try:
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        if response.status_code == 200:
            raise YouTubeSearchFailed(f"Could not parse YouTube response as JSON: {exc}") from exc
        payload = None

    return response.status_code, payload, text


async def _request_with_key_rotation(
    client: httpx.AsyncClient,
    url: str,
    params_base: Dict[str, str],
    api_keys: List[str],
    *,
    query_label: str,
) -> Any:
    """Try each API key; rotate on quota errors."""
    if not api_keys:
        raise YouTubeSearchFailed(
            "No YouTube API keys configured — add keys to fetch_resources.py or YOUTUBE_API_KEY(S) in .env.",
        )

    last_quota_msg = ""
    for index, api_key in enumerate(api_keys, start=1):
        params = {**params_base, "key": api_key}
        status, payload, text = await _http_get_json(client, url, params)

        if status == 200:
            return payload

        snippet = text[:400]
        if _is_quota_exceeded(status, payload):
            last_quota_msg = (
                f"API key {index}/{len(api_keys)} hit daily quota (HTTP {status})."
            )
            logger.warning("%s %s", query_label, last_quota_msg)
            continue

        logger.warning(
            "YouTube API status %s for %s: %s",
            status,
            query_label,
            snippet,
        )
        raise YouTubeSearchFailed(
            f"YouTube returned HTTP {status}. Body (truncated): {snippet!r}",
            status_code=int(status),
        )

    raise YouTubeSearchFailed(
        f"All {len(api_keys)} YouTube API key(s) exhausted for today. "
        f"Last error: {last_quota_msg or 'quota exceeded'}",
        status_code=403,
    )


def _video_ids_from_search(payload: Any) -> List[str]:
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    ids: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        vid = item.get("id") or {}
        if not isinstance(vid, dict):
            continue
        video_id = vid.get("videoId")
        if video_id:
            ids.append(str(video_id))
    return ids


def _thumbnail_url(snippet_d: Dict[str, Any]) -> str:
    thumbs = snippet_d.get("thumbnails") or {}
    if not isinstance(thumbs, dict):
        return ""
    high = thumbs.get("high") or thumbs.get("medium") or thumbs.get("default")
    if isinstance(high, dict):
        return str(high.get("url") or "")
    return ""


def _rows_from_videos_payload(payload: Any, *, max_results: int) -> List[Dict[str, str]]:
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    ranked: List[tuple[int, Dict[str, str]]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        video_id = str(item.get("id") or "").strip()
        if not video_id:
            continue
        snippet_d = item.get("snippet") or {}
        stats = item.get("statistics") or {}
        if not isinstance(snippet_d, dict):
            snippet_d = {}
        if not isinstance(stats, dict):
            stats = {}

        try:
            views = int(stats.get("viewCount") or 0)
        except (TypeError, ValueError):
            views = 0

        title = str(snippet_d.get("title") or "").strip() or "YouTube video"
        channel = str(snippet_d.get("channelTitle") or "").strip()
        ranked.append(
            (
                views,
                {
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": _thumbnail_url(snippet_d),
                    "channel": channel,
                    "view_count": str(views),
                },
            ),
        )

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in ranked[:max_results]]


async def search_topic(
    query: str,
    max_results: int = 3,
    *,
    api_keys: Optional[Sequence[str]] = None,
    candidate_pool: int = SEARCH_CANDIDATE_POOL,
) -> List[Dict[str, str]]:
    """
    Search YouTube for videos matching `query`, return top `max_results` by view count.

    Returns items: { "title", "url", "thumbnail", "channel", "view_count" }
    """
    q = (query or "").strip()
    if not q:
        return []

    keys = resolve_youtube_api_keys(api_keys)
    n = max(1, min(int(max_results), 50))
    pool = max(n, min(int(candidate_pool), 50))

    async with httpx.AsyncClient(timeout=20.0) as client:
        search_payload = await _request_with_key_rotation(
            client,
            YOUTUBE_SEARCH_URL,
            {
                "part": "snippet",
                "q": q,
                "type": "video",
                "maxResults": str(pool),
                "order": "relevance",
            },
            keys,
            query_label=f"search {q[:60]!r}",
        )

        video_ids = _video_ids_from_search(search_payload)
        if not video_ids:
            return []

        videos_payload = await _request_with_key_rotation(
            client,
            YOUTUBE_VIDEOS_URL,
            {
                "part": "snippet,statistics",
                "id": ",".join(video_ids),
            },
            keys,
            query_label=f"videos stats {q[:60]!r}",
        )

    return _rows_from_videos_payload(videos_payload, max_results=n)
