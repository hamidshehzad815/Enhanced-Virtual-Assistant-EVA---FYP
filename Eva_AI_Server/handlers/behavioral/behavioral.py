"""
Phase 31 behavioral handler.
Implements threshold check, sub-intent detection, analytics queries, and natural replies.
"""
from datetime import datetime, timezone as dt_timezone
import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple

from context.redis_client import redis_client
from db.activity_logs import (
    count_completed,
    get_avg_time_taken,
    get_completion_rate,
    get_days_distribution,
    get_hours_distribution,
)
from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.tasks import get_tasks_for_day, task_windows_overlap
from services.gemini import gemini_service
from utils.date_utils import hour_to_12h_format, weekday_name_to_number


_WEEKDAY_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    flags=re.IGNORECASE,
)

_BEST_TIME_KEYWORDS = (
    "best time",
    "when should i schedule",
    "suggest a time",
    "ideal time",
)
_COMPLETION_KEYWORDS = (
    "completion",
    "on time",
    "finish rate",
    "success rate",
    "on-time",
)
_REPORT_KEYWORDS = (
    "report",
    "summary",
    "overview",
    "analytics",
    "performance",
    "habits",
)
_DAYS_KEYWORDS = (
    "days",
    "best day",
    "which day",
    "day of week",
)

_DAY_LABELS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = _coerce_text(value)
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt_timezone.utc).replace(tzinfo=None)
    return parsed


def _normalize_day(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            normalized = _normalize_day(item)
            if normalized:
                return normalized
        return ""

    raw = _coerce_text(value).lower()
    if not raw:
        return ""
    if weekday_name_to_number(raw) is not None:
        return raw

    match = _WEEKDAY_PATTERN.search(raw)
    if match:
        return match.group(1).lower()
    return ""


def _detect_sub_intent(message: str) -> str:
    lowered = _coerce_text(message).lower()

    if any(keyword in lowered for keyword in _BEST_TIME_KEYWORDS):
        return "best_time_for_day"
    if any(keyword in lowered for keyword in _COMPLETION_KEYWORDS):
        return "completion_rate"
    if any(keyword in lowered for keyword in _REPORT_KEYWORDS):
        return "productivity_report"
    if any(keyword in lowered for keyword in _DAYS_KEYWORDS):
        return "productive_days"
    return "productive_hours"


def _pending_payload_for_day() -> Dict[str, Any]:
    return {
        "expected_response": "free_text",
        "pending_action": {
            "intent": "behavioral",
            "sub_intent": "best_time_for_day",
            "entities": {},
        },
    }


def _hour_row_to_text(row: Dict[str, Any]) -> str:
    hour = int(row.get("hour") or 0)
    count = int(row.get("count") or 0)
    on_time_rate = float(row.get("on_time_rate") or 0.0) * 100
    hour_label = hour_to_12h_format(hour) or f"{hour}:00"
    return f"{hour_label} ({count} completions, {on_time_rate:.0f}% on-time)"


def _day_row_to_text(row: Dict[str, Any]) -> str:
    day_name = _coerce_text(row.get("day_name")) or "Unknown day"
    count = int(row.get("count") or 0)
    on_time_rate = float(row.get("on_time_rate") or 0.0) * 100
    return f"{day_name} ({count} completions, {on_time_rate:.0f}% on-time)"


def _hour_has_conflict(hour: int, tasks: List[Dict[str, Any]]) -> bool:
    for task in tasks:
        existing_start = _to_datetime(task.get("due_datetime"))
        if existing_start is None:
            continue
        duration = int(task.get("duration") or 120)
        candidate_start = existing_start.replace(hour=hour, minute=0, second=0, microsecond=0)
        if task_windows_overlap(
            existing_start=existing_start,
            existing_duration_minutes=duration,
            new_start=candidate_start,
            new_duration_minutes=60,
        ):
            return True
    return False


def _pick_best_hour_with_conflict_check(
    hour_rows: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
) -> Tuple[Optional[int], bool]:
    if not hour_rows:
        return None, False

    for row in hour_rows:
        hour = int(row.get("hour") or 0)
        if not _hour_has_conflict(hour, tasks):
            return hour, True

    return int(hour_rows[0].get("hour") or 0), False


def _weekly_trend_text(weekly_trend: List[Dict[str, Any]]) -> str:
    if not weekly_trend:
        return "No weekly trend yet"
    parts = []
    for row in weekly_trend:
        week = int(row.get("week") or 0)
        count = int(row.get("count") or 0)
        parts.append(f"W{week}: {count}")
    return ", ".join(parts)


def productive_hours_prompt(
    user_name: Optional[str],
    top_hours: List[Dict[str, Any]],
    day_filter: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "behavioral_productive_hours",
            "day_filter": day_filter,
            "top_hours_text": ", ".join(_hour_row_to_text(row) for row in top_hours),
        },
        user_name,
        history or [],
    )


