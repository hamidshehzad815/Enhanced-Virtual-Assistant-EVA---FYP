"""
Task database operations for scheduling handlers.
"""
from datetime import date, datetime, time, timedelta
import re
from typing import Any, Dict, Optional, Tuple, Union

from bson import ObjectId

from config.database import get_db


def _to_object_id(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))
    except Exception:
        return value


def _normalize_doc(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {k: _normalize_doc(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_doc(item) for item in value]
    return value


def _day_bounds(day_value: Union[str, date, datetime]) -> Tuple[Optional[datetime], Optional[datetime]]:
    if isinstance(day_value, datetime):
        day = day_value.date()
    elif isinstance(day_value, date):
        day = day_value
    elif isinstance(day_value, str):
        try:
            day = datetime.strptime(day_value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None, None
    else:
        return None, None

    return datetime.combine(day, time.min), datetime.combine(day, time.max)


def task_windows_overlap(
    existing_start: datetime,
    existing_duration_minutes: Any,
    new_start: datetime,
    new_duration_minutes: Any,
) -> bool:
    existing_duration = max(1, int(existing_duration_minutes or 0))
    new_duration = max(1, int(new_duration_minutes or 0))

    existing_end = existing_start + timedelta(minutes=existing_duration)
    new_end = new_start + timedelta(minutes=new_duration)

    return existing_start < new_end and existing_end > new_start


async def insert_task(task_data: Dict[str, Any]) -> str:
    """Insert a task and return inserted id as string."""
    db = get_db()
    result = await db.tasks.insert_one(dict(task_data))
    return str(result.inserted_id)


async def update_task(task_id: str, update_data: Dict[str, Any]) -> bool:
    """Update task fields and return True when a document was updated."""
    db = get_db()
    payload = dict(update_data)
    payload.setdefault("updated_at", datetime.utcnow())

    task_object_id = _to_object_id(task_id)
    query = {"_id": task_object_id}
    result = await db.tasks.update_one(query, {"$set": payload})

    if result.matched_count == 0 and task_object_id != task_id:
        result = await db.tasks.update_one({"_id": task_id}, {"$set": payload})

    return result.modified_count > 0


async def find_duplicate(owner_id: str, title: str, due_date: Union[str, date, datetime]) -> Optional[Dict[str, Any]]:
    """
    Find a non-deleted task with same title on the same day.
    """
    if not title:
        return None

    day_start, day_end = _day_bounds(due_date)
    if not day_start or not day_end:
        return None

    db = get_db()
    owner_object_id = _to_object_id(owner_id)
    safe_title = re.escape(title.strip())

    base_query = {
        "title": {"$regex": f"^{safe_title}$", "$options": "i"},
        "due_datetime": {"$gte": day_start, "$lte": day_end},
        "is_deleted": {"$ne": True},
    }

    query = dict(base_query)
    query["owner_id"] = owner_object_id
    doc = await db.tasks.find_one(query)

    if not doc and owner_object_id != owner_id:
        query = dict(base_query)
        query["owner_id"] = owner_id
        doc = await db.tasks.find_one(query)

    return _normalize_doc(doc) if doc else None


async def has_hour_conflict(owner_id: str, due_date: Union[str, date, datetime], hour: int) -> bool:
    """
    Check if a user already has a non-deleted task in the same date+hour window.
    """
    day_start, day_end = _day_bounds(due_date)
    if day_start is None or day_end is None:
        return False

    hour_start = day_start.replace(hour=int(hour), minute=0, second=0, microsecond=0)
    hour_end = hour_start.replace(minute=59, second=59, microsecond=999999)

    db = get_db()
    owner_object_id = _to_object_id(owner_id)
    base_query = {
        "due_datetime": {"$gte": hour_start, "$lte": hour_end},
        "is_deleted": {"$ne": True},
    }

    query = dict(base_query)
    query["owner_id"] = owner_object_id
    doc = await db.tasks.find_one(query, {"_id": 1})

    if not doc and owner_object_id != owner_id:
        query = dict(base_query)
        query["owner_id"] = owner_id
        doc = await db.tasks.find_one(query, {"_id": 1})

    return bool(doc)


async def find_overlapping_task(
    owner_id: str,
    due_datetime: datetime,
    duration_minutes: int,
) -> Optional[Dict[str, Any]]:
    """
    Find the first non-deleted task that overlaps the requested task window.
    """
    db = get_db()
    owner_object_id = _to_object_id(owner_id)

    new_start = due_datetime
    new_end = new_start + timedelta(minutes=max(1, int(duration_minutes or 0)))
    search_start = new_start - timedelta(days=1)

    base_query = {
        "due_datetime": {"$gte": search_start, "$lt": new_end},
        "is_deleted": {"$ne": True},
    }

    async def _run(owner_value: Any) -> Optional[Dict[str, Any]]:
        cursor = (
            db.tasks.find(
                {
                    **base_query,
                    "owner_id": owner_value,
                }
            )
            .sort("due_datetime", 1)
        )
        rows = await cursor.to_list(length=100)

        for row in rows:
            existing_start = row.get("due_datetime")
            if not isinstance(existing_start, datetime):
                continue

            if task_windows_overlap(
                existing_start,
                row.get("duration", 120),
                new_start,
                duration_minutes,
            ):
                return _normalize_doc(row)

        return None

    conflict = await _run(owner_object_id)
    if conflict is None and owner_object_id != owner_id:
        conflict = await _run(owner_id)

    return conflict
