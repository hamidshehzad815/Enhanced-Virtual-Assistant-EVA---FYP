"""
Behavioral analytics handler (Phase 8).
Uses scoring engine + reliability thresholds for productivity insights.
"""
from datetime import datetime, timezone as dt_timezone
import re
from typing import Any, Dict, List, Optional

from context.redis_client import redis_client
from db.activity_logs import (
    get_avg_time_taken,
    get_completed_logs_for_scoring,
    get_completion_rate,
    get_log_count_per_day,
    get_total_completed,
)
from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.tasks import get_tasks_for_day
from services.gemini import gemini_service
from services.productivity_scorer import (
    get_best_time_for_day,
    get_productive_days,
)
from utils.date_utils import weekday_name_to_number


_WEEKDAY_NAMES = {
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


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _extract_weekday_from_text(text: str) -> Optional[int]:
    lowered = _coerce_text(text).lower()
    if not lowered:
        return None

    for name, day_num in {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }.items():
        if re.search(rf"\b{name}\b", lowered):
            return day_num
    return None


def _extract_day(entities: Dict[str, Any], message: str) -> Optional[int]:
    payload = dict(entities or {})

    for key in ("day", "date"):
        raw = payload.get(key)
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if raw is None:
            continue

        if isinstance(raw, int):
            return raw if 0 <= raw <= 6 else None

        text = _coerce_text(raw)
        if not text:
            continue

        day_num = weekday_name_to_number(text)
        if day_num is not None:
            return day_num

        iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
        if iso:
            try:
                return datetime.strptime(text, "%Y-%m-%d").weekday()
            except ValueError:
                pass

        from_sentence = _extract_weekday_from_text(text)
        if from_sentence is not None:
            return from_sentence

    return _extract_weekday_from_text(message)


def _detect_sub_intent(message: str) -> str:
    text = _coerce_text(message).lower()

    if any(token in text for token in ("productivity report", "productivity snapshot", "full report", "summary report")):
        return "productivity_report"

    if any(token in text for token in ("completion rate", "on-time rate", "ontime rate", "how many completed", "completion trend")):
        return "completion_rate"

    if any(token in text for token in ("best day", "best days", "which day", "which days", "most focused day", "strongest day", "productive day")):
        return "productive_days"

    if any(token in text for token in ("best time", "schedule on", "find time on", "when should i schedule")):
        return "best_time_for_day"

    return "productive_hours"


def _join_with_and(items: List[str]) -> str:
    values = [item for item in items if item]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _unreliable_days_note(unreliable_rows: List[Dict[str, Any]]) -> str:
    if not unreliable_rows:
        return ""
    labels = []
    for row in unreliable_rows:
        day_name = _coerce_text(row.get("day"))
        count = int(row.get("log_count") or 0)
        needed = int(row.get("needed") or 5)
        labels.append(f"{day_name} ({count}/{needed})")
    return f"Still building reliable data for {_join_with_and(labels)}."


async def _save_turn(
    session_id: str,
    user_message: str,
    eva_reply: str,
    input_type: str,
    intent: str,
    entities: Optional[Dict[str, Any]] = None,
) -> None:
    now = datetime.now(dt_timezone.utc).replace(tzinfo=None)
    try:
        await insert_message(
            {
                "session_id": session_id,
                "role": "user",
                "content": user_message,
                "input_type": input_type or "text",
                "intent": intent,
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
        print(f"[BehavioralHandler] Failed to save conversation turn: {error}")


async def handle_behavioral(
    entities: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entities = dict(entities or {})
    context = dict(context or {})

    user_id = str(context.get("user_id") or "")
    session_id = str(context.get("session_id") or "")
    user = context.get("user") or {}
    settings = context.get("settings") or {}
    history = context.get("history") or []
    message = _coerce_text(context.get("message"))
    input_type = _coerce_text(context.get("input_type")) or "text"
    user_name = user.get("name")

    sub_intent = str(context.get("sub_intent") or "") or _detect_sub_intent(message)
    if sub_intent not in {
        "productive_hours",
        "productive_days",
        "best_time_for_day",
        "completion_rate",
        "productivity_report",
    }:
        sub_intent = "productive_hours"

    global_threshold = _safe_int(settings.get("analytics_min_tasks_threshold"), 20)
    if global_threshold <= 0:
        global_threshold = 20
    per_day_threshold = _safe_int(settings.get("analytics_min_tasks_per_day"), 5)
    if per_day_threshold <= 0:
        per_day_threshold = 5

    total_completed = await get_total_completed(user_id)
    if total_completed < global_threshold:
        response_text = gemini_service.generate_reply(
            {
                "action": "behavioral_not_enough_data",
                "total_completed": int(total_completed),
                "threshold": int(global_threshold),
            },
            user_name,
            history,
        )
        await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
        return {
            "status": "not_enough_data",
            "intent": "behavioral",
            "sub_intent": sub_intent,
            "response_text": response_text,
            "analytics": {
                "total_completed": int(total_completed),
                "threshold": int(global_threshold),
            },
            "notifications": [],
        }

    logs = await get_completed_logs_for_scoring(user_id)
    day_counts = await get_log_count_per_day(user_id)

    if sub_intent == "productive_hours":
        day_num = _extract_day(entities, message)
        if day_num is not None and int(day_counts.get(day_num, 0)) < per_day_threshold:
            filter_used = _WEEKDAY_NAMES.get(day_num, "that day")
            response_text = gemini_service.generate_reply(
                {
                    "action": "behavioral_no_data_for_filter",
                    "filter_used": filter_used,
                },
                user_name,
                history,
            )
            await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "analytics": {
                    "filter_day": day_num,
                    "required_per_day": int(per_day_threshold),
                    "day_count": int(day_counts.get(day_num, 0)),
                },
                "notifications": [],
            }

        day_result = get_productive_days(logs, day_counts, per_day_threshold)
        reliable_days = list(day_result.get("reliable") or [])
        unreliable_days = list(day_result.get("unreliable") or [])
        if not reliable_days:
            response_text = gemini_service.generate_reply(
                {
                    "action": "behavioral_no_data_for_filter",
                    "filter_used": "your current history",
                },
                user_name,
                history,
            )
            await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "analytics": {
                    "reliable_days": [],
                    "unreliable_days": unreliable_days,
                },
                "notifications": [],
            }

        top_ranges: List[str] = []
        if day_num is not None:
            best_for_day = get_best_time_for_day(logs, day_num, [])
            if best_for_day.get("best_range"):
                top_ranges.append(f"{_WEEKDAY_NAMES.get(day_num, 'That day')} {best_for_day['best_range']}")
        else:
            for row in reliable_days[:3]:
                row_day_num = int(row.get("day_num"))
                best_for_day = get_best_time_for_day(logs, row_day_num, [])
                if best_for_day.get("best_range"):
                    top_ranges.append(f"{row.get('day')} {best_for_day['best_range']}")

        if not top_ranges:
            response_text = gemini_service.generate_reply(
                {
                    "action": "behavioral_no_data_for_filter",
                    "filter_used": "that request",
                },
                user_name,
                history,
            )
            await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "analytics": {
                    "reliable_days": reliable_days,
                    "unreliable_days": unreliable_days,
                },
                "notifications": [],
            }

        unreliable_note = _unreliable_days_note(unreliable_days)
        response_text = gemini_service.generate_reply(
            {
                "action": "behavioral_productive_hours",
                "top_hours_text": _join_with_and(top_ranges[:3]),
                "unreliable_days_text": unreliable_note,
            },
            user_name,
            history,
        )
        if unreliable_note:
            response_text = f"{response_text} {unreliable_note}"

        await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
        return {
            "status": "success",
            "intent": "behavioral",
            "sub_intent": sub_intent,
            "response_text": response_text,
            "analytics": {
                "top_ranges": top_ranges[:3],
                "reliable_days": reliable_days,
                "unreliable_days": unreliable_days,
            },
            "notifications": [],
        }

    if sub_intent == "productive_days":
        day_result = get_productive_days(logs, day_counts, per_day_threshold)
        reliable_days = list(day_result.get("reliable") or [])
        unreliable_days = list(day_result.get("unreliable") or [])
        if not reliable_days:
            response_text = gemini_service.generate_reply(
                {
                    "action": "behavioral_no_data_for_filter",
                    "filter_used": "your weekdays",
                },
                user_name,
                history,
            )
            await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "analytics": {
                    "reliable_days": [],
                    "unreliable_days": unreliable_days,
                },
                "notifications": [],
            }

        top_days_text = _join_with_and(
            [f"{row.get('day')} ({int(row.get('log_count') or 0)} completions)" for row in reliable_days[:3]]
        )
        unreliable_note = _unreliable_days_note(unreliable_days)
        response_text = gemini_service.generate_reply(
            {
                "action": "behavioral_productive_days",
                "top_days_text": top_days_text,
                "unreliable_days_text": unreliable_note,
            },
            user_name,
            history,
        )
        if unreliable_note:
            response_text = f"{response_text} {unreliable_note}"

        await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
        return {
            "status": "success",
            "intent": "behavioral",
            "sub_intent": sub_intent,
            "response_text": response_text,
            "analytics": {
                "days": reliable_days,
                "unreliable_days": unreliable_days,
            },
            "notifications": [],
        }

    if sub_intent == "best_time_for_day":
        day_num = _extract_day(entities, message)
        if day_num is None:
            pending_context = {
                "expected_response": "free_text",
                "missing_entity": "day",
                "pending_action": {
                    "intent": "behavioral",
                    "sub_intent": "best_time_for_day",
                    "entities": dict(entities),
                },
            }
            await redis_client.set_context(user_id, pending_context)
            response_text = gemini_service.generate_reply(
                {"action": "behavioral_ask_day"},
                user_name,
                history,
            )
            await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
            return {
                "status": "pending",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "pending": {
                    "expected_response": "free_text",
                    "missing_entity": "day",
                },
                "notifications": [],
            }

        if int(day_counts.get(day_num, 0)) < per_day_threshold:
            day_label = _WEEKDAY_NAMES.get(day_num, "that day")
            response_text = gemini_service.generate_reply(
                {
                    "action": "behavioral_no_data_for_filter",
                    "filter_used": day_label,
                },
                user_name,
                history,
            )
            await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "analytics": {
                    "filter_day": day_num,
                    "required_per_day": int(per_day_threshold),
                    "day_count": int(day_counts.get(day_num, 0)),
                },
                "notifications": [],
            }

        existing_tasks = await get_tasks_for_day(user_id, day_num)
        best = get_best_time_for_day(logs, day_num, existing_tasks)
        best_range = _coerce_text(best.get("best_range"))

        if not best_range:
            day_label = _WEEKDAY_NAMES.get(day_num, "that day")
            response_text = gemini_service.generate_reply(
                {
                    "action": "behavioral_no_data_for_filter",
                    "filter_used": day_label,
                },
                user_name,
                history,
            )
            await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
            return {
                "status": "no_data",
                "intent": "behavioral",
                "sub_intent": sub_intent,
                "response_text": response_text,
                "analytics": {
                    "day": day_label,
                    "conflict_free": False,
                },
                "notifications": [],
            }

        conflict_note = (
            "This window is currently conflict-free."
            if best.get("conflict_free")
            else "You may have a conflict in this window."
        )
        response_text = gemini_service.generate_reply(
            {
                "action": "behavioral_best_time",
                "day_filter": _WEEKDAY_NAMES.get(day_num, "that day"),
                "best_hour_text": best_range,
                "conflict_note": conflict_note,
            },
            user_name,
            history,
        )
        await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
        return {
            "status": "success",
            "intent": "behavioral",
            "sub_intent": sub_intent,
            "response_text": response_text,
            "analytics": {
                "day": _WEEKDAY_NAMES.get(day_num, "that day"),
                "day_num": day_num,
                "best_range": best_range,
                "start_hour": best.get("start_hour"),
                "score": best.get("score"),
                "conflict_free": bool(best.get("conflict_free")),
            },
            "notifications": [],
        }

    if sub_intent == "completion_rate":
        completion = await get_completion_rate(user_id)
        response_text = gemini_service.generate_reply(
            {
                "action": "behavioral_completion_rate",
                "total_completed": int(completion.get("total_completed") or 0),
                "on_time": int(completion.get("on_time") or 0),
                "late": int(completion.get("late") or 0),
                "on_time_rate": float(completion.get("on_time_rate") or 0.0),
                "weekly_trend_text": str(completion.get("weekly_trend") or []),
            },
            user_name,
            history,
        )
        await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
        return {
            "status": "success",
            "intent": "behavioral",
            "sub_intent": sub_intent,
            "response_text": response_text,
            "analytics": {"completion_rate": completion},
            "notifications": [],
        }

    # productivity_report
    day_result = get_productive_days(logs, day_counts, per_day_threshold)
    reliable_days = list(day_result.get("reliable") or [])
    unreliable_days = list(day_result.get("unreliable") or [])
    completion = await get_completion_rate(user_id)
    avg_time_taken = await get_avg_time_taken(user_id)

    top_ranges: List[str] = []
    for row in reliable_days[:3]:
        row_day_num = int(row.get("day_num"))
        best_for_day = get_best_time_for_day(logs, row_day_num, [])
        if best_for_day.get("best_range"):
            top_ranges.append(f"{row.get('day')} {best_for_day['best_range']}")

    top_days_text = _join_with_and([_coerce_text(row.get("day")) for row in reliable_days[:3]]) or "No reliable days yet"
    top_hours_text = _join_with_and(top_ranges[:3]) or "No reliable hour ranges yet"
    weekly_trend = completion.get("weekly_trend") or []
    weekly_trend_text = ", ".join([f"W{row.get('week')}: {row.get('count')}" for row in weekly_trend]) or "No recent trend yet"
    avg_time_text = f"{round(float(avg_time_taken), 1)} minutes" if avg_time_taken is not None else "not available yet"
    unreliable_note = _unreliable_days_note(unreliable_days)

    response_text = gemini_service.generate_reply(
        {
            "action": "behavioral_productivity_report",
            "top_hours_text": top_hours_text,
            "top_days_text": top_days_text,
            "on_time_rate": float(completion.get("on_time_rate") or 0.0),
            "total_completed": int(completion.get("total_completed") or 0),
            "avg_time_taken_text": avg_time_text,
            "weekly_trend_text": weekly_trend_text,
            "unreliable_days_text": unreliable_note,
        },
        user_name,
        history,
    )
    if unreliable_note:
        response_text = f"{response_text} {unreliable_note}"

    await _save_turn(session_id, message, response_text, input_type, "behavioral", entities)
    return {
        "status": "success",
        "intent": "behavioral",
        "sub_intent": "productivity_report",
        "response_text": response_text,
        "analytics": {
            "top_ranges": top_ranges[:3],
            "reliable_days": reliable_days,
            "unreliable_days": unreliable_days,
            "completion_rate": completion,
            "avg_time_taken": avg_time_taken,
        },
        "notifications": [],
    }


__all__ = ["handle_behavioral", "_detect_sub_intent"]
