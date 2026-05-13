#!/usr/bin/env python3
"""
Fetch YouTube resources for roadmap_topics with fetched_at=null.

Respects daily search quota (default 100/day, see YOUTUBE_DAILY_SEARCH_LIMIT).

Usage:
  cd Eva_AI_Server
  PYTHONPATH=. python scripts/fetch_resources.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.database import database  # noqa: E402
from config.settings import settings  # noqa: E402
from db.roadmap_resources import count_unfetched, get_unfetched_topics  # noqa: E402
from services.roadmap_youtube_worker import fetch_and_store_for_documents  # noqa: E402
from services.youtube_quota import build_default_quota  # noqa: E402


async def run() -> None:
    ok = await database.connect()
    if not ok:
        raise SystemExit("MongoDB connection failed")

    quota = build_default_quota()
    total_updated = 0
    batch_no = 0

    try:
        initial_left = await count_unfetched()
        print(f"Unfetched roadmap rows: {initial_left}")
        print(f"Daily search quota remaining: {quota.remaining()}/{settings.YOUTUBE_DAILY_SEARCH_LIMIT}")

        while True:
            rem = quota.remaining()
            if rem <= 0:
                print("Daily YouTube search quota reached. Re-run tomorrow.")
                break

            batch_size = min(50, rem)
            docs = await get_unfetched_topics(limit=batch_size)
            if not docs:
                print("All roadmap resources have been fetched (or none pending).")
                break

            batch_no += 1
            print(f"\nBatch {batch_no}: up to {len(docs)} topics (quota {rem})")

            updated, _calls, stopped = await fetch_and_store_for_documents(
                docs,
                quota=quota,
                delay_seconds=settings.RESOURCE_FETCH_DELAY_SECONDS,
                progress_every=10,
                log_prefix="fetch_resources ",
            )
            total_updated += updated

            if stopped and quota.remaining() <= 0:
                print("Stopped: daily quota exhausted.")
                break
    finally:
        await database.disconnect()

    print(f"\nDone. Rows updated this run: {total_updated}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
