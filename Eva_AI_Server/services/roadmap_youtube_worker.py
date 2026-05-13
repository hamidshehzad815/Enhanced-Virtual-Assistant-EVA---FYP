"""
Shared batch worker: YouTube search + persist to roadmap_resources.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Tuple

from db.roadmap_resources import update_resources
from services.youtube import search_topic
from services.youtube_quota import DailySearchQuota

logger = logging.getLogger(__name__)


async def fetch_and_store_for_documents(
    docs: List[Dict[str, Any]],
    *,
    quota: DailySearchQuota,
    delay_seconds: float = 0.5,
    progress_every: int = 10,
    log_prefix: str = "",
) -> Tuple[int, int, bool]:
    """
    For each document, consume one quota unit, search YouTube, update DB if results.

    Returns (updated_count, api_calls_made, stopped_by_quota).
    """
    updated = 0
    calls = 0
    stopped_quota = False

    for i, doc in enumerate(docs):
        if quota.remaining() <= 0:
            stopped_quota = True
            break
        if not quota.consume(1):
            stopped_quota = True
            break

        calls += 1
        doc_id = doc.get("_id")
        title = str(doc.get("title") or "").strip()
        results = await search_topic(title)
        if not results:
            if (i + 1) % progress_every == 0:
                print(f"{log_prefix}[{i + 1}/{len(docs)}] no results for: {title[:60]}...")
            await asyncio.sleep(delay_seconds)
            continue

        ok = await update_resources(str(doc_id), results)
        if ok:
            updated += 1
        if (i + 1) % progress_every == 0:
            print(f"{log_prefix}[{i + 1}/{len(docs)}] updated resources (batch progress)")

        await asyncio.sleep(delay_seconds)

    return updated, calls, stopped_quota
