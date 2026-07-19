"""
Phase 27 scheduling update handler.
Implements STEP 1-12:
- identify target task
- validate requested updates
- confirm with user
- apply DB update after explicit yes
- write activity log and sync Google Calendar (non-blocking)
"""
from datetime import datetime, timezone as dt_timezone
import re
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from context.context_manager import extract_update_fields
from context.redis_client import redis_client
from db.activity_logs import increment_reschedule_count, insert_log
from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.tasks import (
    check_update_overlap,
    find_tasks_for_update,
    get_task_by_id,
    update_task,
)
from pipeline.pending_reply_fallback import (
    resolve_date_fallback,
    resolve_duration_fallback,
    resolve_enum_fallback,
    resolve_time_fallback,
)
from services.duckling import duckling_client
from services.gemini import gemini_service
from services.google_calendar import google_calendar_client
from utils.google_calendar_sync import resolve_google_calendar_sync
from utils.learning_schedule_conflicts import (
    find_task_conflicts_from_settings,
    format_learning_schedule_conflict_message,
)
from utils.quiet_hours import find_quiet_hour_matches, format_quiet_hour_labels
from utils.task_value_normalizer import canonicalize_priority, canonicalize_status, clean_task_name
from utils.timezone_utils import (
    get_zoneinfo,
    local_datetime_to_utc_naive,
    local_day_bounds_to_utc_naive,
    resolve_timezone_name,
    utc_naive_to_local,
)
from utils.api_datetime import serialize_stored_datetime


def _first_value(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_object_id(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))
    except Exception:
        return value


def _to_date_text(value: Any) -> str:
    raw = _coerce_text(value)
    if not raw:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    if "T" in raw and re.match(r"^\d{4}-\d{2}-\d{2}T", raw):
        return raw.split("T")[0]
    return raw


def _to_time_text(value: Any) -> str:
    raw = _coerce_text(value)
    if not raw:
        return ""

    iso_time_match = re.search(r"(\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$", raw)
    if iso_time_match:
        return iso_time_match.group(1)

    if re.match(r"^\d{2}:\d{2}$", raw):
        return f"{raw}:00"
    if re.match(r"^\d{2}:\d{2}:\d{2}$", raw):
        return raw
    if "T" in raw and re.match(r"^\d{4}-\d{2}-\d{2}T", raw):
        return _to_time_text(raw.split("T", 1)[1])

    fragment_match = re.search(r"\b(\d{2}:\d{2}(?::\d{2})?)\b", raw)
    if fragment_match:
        fragment = fragment_match.group(1)
        return fragment if len(fragment) == 8 else f"{fragment}:00"

    ampm_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap]m)\b", raw, flags=re.IGNORECASE)
    if ampm_match:
        hour = int(ampm_match.group(1))
        minute = int(ampm_match.group(2) or 0)
        meridiem = ampm_match.group(3).lower()
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}:00"

    return raw


