"""
Task database operations for scheduling handlers.
"""
from datetime import date, datetime, time, timedelta, timezone
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from bson import ObjectId

from config.database import get_db
from utils.timezone_utils import local_day_bounds_to_utc_naive


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
    payload.setdefault("updated_at", datetime.now(timezone.utc).replace(tzinfo=None))

    task_object_id = _to_object_id(task_id)
    query = {"_id": task_object_id}
    result = await db.tasks.update_one(query, {"$set": payload})

    if result.matched_count == 0 and task_object_id != task_id:
        result = await db.tasks.update_one({"_id": task_id}, {"$set": payload})

    return result.modified_count > 0


async def find_duplicate(
    owner_id: str,
    title: str,
    due_date: Union[str, date, datetime],
    timezone_name: str = "UTC",
) -> Optional[Dict[str, Any]]:
    """
    Find a non-deleted task with same title on the same day.
    """
    if not title:
        return None

    if isinstance(due_date, (str, date)):
        day_start, day_end = local_day_bounds_to_utc_naive(due_date, timezone_name)
    else:
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


def _build_delete_query(
    owner_value: Any,
    filters: Optional[Dict[str, Any]] = None,
    timezone_name: str = "UTC",
) -> Dict[str, Any]:
    filters = filters or {}
    query: Dict[str, Any] = {
        "owner_id": owner_value,
        "is_deleted": {"$ne": True},
    }

    task_name = str(filters.get("task_name") or "").strip()
    if task_name:
        query["title"] = {
            "$regex": re.escape(task_name),
            "$options": "i",
        }

    # Accept explicit date ranges first.
    date_range = filters.get("date_range")
    if isinstance(date_range, dict):
        start_value = date_range.get("start")
        end_value = date_range.get("end")
        if isinstance(start_value, datetime) and isinstance(end_value, datetime):
            query["due_datetime"] = {"$gte": start_value, "$lte": end_value}
    else:
        due_date = filters.get("date")
        if due_date:
            day_start, day_end = local_day_bounds_to_utc_naive(due_date, timezone_name)
            if day_start and day_end:
                query["due_datetime"] = {"$gte": day_start, "$lte": day_end}

    priority = str(filters.get("priority") or "").strip().lower()
    if priority in {"low", "medium", "high"}:
        query["priority"] = priority

    status = str(filters.get("status") or "").strip().lower()
    if status in {"pending", "ongoing", "complete"}:
        query["status"] = status

    return query


def _build_show_query(
    owner_value: Any,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    filters = filters or {}
    query: Dict[str, Any] = {
        "owner_id": owner_value,
        "is_deleted": {"$ne": True},
    }

    now_utc = filters.get("now_utc")
    overdue_only = bool(filters.get("overdue_only"))
    date_range = filters.get("date_range")

    if overdue_only and isinstance(now_utc, datetime):
        query["due_datetime"] = {"$lt": now_utc}
    elif isinstance(date_range, dict):
        start_value = date_range.get("start_utc", date_range.get("start"))
        end_value = date_range.get("end_utc", date_range.get("end"))
        if isinstance(start_value, datetime) and isinstance(end_value, datetime):
            query["due_datetime"] = {"$gte": start_value, "$lte": end_value}
    elif isinstance(now_utc, datetime):
        query["due_datetime"] = {"$gte": now_utc}

    task_name = str(filters.get("task_name") or "").strip()
    if task_name:
        query["title"] = {
            "$regex": re.escape(task_name),
            "$options": "i",
        }

    priority = str(filters.get("priority") or "").strip().lower()
    if priority in {"low", "medium", "high"}:
        query["priority"] = priority

    status = str(filters.get("status") or "").strip().lower()
    if status == "completed":
        status = "complete"
    if status in {"pending", "ongoing", "complete"}:
        query["status"] = status
        # For show completed tasks, do not force an upcoming-only window.
        if status == "complete" and isinstance(filters.get("date_range"), dict):
            pass
        elif status == "complete":
            query.pop("due_datetime", None)

    return query


async def find_tasks_for_delete(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    timezone_name: str = "UTC",
) -> List[Dict[str, Any]]:
    """
    Return matching non-deleted tasks for delete flow.
    Filters supported: task_name, date/date_range, priority, status.
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    for owner_value in owner_variants:
        query = _build_delete_query(owner_value, filters, timezone_name=timezone_name)
        cursor = db.tasks.find(query).sort("due_datetime", 1).limit(10)
        rows = await cursor.to_list(length=10)
        if rows:
            return [_normalize_doc(row) for row in rows]

    return []


async def find_tasks_for_show(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Return up to 10 matching tasks and the total match count for show flow.
    Filters supported: task_name, date_range, priority, status, now_utc.
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    status = str((filters or {}).get("status") or "").strip().lower()
    if status == "completed":
        status = "complete"
    sort_direction = -1 if status == "complete" else 1

    for owner_value in owner_variants:
        query = _build_show_query(owner_value, filters)
        cursor = db.tasks.find(query).sort("due_datetime", sort_direction).limit(10)
        rows = await cursor.to_list(length=10)
        total_count = int(await db.tasks.count_documents(query))
        if rows or total_count > 0:
            return [_normalize_doc(row) for row in rows], total_count

    return [], 0


async def soft_delete_task(task_id: str) -> bool:
    """
    Soft delete one task by id.
    Returns True when a document matched.
    """
    db = get_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    payload = {
        "is_deleted": True,
        "deleted_at": now,
        "updated_at": now,
    }

    task_object_id = _to_object_id(task_id)
    result = await db.tasks.update_one({"_id": task_object_id}, {"$set": payload})

    if result.matched_count == 0 and task_object_id != task_id:
        result = await db.tasks.update_one({"_id": task_id}, {"$set": payload})

    return result.matched_count > 0


async def soft_delete_many(task_ids: List[str]) -> int:
    """
    Soft delete many tasks by id list.
    Returns matched document count.
    """
    if not task_ids:
        return 0

    db = get_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    payload = {
        "is_deleted": True,
        "deleted_at": now,
        "updated_at": now,
    }

    object_ids = [_to_object_id(task_id) for task_id in task_ids]
    query = {
        "_id": {"$in": object_ids},
        "is_deleted": {"$ne": True},
    }
    result = await db.tasks.update_many(query, {"$set": payload})

    if result.matched_count == 0 and any(obj_id != task_id for obj_id, task_id in zip(object_ids, task_ids)):
        query = {
            "_id": {"$in": list(task_ids)},
            "is_deleted": {"$ne": True},
        }
        result = await db.tasks.update_many(query, {"$set": payload})

    return int(result.matched_count)


async def get_task_by_id(task_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch one non-deleted task by id with owner check.
    Returns normalized full task document or None.
    """
    db = get_db()
    task_object_id = _to_object_id(task_id)
    owner_object_id = _to_object_id(user_id)

    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    task_variants = [task_object_id]
    if task_object_id != task_id:
        task_variants.append(task_id)

    for owner_value in owner_variants:
        for task_value in task_variants:
            doc = await db.tasks.find_one(
                {
                    "_id": task_value,
                    "owner_id": owner_value,
                    "is_deleted": {"$ne": True},
                }
            )
            if doc:
                return _normalize_doc(doc)

    return None
