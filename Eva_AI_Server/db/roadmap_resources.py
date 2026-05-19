"""
MongoDB operations for roadmap_resources (seeded from roadmaps JSON; see ``get_roadmaps_json_path()``).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from config.database import get_db


def _to_object_id(value: str) -> ObjectId:
    return ObjectId(str(value))


def _normalize_out(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return doc
    out = dict(doc)
    if "_id" in out and isinstance(out["_id"], ObjectId):
        out["_id"] = str(out["_id"])
    return out


async def get_roadmap(language: str, level: str) -> List[Dict[str, Any]]:
    """Return all roadmap rows for a language + level, sorted by order ascending."""
    db = get_db()
    cursor = (
        db.roadmap_resources.find({"language": language, "level": level})
        .sort("order", 1)
    )
    rows = await cursor.to_list(length=10_000)
    return [_normalize_out(row) for row in rows]


async def get_topic(language: str, level: str, order: int) -> Optional[Dict[str, Any]]:
    """Single roadmap row by 1-based order within level."""
    db = get_db()
    doc = await db.roadmap_resources.find_one(
        {"language": language, "level": level, "order": int(order)},
    )
    return _normalize_out(doc)


async def get_unfetched_topics(limit: int = 50) -> List[Dict[str, Any]]:
    """Topics with no YouTube fetch yet (fetched_at is null or missing)."""
    db = get_db()
    query = {"$or": [{"fetched_at": None}, {"fetched_at": {"$exists": False}}]}
    cursor = db.roadmap_resources.find(query).sort(
        [("language", 1), ("level", 1), ("order", 1)]
    ).limit(limit)
    rows = await cursor.to_list(length=limit)
    return [_normalize_out(row) for row in rows]


async def get_stale_topics(days: int = 30, limit: int = 50) -> List[Dict[str, Any]]:
    """Topics fetched before the cutoff (UTC naive, consistent with other AI DB writes)."""
    db = get_db()
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=int(days))
    query = {
        "fetched_at": {"$ne": None, "$lt": cutoff},
    }
    cursor = db.roadmap_resources.find(query).sort("fetched_at", 1).limit(limit)
    rows = await cursor.to_list(length=limit)
    return [_normalize_out(row) for row in rows]


async def update_resources(doc_id: str, resources: List[Dict[str, Any]]) -> bool:
    """
    Persist YouTube (or other) resources and mark fetched_at.
    Returns True if a document matched.
    """
    db = get_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        oid = _to_object_id(doc_id)
    except Exception:
        return False

    result = await db.roadmap_resources.update_one(
        {"_id": oid},
        {
            "$set": {
                "resources": list(resources or []),
                "fetched_at": now,
                "updated_at": now,
            },
        },
    )
    return result.matched_count == 1


async def count_unfetched() -> int:
    query = {"$or": [{"fetched_at": None}, {"fetched_at": {"$exists": False}}]}
    db = get_db()
    return await db.roadmap_resources.count_documents(query)


async def get_sessions_required(language: str, level: str) -> int:
    """Number of sessions (documents) for a language + level."""
    db = get_db()
    return await db.roadmap_resources.count_documents(
        {"language": language, "level": level},
    )


async def seed_from_roadmaps_json(data: Dict[str, Any]) -> Tuple[int, int, int]:
    """
    Insert roadmap_resources rows from parsed roadmaps.json (idempotent).
    Returns (inserted_count, skipped_count, expected_total_sessions).

    ``days`` in JSON is the **suggested calendar span** for that level (not
    required to equal ``len(topics)``). Session count is ``len(topics)`` (one DB
    row per session). ``level_calendar_days`` copies ``days`` onto each row.
    """
    topic_names: List[str] = list(data.get("topics") or [])
    inserted = 0
    skipped = 0
    expected = 0

    db = get_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for language in topic_names:
        block = data.get(language)
        if not isinstance(block, dict):
            continue
        level_keys = block.get("topics")
        if not isinstance(level_keys, list):
            continue

        for level in level_keys:
            if not isinstance(level, str):
                continue
            level_data = block.get(level)
            if not isinstance(level_data, dict):
                continue
            titles = level_data.get("topics")
            raw_days = level_data.get("days")
            if not isinstance(titles, list):
                continue
            level_calendar_days: Optional[int] = None
            if raw_days is not None:
                try:
                    level_calendar_days = int(raw_days)
                except (TypeError, ValueError):
                    level_calendar_days = None

            for idx, title in enumerate(titles):
                expected += 1
                order = idx + 1
                title_str = str(title).strip()
                exists = await db.roadmap_resources.find_one(
                    {"language": language, "level": level, "order": order},
                    {"_id": 1},
                )
                if exists:
                    skipped += 1
                    continue

                await db.roadmap_resources.insert_one(
                    {
                        "language": language,
                        "level": level,
                        "order": order,
                        "title": title_str,
                        "level_calendar_days": level_calendar_days,
                        "resources": [],
                        "fetched_at": None,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                inserted += 1

    return inserted, skipped, expected
