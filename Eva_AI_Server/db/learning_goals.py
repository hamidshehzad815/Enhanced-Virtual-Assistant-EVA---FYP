"""
Learning goal CRUD helpers (collection: learning_goals).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from config.database import get_db

from db.tasks import _normalize_doc, _to_object_id


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def insert_goal(goal_data: Dict[str, Any]) -> str:
    """Insert a learning goal; returns inserted id as string."""
    db = get_db()
    doc = dict(goal_data)
    now = _now_naive_utc()
    if isinstance(doc.get("subject"), str):
        doc["subject"] = doc["subject"].strip().lower()
    if doc.get("roadmap_key") is not None:
        doc["roadmap_key"] = str(doc["roadmap_key"]).strip().lower()
    doc.setdefault("created_at", now)
    doc.setdefault("updated_at", now)
    doc.setdefault("status", "active")
    doc.setdefault("is_deleted", False)
    doc.setdefault("completed_topics", 0)
    if "user_id" in doc:
        doc["user_id"] = _to_object_id(doc["user_id"])
    res = await db.learning_goals.insert_one(doc)
    return str(res.inserted_id)


async def get_active_goals_for_user(user_id: str) -> List[Dict[str, Any]]:
    """Active, non-deleted goals for a user."""
    db = get_db()
    uid = _to_object_id(user_id)
    cursor = db.learning_goals.find(
        {"user_id": uid, "status": "active", "is_deleted": False},
    ).sort("created_at", -1)
    rows = await cursor.to_list(length=500)
    return [_normalize_doc(r) for r in rows]


async def find_conflicting_goal(
    user_id: str,
    topic: str,
    roadmap_key: str,
) -> Optional[Dict[str, Any]]:
    """
  Return an active goal that blocks creating this plan, or None.

  Blocks when:
    - same subject + same roadmap_key, or
    - same subject + existing \"general\" (general blocks any new track), or
    - same subject + new \"general\" while any other active track exists.

  Different subjects may both be active. Different tracks (e.g. basics vs intermediate) may coexist.
    """
    db = get_db()
    uid = _to_object_id(user_id)
    subject_norm = (topic or "").strip().lower()
    rk = (roadmap_key or "general").strip().lower()

    base: Dict[str, Any] = {
        "user_id": uid,
        "status": "active",
        "is_deleted": False,
        "subject": subject_norm,
    }

    if rk == "general":
        doc = await db.learning_goals.find_one(base)
        return _normalize_doc(doc) if doc else None

    doc = await db.learning_goals.find_one(
        {
            **base,
            "$or": [
                {"roadmap_key": rk},
                {"roadmap_key": "general"},
            ],
        },
    )
    return _normalize_doc(doc) if doc else None


async def check_duplicate_goal(user_id: str, topic: str, roadmap_key: str) -> bool:
    return (await find_conflicting_goal(user_id, topic, roadmap_key)) is not None


async def update_goal_status(
    goal_id: str,
    status: str,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> bool:
    """Update goal status and optional fields; sets completed metadata when completed."""
    db = get_db()
    gid = _to_object_id(goal_id)
    now = _now_naive_utc()
    payload: Dict[str, Any] = {"status": status, "updated_at": now}
    if extra_fields:
        for k, v in extra_fields.items():
            if v is not None:
                payload[k] = v

    if status == "completed":
        doc = await db.learning_goals.find_one({"_id": gid})
        if not doc:
            return False
        completed_at = payload.get("completed_at") or now
        payload["completed_at"] = completed_at
        started = doc.get("started_at")
        if isinstance(started, datetime) and isinstance(completed_at, datetime):
            payload["time_taken_days"] = max(0, (completed_at - started).days)
        elif "time_taken_days" not in payload:
            payload["time_taken_days"] = None

    res = await db.learning_goals.update_one({"_id": gid}, {"$set": payload})
    return res.matched_count == 1


async def update_completed_topics(goal_id: str) -> bool:
    """
    Increment completed_topics. When it reaches total_topics, marks goal completed.
    """
    db = get_db()
    gid = _to_object_id(goal_id)
    now = _now_naive_utc()

    doc = await db.learning_goals.find_one_and_update(
        {"_id": gid},
        {"$inc": {"completed_topics": 1}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        return False

    total = int(doc.get("total_topics") or 0)
    done = int(doc.get("completed_topics") or 0)
    if total > 0 and done >= total:
        await update_goal_status(str(gid), "completed")
    return True


async def get_goal_by_id(goal_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    doc = await db.learning_goals.find_one({"_id": _to_object_id(goal_id)})
    return _normalize_doc(doc) if doc else None
