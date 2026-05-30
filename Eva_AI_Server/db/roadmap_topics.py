"""
Roadmap topic CRUD helpers (collection: roadmap_topics).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from config.database import get_db

from db.learning_goals import update_completed_topics
from db.tasks import _normalize_doc, _to_object_id, update_task


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def insert_topic(topic_data: Dict[str, Any]) -> str:
    db = get_db()
    doc = dict(topic_data)
    now = _now_naive_utc()
    doc.setdefault("created_at", now)
    doc.setdefault("updated_at", now)
    doc.setdefault("status", "pending")
    doc.setdefault("is_deleted", False)
    if "goal_id" in doc:
        doc["goal_id"] = _to_object_id(doc["goal_id"])
    if doc.get("task_id"):
        doc["task_id"] = _to_object_id(doc["task_id"])
    res = await db.roadmap_topics.insert_one(doc)
    return str(res.inserted_id)


async def insert_topics_bulk(topics_list: List[Dict[str, Any]]) -> List[str]:
    if not topics_list:
        return []
    db = get_db()
    now = _now_naive_utc()
    docs: List[Dict[str, Any]] = []
    for row in topics_list:
        doc = dict(row)
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        doc.setdefault("status", "pending")
        doc.setdefault("is_deleted", False)
        if "goal_id" in doc:
            doc["goal_id"] = _to_object_id(doc["goal_id"])
        if doc.get("task_id"):
            doc["task_id"] = _to_object_id(doc["task_id"])
        docs.append(doc)
    res = await db.roadmap_topics.insert_many(docs)
    return [str(i) for i in res.inserted_ids]


async def update_topic_task_id(topic_id: str, task_id: str) -> bool:
    db = get_db()
    res = await db.roadmap_topics.update_one(
        {"_id": _to_object_id(topic_id)},
        {
            "$set": {
                "task_id": _to_object_id(task_id),
                "updated_at": _now_naive_utc(),
            },
        },
    )
    return res.matched_count == 1


async def update_topic_status(
    topic_id: str,
    status: str,
    completed_at: Optional[datetime] = None,
) -> bool:
    db = get_db()
    tid = _to_object_id(topic_id)
    now = _now_naive_utc()

    topic = await db.roadmap_topics.find_one(
        {"_id": tid, "is_deleted": {"$ne": True}},
    )
    if not topic:
        return False

    goal_id = topic.get("goal_id")
    goal_oid = _to_object_id(goal_id) if goal_id is not None else None

    payload: Dict[str, Any] = {"status": status, "updated_at": now}

    if status == "completed":
        payload["completed_at"] = completed_at or now

    res = await db.roadmap_topics.update_one(
        {"_id": tid, "is_deleted": {"$ne": True}},
        {"$set": payload},
    )
    if res.matched_count != 1:
        return False

    if status == "ongoing" and goal_oid is not None:
        await db.learning_goals.update_one(
            {"_id": goal_oid, "started_at": None},
            {"$set": {"started_at": now, "updated_at": now}},
        )

    if status == "completed" and goal_oid is not None:
        gdoc = await db.learning_goals.find_one({"_id": goal_oid}, {"started_at": 1})
        if gdoc and gdoc.get("started_at") is None:
            await db.learning_goals.update_one(
                {"_id": goal_oid},
                {"$set": {"started_at": now, "updated_at": now}},
            )

    if status == "completed" and goal_id is not None:
        task_ref = topic.get("task_id")
        if task_ref:
            await update_task(str(task_ref), {"status": "complete"})
        await update_completed_topics(str(goal_id))

    return True


async def get_topics_for_goal(goal_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    gid = _to_object_id(goal_id)
    cursor = db.roadmap_topics.find({"goal_id": gid, "is_deleted": False}).sort(
        "order",
        1,
    )
    rows = await cursor.to_list(length=2000)
    return [_normalize_doc(r) for r in rows]


async def pick_pending_topic_for_chat_completion(
    user_id: str,
    *,
    subject_hint: Optional[str] = None,
    today_only: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Choose one pending roadmap topic for natural-language "session done" messages.

    Picks the earliest scheduled pending topic across matching active goals.
    When ``today_only`` is True, only topics whose ``scheduled_date`` falls on
    the current UTC calendar day are considered.
    """
    db = get_db()
    uid = _to_object_id(user_id)
    query: Dict[str, Any] = {
        "user_id": uid,
        "status": "active",
        "is_deleted": False,
    }
    if subject_hint:
        query["subject"] = subject_hint.strip().lower()

    cursor = db.learning_goals.find(query).sort("created_at", -1)
    goals = await cursor.to_list(length=50)
    if not goals:
        return None

    today = _now_naive_utc().date()
    candidates: List[tuple] = []

    for g in goals:
        gid = g.get("_id")
        if gid is None:
            continue
        topic = await db.roadmap_topics.find_one(
            {
                "goal_id": gid,
                "status": "pending",
                "is_deleted": False,
            },
            sort=[("scheduled_date", 1), ("order", 1)],
        )
        if not topic:
            continue
        sd = topic.get("scheduled_date")
        if today_only:
            if not isinstance(sd, datetime):
                continue
            if sd.date() != today:
                continue
        sort_key = sd if isinstance(sd, datetime) else datetime.min.replace(tzinfo=None)
        candidates.append((sort_key, dict(g), dict(topic)))

    if not candidates:
        return None

    candidates.sort(key=lambda row: row[0])
    _sk, goal_doc, topic_doc = candidates[0]
    return {"goal": _normalize_doc(goal_doc), "topic": _normalize_doc(topic_doc)}