def productive_days_prompt(
    user_name: Optional[str],
    days: List[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "behavioral_productive_days",
            "top_days_text": ", ".join(_day_row_to_text(row) for row in days[:3]),
        },
        user_name,
        history or [],
    )


def best_time_prompt(
    user_name: Optional[str],
    day: str,
    best_hour: int,
    conflict_free: bool,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "behavioral_best_time",
            "day_filter": day.title(),
            "best_hour_text": hour_to_12h_format(best_hour) or f"{best_hour}:00",
            "conflict_free": bool(conflict_free),
        },
        user_name,
        history or [],
    )


def completion_rate_prompt(
    user_name: Optional[str],
    rate_data: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "behavioral_completion_rate",
            "total_completed": int(rate_data.get("total_completed") or 0),
            "on_time": int(rate_data.get("on_time") or 0),
            "late": int(rate_data.get("late") or 0),
            "on_time_rate": float(rate_data.get("on_time_rate") or 0.0),
            "weekly_trend_text": _weekly_trend_text(rate_data.get("weekly_trend") or []),
        },
        user_name,
        history or [],
    )


def productivity_report_prompt(
    user_name: Optional[str],
    full_data: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    top_hours = full_data.get("top_hours") or []
    top_days = full_data.get("top_days") or []
    completion = full_data.get("completion_rate") or {}
    avg_time_taken = full_data.get("avg_time_taken")

    avg_time_text = "N/A"
    if isinstance(avg_time_taken, (int, float)):
        avg_time_text = f"{float(avg_time_taken):.1f} minutes"

    return gemini_service.generate_reply(
        {
            "action": "behavioral_productivity_report",
            "top_hours_text": ", ".join(_hour_row_to_text(row) for row in top_hours[:3]),
            "top_days_text": ", ".join(_day_row_to_text(row) for row in top_days[:3]),
            "on_time_rate": float(completion.get("on_time_rate") or 0.0),
            "total_completed": int(completion.get("total_completed") or 0),
            "avg_time_taken_text": avg_time_text,
            "weekly_trend_text": _weekly_trend_text(completion.get("weekly_trend") or []),
        },
        user_name,
        history or [],
    )


def not_enough_data_prompt(
    user_name: Optional[str],
    threshold: int,
    completed_count: int,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "behavioral_not_enough_data",
            "threshold": int(threshold),
            "total_completed": int(completed_count),
        },
        user_name,
        history or [],
    )


def no_data_for_filter_prompt(
    user_name: Optional[str],
    filter_used: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "behavioral_no_data_for_filter",
            "filter_used": filter_used,
        },
        user_name,
        history or [],
    )


def ask_day_prompt(user_name: Optional[str], history: Optional[List[Dict[str, Any]]] = None) -> str:
    return gemini_service.generate_reply(
        {
            "action": "behavioral_ask_day",
        },
        user_name,
        history or [],
    )


async def _save_turn(
    session_id: str,
    user_message: str,
    eva_reply: str,
    input_type: str,
    entities: Optional[Dict[str, Any]] = None,
) -> None:
    if not session_id:
        return

    now = datetime.now(dt_timezone.utc).replace(tzinfo=None)
    try:
        await insert_message(
            {
                "session_id": session_id,
                "role": "user",
                "content": user_message,
                "input_type": input_type or "text",
                "intent": "behavioral",
                "entities": entities or {},
                "status": "processed",
                "created_at": now,
            }
        )
        await insert_message(
            {
                "session_id": session_id,
                "role": "eva",
                "content": eva_reply,
                "status": "processed",
                "created_at": now,
            }
        )
        await update_last_message(session_id, eva_reply, now)
    except Exception as error:
        # Save errors should not break behavioral response.
        print(f"[BehavioralHandler] Failed to save conversation turn: {error}")


