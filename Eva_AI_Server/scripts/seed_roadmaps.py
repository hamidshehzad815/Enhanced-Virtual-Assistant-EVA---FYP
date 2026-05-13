#!/usr/bin/env python3
"""
One-time (idempotent) seed: roadmaps.json -> MongoDB roadmap_resources.

Usage:
  cd Eva_AI_Server
  PYTHONPATH=. python scripts/seed_roadmaps.py
  PYTHONPATH=. python scripts/seed_roadmaps.py --json data/roadmaps.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Project root (Eva_AI_Server)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.database import database  # noqa: E402
from db.roadmap_resources import seed_from_roadmaps_json  # noqa: E402


def load_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit("roadmaps.json must be a JSON object")
    return data


async def main_async(json_path: Path) -> None:
    data = load_json(json_path)
    ok = await database.connect()
    if not ok:
        raise SystemExit("MongoDB connection failed")

    try:
        inserted, skipped, expected = await seed_from_roadmaps_json(data)
    finally:
        await database.disconnect()

    print("Seeding roadmap_resources...")
    print(f"  Expected session rows (from JSON): {expected}")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (already present): {skipped}")
    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed roadmap_resources from roadmaps.json")
    parser.add_argument(
        "--json",
        type=Path,
        default=ROOT / "data" / "roadmaps.json",
        help="Path to roadmaps.json",
    )
    args = parser.parse_args()
    path: Path = args.json
    if not path.is_file():
        raise SystemExit(f"File not found: {path}")
    asyncio.run(main_async(path))


if __name__ == "__main__":
    main()
