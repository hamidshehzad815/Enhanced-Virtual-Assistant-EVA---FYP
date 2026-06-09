"""
Learning goal deletion handler (learning_delete intent).
Implements Steps 1–8: identify goal(s), confirm, soft-delete, notify collaborators.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from context.redis_client import redis_client
from db.activity_logs import insert_log
from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.learning_goals import (
    find_goals_for_delete,
    get_goal_by_id,
    soft_delete_goal,
)
from db.roadmap_topics import soft_delete_pending_topics
from db.tasks import get_pending_learning_tasks, soft_delete_pending_learning_tasks
from handlers.scheduling.add import _coerce_text
from utils.google_calendar_sync import resolve_google_calendar_sync
from services.gemini import gemini_service
from services.google_calendar import google_calendar_client
from utils.learning_utils import (
    SUPPORTED_TOPICS,
    normalize_subtopic_entity,
    normalize_topic,
    resolve_subtopic_mapping,
)


def _first_value(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _to_object_id(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))
    except Exception:
        return value


def _goal_preview(goal: Dict[str, Any]) -> Dict[str, Any]:
    title = _coerce_text(goal.get("title"))
    roadmap_key = _coerce_text(goal.get("roadmap_key"))
    subject = _coerce_text(goal.get("subject"))
    if not title:
        if subject and roadmap_key:
            title = f"{subject} {roadmap_key}"
        elif subject:
            title = subject
        elif roadmap_key:
            title = roadmap_key
        else:
            title = "Learning goal"

    return {
        "_id": _coerce_text(goal.get("_id")),
        "title": title,
        "roadmap_key": roadmap_key,
        "status": _coerce_text(goal.get("status")) or "active",
        "completed_topics": int(goal.get("completed_topics") or 0),
        "total_topics": int(goal.get("total_topics") or 0),
        "collaborators": list(goal.get("collaborators") or []),
        "subject": subject,
    }


def _pending_payload(
    entities: Dict[str, Any],
    *,
    goal_ids: Optional[List[str]] = None,
    goals: Optional[List[Dict[str, Any]]] = None,
    bulk: bool = False,
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "pending_action": {
            "intent": "learning_delete",
            "goal_ids": list(goal_ids or []),
            "goals": list(goals or []),
            "bulk": bool(bulk),
            "entities": dict(entities or {}),
        },
    }
    payload.update(extra)
    return payload


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
                "intent": "learning_delete",
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
        print(f"[LearningDelete] Failed to save conversation turn: {error}")


def _topic_label(entities: Dict[str, Any]) -> str:
    return _coerce_text(entities.get("topic")) or "that topic"


def _not_found_prompt(
    username: Optional[str],
    entities: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "learning_delete_not_found",
            "topic": _topic_label(entities),
            "subtopic": _coerce_text(entities.get("subtopic")) or None,
        },
        username,
        history or [],
    )


def _missing_topic_prompt(
    username: Optional[str],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {"action": "learning_delete_missing_topic"},
        username,
        history or [],
    )


def _level_display(value: Optional[str]) -> str:
    text = _coerce_text(value)
    if not text or text.lower() == "general":
        return ""
    return text.replace("_", " ").strip()


def _requested_level_label(
    entities: Dict[str, Any],
    roadmap_key: Optional[str],
) -> str:
    subtopic = _level_display(_coerce_text(entities.get("subtopic")))
    if subtopic:
        return subtopic
    return _level_display(roadmap_key) or "that level"


def _near_miss_prompt(
    username: Optional[str],
    goal: Dict[str, Any],
    *,
    canonical_topic: str,
    requested_level: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    preview = _goal_preview(goal)
    existing_level = _level_display(preview.get("roadmap_key")) or preview.get("title") or "your plan"
    msg = gemini_service.generate_reply(
        {
            "action": "learning_delete_near_miss_confirm",
            "topic": canonical_topic,
            "requested_level": requested_level,
            "existing_level": existing_level,
            "title": preview["title"],
            "status": preview["status"],
            "completed_topics": preview["completed_topics"],
            "total_topics": preview["total_topics"],
        },
        username,
        history or [],
    )
    if msg and str(msg).strip():
        return str(msg).strip()

    name_bit = f", {username}" if username else ""
    return (
        f"I couldn't find a {canonical_topic} {requested_level} roadmap{name_bit}. "
        f"You do have a {canonical_topic} {existing_level} plan "
        f"({preview['completed_topics']} of {preview['total_topics']} sessions done, "
        f"{preview['status']}). Do you want me to delete that instead? Reply yes or no."
    )


def _single_confirm_prompt(
    username: Optional[str],
    goal: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
    *,
    canonical_topic: str = "",
) -> str:
    preview = _goal_preview(goal)
    msg = gemini_service.generate_reply(
        {
            "action": "learning_delete_single_confirm",
            "title": preview["title"],
            "status": preview["status"],
            "completed_topics": preview["completed_topics"],
            "total_topics": preview["total_topics"],
        },
        username,
        history or [],
    )
    if msg and str(msg).strip():
        return str(msg).strip()

    topic_label = canonical_topic or preview.get("subject") or "learning"
    track = str(preview.get("roadmap_key") or "").replace("_", " ").strip()
    track_bit = f" ({track})" if track and track != "general" else ""
    name_bit = f", {username}" if username else ""
    return (
        f"I found your {topic_label} learning plan{track_bit}: "
        f"\"{preview['title']}\" — {preview['completed_topics']} of "
        f"{preview['total_topics']} sessions done, status {preview['status']}{name_bit}. "
        "Do you want me to delete it? Reply yes or no."
    )


def _multi_list_prompt(
    username: Optional[str],
    goals: List[Dict[str, Any]],
    entities: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    intro = gemini_service.generate_reply(
        {
            "action": "learning_delete_multi_list",
            "count": len(goals),
            "topic": _topic_label(entities),
        },
        username,
        history or [],
    )

    lines: List[str] = []
    for index, goal in enumerate(goals, start=1):
        preview = _goal_preview(goal)
        done = preview["completed_topics"]
        total = preview["total_topics"]
        progress = f"{done}/{total} done" if total > 0 else preview["status"]
        lines.append(
            f"{index}. {preview['title']} — {preview['status']} — {progress}",
        )

    lines.append("Or say 'all' to delete all of them.")
    return f"{intro}\n" + "\n".join(lines)


def _too_broad_prompt(
    username: Optional[str],
    entities: Dict[str, Any],
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return gemini_service.generate_reply(
        {
            "action": "learning_delete_too_broad",
            "topic": _topic_label(entities),
        },
        username,
        history or [],
    )


def _success_prompt(
    username: Optional[str],
    deleted_goals: List[Dict[str, Any]],
    *,
    bulk: bool,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    deleted_payload = [_goal_preview(goal) for goal in deleted_goals]
    return gemini_service.generate_reply(
        {
            "action": "learning_goal_deleted",
            "deleted": deleted_payload,
            "count": len(deleted_payload),
            "bulk": bulk,
        },
        username,
        history or [],
    )


def _no_confirmation_message(
    goals: List[Dict[str, Any]],
    *,
    bulk: bool,
    user_name: Optional[str],
) -> str:
    if bulk:
        if user_name:
            return f"No problem, I left all those goals as they are, {user_name}."
        return "No problem, I left all those goals as they are."

    title = _goal_preview(goals[0] if goals else {}).get("title") or "that learning goal"
    if user_name:
        return f"No problem, I left {title} as it is, {user_name}."
    return f"No problem, I left {title} as it is."


def _level_label(goal: Dict[str, Any]) -> str:
    rk = _coerce_text(goal.get("roadmap_key"))
    if rk and rk != "general":
        return rk
    return ""


def _build_collaborator_notifications(
    goal: Dict[str, Any],
    owner_id: str,
    owner_name: Optional[str],
) -> List[Dict[str, Any]]:
    preview = _goal_preview(goal)
    goal_id = _coerce_text(goal.get("_id"))
    sender_name = owner_name or "Your collaborator"
    subject = _coerce_text(goal.get("subject")) or _topic_label(
        {"topic": preview.get("title")},
    )
    level = _level_label(goal)
    topic_part = subject
    level_part = f" {level}" if level else ""

    notifications: List[Dict[str, Any]] = []
    seen = set()
    for collaborator in preview.get("collaborators") or []:
        if not isinstance(collaborator, dict):
            continue

        status = _coerce_text(collaborator.get("status")).lower()
        if status != "accepted":
            continue

        collaborator_id = _coerce_text(collaborator.get("user_id"))
        if not collaborator_id or collaborator_id == str(owner_id):
            continue

        dedupe_key = (collaborator_id, goal_id)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        notifications.append(
            {
                "user_id": collaborator_id,
                "sender_id": str(owner_id),
                "type": "learning_goal_deleted",
                "reference_type": "learning_goal",
                "reference_id": goal_id,
                "title": "Shared learning plan removed",
                "message": (
                    f"{sender_name} removed {topic_part}{level_part} from their plan. "
                    "Your copy is unaffected."
                ),
                "action_required": False,
                "delivery_channel": ["push", "in_app"],
            }
        )

    return notifications


async def _delete_calendar_events_for_goal(
    goal_id: str,
    *,
    access_token: str,
    calendar_id: str,
) -> None:
    pending_tasks = await get_pending_learning_tasks(goal_id)
    for task in pending_tasks:
        event_id = _coerce_text(task.get("google_calendar_event_id"))
        if not event_id:
            continue
        try:
            deleted = await google_calendar_client.delete_event(
                token=access_token,
                calendar_id=calendar_id,
                event_id=event_id,
            )
            if not deleted:
                print(
                    "[LearningDelete] Google Calendar delete_event failed "
                    f"for goal_id={goal_id}, event_id={event_id}"
                )
        except Exception as error:
            print(f"[LearningDelete] Google Calendar delete_event exception: {error}")


async def _perform_deletions(
    goal_ids: List[str],
    *,
    user_id: str,
    entities: Dict[str, Any],
    integrations: List[Dict[str, Any]],
    owner_name: Optional[str],
    settings: Optional[Dict[str, Any]] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    deleted_goals: List[Dict[str, Any]] = []
    notifications: List[Dict[str, Any]] = []

    google_integration = await resolve_google_calendar_sync(user_id, integrations, settings)
    access_token = _coerce_text((google_integration or {}).get("access_token"))
    calendar_id = _coerce_text((google_integration or {}).get("calendar_id")) or "primary"

    subject_for_log = _topic_label(entities).lower()

    for goal_id in goal_ids:
        goal = await get_goal_by_id(goal_id)
        if not goal:
            continue

        if access_token:
            await _delete_calendar_events_for_goal(
                goal_id,
                access_token=access_token,
                calendar_id=calendar_id,
            )

        if not await soft_delete_goal(goal_id):
            continue

        await soft_delete_pending_topics(goal_id)
        await soft_delete_pending_learning_tasks(goal_id)

        try:
            await insert_log(
                {
                    "user_id": _to_object_id(user_id),
                    "task_id": None,
                    "action_type": "goal_deleted",
                    "subject": subject_for_log,
                    "source": "learning_module",
                },
                settings=settings,
            )
        except Exception as error:
            print(f"[LearningDelete] Activity log insert failed for goal_id={goal_id}: {error}")

        deleted_goals.append(goal)
        notifications.extend(
            _build_collaborator_notifications(goal, user_id, owner_name)
        )

    return deleted_goals, notifications


async def handle_learning_delete(
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

    pending_context = context.get("pending_context") or {}
    pending_action = pending_context.get("pending_action") or {}
    pending_reply_type = context.get("pending_reply_type")
    pending_reply_value = context.get("pending_reply_value")

    # Step 6 — perform deletion after yes/no confirmation (States 2 or 4).
    if (
        pending_action.get("intent") == "learning_delete"
        and pending_reply_type == "yes_no"
    ):
        pending_entities = dict(pending_action.get("entities") or {})
        pending_goals = list(pending_action.get("goals") or [])
        pending_goal_ids = [
            str(goal_id) for goal_id in (pending_action.get("goal_ids") or [])
        ]
        is_bulk = bool(pending_action.get("bulk"))

        if pending_reply_value == "no":
            await redis_client.delete_context(user_id)
            response_text = _no_confirmation_message(
                pending_goals,
                bulk=is_bulk,
                user_name=user_name,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                pending_entities,
            )
            return {
                "status": "cancelled",
                "intent": "learning_delete",
                "response_text": response_text,
                "notifications": [],
            }

        if pending_reply_value == "yes":
            deleted_goals, notifications = await _perform_deletions(
                pending_goal_ids,
                user_id=user_id,
                entities=pending_entities,
                integrations=integrations,
                owner_name=user_name,
                settings=settings,
            )
            await redis_client.delete_context(user_id)

            if not deleted_goals:
                response_text = _not_found_prompt(user_name, pending_entities, history)
                await _save_turn(
                    session_id,
                    user_message,
                    response_text,
                    input_type,
                    pending_entities,
                )
                return {
                    "status": "not_found",
                    "intent": "learning_delete",
                    "response_text": response_text,
                    "notifications": [],
                    "match_count": 0,
                }

            response_text = _success_prompt(
                user_name,
                deleted_goals,
                bulk=is_bulk,
                history=history,
            )
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                pending_entities,
            )
            return {
                "status": "success",
                "intent": "learning_delete",
                "response_text": response_text,
                "notifications": notifications,
                "deleted": {
                    "count": len(deleted_goals),
                    "bulk": is_bulk,
                    "goals": [_goal_preview(goal) for goal in deleted_goals],
                },
            }

    # Step 1 — entity check (topic required).
    topic_raw = _coerce_text(_first_value(entities.get("topic")))
    if not topic_raw:
        await redis_client.set_context(
            user_id,
            _pending_payload({}, expected_response="free_text"),
        )
        response_text = _missing_topic_prompt(user_name, history)
        await _save_turn(session_id, user_message, response_text, input_type, entities)
        return {
            "status": "pending",
            "intent": "learning_delete",
            "response_text": response_text,
            "notifications": [],
            "pending": {"expected_response": "free_text"},
        }

    # Step 2 — topic validation.
    canonical_topic = normalize_topic(topic_raw)
    if not canonical_topic or canonical_topic not in SUPPORTED_TOPICS:
        response_text = _not_found_prompt(
            user_name,
            {"topic": topic_raw, **entities},
            history,
        )
        await _save_turn(session_id, user_message, response_text, input_type, entities)
        return {
            "status": "not_found",
            "intent": "learning_delete",
            "response_text": response_text,
            "notifications": [],
        }

    resolved_entities = dict(entities)
    resolved_entities["topic"] = canonical_topic

    # Step 3 — subtopic mapping (ignore NER noise like "ma"; only filter when confident).
    roadmap_key = _coerce_text(resolved_entities.get("roadmap_key")) or None
    if roadmap_key and str(roadmap_key).lower() == "general":
        roadmap_key = None
    subtopic_raw = normalize_subtopic_entity(resolved_entities.get("subtopic"))
    if subtopic_raw:
        resolved_entities["subtopic"] = subtopic_raw
    if not roadmap_key and subtopic_raw:
        resolution = resolve_subtopic_mapping(subtopic_raw, canonical_topic)
        if resolution.confident and resolution.roadmap_key != "general":
            roadmap_key = resolution.roadmap_key
    if roadmap_key:
        resolved_entities["roadmap_key"] = roadmap_key
    elif "roadmap_key" in resolved_entities:
        resolved_entities.pop("roadmap_key", None)

    # Step 4 — query learning goals.
    matches = await find_goals_for_delete(
        user_id,
        canonical_topic,
        roadmap_key=roadmap_key,
    )
    match_count = len(matches)

    # Step 5 — handle query results.
    if match_count == 0:
        if roadmap_key:
            language_matches = await find_goals_for_delete(
                user_id,
                canonical_topic,
                roadmap_key=None,
            )
            if len(language_matches) == 1:
                goal = language_matches[0]
                goal_id = _coerce_text(goal.get("_id"))
                if goal_id:
                    requested_level = _requested_level_label(
                        resolved_entities,
                        roadmap_key,
                    )
                    goal_preview = _goal_preview(goal)
                    await redis_client.set_context(
                        user_id,
                        _pending_payload(
                            resolved_entities,
                            goal_ids=[goal_id],
                            goals=[goal_preview],
                            bulk=False,
                            expected_response="yes_no",
                        ),
                    )
                    response_text = _near_miss_prompt(
                        user_name,
                        goal,
                        canonical_topic=canonical_topic,
                        requested_level=requested_level,
                        history=history,
                    )
                    await _save_turn(
                        session_id,
                        user_message,
                        response_text,
                        input_type,
                        resolved_entities,
                    )
                    return {
                        "status": "pending",
                        "intent": "learning_delete",
                        "response_text": response_text,
                        "notifications": [],
                        "pending": {
                            "expected_response": "yes_no",
                            "bulk": False,
                            "goal_ids": [goal_id],
                            "near_miss": True,
                        },
                    }

        response_text = _not_found_prompt(user_name, resolved_entities, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            resolved_entities,
        )
        return {
            "status": "not_found",
            "intent": "learning_delete",
            "response_text": response_text,
            "notifications": [],
            "match_count": 0,
        }

    if match_count == 1:
        goal = matches[0]
        goal_id = _coerce_text(goal.get("_id"))
        if not goal_id:
            response_text = _not_found_prompt(user_name, resolved_entities, history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                resolved_entities,
            )
            return {
                "status": "not_found",
                "intent": "learning_delete",
                "response_text": response_text,
                "notifications": [],
                "match_count": 0,
            }

        goal_preview = _goal_preview(goal)
        await redis_client.set_context(
            user_id,
            _pending_payload(
                resolved_entities,
                goal_ids=[goal_id],
                goals=[goal_preview],
                bulk=False,
                expected_response="yes_no",
            ),
        )
        response_text = _single_confirm_prompt(
            user_name,
            goal,
            history,
            canonical_topic=canonical_topic,
        )
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            resolved_entities,
        )
        return {
            "status": "pending",
            "intent": "learning_delete",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "yes_no",
                "bulk": False,
                "goal_ids": [goal_id],
            },
        }

    if 2 <= match_count <= 5:
        goal_ids: List[str] = []
        goal_list: List[Dict[str, Any]] = []
        for goal in matches:
            goal_id = _coerce_text(goal.get("_id"))
            if not goal_id:
                continue
            goal_ids.append(goal_id)
            goal_list.append(_goal_preview(goal))

        if not goal_ids:
            response_text = _not_found_prompt(user_name, resolved_entities, history)
            await _save_turn(
                session_id,
                user_message,
                response_text,
                input_type,
                resolved_entities,
            )
            return {
                "status": "not_found",
                "intent": "learning_delete",
                "response_text": response_text,
                "notifications": [],
                "match_count": 0,
            }

        await redis_client.set_context(
            user_id,
            _pending_payload(
                resolved_entities,
                goal_ids=goal_ids,
                goals=goal_list,
                bulk=False,
                expected_response="number",
            ),
        )
        response_text = _multi_list_prompt(user_name, matches, resolved_entities, history)
        await _save_turn(
            session_id,
            user_message,
            response_text,
            input_type,
            resolved_entities,
        )
        return {
            "status": "pending",
            "intent": "learning_delete",
            "response_text": response_text,
            "notifications": [],
            "pending": {
                "expected_response": "number",
                "bulk": False,
                "goal_count": len(goal_ids),
            },
        }

    response_text = _too_broad_prompt(user_name, resolved_entities, history)
    await _save_turn(
        session_id,
        user_message,
        response_text,
        input_type,
        resolved_entities,
    )
    return {
        "status": "too_broad",
        "intent": "learning_delete",
        "response_text": response_text,
        "notifications": [],
        "match_count": match_count,
    }
