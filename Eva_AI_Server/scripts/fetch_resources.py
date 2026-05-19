#!/usr/bin/env python3
"""
Fetch YouTube resources for roadmap_topics with fetched_at=null.

Stops immediately if the YouTube API fails (quota, auth, network) instead of
silently burning through the rest of the batch.

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


def _resource_fetch_paused_banner(reason: str) -> str:
    """Human-friendly stop message when YouTube calls fail mid-run."""
    return (
        "\n"
        "  ╭────────────────────────────────────────────────────────────╮\n"
        "  │  EVA hit a wall — not stubborn, just stopping on purpose.  │\n"
        "  │  The resource train is parked until YouTube cooperates.     │\n"
        "  ╰────────────────────────────────────────────────────────────╯\n"
        f"\n  What went wrong:\n    {reason}\n\n"
        "  What to do: fix the issue above, then run this script again.\n"
        "  Rows already saved in Mongo are untouched; nothing was half-written for this topic.\n"
    )


async def run() -> None:
    ok = await database.connect()
    if not ok:
        raise SystemExit("MongoDB connection failed")

    total_updated = 0
    batch_no = 0

    try:
        initial_left = await count_unfetched()
        print(f"Unfetched roadmap rows: {initial_left}")

        while True:
            batch_size = 50
            docs = await get_unfetched_topics(limit=batch_size)
            if not docs:
                print("All roadmap resources have been fetched (or none pending).")
                break

            batch_no += 1
            print(f"\nBatch {batch_no}: up to {len(docs)} topics")

            updated, _calls, fatal = await fetch_and_store_for_documents(
                docs,
                delay_seconds=settings.RESOURCE_FETCH_DELAY_SECONDS,
                progress_every=10,
                log_prefix="fetch_resources ",
            )
            total_updated += updated

            if fatal:
                print(_resource_fetch_paused_banner(fatal))
                break
    finally:
        await database.disconnect()

    print(f"\nDone. Rows updated this run: {total_updated}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