async def handle_behavioral(
    entities: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entities = dict(entities or {})
    context = dict(context or {})

    user_id = _coerce_text(context.get("user_id"))
    session_id = _coerce_text(context.get("session_id"))
    user_message = _coerce_text(context.get("message"))
    input_type = _coerce_text(context.get("input_type")) or "text"
    user = context.get("user") or {}
    settings = context.get("settings") or {}
    history = context.get("history") or []

    user_name = _coerce_text(user.get("name")) or None
    pending_context = context.get("pending_context") or {}
    pending_action = pending_context.get("pending_action") or {}

    # Step 1: threshold check.
    try:
        threshold = int(settings.get("analytics_min_tasks_threshold", 10))
    except (TypeError, ValueError):
        threshold = 10
    threshold = max(1, threshold)

    completed_count = await count_completed(user_id)
    if completed_count < threshold:
        response_text = not_enough_data_prompt(user_name, threshold, completed_count, history)
        await _save_turn(session_id, user_message, response_text, input_type, entities)
        return {
            "status": "not_enough_data",
            "intent": "behavioral",
            "response_text": response_text,
            "notifications": [],
            "required_threshold": threshold,
            "total_completed": completed_count,
        }

    # Step 2: sub-intent detection.
    forced_sub_intent = ""
    if _coerce_text(pending_action.get("intent")).lower() == "behavioral":
        forced_sub_intent = _coerce_text(pending_action.get("sub_intent")).lower()
    sub_intent = forced_sub_intent or _detect_sub_intent(user_message)

    merged_entities = dict(pending_action.get("entities") or {})
    merged_entities.update(entities)

    day_value = _normalize_day(merged_entities.get("day"))
    if sub_intent == "best_time_for_day" and not day_value:
        await redis_client.set_context(user_id, _pending_payload_for_day())
        response_text = ask_day_prompt(user_name, history)
        await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
        return {
            "status": "pending",
            "intent": "behavioral",
            "sub_intent": "best_time_for_day",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "free_text",
                "missing_entity": "day",
            },
        }

    # Step 3: analytics query + Step 4 no-data handling + Step 5 prompt generation.
    analytics_payload: Dict[str, Any] = {"sub_intent": sub_intent}

    if sub_intent == "productive_hours":
        day_num = weekday_name_to_number(day_value) if day_value else None
        hours = await get_hours_distribution(user_id, day_num)
        if not hours:
            filter_used = day_value.title() if day_value else "your activity history"
            response_text = no_data_for_filter_prompt(user_name, filter_used, history)
            await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "notifications": [],
                "filter_used": filter_used,
            }

        top_hours = hours[:3]
        response_text = productive_hours_prompt(
            user_name=user_name,
            top_hours=top_hours,
            day_filter=day_value.title() if day_value else "",
            history=history,
        )
        analytics_payload["top_hours"] = top_hours

    elif sub_intent == "productive_days":
        days = await get_days_distribution(user_id)
        has_data = any(int(row.get("count") or 0) > 0 for row in days)
        if not has_data:
            response_text = no_data_for_filter_prompt(user_name, "day patterns", history)
            await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "notifications": [],
                "filter_used": "day patterns",
            }

        response_text = productive_days_prompt(
            user_name=user_name,
            days=days,
            history=history,
        )
        analytics_payload["days"] = days

    elif sub_intent == "best_time_for_day":
        day_num = weekday_name_to_number(day_value)
        if day_num is None:
            await redis_client.set_context(user_id, _pending_payload_for_day())
            response_text = ask_day_prompt(user_name, history)
            await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
            return {
                "status": "pending",
                "intent": "behavioral",
                "sub_intent": "best_time_for_day",
                "response_text": response_text,
                "notifications": [],
                "pending": {
                    "expected_response": "free_text",
                    "missing_entity": "day",
                },
            }

        hours = await get_hours_distribution(user_id, day_num)
        if not hours:
            response_text = no_data_for_filter_prompt(user_name, day_value.title(), history)
            await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "notifications": [],
                "filter_used": day_value.title(),
            }

        day_tasks = await get_tasks_for_day(user_id, day_num)
        best_hour, conflict_free = _pick_best_hour_with_conflict_check(hours, day_tasks)
        if best_hour is None:
            response_text = no_data_for_filter_prompt(user_name, day_value.title(), history)
            await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "notifications": [],
                "filter_used": day_value.title(),
            }

        response_text = best_time_prompt(
            user_name=user_name,
            day=day_value,
            best_hour=best_hour,
            conflict_free=conflict_free,
            history=history,
        )
        analytics_payload["day"] = day_value
        analytics_payload["best_hour"] = best_hour
        analytics_payload["conflict_free"] = conflict_free

    elif sub_intent == "completion_rate":
        completion = await get_completion_rate(user_id)
        if int(completion.get("total_completed") or 0) <= 0:
            response_text = no_data_for_filter_prompt(user_name, "completion history", history)
            await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "notifications": [],
                "filter_used": "completion history",
            }

        response_text = completion_rate_prompt(user_name, completion, history)
        analytics_payload["completion_rate"] = completion

    else:
        top_hours, top_days, completion, avg_time_taken = await asyncio.gather(
            get_hours_distribution(user_id),
            get_days_distribution(user_id),
            get_completion_rate(user_id),
            get_avg_time_taken(user_id),
        )
        has_data = int(completion.get("total_completed") or 0) > 0
        if not has_data:
            response_text = no_data_for_filter_prompt(user_name, "productivity report", history)
            await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "notifications": [],
                "filter_used": "productivity report",
            }

        full_data = {
            "top_hours": top_hours,
            "top_days": top_days,
            "completion_rate": completion,
            "avg_time_taken": avg_time_taken,
        }
        response_text = productivity_report_prompt(user_name, full_data, history)
        analytics_payload.update(full_data)

    # Step 6: save + return.
    await _save_turn(session_id, user_message, response_text, input_type, merged_entities)
    return {
        "status": "success",
        "intent": "behavioral",
        "sub_intent": sub_intent,
        "response_text": response_text,
        "notifications": [],
        "analytics": analytics_payload,
    }