def _format_date_display(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%A, %d %b %Y")
    except ValueError:
        return date_str


def _utc_now_naive() -> datetime:
    return datetime.now(dt_timezone.utc).replace(tzinfo=None)


def _normalize_priority(value: Any) -> str:
    return canonicalize_priority(value)


def _normalize_status(value: Any) -> str:
    return canonicalize_status(value)


def _serialize_due_datetime(value: Any, timezone_name: Optional[str] = None) -> str:
    if timezone_name:
        converted = serialize_stored_datetime(value, timezone_name)
        if converted:
            return converted
    if isinstance(value, datetime):
        return value.isoformat()
    return _coerce_text(value)


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    raw = _coerce_text(value)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_due_display(value: Any, timezone_name: str) -> str:
    local_dt = utc_naive_to_local(value, timezone_name)
    if local_dt is None:
        return _coerce_text(value)
    return local_dt.strftime("%A, %d %b %Y at %I:%M %p").replace(" 0", " ")


def _task_preview(task: Dict[str, Any], timezone_name: Optional[str] = None) -> Dict[str, Any]:
    return {
        "task_id": _coerce_text(task.get("_id")) or _coerce_text(task.get("task_id")),
        "title": _coerce_text(task.get("title")) or "Untitled task",
        "due_datetime": _serialize_due_datetime(task.get("due_datetime"), timezone_name),
        "priority": _normalize_priority(task.get("priority")) or "medium",
        "status": _normalize_status(task.get("status")) or "pending",
        "duration": int(task.get("duration") or 120),
        "google_calendar_event_id": _coerce_text(task.get("google_calendar_event_id")),
    }


def _pending_payload(
    entities: Dict[str, Any],
    stage: str,
    expected_response: str,
    task_ids: Optional[List[str]] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    task_id: Optional[str] = None,
    task: Optional[Dict[str, Any]] = None,
    updates: Optional[Dict[str, Any]] = None,
    change_summary: str = "",
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "pending_action": {
            "intent": "update",
            "stage": stage,
            "entities": dict(entities or {}),
            "task_ids": list(task_ids or []),
            "tasks": list(tasks or []),
        },
        "expected_response": expected_response,
    }
    if task_id:
        payload["pending_action"]["task_id"] = str(task_id)
    if task:
        payload["pending_action"]["task"] = dict(task)
    if updates:
        payload["pending_action"]["updates"] = dict(updates)
    if change_summary:
        payload["pending_action"]["change_summary"] = change_summary
    payload.update(extra)
    return payload


async def _save_turn(
    session_id: str,
    user_message: str,
    eva_reply: str,
    input_type: str,
    intent: str,
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
        print(f"[UpdateHandler] Failed to save conversation turn: {error}")


def _filters_summary(filters_used: Dict[str, Any]) -> str:
    parts: List[str] = []

    task_name = _coerce_text(filters_used.get("task_name"))
    if task_name:
        parts.append(f'task name "{task_name}"')

    date_value = _coerce_text(filters_used.get("date"))
    if date_value:
        parts.append(f"date {date_value}")

    priority = _coerce_text(filters_used.get("priority"))
    if priority:
        parts.append(f"priority {priority}")

    status = _coerce_text(filters_used.get("status"))
    if status:
        parts.append(f"status {status}")

    if not parts:
        return "those filters"
    return ", ".join(parts)


def _missing_identifier_prompt(
    username: Optional[str],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_missing_identifier"},
        username,
        history or [],
    )


def _invalid_identifier_date_prompt(
    username: Optional[str],
    date_value: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_invalid_identifier_date", "date": date_value},
        username,
        history or [],
    )


def _invalid_new_date_prompt(
    username: Optional[str],
    date_value: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_invalid_new_date", "date": date_value},
        username,
        history or [],
    )


def _invalid_new_time_prompt(
    username: Optional[str],
    time_value: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_invalid_new_time", "time": time_value},
        username,
        history or [],
    )


def _invalid_priority_prompt(
    username: Optional[str],
    priority_value: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_invalid_priority", "priority": priority_value},
        username,
        history or [],
    )


def _invalid_status_prompt(
    username: Optional[str],
    status_value: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_invalid_status", "status": status_value},
        username,
        history or [],
    )


def _invalid_duration_prompt(
    username: Optional[str],
    duration_value: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_invalid_duration", "duration": duration_value},
        username,
        history or [],
    )


def _status_locked_prompt(
    username: Optional[str],
    task_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_status_locked", "task_name": task_name},
        username,
        history or [],
    )


def _already_complete_prompt(
    username: Optional[str],
    task_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_already_complete", "task_name": task_name},
        username,
        history or [],
    )


def _not_found_prompt(
    username: Optional[str],
    filters_used: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "update_not_found",
            "filters_summary": _filters_summary(filters_used),
            "task_name": _coerce_text(filters_used.get("task_name")),
            "date": _coerce_text(filters_used.get("date")),
            "priority": _coerce_text(filters_used.get("priority")),
            "status": _coerce_text(filters_used.get("status")),
        },
        username,
        history or [],
    )


def _multi_list_prompt(
    username: Optional[str],
    tasks: List[Dict[str, Any]],
    timezone_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    intro = gemini_service.generate_reply(
        {"action": "update_multi_list", "count": len(tasks)},
        username,
        history or [],
    )

    lines: List[str] = []
    for index, task in enumerate(tasks, start=1):
        title = _coerce_text(task.get("title")) or "Untitled task"
        due_display = _format_due_display(task.get("due_datetime"), timezone_name)
        priority = _coerce_text(task.get("priority")).lower() or "medium"
        if due_display:
            lines.append(f"{index}. {title} - {due_display} ({priority})")
        else:
            lines.append(f"{index}. {title} ({priority})")

    lines.append("Reply with a number to choose which task to update.")
    return f"{intro}\n" + "\n".join(lines)


def _too_broad_prompt(
    username: Optional[str],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_too_broad"},
        username,
        history or [],
    )


def _ask_what_to_update_prompt(
    username: Optional[str],
    task_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_ask_fields", "task_name": task_name or "that task"},
        username,
        history or [],
    )


def _overlap_conflict_prompt(
    username: Optional[str],
    task_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_overlap_conflict", "task_name": task_name or "that task"},
        username,
        history or [],
    )


def _confirm_update_prompt(
    username: Optional[str],
    task_name: str,
    change_summary: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "update_confirm",
            "task_name": task_name or "that task",
            "changes_summary": change_summary,
        },
        username,
        history or [],
    )


def _no_changes_prompt(
    username: Optional[str],
    task_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_no_changes", "task_name": task_name or "that task"},
        username,
        history or [],
    )


def _update_failed_prompt(
    username: Optional[str],
    task_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "update_apply_failed", "task_name": task_name or "that task"},
        username,
        history or [],
    )


async def _resolve_identifier_date(
    date_value: str,
    timezone_name: str,
) -> Tuple[Optional[str], Optional[Dict[str, datetime]]]:
    candidate = _to_date_text(date_value)
    if not candidate:
        return None, None

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
        resolved = await duckling_client.resolve_date(candidate, timezone=timezone_name)
        resolved_text = _to_date_text(resolved)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", resolved_text):
            candidate = resolved_text
        else:
            today = datetime.now(get_zoneinfo(timezone_name or "UTC")).date()
            fallback_date = resolve_date_fallback(
                candidate,
                eva_prompt="Which date's task would you like to update?",
                reference_date=today,
                allow_past=True,
                deterministic_miss="duckling_miss",
            )
            candidate = fallback_date or candidate

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
        return None, None

    day_start, day_end = local_day_bounds_to_utc_naive(candidate, timezone_name)
    if not day_start or not day_end:
        return None, None
    return candidate, {"start": day_start, "end": day_end}


async def _resolve_update_date(
    raw_value: Any,
    timezone_name: str,
) -> Optional[str]:
    candidate = _to_date_text(raw_value)
    if not candidate:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
        return candidate
    resolved = await duckling_client.resolve_date(candidate, timezone=timezone_name)
    resolved_text = _to_date_text(resolved)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", resolved_text):
        return resolved_text
    # Past-date rejection happens downstream against the combined datetime,
    # so allow_past here to match this function's existing behavior.
    today = datetime.now(get_zoneinfo(timezone_name or "UTC")).date()
    fallback_date = resolve_date_fallback(
        candidate,
        eva_prompt="What date would you like to reschedule to?",
        reference_date=today,
        allow_past=True,
        deterministic_miss="duckling_miss",
    )
    return fallback_date


