"""
Phase 16/17 scheduling delete handler.
Implements:
- Step 1-4: entity check, date resolution, DB query, and result presentation.
- Step 5-7: confirmed deletion, log/calendar/notifications, save-turn and return.
"""
from datetime import datetime, timezone as dt_timezone
import re
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from context.redis_client import redis_client
from db.activity_logs import insert_log
from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.tasks import find_tasks_for_delete, get_task_by_id, soft_delete_task
from services.duckling import duckling_client
from services.gemini import gemini_service
from services.google_calendar import google_calendar_client
from utils.task_value_normalizer import canonicalize_priority, canonicalize_status
from utils.timezone_utils import (
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


def _normalize_priority(value: Any) -> str:
    return canonicalize_priority(value)


def _normalize_status(value: Any) -> str:
    return canonicalize_status(value)


def _format_due_display(value: Any, timezone_name: str) -> str:
    local_dt = utc_naive_to_local(value, timezone_name)
    if local_dt is None:
        raw = _coerce_text(value)
        return raw
    return local_dt.strftime("%A, %d %b %Y at %I:%M %p").replace(" 0", " ")


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


def _task_preview(task: Dict[str, Any], timezone_name: Optional[str] = None) -> Dict[str, Any]:
    return {
        "title": _coerce_text(task.get("title")) or "Untitled task",
        "due_datetime": _serialize_due_datetime(task.get("due_datetime"), timezone_name),
        "priority": _normalize_priority(task.get("priority")) or "medium",
    }


def _pending_payload(
    intent: str,
    entities: Dict[str, Any],
    task_ids: Optional[List[str]] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    bulk: bool = False,
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "pending_action": {
            "intent": intent,
            "task_ids": list(task_ids or []),
            "tasks": list(tasks or []),
            "bulk": bool(bulk),
            "entities": dict(entities or {}),
        }
    }
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
        # Save failures should never block delete flow.
        print(f"[DeleteHandler] Failed to save conversation turn: {error}")


def _filters_summary(filters_used: Dict[str, Any]) -> str:
    parts: List[str] = []

    task_name = _coerce_text(filters_used.get("task_name"))
    if task_name:
        parts.append(f'name "{task_name}"')

    date_value = _coerce_text(filters_used.get("date"))
    if date_value:
        parts.append(f"date {date_value}")

    priority = _coerce_text(filters_used.get("priority"))
    if priority:
        parts.append(f"priority {priority}")

    status = _coerce_text(filters_used.get("status"))
    if status:
        parts.append(f"status {status}")

    return ", ".join(parts)


def not_found_prompt(
    username: Optional[str],
    filters_used: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "delete_not_found",
            "filters_used": filters_used,
            "filters_summary": _filters_summary(filters_used),
        },
        username,
        history or [],
    )


def single_confirm_prompt(
    username: Optional[str],
    task: Dict[str, Any],
    timezone_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "delete_single_confirm",
            "task_name": _coerce_text(task.get("title")) or "that task",
            "due_datetime": _format_due_display(task.get("due_datetime"), timezone_name),
            "priority": _coerce_text(task.get("priority")) or "medium",
        },
        username,
        history or [],
    )


