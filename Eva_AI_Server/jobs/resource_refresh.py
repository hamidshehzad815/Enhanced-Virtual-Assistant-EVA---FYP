"""
Periodic refresh of stale YouTube links on roadmap_resources (every N days).
"""

from __future__ import annotations

import asyncio
import logging

from config.settings import settings
from db.roadmap_resources import get_stale_topics
from services.roadmap_youtube_worker import fetch_and_store_for_documents

logger = logging.getLogger(__name__)

_refresh_task: asyncio.Task | None = None


async def run_stale_refresh_once(limit: int = 50) -> None:
    """Refresh up to `limit` roadmap rows with fetched_at older than 30 days."""
    docs = await get_stale_topics(days=30, limit=limit)
    if not docs:
        logger.info("resource_refresh: no stale roadmap_resources rows")
        return

    updated, calls, fatal = await fetch_and_store_for_documents(
        docs,
        delay_seconds=settings.RESOURCE_FETCH_DELAY_SECONDS,
        progress_every=10,
        log_prefix="resource_refresh ",
    )
    if fatal:
        logger.warning(
            "resource_refresh: halted after %s calls (%s rows updated). Reason: %s",
            calls,
            updated,
            fatal,
        )
    else:
        logger.info("resource_refresh: updated=%s api_calls=%s", updated, calls)


async def _refresh_loop() -> None:
    interval_sec = max(1, int(settings.RESOURCE_REFRESH_INTERVAL_DAYS)) * 86400
    while True:
        await asyncio.sleep(interval_sec)
        try:
            await run_stale_refresh_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("resource_refresh loop iteration failed")


async def start_refresh_scheduler() -> None:
    """Start background task (sleep first, then refresh on each interval)."""
    global _refresh_task
    if not settings.RESOURCE_REFRESH_ENABLED:
        logger.info("RESOURCE_REFRESH_ENABLED=false; background resource refresh off")
        return
    if _refresh_task is not None and not _refresh_task.done():
        return
    _refresh_task = asyncio.create_task(
        _refresh_loop(),
        name="roadmap_resource_refresh",
    )
    logger.info(
        "resource_refresh: background loop started (interval=%s days, sleep-first)",
        settings.RESOURCE_REFRESH_INTERVAL_DAYS,
    )


async def shutdown_refresh_scheduler() -> None:
    global _refresh_task
    if _refresh_task is None:
        return
    _refresh_task.cancel()
    try:
        await _refresh_task
    except asyncio.CancelledError:
        pass
    _refresh_task = None
    logger.info("resource_refresh: background loop stopped")