async def _resolve_update_time(
    raw_value: Any,
    timezone_name: str,
) -> Optional[str]:
    candidate = _to_time_text(raw_value)
    if not candidate:
        return None
    if re.match(r"^\d{2}:\d{2}:\d{2}$", candidate):
        return candidate
    resolved = await duckling_client.resolve_time(candidate, timezone=timezone_name)
    resolved_text = _to_time_text(resolved)
    if re.match(r"^\d{2}:\d{2}:\d{2}$", resolved_text):
        return resolved_text
    fallback_time = resolve_time_fallback(
        candidate,
        eva_prompt="What time would you like to reschedule to?",
        deterministic_miss="duckling_miss",
    )
    return fallback_time


async def _parse_duration_minutes(raw_value: Any) -> Optional[int]:
    first = _first_value(raw_value)
    if isinstance(first, int):
        return max(5, int(first))
    if isinstance(first, float):
        return max(5, int(first))

    raw = _coerce_text(first).lower()
    if not raw:
        return None

    if raw.isdigit():
        return max(5, int(raw))

    number_match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if number_match:
        amount = float(number_match.group(1))
        if "hour" in raw or "hr" in raw:
            return max(5, int(amount * 60))
        if "min" in raw:
            return max(5, int(amount))

    duckling_minutes = await duckling_client.resolve_duration(raw)
    if duckling_minutes is not None:
        return max(5, int(duckling_minutes))

    return resolve_duration_fallback(
        raw,
        unit="minutes",
        eva_prompt="How long should the task take?",
        min_value=5,
        max_value=1440,
        deterministic_miss="duckling_miss",
    )


