"""
Task database operations for scheduling handlers.
"""
from datetime import date, datetime, time, timedelta, timezone
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from bson import ObjectId

from config.database import get_db
from utils.timezone_utils import local_day_bounds_to_utc_naive, utc_naive_to_local


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


# Only pending/ongoing tasks block new scheduling; completed sessions free the slot.
_OVERLAP_BLOCKING_STATUS_FILTER: Dict[str, Any] = {
    "status": {"$nin": ["complete", "completed"]},
}


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
    normalized_status = str(payload.get("status") or "").strip().lower()
    if normalized_status == "completed":
        normalized_status = "complete"
        payload["status"] = "complete"
    if normalized_status == "complete":
        payload.setdefault("completed_at", datetime.now(timezone.utc).replace(tzinfo=None))

    task_object_id = _to_object_id(task_id)
    query = {"_id": task_object_id}
    update_doc: Dict[str, Any] = {"$set": payload}
    if "due_datetime" in payload:
        update_doc["$unset"] = {
            "reminder_sent_at": "",
            "overdue_notified_at": "",
        }
    result = await db.tasks.update_one(query, update_doc)

    if result.matched_count == 0 and task_object_id != task_id:
        result = await db.tasks.update_one({"_id": task_id}, update_doc)

    return result.matched_count > 0


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
        **_OVERLAP_BLOCKING_STATUS_FILTER,
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
        **_OVERLAP_BLOCKING_STATUS_FILTER,
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


