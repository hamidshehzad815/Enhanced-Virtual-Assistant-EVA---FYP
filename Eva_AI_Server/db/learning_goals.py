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


async def get_paused_goals_for_user(
    user_id: str,
    topic: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Paused, non-deleted goals for a user (optional subject filter)."""
    db = get_db()
    uid = _to_object_id(user_id)
    query: Dict[str, Any] = {
        "user_id": uid,
        "status": "paused",
        "is_deleted": False,
    }
    subject = (topic or "").strip().lower()
    if subject:
        query["subject"] = subject

    cursor = db.learning_goals.find(query).sort("created_at", -1)
    rows = await cursor.to_list(length=500)
    return [_normalize_doc(r) for r in rows]


async def find_conflicting_goal(
    user_id: str,
    topic: str,
    roadmap_key: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Return an active learning goal for this language/subject if one exists.

    One active plan per language: a second Python plan is blocked regardless of track
    (basics vs intermediate). Different languages (Python vs JavaScript) may coexist.
    ``roadmap_key`` is accepted for API compatibility but not used in the query.
    """
    _ = roadmap_key
    db = get_db()
    uid = _to_object_id(user_id)
    subject_norm = (topic or "").strip().lower()
    if not subject_norm:
        return None

    doc = await db.learning_goals.find_one(
        {
            "user_id": uid,
            "status": "active",
            "is_deleted": False,
            "subject": subject_norm,
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


async def find_goals_for_update(
    user_id: str,
    topic: str,
    roadmap_key: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Non-deleted learning goals for a user matching subject (and optional roadmap_key/status).
    Sorted newest first.
    """
    db = get_db()
    uid = _to_object_id(user_id)
    query: Dict[str, Any] = {
        "user_id": uid,
        "subject": (topic or "").strip().lower(),
        "is_deleted": False,
    }
    rk = (roadmap_key or "").strip().lower()
    if rk:
        query["roadmap_key"] = rk
    if status_filter:
        query["status"] = str(status_filter).strip().lower()

    cursor = db.learning_goals.find(query).sort("created_at", -1)
    rows = await cursor.to_list(length=500)
    return [_normalize_doc(r) for r in rows]


async def pause_goal(goal_id: str) -> bool:
    """Pause a goal (status=paused, paused_at=now)."""
    return await update_goal_status(str(goal_id), "paused", {"paused_at": _now_naive_utc()})


async def resume_goal(goal_id: str) -> bool:
    """Resume a goal (status=active, paused_at=null)."""
    return await update_goal_status(str(goal_id), "active", {"paused_at": None})


async def complete_goal(goal_id: str, started_at: Optional[datetime]) -> bool:
    """
    Mark goal completed and compute time_taken_days from started_at when provided.
    Falls back to existing started_at stored in DB when started_at is None.
    """
    extra: Dict[str, Any] = {}
    if started_at is not None:
        extra["started_at"] = started_at
    return await update_goal_status(str(goal_id), "completed", extra_fields=extra)


async def increment_completed_topics(goal_id: str) -> Optional[int]:
    """$inc completed_topics by 1 and return the new count, or None when not found."""
    db = get_db()
    gid = _to_object_id(goal_id)
    now = _now_naive_utc()
    doc = await db.learning_goals.find_one_and_update(
        {"_id": gid, "is_deleted": False},
        {"$inc": {"completed_topics": 1}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc and gid != goal_id:
        doc = await db.learning_goals.find_one_and_update(
            {"_id": goal_id, "is_deleted": False},
            {"$inc": {"completed_topics": 1}, "$set": {"updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
    if not doc:
        return None
    return int(doc.get("completed_topics") or 0)


async def set_started_at(goal_id: str) -> bool:
    """Set started_at=now only when started_at is currently null."""
    db = get_db()
    gid = _to_object_id(goal_id)
    now = _now_naive_utc()
    result = await db.learning_goals.update_one(
        {"_id": gid, "started_at": None},
        {"$set": {"started_at": now, "updated_at": now}},
    )
    if result.matched_count == 0 and gid != goal_id:
        result = await db.learning_goals.update_one(
            {"_id": goal_id, "started_at": None},
            {"$set": {"started_at": now, "updated_at": now}},
        )
    return result.matched_count > 0


async def update_end_date(goal_id: str, new_end_date: datetime) -> bool:
    """Update goal end_date."""
    db = get_db()
    gid = _to_object_id(goal_id)
    now = _now_naive_utc()
    result = await db.learning_goals.update_one(
        {"_id": gid},
        {"$set": {"end_date": new_end_date, "updated_at": now}},
    )
    if result.matched_count == 0 and gid != goal_id:
        result = await db.learning_goals.update_one(
            {"_id": goal_id},
            {"$set": {"end_date": new_end_date, "updated_at": now}},
        )
    return result.matched_count > 0


async def find_goals_for_delete(
    user_id: str,
    topic: str,
    roadmap_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Non-deleted learning goals for a user matching subject (and optional roadmap_key).
    All statuses (active, paused, completed) are included. Sorted newest first.
    """
    db = get_db()
    uid = _to_object_id(user_id)
    query: Dict[str, Any] = {
        "user_id": uid,
        "subject": (topic or "").strip().lower(),
        "is_deleted": False,
    }
    rk = (roadmap_key or "").strip().lower()
    if rk:
        query["roadmap_key"] = rk

    projection = {
        "_id": 1,
        "title": 1,
        "roadmap_key": 1,
        "status": 1,
        "completed_topics": 1,
        "total_topics": 1,
        "collaborators": 1,
    }
    cursor = db.learning_goals.find(query, projection).sort("created_at", -1)
    rows = await cursor.to_list(length=500)
    return [_normalize_doc(r) for r in rows]


async def soft_delete_goal(goal_id: str) -> bool:
    """Soft-delete one learning goal. Returns True when a document matched."""
    db = get_db()
    now = _now_naive_utc()
    payload = {
        "is_deleted": True,
        "deleted_at": now,
        "updated_at": now,
    }
    gid = _to_object_id(goal_id)
    result = await db.learning_goals.update_one(
        {"_id": gid, "is_deleted": False},
        {"$set": payload},
    )
    if result.matched_count == 0 and gid != goal_id:
        result = await db.learning_goals.update_one(
            {"_id": goal_id, "is_deleted": False},
            {"$set": payload},
        )
    return result.matched_count > 0


async def soft_delete_goals_bulk(goal_ids: List[str]) -> int:
    """Soft-delete many learning goals. Returns matched document count."""
    if not goal_ids:
        return 0

    db = get_db()
    now = _now_naive_utc()
    payload = {
        "is_deleted": True,
        "deleted_at": now,
        "updated_at": now,
    }
    object_ids = [_to_object_id(goal_id) for goal_id in goal_ids]
    query: Dict[str, Any] = {
        "_id": {"$in": object_ids},
        "is_deleted": False,
    }
    result = await db.learning_goals.update_many(query, {"$set": payload})

    if result.matched_count == 0 and any(
        obj_id != goal_id for obj_id, goal_id in zip(object_ids, goal_ids)
    ):
        result = await db.learning_goals.update_many(
            {"_id": {"$in": list(goal_ids)}, "is_deleted": False},
            {"$set": payload},
        )

    return int(result.matched_count)
