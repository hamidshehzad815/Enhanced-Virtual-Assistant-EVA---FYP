"""
Activity log database operations for behavioral scheduling decisions.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    payload.setdefault(
        "action_timestamp",
        datetime.now(timezone.utc).replace(tzinfo=None),
    )
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
    Return the most frequent scheduled hour for a weekday, or None.

    Uses scheduled fields from completion logs:
      - scheduled_day
      - scheduled_hour

    Rows without scheduled fields are intentionally ignored.
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)

    async def _run(owner_value: Any):
        pipeline = [
            {
                "$match": {
                    "user_id": owner_value,
                    "action_type": "task_completed",
                    "scheduled_day": int(weekday),
                    "scheduled_hour": {"$gte": 0, "$lte": 23},
                }
            },
            {
                "$group": {
                    "_id": "$scheduled_hour",
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


async def get_hours_distribution(
    user_id: str,
    day_of_week: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Aggregate completion logs by scheduled_hour.
    Returns rows sorted by count desc:
      [{ hour, count, on_time_rate }, ...]
    where on_time_rate is in [0, 1].

    Rows with missing scheduled_hour are ignored.
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    base_match: Dict[str, Any] = {
        "action_type": "task_completed",
        "scheduled_hour": {"$gte": 0, "$lte": 23},
    }
    if isinstance(day_of_week, int) and 0 <= day_of_week <= 6:
        base_match["scheduled_day"] = int(day_of_week)

    for owner_value in owner_variants:
        match_query = {
            **base_match,
            "user_id": owner_value,
        }
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": "$scheduled_hour",
                    "count": {"$sum": 1},
                    "on_time_count": {
                        "$sum": {
                            "$cond": [{"$eq": ["$was_on_time", True]}, 1, 0]
                        }
                    },
                }
            },
            {"$sort": {"count": -1, "_id": 1}},
        ]
        rows = await db.activity_logs.aggregate(pipeline).to_list(length=24)
        if not rows:
            continue

        result: List[Dict[str, Any]] = []
        for row in rows:
            count = int(row.get("count") or 0)
            on_time_count = int(row.get("on_time_count") or 0)
            rate = round((on_time_count / count), 2) if count > 0 else 0.0
            result.append(
                {
                    "hour": int(row.get("_id")),
                    "count": count,
                    "on_time_rate": rate,
                }
            )
        return result

    return []


async def get_days_distribution(user_id: str) -> List[Dict[str, Any]]:
    """
    Aggregate completion logs by scheduled_day.
    Returns all 7 days sorted by count desc:
      [{ day_name, day_num, count, on_time_rate }, ...]
    where on_time_rate is in [0, 1].

    Rows with missing scheduled_day are ignored.
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    day_labels = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday",
    }

    pipeline_template = [
        {
            "$group": {
                "_id": "$scheduled_day",
                "count": {"$sum": 1},
                "on_time_count": {
                    "$sum": {
                        "$cond": [{"$eq": ["$was_on_time", True]}, 1, 0]
                    }
                },
            }
        }
    ]

    for owner_value in owner_variants:
        pipeline = [
            {
                "$match": {
                    "user_id": owner_value,
                    "action_type": "task_completed",
                    "scheduled_day": {"$gte": 0, "$lte": 6},
                }
            },
            *pipeline_template,
        ]
        rows = await db.activity_logs.aggregate(pipeline).to_list(length=7)

        if not rows:
            continue

        by_day: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            day_num = int(row.get("_id"))
            count = int(row.get("count") or 0)
            on_time_count = int(row.get("on_time_count") or 0)
            rate = round((on_time_count / count), 2) if count > 0 else 0.0
            by_day[day_num] = {
                "day_name": day_labels.get(day_num, str(day_num)),
                "day_num": day_num,
                "count": count,
                "on_time_rate": rate,
            }

        full_week = []
        for day_num in range(7):
            full_week.append(
                by_day.get(
                    day_num,
                    {
                        "day_name": day_labels[day_num],
                        "day_num": day_num,
                        "count": 0,
                        "on_time_rate": 0.0,
                    },
                )
            )

        full_week.sort(key=lambda item: (-int(item["count"]), int(item["day_num"])))
        return full_week

    return [
        {
            "day_name": day_labels[day_num],
            "day_num": day_num,
            "count": 0,
            "on_time_rate": 0.0,
        }
        for day_num in range(7)
    ]


async def get_completion_rate(user_id: str) -> Dict[str, Any]:
    """
    Return completion summary and weekly trend.
    {
      total_completed, on_time, late, on_time_rate, weekly_trend
    }
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    for owner_value in owner_variants:
        summary_pipeline = [
            {
                "$match": {
                    "user_id": owner_value,
                    "action_type": "task_completed",
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_completed": {"$sum": 1},
                    "on_time": {
                        "$sum": {
                            "$cond": [{"$eq": ["$was_on_time", True]}, 1, 0]
                        }
                    },
                }
            },
        ]
        summary_rows = await db.activity_logs.aggregate(summary_pipeline).to_list(length=1)

        trend_pipeline = [
            {
                "$match": {
                    "user_id": owner_value,
                    "action_type": "task_completed",
                    "week_number": {"$gte": 1, "$lte": 53},
                }
            },
            {
                "$group": {
                    "_id": "$week_number",
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": -1}},
            {"$limit": 4},
            {"$sort": {"_id": 1}},
        ]
        trend_rows = await db.activity_logs.aggregate(trend_pipeline).to_list(length=4)

        if not summary_rows and not trend_rows:
            continue

        summary = summary_rows[0] if summary_rows else {}
        total_completed = int(summary.get("total_completed") or 0)
        on_time = int(summary.get("on_time") or 0)
        late = max(0, total_completed - on_time)
        on_time_rate = round((on_time / total_completed) * 100, 1) if total_completed > 0 else 0.0

        weekly_trend = [
            {
                "week": int(row.get("_id")),
                "count": int(row.get("count") or 0),
            }
            for row in trend_rows
        ]

        return {
            "total_completed": total_completed,
            "on_time": on_time,
            "late": late,
            "on_time_rate": on_time_rate,
            "weekly_trend": weekly_trend,
        }

    return {
        "total_completed": 0,
        "on_time": 0,
        "late": 0,
        "on_time_rate": 0.0,
        "weekly_trend": [],
    }


async def get_avg_time_taken(user_id: str) -> Optional[float]:
    """
    Return average time_taken_minutes over completed tasks, or None.
    """
    db = get_db()
    owner_object_id = _to_object_id(user_id)
    owner_variants = [owner_object_id]
    if owner_object_id != user_id:
        owner_variants.append(user_id)

    for owner_value in owner_variants:
        pipeline = [
            {
                "$match": {
                    "user_id": owner_value,
                    "action_type": "task_completed",
                    "time_taken_minutes": {"$type": "number"},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_time_taken": {"$avg": "$time_taken_minutes"},
                }
            },
        ]
        rows = await db.activity_logs.aggregate(pipeline).to_list(length=1)
        if not rows:
            continue
        avg_time = rows[0].get("avg_time_taken")
        if avg_time is None:
            continue
        return float(round(float(avg_time), 2))

    return None
