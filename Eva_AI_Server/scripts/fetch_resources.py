#!/usr/bin/env python3
"""
Fetch YouTube resources for roadmap_topics with fetched_at=null.

Uses multiple API keys (rotates when daily quota is hit).
Stores top 3 videos per topic ranked by view count.

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
from services.youtube import resolve_youtube_api_keys  # noqa: E402

# ---------------------------------------------------------------------------
# Add all your YouTube Data API keys here (used in order; rotates on quota).
# Leave empty strings out — only non-empty keys are used.
# Falls back to YOUTUBE_API_KEYS / YOUTUBE_API_KEY in .env when this list is empty.
# ---------------------------------------------------------------------------
YOUTUBE_API_KEYS: list[str] = [
   "AIzaSyAd8Or7CL6gYrDk5eD6fUFJJwkQdzyc0Cw",
   "AIzaSyAELI4hxQ4EtS-BeiXDi_ChGtOHRmnBchQ"
]


def _configured_api_keys() -> list[str]:
    script_keys = [k.strip() for k in YOUTUBE_API_KEYS if k and str(k).strip()]
    if script_keys:
        return script_keys
    return resolve_youtube_api_keys(None)


def _resource_fetch_paused_banner(reason: str) -> str:
    """Human-friendly stop message when YouTube calls fail mid-run."""
    return (
        "\n"
        "  ╭────────────────────────────────────────────────────────────╮\n"
        "  │  EVA hit a wall — not stubborn, just stopping on purpose.  │\n"
        "  │  The resource train is parked until YouTube cooperates.     │\n"
        "  ╰────────────────────────────────────────────────────────────╯\n"
        f"\n  What went wrong:\n    {reason}\n\n"
        "  What to do: add another API key to YOUTUBE_API_KEYS in this script,\n"
        "  or wait until quota resets, then run again.\n"
        "  Rows already saved in Mongo are untouched.\n"
    )


async def run() -> None:
    api_keys = _configured_api_keys()
    if not api_keys:
        raise SystemExit(
            "No YouTube API keys configured. Add keys to YOUTUBE_API_KEYS in "
            "scripts/fetch_resources.py or set YOUTUBE_API_KEY / YOUTUBE_API_KEYS in .env",
        )

    print(f"YouTube API keys loaded: {len(api_keys)}")

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
                api_keys=api_keys,
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