def _serialize_updates_for_context(update_data: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(update_data or {})
    due_datetime = payload.get("due_datetime")
    if isinstance(due_datetime, datetime):
        payload["due_datetime"] = due_datetime.isoformat()
    return payload


def _deserialize_updates_from_context(update_data: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(update_data or {})
    due_datetime = payload.get("due_datetime")
    if due_datetime is not None:
        parsed = _coerce_datetime(due_datetime)
        if parsed is not None:
            payload["due_datetime"] = parsed
        else:
            payload.pop("due_datetime", None)
    if "duration" in payload:
        try:
            payload["duration"] = max(5, int(payload["duration"]))
        except (TypeError, ValueError):
            payload.pop("duration", None)
    return payload


def _build_change_summary(
    current_task: Dict[str, Any],
    update_data: Dict[str, Any],
    timezone_name: str,
) -> str:
    parts: List[str] = []

    current_title = _coerce_text(current_task.get("title"))
    new_title = _coerce_text(update_data.get("title"))
    if "title" in update_data and new_title:
        if current_title and current_title != new_title:
            parts.append(f'title from "{current_title}" to "{new_title}"')
        else:
            parts.append(f'title to "{new_title}"')

    current_priority = _normalize_priority(current_task.get("priority"))
    new_priority = _normalize_priority(update_data.get("priority"))
    if "priority" in update_data and new_priority:
        if current_priority and current_priority != new_priority:
            parts.append(f"priority from {current_priority} to {new_priority}")
        else:
            parts.append(f"priority to {new_priority}")

    current_status = _normalize_status(current_task.get("status"))
    new_status = _normalize_status(update_data.get("status"))
    if "status" in update_data and new_status:
        if current_status and current_status != new_status:
            parts.append(f"status from {current_status} to {new_status}")
        else:
            parts.append(f"status to {new_status}")

    current_duration = int(current_task.get("duration") or 120)
    new_duration = update_data.get("duration")
    if "duration" in update_data and new_duration is not None:
        try:
            duration_value = int(new_duration)
            if duration_value != current_duration:
                parts.append(f"duration from {current_duration} to {duration_value} minutes")
            else:
                parts.append(f"duration to {duration_value} minutes")
        except (TypeError, ValueError):
            pass

    current_due = _coerce_datetime(current_task.get("due_datetime"))
    new_due = _coerce_datetime(update_data.get("due_datetime"))
    if "due_datetime" in update_data and new_due is not None:
        current_due_text = _format_due_display(current_due, timezone_name) if current_due else ""
        new_due_text = _format_due_display(new_due, timezone_name)
        if current_due_text and current_due_text != new_due_text:
            parts.append(f"schedule from {current_due_text} to {new_due_text}")
        else:
            parts.append(f"schedule to {new_due_text}")

    if not parts:
        return "apply the requested changes"
    return ", ".join(parts)


def _remove_noop_updates(
    current_task: Dict[str, Any],
    update_data: Dict[str, Any],
) -> Dict[str, Any]:
    cleaned = dict(update_data or {})

    if "title" in cleaned:
        if _coerce_text(cleaned["title"]) == _coerce_text(current_task.get("title")):
            cleaned.pop("title", None)

    if "priority" in cleaned:
        if _normalize_priority(cleaned["priority"]) == _normalize_priority(current_task.get("priority")):
            cleaned.pop("priority", None)

    if "status" in cleaned:
        if _normalize_status(cleaned["status"]) == _normalize_status(current_task.get("status")):
            cleaned.pop("status", None)

    if "duration" in cleaned:
        try:
            if int(cleaned["duration"]) == int(current_task.get("duration") or 120):
                cleaned.pop("duration", None)
        except (TypeError, ValueError):
            pass

    if "due_datetime" in cleaned:
        current_due = _coerce_datetime(current_task.get("due_datetime"))
        new_due = _coerce_datetime(cleaned["due_datetime"])
        if current_due is not None and new_due is not None:
            if current_due.replace(tzinfo=None) == new_due.replace(tzinfo=None):
                cleaned.pop("due_datetime", None)

    return cleaned


async def _set_what_to_update_context(
    user_id: str,
    entities: Dict[str, Any],
    task_id: str,
    task_preview: Dict[str, Any],
    remove_keys: Optional[List[str]] = None,
) -> None:
    pending_entities = dict(entities or {})
    for key in list(remove_keys or []):
        pending_entities.pop(key, None)
    pending_entities["task_id"] = task_id
    if not pending_entities.get("task_name"):
        pending_entities["task_name"] = _coerce_text(task_preview.get("title"))

    await redis_client.set_context(
        user_id,
        _pending_payload(
            entities=pending_entities,
            stage="what_to_update",
            expected_response="free_text",
            task_id=task_id,
            task=task_preview,
        ),
    )


async def _execute_confirmed_update(
    user_id: str,
    user_name: Optional[str],
    session_id: str,
    user_message: str,
    input_type: str,
    history: List[Dict[str, Any]],
    integrations: List[Dict[str, Any]],
    timezone_name: str,
    pending_action: Dict[str, Any],
    entities: Dict[str, Any],
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    task_id = _coerce_text(pending_action.get("task_id") or entities.get("task_id"))
    if not task_id:
        response_text = _update_failed_prompt(user_name, "that task", history)
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_update", entities)
        return {
            "status": "validation_error",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
        }

    current_task = await get_task_by_id(task_id, user_id)
    if not current_task:
        response_text = _not_found_prompt(
            user_name,
            {"task_name": _coerce_text(entities.get("task_name"))},
            history,
        )
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_update", entities)
        return {
            "status": "not_found",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
            "match_count": 0,
        }

    update_data = _deserialize_updates_from_context(pending_action.get("updates") or {})
    if not update_data:
        response_text = _no_changes_prompt(user_name, _coerce_text(current_task.get("title")), history)
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_update", entities)
        return {
            "status": "validation_error",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
        }

    updated = await update_task(task_id, update_data)
    if not updated:
        response_text = _update_failed_prompt(user_name, _coerce_text(current_task.get("title")), history)
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_update", entities)
        return {
            "status": "error",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
        }

    updated_task = await get_task_by_id(task_id, user_id)
    if not updated_task:
        updated_task = dict(current_task)
        updated_task.update(update_data)

    final_due = _coerce_datetime(updated_task.get("due_datetime"))
    if isinstance(final_due, datetime) and final_due.tzinfo is not None:
        final_due = final_due.astimezone(dt_timezone.utc).replace(tzinfo=None)

    final_priority = _normalize_priority(updated_task.get("priority")) or "medium"
    final_title = _coerce_text(updated_task.get("title")) or "Untitled task"
    final_status = _normalize_status(updated_task.get("status")) or "pending"
    previous_status = _normalize_status(current_task.get("status")) or "pending"
    transitioned_to_complete = previous_status != "complete" and final_status == "complete"

    log_payload: Dict[str, Any] = {
        "user_id": _to_object_id(user_id),
        "task_id": _to_object_id(task_id),
        "task_priority": final_priority,
        "subject": final_title,
        "source": "scheduling_module",
    }

    if transitioned_to_complete:
        completed_at = _coerce_datetime(updated_task.get("completed_at")) or datetime.now(dt_timezone.utc).replace(tzinfo=None)
        if isinstance(completed_at, datetime) and completed_at.tzinfo is not None:
            completed_at = completed_at.astimezone(dt_timezone.utc).replace(tzinfo=None)

        created_at = _coerce_datetime(updated_task.get("created_at") or current_task.get("created_at"))
        if isinstance(created_at, datetime) and created_at.tzinfo is not None:
            created_at = created_at.astimezone(dt_timezone.utc).replace(tzinfo=None)

        log_payload.update(
            {
                "action_type": "task_completed",
                "action_timestamp": completed_at,
                "day_of_week": completed_at.weekday(),
                "hour_of_day": completed_at.hour,
                "week_number": completed_at.isocalendar().week,
                "scheduled_hour": final_due.hour if isinstance(final_due, datetime) else None,
                "scheduled_day": final_due.weekday() if isinstance(final_due, datetime) else None,
            }
        )
        if isinstance(final_due, datetime):
            log_payload["was_on_time"] = completed_at <= final_due
        if isinstance(created_at, datetime):
            elapsed_minutes = int((completed_at - created_at).total_seconds() // 60)
            log_payload["time_taken_minutes"] = max(0, elapsed_minutes)
    elif final_due is not None:
        log_payload.update(
            {
                "action_type": "task_updated",
                "day_of_week": final_due.weekday(),
                "hour_of_day": final_due.hour,
                "week_number": final_due.isocalendar().week,
                "scheduled_hour": final_due.hour,
                "scheduled_day": final_due.weekday(),
            }
        )
    else:
        log_payload["action_type"] = "task_updated"
    try:
        await insert_log(log_payload, settings=settings)
    except Exception as error:
        print(f"[UpdateHandler] Activity log insert failed for task_id={task_id}: {error}")

    if "due_datetime" in update_data:
        try:
            await increment_reschedule_count(task_id, settings=settings, user_id=user_id)
        except Exception as error:
            print(f"[UpdateHandler] Reschedule count increment failed for task_id={task_id}: {error}")

    calendar_updated = False
    old_event_id = _coerce_text(current_task.get("google_calendar_event_id"))
    calendar_change_requested = any(
        key in update_data
        for key in ("due_datetime", "title", "duration")
    )
    if old_event_id and calendar_change_requested:
        integration = await resolve_google_calendar_sync(user_id, integrations, settings)
        access_token = _coerce_text((integration or {}).get("access_token"))
        calendar_id = _coerce_text((integration or {}).get("calendar_id")) or "primary"
        if access_token:
            try:
                calendar_updated = await google_calendar_client.update_event(
                    token=access_token,
                    calendar_id=calendar_id,
                    event_id=old_event_id,
                    task_data={
                        "title": final_title,
                        "due_datetime": final_due or current_task.get("due_datetime"),
                        "duration_minutes": int(updated_task.get("duration") or 120),
                        "timezone": timezone_name,
                        "description": f"Priority: {final_priority}",
                    },
                )
            except Exception as error:
                print(f"[UpdateHandler] Google Calendar update_event exception: {error}")

    change_summary = _coerce_text(pending_action.get("change_summary"))
    if not change_summary:
        change_summary = _build_change_summary(current_task, update_data, timezone_name)

    response_text = gemini_service.generate_reply(
        {
            "action": "task_updated",
            "task_name": final_title,
            "changes_summary": change_summary,
            "calendar_synced": calendar_updated,
        },
        user_name,
        history,
    )
    await _save_turn(
        session_id,
        user_message,
        response_text,
        input_type,
        "scheduling_update",
        entities,
    )

    notifications: List[Dict[str, Any]] = []
    if "due_datetime" in update_data:
        final_due_for_notice = _coerce_datetime(updated_task.get("due_datetime"))
        if final_due_for_notice is not None:
            from utils.task_notifications import build_task_rescheduled_notification

            notifications.append(
                build_task_rescheduled_notification(
                    user_id=str(user_id),
                    user_name=user_name,
                    task_title=final_title,
                    due_datetime=final_due_for_notice,
                    timezone_name=timezone_name,
                    reference_type="task",
                    reference_id=str(updated_task.get("_id") or task_id),
                )
            )

    return {
        "status": "success",
        "intent": "scheduling_update",
        "response_text": response_text,
        "notifications": notifications,
        "task": {
            "task_id": _coerce_text(updated_task.get("_id")) or task_id,
            "title": final_title,
            "due_datetime": _serialize_due_datetime(updated_task.get("due_datetime"), timezone_name),
            "priority": final_priority,
            "status": _normalize_status(updated_task.get("status")) or "pending",
            "duration": int(updated_task.get("duration") or 120),
        },
        "changes_summary": change_summary,
    }


async def handle_scheduling_update(
    entities: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entities = dict(entities or {})
    context = dict(context or {})

    user_id = str(context.get("user_id") or "")
    session_id = str(context.get("session_id") or "")
    user = context.get("user") or {}
    settings = context.get("settings") or {}
    integrations = context.get("integrations") or []
    history = context.get("history") or []
    user_message = str(context.get("message") or "")
    input_type = str(context.get("input_type") or "text")

    user_name = user.get("name")
    timezone_name = resolve_timezone_name(user.get("timezone"))

    pending_context = context.get("pending_context") or {}
    pending_action = pending_context.get("pending_action") or {}
    pending_reason = _coerce_text(pending_context.get("pending_reason"))
    pending_reply_type = _coerce_text(context.get("pending_reply_type"))
    pending_reply_value = _coerce_text(context.get("pending_reply_value")).lower()

    if not user_id:
        response_text = gemini_service.generate_reply(
            {"action": "validation_error"},
            user_name,
            history,
        )
        return {
            "status": "validation_error",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
        }

    # Quiet-hours override confirmation (before final update confirm).
    if (
        pending_action.get("intent") in {"update", "scheduling_update"}
        and pending_reply_type == "yes_no"
        and pending_reason == "quiet_hours"
    ):
        if pending_reply_value == "no":
            await redis_client.delete_context(user_id)
            await _set_what_to_update_context(
                user_id=user_id,
                entities=dict(pending_action.get("entities") or {}),
                task_id=str(pending_action.get("task_id") or ""),
                task_preview=pending_action.get("task") or {},
                remove_keys=["new_time"],
            )
            response_text = gemini_service.generate_reply(
                {
                    "action": "quiet_hours_alternative_time",
                    "task_name": _coerce_text(
                        (pending_action.get("task") or {}).get("title"),
                    ),
                    "date": _to_date_text(
                        _first_value(
                            (pending_action.get("entities") or {}).get("new_date"),
                        ),
                    ),
                },
                user_name,
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {
                    "expected_response": "free_text",
                    "stage": "what_to_update",
                    "reason": "quiet_hours",
                },
            }

        if pending_reply_value == "yes":
            task_id = str(pending_action.get("task_id") or "")
            task_preview = pending_action.get("task") or {}
            final_entities = dict(pending_action.get("entities") or {})
            updates = dict(pending_action.get("updates") or {})
            change_summary = str(pending_action.get("change_summary") or "")
            await redis_client.set_context(
                user_id,
                _pending_payload(
                    entities=final_entities,
                    stage="confirm",
                    expected_response="yes_no",
                    task_id=task_id,
                    task=task_preview,
                    updates=updates,
                    change_summary=change_summary,
                    allow_quiet_hours_override=True,
                ),
            )
            response_text = _confirm_update_prompt(
                user_name,
                _coerce_text(task_preview.get("title")),
                change_summary,
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                final_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {
                    "expected_response": "yes_no",
                    "stage": "confirm",
                    "task_id": task_id,
                    "change_summary": change_summary,
                },
                "updates": updates,
            }

    # STEP 8+ entry point from context-manager confirmation flow.
    if (
        pending_action.get("intent") in {"update", "scheduling_update"}
        and pending_reply_type == "yes_no"
        and pending_reply_value == "yes"
        and pending_action.get("stage") == "confirm"
    ):
        return await _execute_confirmed_update(
            user_id=user_id,
            user_name=user_name,
            session_id=session_id,
            user_message=user_message,
            input_type=input_type,
            history=history,
            integrations=integrations,
            timezone_name=timezone_name,
            pending_action=pending_action,
            entities=entities,
            settings=settings,
        )

    # STEP 1: identifier entity check.
    task_id_direct = _coerce_text(_first_value(entities.get("task_id")))
    task_name = clean_task_name(_coerce_text(_first_value(entities.get("task_name"))))
    date_raw = _to_date_text(_first_value(entities.get("date")))
    priority = _normalize_priority(_first_value(entities.get("priority")))
    status = _normalize_status(_first_value(entities.get("status")))
    update_fields = extract_update_fields(entities)

    extracted_filters: Dict[str, Any] = {}
    if task_name:
        extracted_filters["task_name"] = task_name
    if date_raw:
        extracted_filters["date"] = date_raw
    if priority:
        extracted_filters["priority"] = priority
    if status:
        extracted_filters["status"] = status

    if not extracted_filters and not task_id_direct:
        await redis_client.set_context(
            user_id,
            _pending_payload(
                entities=update_fields,
                stage="identify",
                expected_response="free_text",
                missing_entity="task_name",
            ),
        )
        response_text = _missing_identifier_prompt(user_name, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_update",
            entities,
        )
        return {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "free_text",
                "missing_entity": "task_name",
                "stage": "identify",
            },
        }

    # STEP 2: date resolution for identifier entities.
    resolved_filters = dict(extracted_filters)
    query_filters: Dict[str, Any] = {}
    if date_raw:
        resolved_date, date_range = await _resolve_identifier_date(date_raw, timezone_name)
        if not resolved_date or not date_range:
            pending_entities = dict(extracted_filters)
            pending_entities.pop("date", None)
            pending_entities.update(update_fields)
            if task_id_direct:
                pending_entities["task_id"] = task_id_direct

            await redis_client.set_context(
                user_id,
                _pending_payload(
                    entities=pending_entities,
                    stage="identify",
                    expected_response="free_text",
                    missing_entity="date",
                ),
            )
            response_text = _invalid_identifier_date_prompt(user_name, date_raw, history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {
                    "expected_response": "free_text",
                    "missing_entity": "date",
                    "stage": "identify",
                },
            }

        resolved_filters["date"] = resolved_date
        query_filters["date_range"] = date_range

    if task_name:
        query_filters["task_name"] = task_name
    if priority:
        query_filters["priority"] = priority
    if status:
        query_filters["status"] = status

    combined_entities = dict(resolved_filters)
    combined_entities.update(update_fields)
    if task_id_direct:
        combined_entities["task_id"] = task_id_direct

    # STEP 3: query tasks.
    if task_id_direct:
        task_by_id = await get_task_by_id(task_id_direct, user_id)
        matches = [task_by_id] if task_by_id else []
    else:
        matches = await find_tasks_for_update(
            user_id,
            query_filters,
            timezone_name=timezone_name,
        )

    # STEP 4: handle result count.
    match_count = len(matches)
    if match_count == 0:
        response_text = _not_found_prompt(user_name, resolved_filters or combined_entities, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_update",
            combined_entities,
        )
        return {
            "status": "not_found",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
            "match_count": 0,
        }

    if 2 <= match_count <= 5:
        task_ids: List[str] = []
        task_list: List[Dict[str, Any]] = []
        for task in matches:
            task_id = _coerce_text(task.get("_id"))
            if not task_id:
                continue
            task_ids.append(task_id)
            task_list.append(_task_preview(task, timezone_name))

        if not task_ids:
            response_text = _not_found_prompt(user_name, resolved_filters or combined_entities, history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "not_found",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "match_count": 0,
            }

        await redis_client.set_context(
            user_id,
            _pending_payload(
                entities=combined_entities,
                stage="identify",
                expected_response="number",
                task_ids=task_ids,
                tasks=task_list,
            ),
        )
        response_text = _multi_list_prompt(user_name, task_list, timezone_name, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_update",
            combined_entities,
        )
        return {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "number",
                "stage": "identify",
                "task_count": len(task_ids),
            },
        }

    if match_count >= 6:
        response_text = _too_broad_prompt(user_name, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_update",
            combined_entities,
        )
        return {
            "status": "too_broad",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
            "match_count": match_count,
        }

    # Single match: proceed.
    matched_task = matches[0]
    selected_task = _task_preview(matched_task, timezone_name)
    selected_task_id = _coerce_text(selected_task.get("task_id")) or task_id_direct
    selected_task["task_id"] = selected_task_id

    if not selected_task_id:
        response_text = _not_found_prompt(user_name, resolved_filters or combined_entities, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_update",
            combined_entities,
        )
        return {
            "status": "not_found",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
            "match_count": 0,
        }

    combined_entities["task_id"] = selected_task_id
    if not combined_entities.get("task_name"):
        combined_entities["task_name"] = selected_task.get("title")

    # STEP 5: check update fields.
    if not update_fields:
        await _set_what_to_update_context(
            user_id=user_id,
            entities=combined_entities,
            task_id=selected_task_id,
            task_preview=selected_task,
        )
        response_text = _ask_what_to_update_prompt(
            user_name,
            selected_task.get("title") or task_name,
            history,
        )
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_update",
            combined_entities,
        )
        return {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "free_text",
                "stage": "what_to_update",
                "task_id": selected_task_id,
            },
        }

    # STEP 6: validate update fields.
    normalized_updates_for_entities: Dict[str, Any] = {}
    update_data: Dict[str, Any] = {}
    current_status = _normalize_status(matched_task.get("status"))
    current_due_utc = _coerce_datetime(matched_task.get("due_datetime"))
    local_due = utc_naive_to_local(current_due_utc, timezone_name) if current_due_utc else None
    local_date = local_due.strftime("%Y-%m-%d") if local_due else None
    local_time = local_due.strftime("%H:%M:%S") if local_due else None
    current_duration = int(matched_task.get("duration") or 120)

    if "new_title" in update_fields:
        new_title = _coerce_text(update_fields.get("new_title"))
        if new_title:
            normalized_updates_for_entities["new_title"] = new_title
            update_data["title"] = new_title

    if "new_priority" in update_fields:
        new_priority = _normalize_priority(update_fields.get("new_priority"))
        if not new_priority:
            new_priority = resolve_enum_fallback(
                _coerce_text(update_fields.get("new_priority")),
                ["low", "medium", "high"],
                eva_prompt="What priority would you like?",
                kind="priority",
                deterministic_miss="normalize_miss",
            )
        if not new_priority:
            await _set_what_to_update_context(
                user_id=user_id,
                entities=combined_entities,
                task_id=selected_task_id,
                task_preview=selected_task,
                remove_keys=["new_priority"],
            )
            response_text = _invalid_priority_prompt(
                user_name,
                _coerce_text(update_fields.get("new_priority")),
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {"expected_response": "free_text", "stage": "what_to_update"},
            }
        normalized_updates_for_entities["new_priority"] = new_priority
        update_data["priority"] = new_priority

    if "new_status" in update_fields:
        new_status = _normalize_status(update_fields.get("new_status"))
        if not new_status:
            new_status = resolve_enum_fallback(
                _coerce_text(update_fields.get("new_status")),
                ["pending", "ongoing", "complete"],
                eva_prompt="What status would you like?",
                kind="status",
                deterministic_miss="normalize_miss",
            )
        if not new_status:
            await _set_what_to_update_context(
                user_id=user_id,
                entities=combined_entities,
                task_id=selected_task_id,
                task_preview=selected_task,
                remove_keys=["new_status"],
            )
            response_text = _invalid_status_prompt(
                user_name,
                _coerce_text(update_fields.get("new_status")),
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {"expected_response": "free_text", "stage": "what_to_update"},
            }

        if current_status == "complete" and new_status != "complete":
            response_text = _status_locked_prompt(user_name, _coerce_text(matched_task.get("title")), history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "blocked",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
            }

        if current_status == "complete" and new_status == "complete":
            response_text = _already_complete_prompt(user_name, _coerce_text(matched_task.get("title")), history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "blocked",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
            }

        normalized_updates_for_entities["new_status"] = new_status
        update_data["status"] = new_status

    if "new_duration" in update_fields:
        parsed_duration = await _parse_duration_minutes(update_fields.get("new_duration"))
        if parsed_duration is None:
            await _set_what_to_update_context(
                user_id=user_id,
                entities=combined_entities,
                task_id=selected_task_id,
                task_preview=selected_task,
                remove_keys=["new_duration"],
            )
            response_text = _invalid_duration_prompt(
                user_name,
                _coerce_text(update_fields.get("new_duration")),
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {"expected_response": "free_text", "stage": "what_to_update"},
            }
        normalized_updates_for_entities["new_duration"] = parsed_duration
        update_data["duration"] = parsed_duration

    has_new_date = "new_date" in update_fields
    has_new_time = "new_time" in update_fields
    if has_new_date or has_new_time:
        resolved_new_date = local_date
        resolved_new_time = local_time

        if has_new_date:
            resolved_new_date = await _resolve_update_date(update_fields.get("new_date"), timezone_name)
            if not resolved_new_date:
                await _set_what_to_update_context(
                    user_id=user_id,
                    entities=combined_entities,
                    task_id=selected_task_id,
                    task_preview=selected_task,
                    remove_keys=["new_date"],
                )
                response_text = _invalid_new_date_prompt(
                    user_name,
                    _coerce_text(update_fields.get("new_date")),
                    history,
                )
                await _save_turn(
                    session_id,
                    user_message,
                    response_text,
                    input_type,
                    "scheduling_update",
                    combined_entities,
                )
                return {
                    "status": "pending",
                    "intent": "scheduling_update",
                    "response_text": response_text,
                    "notifications": [],
                    "pending": {"expected_response": "free_text", "stage": "what_to_update"},
                }
            normalized_updates_for_entities["new_date"] = resolved_new_date

        if has_new_time:
            resolved_new_time = await _resolve_update_time(update_fields.get("new_time"), timezone_name)
            if not resolved_new_time:
                await _set_what_to_update_context(
                    user_id=user_id,
                    entities=combined_entities,
                    task_id=selected_task_id,
                    task_preview=selected_task,
                    remove_keys=["new_time"],
                )
                response_text = _invalid_new_time_prompt(
                    user_name,
                    _coerce_text(update_fields.get("new_time")),
                    history,
                )
                await _save_turn(
                    session_id,
                    user_message,
                    response_text,
                    input_type,
                    "scheduling_update",
                    combined_entities,
                )
                return {
                    "status": "pending",
                    "intent": "scheduling_update",
                    "response_text": response_text,
                    "notifications": [],
                    "pending": {"expected_response": "free_text", "stage": "what_to_update"},
                }
            normalized_updates_for_entities["new_time"] = resolved_new_time

        if not resolved_new_date or not resolved_new_time:
            await _set_what_to_update_context(
                user_id=user_id,
                entities=combined_entities,
                task_id=selected_task_id,
                task_preview=selected_task,
            )
            response_text = _invalid_new_time_prompt(
                user_name,
                _coerce_text(update_fields.get("new_time")) or "that time",
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {"expected_response": "free_text", "stage": "what_to_update"},
            }

        candidate_due_utc = local_datetime_to_utc_naive(
            resolved_new_date,
            resolved_new_time,
            timezone_name,
        )
        if candidate_due_utc is None:
            await _set_what_to_update_context(
                user_id=user_id,
                entities=combined_entities,
                task_id=selected_task_id,
                task_preview=selected_task,
            )
            response_text = _invalid_new_time_prompt(
                user_name,
                _coerce_text(update_fields.get("new_time")),
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {"expected_response": "free_text", "stage": "what_to_update"},
            }

        # Never allow rescheduling into the past (mirrors scheduling add Step 3.5).
        now_utc = _utc_now_naive()
        if candidate_due_utc <= now_utc:
            local_due = utc_naive_to_local(candidate_due_utc, timezone_name)
            local_now = utc_naive_to_local(now_utc, timezone_name)
            ask_for_time_only = bool(
                local_due
                and local_now
                and local_due.date() == local_now.date()
            )
            task_title = _coerce_text(matched_task.get("title"))

            if ask_for_time_only:
                await _set_what_to_update_context(
                    user_id=user_id,
                    entities={**combined_entities, **normalized_updates_for_entities},
                    task_id=selected_task_id,
                    task_preview=selected_task,
                    remove_keys=["new_time"],
                )
                if user_name:
                    response_text = (
                        f"That time has already passed today, {user_name}. "
                        f"What future time should I use for {task_title} on "
                        f"{_format_date_display(resolved_new_date)}?"
                    )
                else:
                    response_text = (
                        f"That time has already passed today. What future time should I use "
                        f"for {task_title} on {_format_date_display(resolved_new_date)}?"
                    )
            else:
                await _set_what_to_update_context(
                    user_id=user_id,
                    entities={**combined_entities, **normalized_updates_for_entities},
                    task_id=selected_task_id,
                    task_preview=selected_task,
                    remove_keys=["new_date"],
                )
                if user_name:
                    response_text = (
                        f"I cannot schedule {task_title} in the past, {user_name}. "
                        "Please share a future date."
                    )
                else:
                    response_text = (
                        f"I cannot schedule {task_title} in the past. "
                        "Please share a future date."
                    )

            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {
                    "expected_response": "free_text",
                    "stage": "what_to_update",
                    "reason": "past_datetime",
                },
            }

        overlap_duration = int(update_data.get("duration") or current_duration)
        learning_slot_conflicts = find_task_conflicts_from_settings(
            candidate_due_utc,
            overlap_duration,
            settings,
            timezone_name=timezone_name,
        )
        if learning_slot_conflicts:
            await _set_what_to_update_context(
                user_id=user_id,
                entities={**combined_entities, **normalized_updates_for_entities},
                task_id=selected_task_id,
                task_preview=selected_task,
            )
            response_text = format_learning_schedule_conflict_message(
                learning_slot_conflicts,
                user_name=user_name,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "conflict",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {"expected_response": "free_text", "stage": "what_to_update"},
            }

        allow_quiet_hours_override = bool(
            pending_context.get("allow_quiet_hours_override")
            or pending_action.get("allow_quiet_hours_override"),
        )
        quiet_hour_matches: List[Dict[str, str]] = []
        if not allow_quiet_hours_override:
            quiet_hour_matches = find_quiet_hour_matches(
                settings,
                resolved_new_time,
                overlap_duration,
            )

        if quiet_hour_matches:
            update_data_with_due = dict(update_data)
            update_data_with_due["due_datetime"] = candidate_due_utc
            change_summary = _build_change_summary(
                matched_task,
                update_data_with_due,
                timezone_name,
            )
            final_entities_for_quiet = dict(combined_entities)
            final_entities_for_quiet.update(normalized_updates_for_entities)
            final_entities_for_quiet["task_id"] = selected_task_id
            await redis_client.set_context(
                user_id,
                _pending_payload(
                    entities=final_entities_for_quiet,
                    stage="quiet_hours",
                    expected_response="yes_no",
                    task_id=selected_task_id,
                    task=selected_task,
                    updates=_serialize_updates_for_context(update_data_with_due),
                    change_summary=change_summary,
                    pending_reason="quiet_hours",
                    quiet_hour_matches=quiet_hour_matches,
                ),
            )
            response_text = gemini_service.generate_reply(
                {
                    "action": "quiet_hours_conflict",
                    "task_name": _coerce_text(matched_task.get("title")),
                    "date": resolved_new_date,
                    "time": resolved_new_time,
                    "quiet_hours": format_quiet_hour_labels(quiet_hour_matches),
                },
                user_name,
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {
                    "expected_response": "yes_no",
                    "stage": "quiet_hours",
                    "reason": "quiet_hours",
                    "quiet_hour_matches": quiet_hour_matches,
                },
            }

        has_conflict = await check_update_overlap(
            user_id,
            selected_task_id,
            candidate_due_utc,
            overlap_duration,
        )
        if has_conflict:
            await _set_what_to_update_context(
                user_id=user_id,
                entities={**combined_entities, **normalized_updates_for_entities},
                task_id=selected_task_id,
                task_preview=selected_task,
            )
            response_text = _overlap_conflict_prompt(
                user_name,
                _coerce_text(matched_task.get("title")),
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_update",
                combined_entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_update",
                "response_text": response_text,
                "notifications": [],
                "pending": {"expected_response": "free_text", "stage": "what_to_update"},
            }

        update_data["due_datetime"] = candidate_due_utc

    update_data = _remove_noop_updates(matched_task, update_data)
    if not update_data:
        await _set_what_to_update_context(
            user_id=user_id,
            entities=combined_entities,
            task_id=selected_task_id,
            task_preview=selected_task,
        )
        response_text = _no_changes_prompt(
            user_name,
            _coerce_text(matched_task.get("title")),
            history,
        )
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_update",
            combined_entities,
        )
        return {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": response_text,
            "notifications": [],
            "pending": {"expected_response": "free_text", "stage": "what_to_update"},
        }

    # STEP 7: build confirmation and set Redis.
    final_entities_for_confirm = dict(combined_entities)
    final_entities_for_confirm.update(normalized_updates_for_entities)
    final_entities_for_confirm["task_id"] = selected_task_id
    change_summary = _build_change_summary(matched_task, update_data, timezone_name)

    await redis_client.set_context(
        user_id,
        _pending_payload(
            entities=final_entities_for_confirm,
            stage="confirm",
            expected_response="yes_no",
            task_id=selected_task_id,
            task=selected_task,
            updates=_serialize_updates_for_context(update_data),
            change_summary=change_summary,
        ),
    )

    response_text = _confirm_update_prompt(
        user_name,
        _coerce_text(matched_task.get("title")),
        change_summary,
        history,
    )
    await _save_turn(
        session_id,
        user_message,
        response_text,
        input_type,
        "scheduling_update",
        final_entities_for_confirm,
    )
    return {
        "status": "pending",
        "intent": "scheduling_update",
        "response_text": response_text,
        "notifications": [],
        "pending": {
            "expected_response": "yes_no",
            "stage": "confirm",
            "task_id": selected_task_id,
            "change_summary": change_summary,
        },
        "updates": _serialize_updates_for_context(update_data),
    }