async def find_overlapping_task_for_user(
    user_id: str,
    due_datetime: datetime,
    duration_minutes: int,
    *,
    exclude_task_ids: Optional[Set[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Find the first non-deleted overlapping task where the user is either:
    - owner_id, or
    - an accepted collaborator.
    """
    db = get_db()
    user_object_id = _to_object_id(user_id)
    user_variants = [user_object_id]
    if user_object_id != user_id:
        user_variants.append(user_id)

    new_start = due_datetime
    new_end = new_start + timedelta(minutes=max(1, int(duration_minutes or 0)))
    search_start = new_start - timedelta(days=1)

    base_query = {
        "due_datetime": {"$gte": search_start, "$lt": new_end},
        "is_deleted": {"$ne": True},
        **_OVERLAP_BLOCKING_STATUS_FILTER,
    }

    for user_value in user_variants:
        query = {
            **base_query,
            "$or": [
                {"owner_id": user_value},
                {
                    "collaborators": {
                        "$elemMatch": {
                            "user_id": user_value,
                            "status": "accepted",
                        }
                    }
                },
            ],
        }
        rows = await db.tasks.find(query).sort("due_datetime", 1).to_list(length=100)

        for row in rows:
            if exclude_task_ids and str(row.get("_id")) in exclude_task_ids:
                continue
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



def _parse_time_of_day_minutes(time_value: Any) -> Optional[int]:
    raw = str(time_value or "").strip()
    if not raw:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.hour * 60 + parsed.minute
        except ValueError:
            continue
    return None


def _filter_rows_by_time_of_day(
    rows: List[Dict[str, Any]],
    time_value: Any,
    timezone_name: str,
    window_minutes: int = 15,
) -> List[Dict[str, Any]]:
    target = _parse_time_of_day_minutes(time_value)
    if target is None:
        return rows

    matched: List[Dict[str, Any]] = []
    for row in rows:
        due = row.get("due_datetime")
        local_dt = utc_naive_to_local(due, timezone_name) if due is not None else None
        if local_dt is None:
            continue
        minutes = local_dt.hour * 60 + local_dt.minute
        delta = abs(minutes - target)
        # Handle wrap-around near midnight (e.g. 23:55 vs 00:05).
        delta = min(delta, 1440 - delta)
        if delta <= window_minutes:
            matched.append(row)
    return matched


async def find_tasks_for_delete(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    timezone_name: str = "UTC",
) -> List[Dict[str, Any]]:
    """
    Return matching non-deleted tasks for delete flow.
    Filters supported: task_name, date/date_range, time_of_day, priority, status.
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    filters = filters or {}
    time_of_day = filters.get("time_of_day")
    # Time-only matching needs a wider candidate set before local-time filtering.
    fetch_limit = 200 if time_of_day and not filters.get("date_range") and not filters.get("date") else 10

    for owner_value in owner_variants:
        query = _build_delete_query(owner_value, filters, timezone_name=timezone_name)
        cursor = db.tasks.find(query).sort("due_datetime", 1).limit(fetch_limit)
        rows = await cursor.to_list(length=fetch_limit)
        if not rows:
            continue
        normalized = [_normalize_doc(row) for row in rows]
        if time_of_day:
            normalized = _filter_rows_by_time_of_day(
                normalized,
                time_of_day,
                timezone_name,
            )
        if normalized:
            return normalized[:10]

    return []


async def find_tasks_for_update(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    timezone_name: str = "UTC",
) -> List[Dict[str, Any]]:
    """
    Return matching non-deleted tasks for update flow.
    Filters are identifier-only: task_name, date/date_range, priority, status.
    """
    # Update identification logic is intentionally aligned with delete matching.
    return await find_tasks_for_delete(
        user_id=user_id,
        filters=filters,
        timezone_name=timezone_name,
    )


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
        # Primary owner-only query for deterministic behavior and testability.
        query = _build_show_query(owner_value, filters)
        cursor = db.tasks.find(query).sort("due_datetime", sort_direction).limit(10)
        rows = await cursor.to_list(length=10)
        total_count = int(await db.tasks.count_documents(query))
        if rows or total_count > 0:
            return [_normalize_doc(row) for row in rows], total_count

        # Fallback collaborator query (accepted collaborators can view shared tasks).
        collab_query = dict(query)
        collab_query.pop("owner_id", None)
        collab_query["collaborators"] = {
            "$elemMatch": {
                "user_id": owner_value,
                "status": "accepted",
            }
        }
        collab_cursor = db.tasks.find(collab_query).sort("due_datetime", sort_direction).limit(10)
        collab_rows = await collab_cursor.to_list(length=10)
        collab_total = int(await db.tasks.count_documents(collab_query))
        if collab_rows or collab_total > 0:
            return [_normalize_doc(row) for row in collab_rows], collab_total

    return [], 0


async def get_tasks_for_day(user_id: str, day_of_week: int) -> List[Dict[str, Any]]:
    """
    Return non-deleted tasks for a weekday number.
    day_of_week: Monday=0 ... Sunday=6
    """
    if not isinstance(day_of_week, int) or day_of_week < 0 or day_of_week > 6:
        return []

    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    for owner_value in owner_variants:
        query = {
            "owner_id": owner_value,
            "is_deleted": {"$ne": True},
            "due_datetime": {"$type": "date"},
            "$expr": {
                "$eq": [
                    {"$subtract": [{"$isoDayOfWeek": "$due_datetime"}, 1]},
                    int(day_of_week),
                ]
            },
        }
        rows = await (
            db.tasks.find(query, {"due_datetime": 1, "duration": 1})
            .sort("due_datetime", 1)
            .to_list(length=200)
        )
        if rows:
            return [_normalize_doc(row) for row in rows]

    return []


async def check_update_overlap(
    user_id: str,
    task_id: str,
    new_datetime: datetime,
    duration: Any,
    *,
    exclude_task_ids: Optional[Set[str]] = None,
) -> bool:
    """
    Return True when the updated task window overlaps another non-deleted task.
    The currently updated task is excluded from overlap checks.
    """
    if not isinstance(new_datetime, datetime):
        return False

    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    task_object_id = _to_object_id(task_id)
    task_variants: List[Any] = [task_object_id]
    if task_object_id != task_id:
        task_variants.append(task_id)
    excluded_ids = {str(value) for value in task_variants}
    if exclude_task_ids:
        excluded_ids.update(str(value) for value in exclude_task_ids)

    requested_duration = max(1, int(duration or 0))
    new_start = new_datetime
    new_end = new_start + timedelta(minutes=requested_duration)
    search_start = new_start - timedelta(days=1)

    base_query: Dict[str, Any] = {
        "due_datetime": {"$gte": search_start, "$lt": new_end},
        "is_deleted": {"$ne": True},
        **_OVERLAP_BLOCKING_STATUS_FILTER,
    }

    for owner_value in owner_variants:
        query = {
            **base_query,
            "owner_id": owner_value,
        }
        cursor = db.tasks.find(query).sort("due_datetime", 1)
        rows = await cursor.to_list(length=100)

        for row in rows:
            if str(row.get("_id")) in excluded_ids:
                continue
            existing_start = row.get("due_datetime")
            if not isinstance(existing_start, datetime):
                continue
            if task_windows_overlap(
                existing_start,
                row.get("duration", 120),
                new_start,
                requested_duration,
            ):
                return True

    return False


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


async def get_pending_learning_tasks(goal_id: str) -> List[Dict[str, Any]]:
    """
    Pending and ongoing learning tasks for a goal (for calendar cleanup before delete).
    """
    db = get_db()
    plan_id = _to_object_id(goal_id)
    query = {
        "learning_plan_id": plan_id,
        "status": {"$in": ["pending", "ongoing"]},
        "is_deleted": False,
    }
    cursor = db.tasks.find(query).sort("due_datetime", 1)
    rows = await cursor.to_list(length=500)

    if not rows and plan_id != goal_id:
        query["learning_plan_id"] = goal_id
        cursor = db.tasks.find(query).sort("due_datetime", 1)
        rows = await cursor.to_list(length=500)

    return [_normalize_doc(row) for row in rows]


async def soft_delete_pending_learning_tasks(goal_id: str) -> int:
    """
    Soft-delete pending and ongoing tasks linked to a learning goal.
    Completed tasks are left unchanged. Returns matched count.
    """
    db = get_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    plan_id = _to_object_id(goal_id)
    payload = {
        "is_deleted": True,
        "deleted_at": now,
        "updated_at": now,
    }
    query = {
        "learning_plan_id": plan_id,
        "status": {"$in": ["pending", "ongoing"]},
        "is_deleted": False,
    }
    result = await db.tasks.update_many(query, {"$set": payload})

    if result.matched_count == 0 and plan_id != goal_id:
        query["learning_plan_id"] = goal_id
        result = await db.tasks.update_many(query, {"$set": payload})

    return int(result.matched_count)


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


async def get_task_for_learning_topic(
    topic_id: str,
    goal_id: str,
    user_id: str,
    *,
    topic_task_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Resolve the calendar task for a learning session.

    Prefer ``roadmap_topics.task_id``; fall back to ``tasks.learning_topic_id``
    when the topic link was never backfilled.
    """
    direct_id = str(topic_task_id or "").strip()
    if direct_id:
        doc = await get_task_by_id(direct_id, user_id)
        if doc:
            return doc

    db = get_db()
    topic_variants = [_to_object_id(topic_id)]
    if topic_variants[0] != topic_id:
        topic_variants.append(topic_id)

    goal_variants = [_to_object_id(goal_id)]
    if goal_variants[0] != goal_id:
        goal_variants.append(goal_id)

    owner_variants = [_to_object_id(user_id)]
    if owner_variants[0] != user_id:
        owner_variants.append(user_id)

    for topic_value in topic_variants:
        for goal_value in goal_variants:
            for owner_value in owner_variants:
                doc = await db.tasks.find_one(
                    {
                        "learning_topic_id": topic_value,
                        "learning_plan_id": goal_value,
                        "owner_id": owner_value,
                        "is_deleted": {"$ne": True},
                    }
                )
                if doc:
                    return _normalize_doc(doc)

    return None


async def soft_delete_learning_topic_task(
    *,
    topic_id: str,
    goal_id: str,
    user_id: str,
    topic_task_id: Optional[str] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Soft-delete the task linked to a learning topic.

    Returns ``(deleted, task_doc)`` where ``task_doc`` is the pre-delete snapshot
    (for calendar cleanup).
    """
    task_doc = await get_task_for_learning_topic(
        topic_id,
        goal_id,
        user_id,
        topic_task_id=topic_task_id,
    )
    if not task_doc:
        return False, None

    resolved_task_id = str(task_doc.get("_id") or "").strip()
    if not resolved_task_id:
        return False, None

    deleted = await soft_delete_task(resolved_task_id)
    return deleted, task_doc if deleted else None
