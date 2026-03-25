"""
Activity log database operations for behavioral scheduling decisions.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId

from config.database import get_db


_ALLOWED_ACTION_TYPES = {
    "task_created",
    "task_updated",
    "task_deleted",
    "task_completed",
}


def _to_object_id(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))
    except Exception:
        return value


async def insert_log(log_data: Dict[str, Any]) -> str:
    """Insert an activity log and return inserted id as string."""
    db = get_db()
    payload = dict(log_data)
    action_type = str(payload.get("action_type") or "").strip()
    if action_type and action_type not in _ALLOWED_ACTION_TYPES:
        # Keep inserts non-breaking for forward compatibility while still flagging unknown values.
        print(f"[ActivityLogs] Unknown action_type '{action_type}', inserting anyway.")
    payload.setdefault("action_timestamp", datetime.utcnow())
    result = await db.activity_logs.insert_one(payload)
    return str(result.inserted_id)


async def count_completed(user_id: str) -> int:
    """Count completed-task events for a user."""
    db = get_db()
    owner_object_id = _to_object_id(user_id)

    query = {
        "user_id": owner_object_id,
        "action_type": "task_completed",
    }
    count = await db.activity_logs.count_documents(query)

    if count == 0 and owner_object_id != user_id:
        query["user_id"] = user_id
        count = await db.activity_logs.count_documents(query)

    return int(count)


async def get_best_hour(user_id: str, weekday: int) -> Optional[int]:
    """
    Return the most frequent completion hour for a weekday, or None.
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)

    async def _run(owner_value: Any):
        pipeline = [
            {
                "$match": {
                    "user_id": owner_value,
                    "action_type": "task_completed",
                    "day_of_week": int(weekday),
                    "hour_of_day": {"$gte": 0, "$lte": 23},
                }
            },
            {
                "$group": {
                    "_id": "$hour_of_day",
                    "count": {"$sum": 1},
                }
            },
            {
                "$sort": {
                    "count": -1,
                    "_id": 1,
                }
            },
            {"$limit": 1},
        ]
        rows = await db.activity_logs.aggregate(pipeline).to_list(length=1)
        return rows[0]["_id"] if rows else None

    best = await _run(owner_object_id)
    if best is None and owner_object_id != user_id:
        best = await _run(user_id)

    return int(best) if best is not None else None
