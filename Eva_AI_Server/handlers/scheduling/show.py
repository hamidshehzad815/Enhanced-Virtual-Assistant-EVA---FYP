"""
Phase 21 scheduling show handler.
Implements read-only task listing with optional date/priority/status/task_name filters.
"""
from datetime import datetime, time, timedelta, timezone as dt_timezone
import re
from typing import Any, Dict, List, Optional, Tuple

from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.tasks import find_tasks_for_show
from services.duckling import duckling_client
from services.gemini import gemini_service
from utils.date_utils import build_date_range, convert_tasks_to_local
from utils.task_value_normalizer import canonicalize_priority, canonicalize_status, clean_task_name
from utils.timezone_utils import get_zoneinfo, resolve_timezone_name


_TASK_NAME_GENERIC_WORDS = {
    "task",
    "tasks",
    "todo",
    "todos",
    "item",
    "items",
    "schedule",
    "scheduled",
    "plan",
    "plans",
}

_WEEK_SCOPE_PATTERN = re.compile(r"\b(this|next|last|previous)\s+weeks?\b", flags=re.IGNORECASE)
_WEEKDAY_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    flags=re.IGNORECASE,
)


def _first_value(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_priority(value: Any) -> str:
    return canonicalize_priority(value)


def _normalize_status(value: Any) -> str:
    return canonicalize_status(value)


def _filters_summary(filters_used: Dict[str, Any], overdue_only: bool) -> str:
    if overdue_only:
        return "overdue pending tasks"

    parts: List[str] = []
    date_label = _coerce_text(filters_used.get("date"))
    if date_label:
        parts.append(f"date {date_label}")

    task_name = _coerce_text(filters_used.get("task_name"))
    if task_name:
        parts.append(f'task name "{task_name}"')

    priority = _coerce_text(filters_used.get("priority"))
    if priority:
        parts.append(f"priority {priority}")

    status = _coerce_text(filters_used.get("status"))
    if status:
        parts.append(f"status {status}")

    if not parts:
        return "upcoming tasks"

    return ", ".join(parts)


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


def _fallback_due_text(task: Dict[str, Any]) -> str:
    due_dt = _coerce_datetime(task.get("due_datetime"))
    if due_dt is None:
        return "its scheduled time"
    return due_dt.strftime("%A, %d %b %Y at %I:%M %p").replace(" 0", " ")


def _task_line(task: Dict[str, Any], include_date: bool) -> str:
    title = _coerce_text(task.get("title")) or "Untitled task"
    priority = _coerce_text(task.get("priority")).lower() or "medium"
    local_date = _coerce_text(task.get("local_date_str"))
    local_time = _coerce_text(task.get("local_time_str"))
    due_fallback = _fallback_due_text(task)

    if include_date:
        when = local_date
        if local_time:
            when = f"{when} at {local_time}" if when else local_time
        if not when:
            when = due_fallback
        return f"- {title} - {when} ({priority})"

    if local_time:
        return f"- {title} at {local_time} ({priority})"

    return f"- {title} ({priority})"


def _group_by_local_date(tasks: List[Dict[str, Any]]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    order: List[str] = []
    for task in tasks:
        date_label = _coerce_text(task.get("local_date_str")) or "Scheduled tasks"
        if date_label not in grouped:
            grouped[date_label] = []
            order.append(date_label)
        grouped[date_label].append(task)

    return [(label, grouped[label]) for label in order]


def _build_relaxed_task_name_candidates(task_name: str) -> List[str]:
    original = _coerce_text(task_name).lower()
    if not original:
        return []

    tokens = [token for token in re.findall(r"[a-z0-9]+", original) if token]
    if not tokens:
        return []

    filtered_tokens = [token for token in tokens if token not in _TASK_NAME_GENERIC_WORDS]
    if not filtered_tokens:
        return []

    candidates: List[str] = []
    seen = set()

    phrase_candidate = " ".join(filtered_tokens)
    if phrase_candidate and phrase_candidate != original:
        candidates.append(phrase_candidate)
        seen.add(phrase_candidate)

    for token in filtered_tokens:
        if len(token) < 3:
            continue
        if token in seen:
            continue
        candidates.append(token)
        seen.add(token)

    return candidates


def _has_explicit_weekday(text: str) -> bool:
    return bool(_WEEKDAY_PATTERN.search(_coerce_text(text).lower()))


def _detect_week_scope(text: str) -> str:
    match = _WEEK_SCOPE_PATTERN.search(_coerce_text(text).lower())
    if not match:
        return ""
    value = _coerce_text(match.group(1)).lower()
    if value == "previous":
        return "last"
    return value


def _build_week_scope_range(
    week_scope: str,
    timezone_name: str,
    now_utc: datetime,
) -> Optional[Dict[str, Any]]:
    normalized_scope = _coerce_text(week_scope).lower()
    if normalized_scope not in {"this", "next", "last"}:
        return None

    zone = get_zoneinfo(timezone_name)
    now_aware = now_utc.replace(tzinfo=dt_timezone.utc).astimezone(zone)
    anchor_date = now_aware.date()
    if normalized_scope == "next":
        anchor_date = anchor_date + timedelta(days=7)
    elif normalized_scope == "last":
        anchor_date = anchor_date - timedelta(days=7)

    week_start = anchor_date - timedelta(days=anchor_date.weekday())
    week_end = week_start + timedelta(days=6)

    local_start = datetime.combine(week_start, time.min, tzinfo=zone)
    local_end = datetime.combine(week_end, time.max, tzinfo=zone)

    start_utc = local_start.astimezone(dt_timezone.utc).replace(tzinfo=None)
    end_utc = local_end.astimezone(dt_timezone.utc).replace(tzinfo=None)

    label_prefix = {
        "this": "This week",
        "next": "Next week",
        "last": "Last week",
    }[normalized_scope]
    display_label = (
        f"{label_prefix} ({week_start.strftime('%d %b %Y').replace(' 0', ' ')})"
    )

    return {
        "start_utc": start_utc,
        "end_utc": end_utc,
        "display_label": display_label,
    }


def _approximate_match_prefix(
    username: Optional[str],
    original_task_name: str,
    matched_task_name: str,
) -> str:
    original = _coerce_text(original_task_name)
    matched = _coerce_text(matched_task_name)
    if not original:
        return ""

    if username:
        if matched:
            return (
                f'I could not find an exact match for "{original}", {username}, '
                f'but I found related tasks for "{matched}".'
            )
        return f'I could not find an exact match for "{original}", {username}, but I found related tasks.'

    if matched:
        return (
            f'I could not find an exact match for "{original}", '
            f'but I found related tasks for "{matched}".'
        )
    return f'I could not find an exact match for "{original}", but I found related tasks.'


async def _find_relaxed_task_name_matches(
    user_id: str,
    base_filters: Dict[str, Any],
    task_name: str,
) -> Tuple[List[Dict[str, Any]], int, str]:
    candidates = _build_relaxed_task_name_candidates(task_name)
    if not candidates:
        return [], 0, ""

    for candidate in candidates:
        relaxed_filters = dict(base_filters)
        relaxed_filters["task_name"] = candidate
        tasks, total_count = await find_tasks_for_show(user_id, relaxed_filters)
        if total_count > 0:
            return tasks, total_count, candidate

    return [], 0, ""


def not_found_prompt(
    username: Optional[str],
    filters_used: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
    overdue_only: bool = False,
) -> str:
    filters_summary = _filters_summary(filters_used, overdue_only)
    return gemini_service.generate_reply(
        {
            "action": "show_not_found",
            "filters_summary": filters_summary,
            "date": _coerce_text(filters_used.get("date")),
            "task_name": _coerce_text(filters_used.get("task_name")),
            "priority": _coerce_text(filters_used.get("priority")),
            "status": _coerce_text(filters_used.get("status")),
        },
        username,
        history or [],
    )


def results_prompt(
    username: Optional[str],
    tasks: List[Dict[str, Any]],
    filters_used: Dict[str, Any],
    total_count: int,
    has_more: bool,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    intro = gemini_service.generate_reply(
        {
            "action": "show_results",
            "count": len(tasks),
            "filters_summary": _filters_summary(filters_used, overdue_only=False),
            "date": _coerce_text(filters_used.get("date")),
            "priority": _coerce_text(filters_used.get("priority")),
            "status": _coerce_text(filters_used.get("status")),
            "task_name": _coerce_text(filters_used.get("task_name")),
        },
        username,
        history or [],
    )

    if not tasks:
        return intro

    if len(tasks) == 1:
        task = tasks[0]
        title = _coerce_text(task.get("title")) or "Untitled task"
        priority = _coerce_text(task.get("priority")).lower() or "medium"
        local_date = _coerce_text(task.get("local_date_str"))
        local_time = _coerce_text(task.get("local_time_str"))
        when = local_date
        if local_time:
            when = f"{when} at {local_time}" if when else local_time
        if not when:
            when = _fallback_due_text(task)

        detail = f"{title} is scheduled for {when} ({priority})."
        if has_more:
            return (
                f"{intro}\n{detail}\n"
                f"You have {total_count} tasks in total. Try adding a filter to narrow the list."
            )
        return f"{intro}\n{detail}"

    groups = _group_by_local_date(tasks)
    lines: List[str] = [intro]
    multi_day = len(groups) > 1
    for day_label, items in groups:
        if multi_day:
            lines.append(f"{day_label}:")
            for task in items:
                lines.append(_task_line(task, include_date=False))
        else:
            for task in items:
                lines.append(_task_line(task, include_date=True))

    if has_more:
        lines.append(
            f"You have {total_count} tasks in total. "
            "Use date, priority, status, or task name to narrow it down."
        )

    return "\n".join(lines)


async def _resolve_date_filter(date_value: str, timezone_name: str) -> Optional[Dict[str, Any]]:
    candidate = _coerce_text(date_value)
    if not candidate:
        return None

    parsed = await duckling_client.parse(candidate, dims=["time"], timezone=timezone_name)
    if not isinstance(parsed, list):
        return None

    for item in parsed:
        if isinstance(item, dict) and item.get("dim") == "time":
            resolved = build_date_range(item, timezone_name)
            if resolved:
                return resolved

    return None


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
        # Conversation save should not block read-only show flow.
        print(f"[ShowHandler] Failed to save conversation turn: {error}")


def _serialize_due_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return _coerce_text(value)


async def handle_scheduling_show(
    entities: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entities = dict(entities or {})
    context = dict(context or {})

    user_id = str(context.get("user_id") or "")
    session_id = str(context.get("session_id") or "")
    user = context.get("user") or {}
    history = context.get("history") or []
    user_message = str(context.get("message") or "")
    input_type = str(context.get("input_type") or "text")

    user_name = user.get("name")
    timezone_name = resolve_timezone_name(user.get("timezone"))
    now_utc = datetime.now(dt_timezone.utc).replace(tzinfo=None)

    task_name = clean_task_name(_coerce_text(_first_value(entities.get("task_name"))))
    date_raw = _coerce_text(_first_value(entities.get("date")))
    priority = _normalize_priority(_first_value(entities.get("priority")))
    status = _normalize_status(_first_value(entities.get("status")))

    message_lower = user_message.lower()
    overdue_only = "overdue" in message_lower and not status

    filters_used: Dict[str, Any] = {}
    query_filters: Dict[str, Any] = {"now_utc": now_utc}

    # Handle explicit week windows directly from user text so phrases like
    # "this week"/"next week" do not collapse to a single weekday.
    week_scope = _detect_week_scope(message_lower)
    date_raw_normalized = _coerce_text(date_raw).lower()
    date_entity_is_explicit_week_phrase = date_raw_normalized in {
        "this week",
        "next week",
        "last week",
        "previous week",
    }
    if (
        week_scope
        and not _has_explicit_weekday(message_lower)
        and not date_entity_is_explicit_week_phrase
    ):
        week_range = _build_week_scope_range(week_scope, timezone_name, now_utc)
        if week_range:
            query_filters["date_range"] = {
                "start_utc": week_range["start_utc"],
                "end_utc": week_range["end_utc"],
            }
            filters_used["date"] = _coerce_text(week_range["display_label"])

    if date_raw and "date_range" not in query_filters:
        date_range = await _resolve_date_filter(date_raw, timezone_name)
        if date_range:
            query_filters["date_range"] = {
                "start_utc": date_range["start_utc"],
                "end_utc": date_range["end_utc"],
            }
            filters_used["date"] = _coerce_text(date_range.get("display_label")) or date_raw

    if task_name:
        query_filters["task_name"] = task_name
        filters_used["task_name"] = task_name

    if priority:
        query_filters["priority"] = priority
        filters_used["priority"] = priority

    if status:
        query_filters["status"] = status
        filters_used["status"] = status
    elif overdue_only:
        query_filters["status"] = "pending"
        query_filters["overdue_only"] = True
        filters_used["status"] = "pending"

    tasks, total_count = await find_tasks_for_show(user_id, query_filters)

    approximate_match = False
    matched_task_name = ""
    if total_count == 0 and task_name:
        relaxed_tasks, relaxed_total_count, relaxed_name = await _find_relaxed_task_name_matches(
            user_id,
            query_filters,
            task_name,
        )
        if relaxed_total_count > 0:
            tasks = relaxed_tasks
            total_count = relaxed_total_count
            matched_task_name = relaxed_name
            approximate_match = True

    if total_count == 0:
        response_text = not_found_prompt(
            user_name,
            filters_used,
            history,
            overdue_only=overdue_only,
        )
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_show",
            entities,
        )
        return {
            "status": "not_found",
            "intent": "scheduling_show",
            "response_text": response_text,
            "notifications": [],
            "total_count": 0,
            "has_more": False,
            "tasks": [],
        }

    localized_tasks = convert_tasks_to_local(tasks, timezone_name)
    has_more = total_count > len(localized_tasks)
    response_text = results_prompt(
        user_name,
        localized_tasks,
        filters_used,
        total_count,
        has_more,
        history,
    )
    if approximate_match:
        relaxed_prefix = _approximate_match_prefix(user_name, task_name, matched_task_name)
        if relaxed_prefix:
            response_text = f"{relaxed_prefix}\n{response_text}"

    await _save_turn(
        session_id,
        user_message,
        response_text,
        input_type,
        "scheduling_show",
        entities,
    )

    response_tasks = [
        {
            "task_id": _coerce_text(task.get("_id")),
            "title": _coerce_text(task.get("title")),
            "due_datetime": _coerce_text(task.get("due_datetime")),
            "priority": _coerce_text(task.get("priority")) or "medium",
            "status": _coerce_text(task.get("status")) or "pending",
            "local_datetime_str": _coerce_text(task.get("local_datetime_str")),
        }
        for task in localized_tasks
    ]

    return {
        "status": "success",
        "intent": "scheduling_show",
        "response_text": response_text,
        "notifications": [],
        "total_count": total_count,
        "has_more": has_more,
        "tasks": response_tasks,
    }