async def get_pending_topic(goal_id: str) -> Optional[Dict[str, Any]]:
    """Lowest-order topic with status pending."""
    db = get_db()
    gid = _to_object_id(goal_id)
    doc = await db.roadmap_topics.find_one(
        {"goal_id": gid, "status": "pending", "is_deleted": False},
        sort=[("order", 1)],
    )
    return _normalize_doc(doc) if doc else None


async def get_current_session(goal_id: str) -> Optional[Dict[str, Any]]:
    """Alias for the current interactable session (lowest-order pending topic)."""
    return await get_pending_topic(goal_id)


async def get_pending_sessions_after(goal_id: str, order: int) -> List[Dict[str, Any]]:
    """All pending sessions with order > given order (sorted ascending)."""
    db = get_db()
    gid = _to_object_id(goal_id)
    cursor = db.roadmap_topics.find(
        {
            "goal_id": gid,
            "status": "pending",
            "order": {"$gt": int(order)},
            "is_deleted": False,
        },
    ).sort("order", 1)
    rows = await cursor.to_list(length=2000)
    return [_normalize_doc(r) for r in rows]


async def get_all_pending_sessions(goal_id: str) -> List[Dict[str, Any]]:
    """All pending sessions sorted by order ascending."""
    db = get_db()
    gid = _to_object_id(goal_id)
    cursor = db.roadmap_topics.find(
        {"goal_id": gid, "status": "pending", "is_deleted": False},
    ).sort("order", 1)
    rows = await cursor.to_list(length=2000)
    return [_normalize_doc(r) for r in rows]


async def complete_topic(topic_id: str) -> bool:
    """Mark one topic completed and cascade goal/task updates via update_topic_status."""
    return await update_topic_status(topic_id, "completed")


async def skip_topic(topic_id: str) -> bool:
    """Mark one topic skipped."""
    db = get_db()
    tid = _to_object_id(topic_id)
    now = _now_naive_utc()
    result = await db.roadmap_topics.update_one(
        {"_id": tid, "is_deleted": {"$ne": True}},
        {"$set": {"status": "skipped", "updated_at": now}},
    )
    if result.matched_count == 0 and tid != topic_id:
        result = await db.roadmap_topics.update_one(
            {"_id": topic_id, "is_deleted": {"$ne": True}},
            {"$set": {"status": "skipped", "updated_at": now}},
        )
    return result.matched_count > 0


async def reschedule_topic(topic_id: str, new_datetime: datetime) -> bool:
    """Update scheduled_date for one topic."""
    db = get_db()
    tid = _to_object_id(topic_id)
    now = _now_naive_utc()
    result = await db.roadmap_topics.update_one(
        {"_id": tid, "is_deleted": {"$ne": True}},
        {"$set": {"scheduled_date": new_datetime, "updated_at": now}},
    )
    if result.matched_count == 0 and tid != topic_id:
        result = await db.roadmap_topics.update_one(
            {"_id": topic_id, "is_deleted": {"$ne": True}},
            {"$set": {"scheduled_date": new_datetime, "updated_at": now}},
        )
    return result.matched_count > 0


async def bulk_reschedule_topics(updates: List[Dict[str, Any]]) -> int:
    """
    Bulk update scheduled_date for many topics.
    `updates`: [{ topic_id, new_datetime }, ...]
    Returns the number of topics updated.
    """
    if not updates:
        return 0
    db = get_db()
    now = _now_naive_utc()
    updated = 0
    for row in updates:
        topic_id = row.get("topic_id")
        new_dt = row.get("new_datetime")
        if not topic_id or not isinstance(new_dt, datetime):
            continue
        ok = await reschedule_topic(str(topic_id), new_dt)
        if ok:
            updated += 1
    # best-effort: ensure updated_at is touched on all writes (already done in reschedule_topic)
    _ = now
    return int(updated)


async def soft_delete_pending_topics(goal_id: str) -> int:
    """
    Soft-delete pending and ongoing roadmap topics for a goal.
    Completed/skipped topics are left unchanged. Returns matched count.
    """
    db = get_db()
    gid = _to_object_id(goal_id)
    now = _now_naive_utc()
    payload = {
        "is_deleted": True,
        "deleted_at": now,
        "updated_at": now,
    }
    query = {
        "goal_id": gid,
        "status": {"$in": ["pending", "ongoing"]},
        "is_deleted": False,
    }
    result = await db.roadmap_topics.update_many(query, {"$set": payload})

    if result.matched_count == 0 and gid != goal_id:
        query["goal_id"] = goal_id
        result = await db.roadmap_topics.update_many(query, {"$set": payload})

    return int(result.matched_count)
