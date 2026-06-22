"""
Shared batch worker: YouTube search + persist to roadmap_resources.

LOCKED (product): resource discovery runs only in this Python stack
(``fetch_and_store_for_documents`` + ``services.youtube.search_topic``).

LOCKED (query): YouTube search string ``q`` is built from the roadmap row's
``language`` field (same subject name as a learning goal, e.g. Python, C++)
plus the session line ``title``. If ``title`` already begins with that
language, ``title`` alone is used to avoid duplicating the subject.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from db.roadmap_resources import update_resources
from services.youtube import YouTubeSearchFailed, search_topic

logger = logging.getLogger(__name__)


def build_youtube_search_query(doc: Dict[str, Any]) -> str:
    """
    Build the YouTube ``q`` string for one ``roadmap_resources`` document.

    ``language`` matches the learning goal's subject / track (from roadmaps.json).
    ``title`` is that goal's roadmap session line for this order.
    """
    language = str(doc.get("language") or "").strip()
    title = str(doc.get("title") or "").strip()

    if not language:
        return title
    if not title:
        return language

    if title.casefold().startswith(language.casefold()):
        return title

    return f"{language} {title}".strip()


async def fetch_and_store_for_documents(
    docs: List[Dict[str, Any]],
    *,
    delay_seconds: float = 0.5,
    progress_every: int = 10,
    log_prefix: str = "",
    api_keys: Optional[Sequence[str]] = None,
) -> Tuple[int, int, Optional[str]]:
    """
    For each document, search YouTube and update DB when there are results.

    Returns (updated_count, api_calls_made, fatal_error).
    ``fatal_error`` is set if the YouTube API fails: processing stops immediately
    (no further topics in this batch). Legitimately empty search results do not stop the run.
    """
    updated = 0
    calls = 0

    for i, doc in enumerate(docs):
        doc_id = doc.get("_id")
        search_q = build_youtube_search_query(doc)
        calls += 1
        try:
            results = await search_topic(search_q, api_keys=api_keys)
        except YouTubeSearchFailed as exc:
            err = str(exc)
            logger.warning("%sYouTube fetch halted on topic %s/%s: %s", log_prefix, i + 1, len(docs), err)
            return updated, calls, err

        if not results:
            if (i + 1) % progress_every == 0:
                print(f"{log_prefix}[{i + 1}/{len(docs)}] no results for: {search_q[:80]}...")
            await asyncio.sleep(delay_seconds)
            continue

        ok = await update_resources(str(doc_id), results)
        if ok:
            updated += 1
        if (i + 1) % progress_every == 0:
            print(f"{log_prefix}[{i + 1}/{len(docs)}] updated resources (batch progress)")

        await asyncio.sleep(delay_seconds)

    return updated, calls, None
