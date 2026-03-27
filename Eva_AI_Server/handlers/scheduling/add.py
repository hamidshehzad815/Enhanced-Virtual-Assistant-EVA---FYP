"""
Phase 9 scheduling add handler.
Implements required-entity prompts, behavioral suggestion, duplicate checks,
time-overlap protection, and final task creation with history/session updates.
"""
from datetime import datetime, timedelta, timezone as dt_timezone
import re
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from config.database import get_db
from context.redis_client import redis_client
from db.activity_logs import count_completed, get_best_hour, insert_log
from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.tasks import find_duplicate, find_overlapping_task, insert_task, update_task
from services.duckling import duckling_client
from services.gemini import gemini_service
from services.google_calendar import google_calendar_client
from utils.timezone_utils import (
    local_datetime_to_utc_naive,
    resolve_timezone_name,
    utc_naive_to_local,
)


def _to_object_id(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))
    except Exception:
        return value


def _owner_variants(owner_id: str) -> List[Any]:
    owner_object_id = _to_object_id(owner_id)
    values = [owner_object_id]
    if owner_object_id != owner_id:
        values.append(owner_id)
    return values


def _first_value(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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

    # Normalize common ISO/time variants (including milliseconds/timezone)
    # to strict HH:MM:SS used by downstream parsing.
    iso_time_match = re.search(r"(\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$", raw)
    if iso_time_match:
        return iso_time_match.group(1)

    if re.match(r"^\d{2}:\d{2}$", raw):
        return f"{raw}:00"
    if re.match(r"^\d{2}:\d{2}:\d{2}$", raw):
        return raw
    if "T" in raw and re.match(r"^\d{4}-\d{2}-\d{2}T", raw):
        time_part = raw.split("T", 1)[1]
        normalized = _to_time_text(time_part)
        if normalized:
            return normalized

    # Accept time fragments inside longer text when already in 24h format.
    fragment_match = re.search(r"\b(\d{2}:\d{2}(?::\d{2})?)\b", raw)
    if fragment_match:
        fragment = fragment_match.group(1)
        return fragment if len(fragment) == 8 else f"{fragment}:00"

    # Fallback for casual 12-hour forms inside longer text, e.g. "at 5pm".
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


def _normalize_priority(value: Any, default_priority: str = "medium") -> str:
    raw = _coerce_text(_first_value(value)).lower()
    if raw in {"low", "medium", "high"}:
        return raw
    return default_priority


def _format_time_display(time_str: str) -> str:
    try:
        dt = datetime.strptime(time_str[:8], "%H:%M:%S")
        return dt.strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return time_str


def _format_date_display(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%A, %d %b %Y")
    except ValueError:
        return date_str


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value

    raw = _coerce_text(value)
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _format_time_range(start_value: Any, duration_minutes: Any, timezone_name: str) -> str:
    start_dt = utc_naive_to_local(start_value, timezone_name)
    if start_dt is None:
        return ""

    duration = max(1, int(duration_minutes or 0))
    end_dt = start_dt + timedelta(minutes=duration)
    start_text = _format_time_display(start_dt.strftime("%H:%M:%S"))
    end_text = _format_time_display(end_dt.strftime("%H:%M:%S"))
    return f"{start_text} to {end_text}"


def _parse_duration_minutes(value: Any, default_minutes: int) -> int:
    if value is None:
        return int(default_minutes)

    first = _first_value(value)
    if isinstance(first, int):
        return max(5, first)
    if isinstance(first, float):
        return max(5, int(first))

    raw = _coerce_text(first).lower()
    if not raw:
        return int(default_minutes)

    # Simple fallback parser in case Duckling duration parsing is unavailable.
    number_match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not number_match:
        return int(default_minutes)

    amount = float(number_match.group(1))
    if "hour" in raw:
        return max(5, int(amount * 60))
    return max(5, int(amount))


def _parse_clock_minutes(value: Any) -> Optional[int]:
    raw = _coerce_text(value)
    if not raw:
        return None

    match = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", raw)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    return hour * 60 + minute


def _normalize_quiet_hour_blocks(settings: Dict[str, Any]) -> List[Dict[str, str]]:
    has_quiet_hours = bool(
        settings.get("has_quiet_hours")
        or settings.get("quiet_hours_enabled")
    )
    if not has_quiet_hours:
        return []

    blocks: List[Dict[str, str]] = []
    for block in settings.get("quiet_hours") or []:
        if not isinstance(block, dict):
            continue

        if block.get("enabled") is False:
            continue

        start = _coerce_text(block.get("start"))
        end = _coerce_text(block.get("end"))
        if _parse_clock_minutes(start) is None or _parse_clock_minutes(end) is None:
            continue

        label = _coerce_text(block.get("label")) or "quiet hours"
        blocks.append(
            {
                "label": label,
                "start": start,
                "end": end,
            }
        )

    if blocks:
        return blocks

    legacy_start = _coerce_text(settings.get("quiet_hours_start"))
    legacy_end = _coerce_text(settings.get("quiet_hours_end"))
    if (
        _parse_clock_minutes(legacy_start) is not None
        and _parse_clock_minutes(legacy_end) is not None
    ):
        return [
            {
                "label": "quiet hours",
                "start": legacy_start,
                "end": legacy_end,
            }
        ]

    return []


def _find_quiet_hour_matches(
    settings: Dict[str, Any],
    time_value: str,
) -> List[Dict[str, str]]:
    task_minutes = _parse_clock_minutes(time_value)
    if task_minutes is None:
        return []

    matches: List[Dict[str, str]] = []
    for block in _normalize_quiet_hour_blocks(settings):
        start_minutes = _parse_clock_minutes(block.get("start"))
        end_minutes = _parse_clock_minutes(block.get("end"))
        if start_minutes is None or end_minutes is None:
            continue

        if start_minutes == end_minutes:
            in_block = True
        elif start_minutes < end_minutes:
            in_block = start_minutes <= task_minutes < end_minutes
        else:
            in_block = task_minutes >= start_minutes or task_minutes < end_minutes

        if in_block:
            matches.append(block)

    return matches


def _format_quiet_hour_labels(blocks: List[Dict[str, str]]) -> str:
    labels = []
    for block in blocks:
        label = _coerce_text(block.get("label")).replace("_", " ")
        if label:
            labels.append(label)

    if not labels:
        return "quiet hours"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _split_collaborators(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        items = value
    else:
        text = _coerce_text(value)
        if not text:
            return []
        items = re.split(r",|\band\b", text, flags=re.IGNORECASE)

    cleaned: List[str] = []
    seen = set()
    for item in items:
        name = _coerce_text(item)
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
    return cleaned


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
        # Conversation save failures should not block the main action result.
        print(f"[AddHandler] Failed to save conversation turn: {error}")


async def _resolve_date_time(
    entities: Dict[str, Any],
    timezone: str,
) -> Tuple[Optional[str], Optional[str]]:
    date_text = _to_date_text(_first_value(entities.get("date")))
    time_text = _to_time_text(_first_value(entities.get("time")))

    if date_text and not re.match(r"^\d{4}-\d{2}-\d{2}$", date_text):
        resolved = await duckling_client.resolve_date(date_text, timezone=timezone)
        if resolved:
            date_text = resolved

    if time_text and not re.match(r"^\d{2}:\d{2}:\d{2}$", time_text):
        resolved = await duckling_client.resolve_time(time_text, timezone=timezone)
        if resolved:
            time_text = resolved

    if time_text:
        normalized_time = _to_time_text(time_text)
        if normalized_time:
            time_text = normalized_time

    if date_text and not re.match(r"^\d{4}-\d{2}-\d{2}$", date_text):
        return None, time_text or None

    if time_text and not re.match(r"^\d{2}:\d{2}:\d{2}$", time_text):
        return date_text or None, None

    return date_text or None, time_text or None


async def _find_and_validate_collaborators(owner_id: str, collaborator_names: List[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not collaborator_names:
        return [], None

    if len(collaborator_names) > 2:
        return [], "I can only add up to 2 collaborators for one task."

    db = get_db()
    owner_values = _owner_variants(owner_id)
    validated: List[Dict[str, Any]] = []

    for name in collaborator_names:
        username_candidate = name.lower().replace(" ", "")
        user_doc = await db.users.find_one(
            {
                "$or": [
                    {"username": {"$regex": f"^{re.escape(username_candidate)}$", "$options": "i"}},
                    {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}},
                ],
                "is_active": True,
            },
            {"_id": 1, "name": 1, "username": 1},
        )

        if not user_doc:
            return [], f"I could not find {name} in your friends list."

        friend_values = _owner_variants(str(user_doc["_id"]))
        friendship = await db.friends.find_one(
            {
                "$or": [
                    {
                        "requester_id": {"$in": owner_values},
                        "recipient_id": {"$in": friend_values},
                    },
                    {
                        "requester_id": {"$in": friend_values},
                        "recipient_id": {"$in": owner_values},
                    },
                ],
                "status": "accepted",
            },
            {"_id": 1},
        )

        if not friendship:
            display_name = user_doc.get("name") or name
            return [], f"{display_name} is not in your friends list. Add them as a friend first."

        validated.append(
            {
                "user_id": user_doc["_id"],
                "status": "pending",
                "name": user_doc.get("name") or user_doc.get("username") or name,
            }
        )

    return validated, None


def _pending_payload(intent: str, entities: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "pending_action": {
            "intent": intent,
            "entities": entities,
        }
    }
    payload.update(extra)
    return payload


def _pick_active_google_integration(integrations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for integration in integrations:
        if not isinstance(integration, dict):
            continue

        provider = str(integration.get("provider") or "").lower()
        is_active = integration.get("is_active") is True
        if provider == "google_calendar" and is_active:
            return integration

    return None


async def handle_scheduling_add(
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
    integrations = context.get("integrations") or []
    user_message = str(context.get("message") or "")
    input_type = str(context.get("input_type") or "text")

    user_name = user.get("name")
    timezone = resolve_timezone_name(user.get("timezone"))

    pending_context = context.get("pending_context") or {}
    pending_action = pending_context.get("pending_action") or {}
    pending_reply_type = context.get("pending_reply_type")
    pending_reply_value = context.get("pending_reply_value")
    pending_reason = _coerce_text(pending_context.get("pending_reason"))

    force_duplicate = False
    allow_quiet_hours_override = False
    scheduled_by = "manual"

    # Resume from pending yes/no and number replies before the normal add flow.
    if pending_action.get("intent") in {"add", "scheduling_add"}:
        base_entities = dict(pending_action.get("entities") or {})
        base_entities.update(entities)
        entities = base_entities

        if pending_reply_type == "yes_no":
            if pending_reason == "quiet_hours":
                if pending_reply_value == "no":
                    pending_entities = dict(entities)
                    pending_entities.pop("time", None)
                    await redis_client.set_context(
                        user_id,
                        _pending_payload(
                            "add",
                            pending_entities,
                            expected_response="free_text",
                            missing_entity="time",
                        ),
                    )
                    response_text = gemini_service.generate_reply(
                        {
                            "action": "quiet_hours_alternative_time",
                            "task_name": _coerce_text(
                                _first_value(pending_entities.get("task_name"))
                            ),
                            "date": _format_date_display(
                                _to_date_text(_first_value(pending_entities.get("date")))
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
                        "scheduling_add",
                        entities,
                    )
                    return {
                        "status": "pending",
                        "intent": "scheduling_add",
                        "response_text": response_text,
                        "notifications": [],
                        "pending": {
                            "expected_response": "free_text",
                            "missing_entity": "time",
                        },
                    }

                if pending_reply_value == "yes":
                    allow_quiet_hours_override = True
                    await redis_client.delete_context(user_id)
            else:
                if pending_reply_value == "no":
                    await redis_client.delete_context(user_id)
                    response_text = gemini_service.generate_reply(
                        {"action": "cancelled"},
                        user_name,
                        history,
                    )
                    await _save_turn(
                        session_id,
                        user_message,
                        response_text,
                        input_type,
                        "scheduling_add",
                        entities,
                    )
                    return {
                        "status": "cancelled",
                        "intent": "scheduling_add",
                        "response_text": response_text,
                        "notifications": [],
                    }

                if pending_reply_value == "yes":
                    force_duplicate = True
                    await redis_client.delete_context(user_id)

        if pending_reply_type == "number":
            if pending_reply_value == 1:
                suggested_time = _coerce_text(pending_context.get("suggested_time"))
                if suggested_time:
                    entities["time"] = suggested_time
                    scheduled_by = "behavioral_analytics"
                await redis_client.delete_context(user_id)
            elif pending_reply_value == 2:
                pending_entities = dict(entities)
                pending_entities.pop("time", None)
                await redis_client.set_context(
                    user_id,
                    _pending_payload(
                        "add",
                        pending_entities,
                        expected_response="free_text",
                        missing_entity="time",
                    ),
                )
                response_text = gemini_service.generate_reply(
                    {"action": "missing_time"},
                    user_name,
                    history,
                )
                await _save_turn(
                    session_id,
                    user_message,
                    response_text,
                    input_type,
                    "scheduling_add",
                    entities,
                )
                return {
                    "status": "pending",
                    "intent": "scheduling_add",
                    "response_text": response_text,
                    "notifications": [],
                    "pending": {
                        "expected_response": "free_text",
                        "missing_entity": "time",
                    },
                }

    # Step 1: required entity check in order: task_name -> date -> time.
    task_name = _coerce_text(_first_value(entities.get("task_name")))
    if not task_name:
        pending_entities = dict(entities)
        pending_entities.pop("task_name", None)
        await redis_client.set_context(
            user_id,
            _pending_payload(
                "add",
                pending_entities,
                expected_response="free_text",
                missing_entity="task_name",
            ),
        )
        response_text = gemini_service.generate_reply(
            {"action": "missing_task_name"},
            user_name,
            history,
        )
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_add", entities)
        return {
            "status": "pending",
            "intent": "scheduling_add",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "free_text",
                "missing_entity": "task_name",
            },
        }

    date_value, time_value = await _resolve_date_time(entities, timezone)

    if not date_value:
        pending_entities = dict(entities)
        pending_entities["task_name"] = task_name
        pending_entities.pop("date", None)
        await redis_client.set_context(
            user_id,
            _pending_payload(
                "add",
                pending_entities,
                expected_response="free_text",
                missing_entity="date",
            ),
        )
        response_text = gemini_service.generate_reply(
            {"action": "missing_date", "task_name": task_name},
            user_name,
            history,
        )
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_add", entities)
        return {
            "status": "pending",
            "intent": "scheduling_add",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "free_text",
                "missing_entity": "date",
            },
        }

    default_duration = int(settings.get("default_task_duration", 120))
    duration_minutes = _parse_duration_minutes(entities.get("duration"), default_duration)
    default_priority = _normalize_priority(settings.get("default_task_priority", "medium"), "medium")
    priority = _normalize_priority(entities.get("priority"), default_priority)

    # Step 3: time resolution and behavioral suggestion fallback.
    if not time_value:
        threshold = int(settings.get("analytics_min_tasks_threshold", 10))
        total_completed = await count_completed(user_id)

        if total_completed >= threshold:
            weekday = datetime.strptime(date_value, "%Y-%m-%d").weekday()
            best_hour = await get_best_hour(user_id, weekday)

            if best_hour is not None:
                chosen_hour: Optional[int] = None
                for offset in range(24):
                    candidate = (best_hour + offset) % 24
                    candidate_time = f"{candidate:02d}:00:00"
                    if _find_quiet_hour_matches(settings, candidate_time):
                        continue
                    candidate_due_datetime = local_datetime_to_utc_naive(
                        date_value,
                        candidate_time,
                        timezone,
                    )
                    if candidate_due_datetime is None:
                        continue
                    conflict = await find_overlapping_task(
                        user_id,
                        candidate_due_datetime,
                        duration_minutes,
                    )
                    if not conflict:
                        chosen_hour = candidate
                        break

                if chosen_hour is not None:
                    suggested_time = f"{chosen_hour:02d}:00:00"
                    display_time = _format_time_display(suggested_time)
                    await redis_client.set_context(
                        user_id,
                        _pending_payload(
                            "add",
                            {
                                **entities,
                                "task_name": task_name,
                                "date": date_value,
                            },
                            expected_response="number",
                            suggested_time=suggested_time,
                        ),
                    )
                    base = gemini_service.generate_reply(
                        {
                            "action": "missing_time",
                            "task_name": task_name,
                            "date": _format_date_display(date_value),
                            "suggested_time": display_time,
                        },
                        user_name,
                        history,
                    )
                    response_text = f"{base}\n1. Use {display_time}\n2. Enter a time"
                    await _save_turn(session_id, user_message, response_text, input_type, "scheduling_add", entities)
                    return {
                        "status": "pending",
                        "intent": "scheduling_add",
                        "response_text": response_text,
                        "notifications": [],
                        "pending": {
                            "expected_response": "number",
                            "suggested_time": suggested_time,
                        },
                    }

        pending_entities = {
            **entities,
            "task_name": task_name,
            "date": date_value,
        }
        pending_entities.pop("time", None)
        await redis_client.set_context(
            user_id,
            _pending_payload(
                "add",
                pending_entities,
                expected_response="free_text",
                missing_entity="time",
            ),
        )
        response_text = gemini_service.generate_reply(
            {
                "action": "missing_time",
                "task_name": task_name,
                "date": _format_date_display(date_value),
            },
            user_name,
            history,
        )
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_add", entities)
        return {
            "status": "pending",
            "intent": "scheduling_add",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "free_text",
                "missing_entity": "time",
            },
        }

    due_datetime = local_datetime_to_utc_naive(date_value, time_value, timezone)
    if due_datetime is None:
        pending_entities = {
            **entities,
            "task_name": task_name,
            "date": date_value,
        }
        pending_entities.pop("time", None)
        await redis_client.set_context(
            user_id,
            _pending_payload(
                "add",
                pending_entities,
                expected_response="free_text",
                missing_entity="time",
            ),
        )
        response_text = gemini_service.generate_reply(
            {
                "action": "missing_time",
                "task_name": task_name,
                "date": _format_date_display(date_value),
            },
            user_name,
            history,
        )
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_add",
            entities,
        )
        return {
            "status": "pending",
            "intent": "scheduling_add",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "free_text",
                "missing_entity": "time",
            },
        }

    quiet_hour_matches = []
    if not allow_quiet_hours_override:
        quiet_hour_matches = _find_quiet_hour_matches(settings, time_value)

    if quiet_hour_matches:
        await redis_client.set_context(
            user_id,
            _pending_payload(
                "add",
                {
                    **entities,
                    "task_name": task_name,
                    "date": date_value,
                    "time": time_value,
                },
                expected_response="yes_no",
                pending_reason="quiet_hours",
                quiet_hour_matches=quiet_hour_matches,
            ),
        )
        response_text = gemini_service.generate_reply(
            {
                "action": "quiet_hours_conflict",
                "task_name": task_name,
                "date": _format_date_display(date_value),
                "time": _format_time_display(time_value),
                "quiet_hours": _format_quiet_hour_labels(quiet_hour_matches),
            },
            user_name,
            history,
        )
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_add", entities)
        return {
            "status": "pending",
            "intent": "scheduling_add",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "yes_no",
                "reason": "quiet_hours",
                "quiet_hour_matches": quiet_hour_matches,
            },
        }

    # Step 4: cancel immediately if the requested window overlaps another task.
    conflicting_task = await find_overlapping_task(user_id, due_datetime, duration_minutes)
    if conflicting_task:
        conflicting_title = _coerce_text(conflicting_task.get("title")) or "another task"
        conflicting_time = _format_time_range(
            conflicting_task.get("due_datetime"),
            conflicting_task.get("duration", 120),
            timezone,
        )
        response_text = gemini_service.generate_reply(
            {
                "action": "task_time_conflict",
                "task_name": task_name,
                "date": _format_date_display(date_value),
                "time": _format_time_display(time_value),
                "conflicting_task_name": conflicting_title,
                "conflicting_time": conflicting_time,
            },
            user_name,
            history,
        )
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_add",
            entities,
        )
        return {
            "status": "conflict",
            "intent": "scheduling_add",
            "response_text": response_text,
            "notifications": [],
            "conflict": {
                "task_id": conflicting_task.get("_id"),
                "title": conflicting_title,
                "due_datetime": (
                    conflicting_task["due_datetime"].isoformat()
                    if isinstance(conflicting_task.get("due_datetime"), datetime)
                    else conflicting_task.get("due_datetime")
                ),
                "duration": conflicting_task.get("duration", 120),
            },
        }

    # Step 5: duplicate check.
    duplicate = await find_duplicate(
        user_id,
        task_name,
        date_value,
        timezone_name=timezone,
    )
    if duplicate and not force_duplicate:
        duplicate_due_datetime = utc_naive_to_local(duplicate.get("due_datetime"), timezone)
        duplicate_date_display = (
            _format_date_display(duplicate_due_datetime.strftime("%Y-%m-%d"))
            if duplicate_due_datetime
            else _format_date_display(date_value)
        )
        duplicate_time_display = (
            _format_time_display(duplicate_due_datetime.strftime("%H:%M:%S"))
            if duplicate_due_datetime
            else _format_time_display(time_value)
        )
        await redis_client.set_context(
            user_id,
            _pending_payload(
                "add",
                {
                    **entities,
                    "task_name": task_name,
                    "date": date_value,
                    "time": time_value,
                },
                expected_response="yes_no",
                pending_reason="duplicate",
            ),
        )
        response_text = gemini_service.generate_reply(
            {
                "action": "duplicate_found",
                "task_name": task_name,
                "date": duplicate_date_display,
                "time": duplicate_time_display,
                "existing_date": duplicate_date_display,
                "existing_time": duplicate_time_display,
            },
            user_name,
            history,
        )
        await _save_turn(session_id, user_message, response_text, input_type, "scheduling_add", entities)
        return {
            "status": "pending",
            "intent": "scheduling_add",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "yes_no",
            },
            "duplicate": duplicate,
        }

    # Step 6: collaborator validation.
    collaborator_names = _split_collaborators(entities.get("collaborator"))
    collaborators, collaborator_error = await _find_and_validate_collaborators(user_id, collaborator_names)
    if collaborator_error:
        await _save_turn(session_id, user_message, collaborator_error, input_type, "scheduling_add", entities)
        return {
            "status": "validation_error",
            "intent": "scheduling_add",
            "response_text": collaborator_error,
            "notifications": [],
        }

    reminder_minutes = int(settings.get("default_reminder_minutes", 30))
    now = datetime.now(dt_timezone.utc).replace(tzinfo=None)

    # Step 7: insert task.
    task_payload = {
        "owner_id": _to_object_id(user_id),
        "title": task_name,
        "due_datetime": due_datetime,
        "is_all_day": False,
        "duration": duration_minutes,
        "priority": priority,
        "status": "pending",
        "source": "eva",
        "scheduled_by": scheduled_by,
        "collaborators": [
            {
                "user_id": collaborator["user_id"],
                "status": collaborator["status"],
            }
            for collaborator in collaborators
        ],
        "is_deleted": False,
        "reminder_minutes_before": reminder_minutes,
        "created_at": now,
        "updated_at": now,
    }
    task_id = await insert_task(task_payload)

    # Step 8: insert activity log.
    await insert_log(
        {
            "user_id": _to_object_id(user_id),
            "task_id": _to_object_id(task_id),
            "action_type": "task_created",
            "action_timestamp": now,
            "day_of_week": due_datetime.weekday(),
            "hour_of_day": due_datetime.hour,
            "week_number": due_datetime.isocalendar().week,
            "task_priority": priority,
            "subject": task_name,
            "source": "scheduling_module",
            "scheduled_hour": due_datetime.hour,
            "scheduled_day": due_datetime.weekday(),
        }
    )

    # Step 9: Google Calendar sync (non-blocking).
    calendar_synced = False
    google_integration = _pick_active_google_integration(integrations)
    if google_integration:
        access_token = _coerce_text(google_integration.get("access_token"))
        calendar_id = _coerce_text(google_integration.get("calendar_id")) or "primary"

        if access_token:
            event_id = await google_calendar_client.create_event(
                token=access_token,
                calendar_id=calendar_id,
                task_data={
                    "title": task_name,
                    "due_datetime": due_datetime,
                    "duration_minutes": duration_minutes,
                    "timezone": timezone,
                    "description": f"Priority: {priority}",
                },
            )

            if event_id:
                calendar_synced = True
                updated = await update_task(
                    task_id,
                    {
                        "google_calendar_event_id": event_id,
                    },
                )
                if not updated:
                    print(
                        "[AddHandler] Google event created but task update failed "
                        f"for task_id={task_id}"
                    )

    # Step 10: natural reply.
    response_text = gemini_service.generate_reply(
        {
            "action": "task_added",
            "task_name": task_name,
            "date": _format_date_display(date_value),
            "time": _format_time_display(time_value),
            "priority": priority,
            "scheduled_by": scheduled_by,
            "calendar_synced": calendar_synced,
            "collaborator": [c["name"] for c in collaborators] if collaborators else None,
        },
        user_name,
        history,
    )

    # Step 11: save conversation messages and update chat session metadata.
    await _save_turn(
        session_id,
        user_message,
        response_text,
        input_type,
        "scheduling_add",
        {
            "task_name": task_name,
            "date": date_value,
            "time": time_value,
            "priority": priority,
            "duration": duration_minutes,
            "collaborator": collaborator_names,
        },
    )

    # Step 12: minimal response with notification payload.
    scheduled_date_display = _format_date_display(date_value)
    scheduled_time_display = _format_time_display(time_value)

    notifications = [
        {
            "user_id": str(user_id),
            "sender_id": None,
            "type": "task_scheduled",
            "reference_type": "task",
            "reference_id": str(task_id),
            "title": "Task scheduled",
            "message": (
                f"{task_name} is scheduled for {scheduled_date_display} at "
                f"{scheduled_time_display}."
            ),
            "action_required": False,
            "delivery_channel": ["in_app", "email"],
        }
    ]

    for collaborator in collaborators:
        notifications.append(
            {
                "user_id": str(collaborator["user_id"]),
                "sender_id": str(user_id),
                "type": "collaboration_invite",
                "reference_type": "task",
                "reference_id": str(task_id),
                "title": "Collaboration invite",
                "message": f"{user_name or 'Your friend'} added you to {task_name}",
                "action_required": True,
                "delivery_channel": ["push", "in_app"],
            }
        )

    return {
        "status": "success",
        "intent": "scheduling_add",
        "response_text": response_text,
        "task": {
            "task_id": task_id,
            "title": task_name,
            "due_datetime": due_datetime.isoformat(),
            "priority": priority,
            "duration": duration_minutes,
            "scheduled_by": scheduled_by,
        },
        "notifications": notifications,
    }
