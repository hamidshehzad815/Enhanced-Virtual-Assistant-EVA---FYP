"""
YouTube Data API v3 — search helper for roadmap resources.

Fetches candidate videos, filters out Shorts / live streams, then ranks by a
blended quality score (views, engagement, search relevance, recency, and
tutorial-length fit) and returns the top N. Rotates through multiple API keys
when daily quota is exceeded.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# Search broader, then filter Shorts and rank — avoids low-view junk and Shorts.
SEARCH_CANDIDATE_POOL = 30

# Videos at/under this length are treated as Shorts and dropped. Real tutorials
# run longer, so this reliably removes Shorts without losing useful content.
MIN_VIDEO_SECONDS = int(getattr(settings, "YOUTUBE_MIN_VIDEO_SECONDS", 61) or 61)

# Tutorial "sweet spot" length (seconds) used for the duration-fit score.
_IDEAL_MIN_SECONDS = 4 * 60      # 4 min
_IDEAL_MAX_SECONDS = 40 * 60     # 40 min

# Blended-score weights (must roughly sum to 1.0).
_W_VIEWS = 0.45
_W_RELEVANCE = 0.20
_W_ENGAGEMENT = 0.15
_W_RECENCY = 0.10
_W_DURATION = 0.10

_SHORTS_HINT = re.compile(r"#shorts?\b", re.IGNORECASE)
# ISO-8601 duration, e.g. PT12M30S, PT1H2M, PT45S. Live streams report "P0D".
_ISO_DURATION_RE = re.compile(
    r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$",
)

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
            f"Could not reach YouTube (network/firewall/proxy or timeout). Underlying error: {exc}",
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


def _duration_seconds(iso: Any) -> int:
    """Parse an ISO-8601 duration (e.g. 'PT12M30S') to seconds. 0 if unparseable/live."""
    if not iso or not isinstance(iso, str):
        return 0
    match = _ISO_DURATION_RE.match(iso.strip())
    if not match:
        return 0
    days, hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _age_days(published_at: Any) -> float:
    """Days since publication; unknown/unparseable dates are treated as old."""
    if not published_at or not isinstance(published_at, str):
        return 3650.0
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
    except Exception:  # noqa: BLE001
        return 3650.0


def _duration_fit(seconds: int) -> float:
    """1.0 for tutorial-length videos, tapering off for very short/long ones."""
    if _IDEAL_MIN_SECONDS <= seconds <= _IDEAL_MAX_SECONDS:
        return 1.0
    if seconds < _IDEAL_MIN_SECONDS:  # 61s–4min: short but not a Short
        return 0.6
    if seconds <= 90 * 60:  # 40–90 min: long-form course
        return 0.6
    return 0.3  # 90 min+: likely a livestream replay / full playlist dump


def _normalize(values: List[float]) -> List[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [0.5] * len(values)
    span = hi - lo
    return [(v - lo) / span for v in values]


def _rows_from_videos_payload(
    payload: Any,
    *,
    max_results: int,
    min_seconds: int,
) -> List[Dict[str, str]]:
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    # 1) Collect raw metrics, keeping search-relevance order as the index.
    candidates: List[Dict[str, Any]] = []
    for rank, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        video_id = str(item.get("id") or "").strip()
        if not video_id:
            continue
        snippet_d = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
        stats = item.get("statistics") if isinstance(item.get("statistics"), dict) else {}
        details = item.get("contentDetails") if isinstance(item.get("contentDetails"), dict) else {}

        try:
            views = int(stats.get("viewCount") or 0)
        except (TypeError, ValueError):
            views = 0
        try:
            likes = int(stats.get("likeCount") or 0)
        except (TypeError, ValueError):
            likes = 0

        duration = _duration_seconds(details.get("duration"))
        title = str(snippet_d.get("title") or "").strip() or "YouTube video"
        description = str(snippet_d.get("description") or "")
        is_live = str(snippet_d.get("liveBroadcastContent") or "none") not in ("none", "")

        candidates.append(
            {
                "video_id": video_id,
                "rank": rank,
                "views": views,
                "likes": likes,
                "duration": duration,
                "age_days": _age_days(snippet_d.get("publishedAt")),
                "is_short": (
                    duration <= min_seconds
                    or bool(_SHORTS_HINT.search(f"{title} {description}"))
                ),
                "is_live": is_live or duration == 0,
                "row": {
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": _thumbnail_url(snippet_d),
                    "channel": str(snippet_d.get("channelTitle") or "").strip(),
                    "view_count": str(views),
                },
            },
        )

    if not candidates:
        return []

    # 2) Drop Shorts and live streams. Fall back to view-count ranking only if
    #    filtering would leave nothing (so a topic still gets some resources).
    eligible = [c for c in candidates if not c["is_short"] and not c["is_live"]]
    if not eligible:
        eligible = sorted(candidates, key=lambda c: c["views"], reverse=True)
        return [c["row"] for c in eligible[:max_results]]

    # 3) Blended score (each component normalized within this query's candidates).
    views_n = _normalize([math.log10(c["views"] + 1) for c in eligible])
    eng_n = _normalize(
        [(c["likes"] / c["views"]) if c["views"] > 0 else 0.0 for c in eligible],
    )
    n = len(eligible)
    for i, c in enumerate(eligible):
        relevance = 1.0 - (c["rank"] / max(1, n - 1)) if n > 1 else 1.0
        recency = max(0.15, min(1.0, 1.0 - c["age_days"] / (5 * 365.0)))
        c["score"] = (
            _W_VIEWS * views_n[i]
            + _W_RELEVANCE * relevance
            + _W_ENGAGEMENT * eng_n[i]
            + _W_RECENCY * recency
            + _W_DURATION * _duration_fit(c["duration"])
        )

    eligible.sort(key=lambda c: c["score"], reverse=True)
    return [c["row"] for c in eligible[:max_results]]


async def search_topic(
    query: str,
    max_results: int = 3,
    *,
    api_keys: Optional[Sequence[str]] = None,
    candidate_pool: int = SEARCH_CANDIDATE_POOL,
    min_seconds: int = MIN_VIDEO_SECONDS,
) -> List[Dict[str, str]]:
    """
    Search YouTube for `query`, drop Shorts/live videos, and return the top
    `max_results` by a blended quality score.

    Returns items: { "title", "url", "thumbnail", "channel", "view_count" }
    """
    q = (query or "").strip()
    if not q:
        return []

    keys = resolve_youtube_api_keys(api_keys)
    n = max(1, min(int(max_results), 50))
    pool = max(n, min(int(candidate_pool), 50))

    # Explicit connect/read timeouts so an unreachable network fails fast with a
    # clear message instead of appearing to hang.
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        search_payload = await _request_with_key_rotation(
            client,
            YOUTUBE_SEARCH_URL,
            {
                "part": "snippet",
                "q": q,
                "type": "video",
                "maxResults": str(pool),
                "order": "relevance",
                "relevanceLanguage": "en",
                "videoEmbeddable": "true",
                "safeSearch": "moderate",
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
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(video_ids),
            },
            keys,
            query_label=f"videos stats {q[:60]!r}",
        )

    return _rows_from_videos_payload(
        videos_payload,
        max_results=n,
        min_seconds=min_seconds,
    )