def multi_list_prompt(
    username: Optional[str],
    tasks: List[Dict[str, Any]],
    timezone_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    intro = gemini_service.generate_reply(
        {
            "action": "delete_multi_list",
            "count": len(tasks),
        },
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

    lines.append("Reply with a number, or say 'all' to delete all of them.")
    return f"{intro}\n" + "\n".join(lines)


def too_broad_prompt(
    username: Optional[str],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "delete_too_broad",
        },
        username,
        history or [],
    )


def _pick_active_google_integration(integrations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for integration in integrations:
        if not isinstance(integration, dict):
            continue

        provider = _coerce_text(integration.get("provider")).lower()
        is_active = integration.get("is_active") is True
        if provider == "google_calendar" and is_active:
            return integration

    return None


def _task_names_summary(tasks: List[Dict[str, Any]], limit: int = 3) -> str:
    names = [
        _coerce_text(task.get("title"))
        for task in tasks
        if _coerce_text(task.get("title"))
    ]
    if not names:
        return "those tasks"
    if len(names) <= limit:
        return ", ".join(names)
    return f"{', '.join(names[:limit])}, and more"


def _delete_cancel_prompt(
    username: Optional[str],
    tasks: List[Dict[str, Any]],
    bulk: bool,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    if bulk:
        return gemini_service.generate_reply(
            {
                "action": "delete_cancel_bulk",
                "count": len(tasks),
                "task_names": _task_names_summary(tasks),
            },
            username,
            history or [],
        )

    first_task = tasks[0] if tasks else {}
    return gemini_service.generate_reply(
        {
            "action": "delete_cancel_single",
            "task_name": _coerce_text(first_task.get("title")) or "that task",
        },
        username,
        history or [],
    )


def _delete_success_prompt(
    username: Optional[str],
    deleted_tasks: List[Dict[str, Any]],
    bulk: bool,
    timezone_name: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    if len(deleted_tasks) == 1 and not bulk:
        first = deleted_tasks[0]
        return gemini_service.generate_reply(
            {
                "action": "task_deleted",
                "task_name": _coerce_text(first.get("title")) or "that task",
                "due_datetime": _format_due_display(first.get("due_datetime"), timezone_name),
                "priority": _coerce_text(first.get("priority")) or "medium",
            },
            username,
            history or [],
        )

    return gemini_service.generate_reply(
        {
            "action": "delete_bulk_completed",
            "count": len(deleted_tasks),
            "task_names": _task_names_summary(deleted_tasks),
        },
        username,
        history or [],
    )


def _build_collaborator_notifications(
    task: Dict[str, Any],
    owner_id: str,
    owner_name: Optional[str],
) -> List[Dict[str, Any]]:
    task_title = _coerce_text(task.get("title")) or "a shared task"
    task_id = _coerce_text(task.get("_id"))
    sender_name = owner_name or "Your collaborator"

    notifications: List[Dict[str, Any]] = []
    seen = set()
    for collaborator in task.get("collaborators") or []:
        if not isinstance(collaborator, dict):
            continue

        status = _coerce_text(collaborator.get("status")).lower()
        if status != "accepted":
            continue

        collaborator_id = _coerce_text(collaborator.get("user_id"))
        if not collaborator_id or collaborator_id == str(owner_id):
            continue

        dedupe_key = (collaborator_id, task_id)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        notifications.append(
            {
                "user_id": collaborator_id,
                "sender_id": str(owner_id),
                "type": "task_deleted",
                "reference_type": "task",
                "reference_id": task_id,
                "title": "Shared task removed",
                "message": f"{sender_name} deleted {task_title}.",
                "action_required": False,
                "delivery_channel": ["push", "in_app"],
            }
        )

    return notifications


async def _resolve_date_filter(
    date_value: str,
    timezone: str,
) -> Tuple[Optional[str], Optional[Dict[str, datetime]]]:
    candidate = _to_date_text(date_value)
    if not candidate:
        return None, None

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
        resolved = await duckling_client.resolve_date(candidate, timezone=timezone)
        candidate = _to_date_text(resolved)

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
        return None, None

    day_start, day_end = local_day_bounds_to_utc_naive(candidate, timezone)
    if not day_start or not day_end:
        return None, None
    return candidate, {"start": day_start, "end": day_end}


async def handle_scheduling_delete(
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
    timezone = resolve_timezone_name(user.get("timezone"))
    pending_context = context.get("pending_context") or {}
    pending_action = pending_context.get("pending_action") or {}
    pending_reply_type = context.get("pending_reply_type")
    pending_reply_value = context.get("pending_reply_value")

    # Step 5 entry point from context manager (yes/no on State 2 or State 4).
    if (
        pending_action.get("intent") in {"delete", "scheduling_delete"}
        and pending_reply_type == "yes_no"
    ):
        pending_entities = dict(pending_action.get("entities") or {})
        pending_tasks = list(pending_action.get("tasks") or [])
        pending_task_ids = [str(task_id) for task_id in (pending_action.get("task_ids") or [])]
        is_bulk = bool(pending_action.get("bulk"))

        if pending_reply_value == "no":
            await redis_client.delete_context(user_id)
            response_text = _delete_cancel_prompt(user_name, pending_tasks, is_bulk, history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_delete",
                pending_entities,
            )
            return {
                "status": "cancelled",
                "intent": "scheduling_delete",
                "response_text": response_text,
                "notifications": [],
            }

        if pending_reply_value == "yes":
            deleted_tasks: List[Dict[str, Any]] = []
            notifications: List[Dict[str, Any]] = []

            google_integration = _pick_active_google_integration(integrations)
            access_token = _coerce_text((google_integration or {}).get("access_token"))
            calendar_id = _coerce_text((google_integration or {}).get("calendar_id")) or "primary"

            for task_id in pending_task_ids:
                task = await get_task_by_id(task_id, user_id)
                if not task:
                    continue

                delete_ok = await soft_delete_task(task_id)
                if not delete_ok:
                    continue

                task_title = _coerce_text(task.get("title")) or "Untitled task"
                task_due_datetime = task.get("due_datetime")
                task_priority = _normalize_priority(task.get("priority")) or "medium"

                deleted_tasks.append(
                    {
                        "_id": _coerce_text(task.get("_id")) or str(task_id),
                        "title": task_title,
                        "due_datetime": _serialize_due_datetime(task_due_datetime, timezone),
                        "priority": task_priority,
                    }
                )

                due_dt = _coerce_datetime(task_due_datetime)
                log_payload: Dict[str, Any] = {
                    "user_id": _to_object_id(user_id),
                    "task_id": _to_object_id(task_id),
                    "action_type": "task_deleted",
                    "task_priority": task_priority,
                    "subject": task_title,
                    "source": "scheduling_module",
                }
                if due_dt is not None:
                    log_payload.update(
                        {
                            "day_of_week": due_dt.weekday(),
                            "hour_of_day": due_dt.hour,
                            "week_number": due_dt.isocalendar().week,
                            "scheduled_hour": due_dt.hour,
                            "scheduled_day": due_dt.weekday(),
                        }
                    )
                try:
                    await insert_log(log_payload, settings=settings)
                except Exception as error:
                    print(f"[DeleteHandler] Activity log insert failed for task_id={task_id}: {error}")

                event_id = _coerce_text(task.get("google_calendar_event_id"))
                if event_id and access_token:
                    try:
                        deleted = await google_calendar_client.delete_event(
                            token=access_token,
                            calendar_id=calendar_id,
                            event_id=event_id,
                        )
                        if not deleted:
                            print(
                                "[DeleteHandler] Google Calendar delete_event failed "
                                f"for task_id={task_id}, event_id={event_id}"
                            )
                    except Exception as error:
                        print(f"[DeleteHandler] Google Calendar delete_event exception: {error}")

                notifications.extend(
                    _build_collaborator_notifications(task, user_id, user_name)
                )

            await redis_client.delete_context(user_id)

            if not deleted_tasks:
                response_text = not_found_prompt(user_name, pending_entities, history)
                await _save_turn(
                    session_id,
                    user_message,
                    response_text,
                    input_type,
                    "scheduling_delete",
                    pending_entities,
                )
                return {
                    "status": "not_found",
                    "intent": "scheduling_delete",
                    "response_text": response_text,
                    "notifications": [],
                    "match_count": 0,
                }

            response_text = _delete_success_prompt(
                user_name,
                deleted_tasks,
                is_bulk,
                timezone,
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_delete",
                pending_entities,
            )
            return {
                "status": "success",
                "intent": "scheduling_delete",
                "response_text": response_text,
                "notifications": notifications,
                "deleted": {
                    "count": len(deleted_tasks),
                    "bulk": is_bulk,
                    "tasks": deleted_tasks,
                },
            }

    # Step 1: entity check.
    task_name = _coerce_text(_first_value(entities.get("task_name")))
    date_raw = _to_date_text(_first_value(entities.get("date")))
    priority = _normalize_priority(_first_value(entities.get("priority")))
    status = _normalize_status(_first_value(entities.get("status")))

    extracted_filters: Dict[str, Any] = {}
    if task_name:
        extracted_filters["task_name"] = task_name
    if date_raw:
        extracted_filters["date"] = date_raw
    if priority:
        extracted_filters["priority"] = priority
    if status:
        extracted_filters["status"] = status

    if not extracted_filters:
        await redis_client.set_context(
            user_id,
            _pending_payload(
                "delete",
                {},
                expected_response="free_text",
            ),
        )
        response_text = gemini_service.generate_reply(
            {"action": "delete_missing_entities"},
            user_name,
            history,
        )
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_delete",
            entities,
        )
        return {
            "status": "pending",
            "intent": "scheduling_delete",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "free_text",
            },
        }

    # Step 2: date resolution.
    resolved_filters = dict(extracted_filters)
    query_filters: Dict[str, Any] = {}
    date_range = None

    if date_raw:
        resolved_date, date_range = await _resolve_date_filter(date_raw, timezone)
        if not resolved_date or not date_range:
            pending_entities = dict(extracted_filters)
            pending_entities.pop("date", None)
            await redis_client.set_context(
                user_id,
                _pending_payload(
                    "delete",
                    pending_entities,
                    expected_response="free_text",
                    missing_entity="date",
                ),
            )
            response_text = gemini_service.generate_reply(
                {
                    "action": "delete_invalid_date",
                    "date": date_raw,
                },
                user_name,
                history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_delete",
                entities,
            )
            return {
                "status": "pending",
                "intent": "scheduling_delete",
                "response_text": response_text,
                "notifications": [],
                "pending": {
                    "expected_response": "free_text",
                    "missing_entity": "date",
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

    # Step 3: query tasks.
    matches = await find_tasks_for_delete(
        user_id,
        query_filters,
        timezone_name=timezone,
    )
    match_count = len(matches)

    # Step 4: handle result count.
    if match_count == 0:
        response_text = not_found_prompt(user_name, resolved_filters, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_delete",
            resolved_filters,
        )
        return {
            "status": "not_found",
            "intent": "scheduling_delete",
            "response_text": response_text,
            "notifications": [],
            "match_count": 0,
        }

    if match_count == 1:
        task = matches[0]
        task_id = _coerce_text(task.get("_id"))
        if not task_id:
            response_text = not_found_prompt(user_name, resolved_filters, history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_delete",
                resolved_filters,
            )
            return {
                "status": "not_found",
                "intent": "scheduling_delete",
                "response_text": response_text,
                "notifications": [],
                "match_count": 0,
            }

        task_info = _task_preview(task, timezone)
        await redis_client.set_context(
            user_id,
            _pending_payload(
                "delete",
                resolved_filters,
                task_ids=[task_id],
                tasks=[task_info],
                bulk=False,
                expected_response="yes_no",
            ),
        )
        response_text = single_confirm_prompt(user_name, task_info, timezone, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_delete",
            resolved_filters,
        )
        return {
            "status": "pending",
            "intent": "scheduling_delete",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "yes_no",
                "bulk": False,
                "task_ids": [task_id],
            },
        }

    if 2 <= match_count <= 5:
        task_ids: List[str] = []
        task_list: List[Dict[str, Any]] = []
        for task in matches:
            task_id = _coerce_text(task.get("_id"))
            if not task_id:
                continue
            task_ids.append(task_id)
            task_list.append(_task_preview(task, timezone))

        if not task_ids:
            response_text = not_found_prompt(user_name, resolved_filters, history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                "scheduling_delete",
                resolved_filters,
            )
            return {
                "status": "not_found",
                "intent": "scheduling_delete",
                "response_text": response_text,
                "notifications": [],
                "match_count": 0,
            }

        await redis_client.set_context(
            user_id,
            _pending_payload(
                "delete",
                resolved_filters,
                task_ids=task_ids,
                tasks=task_list,
                bulk=False,
                expected_response="number",
            ),
        )
        response_text = multi_list_prompt(user_name, task_list, timezone, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            "scheduling_delete",
            resolved_filters,
        )
        return {
            "status": "pending",
            "intent": "scheduling_delete",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "number",
                "bulk": False,
                "task_count": len(task_ids),
            },
        }

    response_text = too_broad_prompt(user_name, history)
    await _save_turn(
        session_id,
        user_message,
        response_text,
        input_type,
        "scheduling_delete",
        resolved_filters,
    )
    return {
        "status": "too_broad",
        "intent": "scheduling_delete",
        "response_text": response_text,
        "notifications": [],
        "match_count": match_count,
    }
