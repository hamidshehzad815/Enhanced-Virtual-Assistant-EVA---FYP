"""
Learning plan creation (learning_create intent) — roadmap, goals, topics, tasks.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any, Dict, List, Optional, Set

from bson import ObjectId

from context.redis_client import redis_client
from db.activity_logs import insert_log
from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.learning_goals import find_conflicting_goal, insert_goal
from db.roadmap_resources import get_roadmap, get_sessions_required
from db.roadmap_topics import insert_topics_bulk, update_topic_task_id
from db.tasks import find_overlapping_task_for_user, insert_task, update_task
from handlers.scheduling.add import (
    _coerce_text,
    _find_and_validate_collaborators,
    _format_date_display,
    _format_time_display,
    _split_collaborators,
)
from utils.google_calendar_sync import resolve_google_calendar_sync
from services.duckling import duckling_client
from services.gemini import gemini_service
from services.google_calendar import google_calendar_client
from utils.collaborator_calendar import (
    find_user_calendar_conflicts,
    format_collaborator_conflict_message,
)
from utils.learning_schedules import (
    DEFAULT_DURATION_MINUTES,
    resolve_schedule_for_learning,
    schedules_from_settings,
    used_learning_schedule_ids,
)
from utils.quiet_hours import (
    find_quiet_hour_matches_for_datetime,
    format_quiet_hours_learning_block_message,
)
from utils.learning_utils import (
    resolve_learning_reminder_minutes,
    SUPPORTED_TOPICS,
    build_schedule,
    calculate_available_sessions,
    duration_entity_to_days,
    normalize_subtopic_entity,
    normalize_topic,
    resolve_subtopic_mapping,
    subtopic_hint_from_message,
)
from utils.timezone_utils import get_zoneinfo, resolve_timezone_name, utc_naive_to_local

logger = logging.getLogger(__name__)


def _to_object_id(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))
    except Exception:
        return value


def _today_date(tz_name: str) -> date:
    return datetime.now(get_zoneinfo(tz_name)).date()


def _learning_days(schedule: Any) -> Set[int]:
    days: Set[int] = set()
    if not isinstance(schedule, list):
        return days
    for slot in schedule:
        if isinstance(slot, dict) and "day" in slot:
            try:
                days.add(int(slot["day"]))
            except (TypeError, ValueError):
                continue
    return days


def _pending_payload(entities: Dict[str, Any], stage: str) -> Dict[str, Any]:
    return {
        "pending_action": {
            "intent": "learning_create",
            "stage": stage,
            "entities": dict(entities),
        },
        "expected_response": "free_text",
    }


async def _save_turn(
    session_id: str,
    user_message: str,
    eva_reply: str,
    input_type: str,
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
                "intent": "learning_create",
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
        print(f"[LearningCreate] conversation save failed: {error}")


def _session_preview_label(stored_dt: datetime, timezone_name: str) -> str:
    """Format UTC-naive stored instant as local date/time for chat display."""
    local_dt = utc_naive_to_local(stored_dt, timezone_name)
    if local_dt is None:
        return ""
    return (
        f"{_format_date_display(local_dt.date().isoformat())} at "
        f"{_format_time_display(local_dt.strftime('%H:%M:%S'))}"
    )


def _topic_raw(entities: Dict[str, Any]) -> str:
    return _coerce_text(entities.get("topic"))


def _subtopic_clarification_message(
    topic: str,
    heard: str,
    user_name: Optional[str],
) -> str:
    name_bit = f", {user_name}" if user_name else ""
    heard_bit = f' "{heard}"' if heard else ""
    return (
        f"I couldn't tell which {topic} level you meant from{heard_bit}{name_bit}. "
        "Reply with something like basics (beginner), intermediate, advanced, "
        "or a specific focus (e.g. OOP, loops, lists)."
    )


def _start_iso(entities: Dict[str, Any]) -> str:
    raw = _coerce_text(entities.get("start_date"))
    if not raw:
        return ""
    if "T" in raw:
        return raw.split("T")[0][:10]
    return raw[:10]


def _duration_days_value(entities: Dict[str, Any]) -> Optional[int]:
    raw = entities.get("duration_days")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    return duration_entity_to_days(entities.get("duration"))


async def handle_learning_create(
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
    integrations = list(context.get("integrations") or [])
    user_message = str(context.get("message") or "")
    input_type = str(context.get("input_type") or "text")
    user_name = user.get("name")
    tz = resolve_timezone_name(user.get("timezone"))
    labeled_schedules = schedules_from_settings(settings)

    reminder_minutes = resolve_learning_reminder_minutes(settings)
    schedule_slots: List[Dict[str, Any]] = []
    chosen_schedule_id = ""

    async def finish(reply: str, **extra: Any) -> Dict[str, Any]:
        await _save_turn(session_id, user_message, reply, input_type, entities)
        out: Dict[str, Any] = {
            "status": extra.pop("status", "ok"),
            "intent": "learning_create",
            "response_text": reply,
            "notifications": extra.pop("notifications", []),
        }
        out.update(extra)
        return out

    if not user_id:
        msg = "I need a signed-in user to create a learning plan."
        return await finish(msg, status="error")

    if not labeled_schedules:
        msg = (
            "Set up at least one labeled learning schedule in Settings "
            "(pick your days, times, and how long each session should run), then ask me again."
        )
        return await finish(msg, status="pending")

    raw_topic = _topic_raw(entities)
    canonical_topic = normalize_topic(raw_topic) if raw_topic else None

    if not raw_topic:
        await redis_client.set_context(user_id, _pending_payload(entities, "topic"))
        msg = gemini_service.generate_reply(
            {"action": "learning_missing_topic"},
            user_name,
            history,
        )
        if not msg or not str(msg).strip():
            msg = "What topic would you like to learn? For example, Python, JavaScript, or MySQL."
        return await finish(msg, status="pending")

    if not canonical_topic:
        sample = ", ".join(sorted(SUPPORTED_TOPICS)[:8])
        msg = (
            "That topic isn't in our roadmaps yet. "
            f"Try one of the supported tracks — e.g. {sample}. "
            "I can list all if you ask."
        )
        return await finish(msg, status="error")

    entities["topic"] = canonical_topic
    subtopic_raw = normalize_subtopic_entity(entities.get("subtopic"))
    if not subtopic_raw:
        subtopic_raw = subtopic_hint_from_message(user_message)
    if subtopic_raw:
        entities["subtopic"] = subtopic_raw

    subtopic_resolution = resolve_subtopic_mapping(subtopic_raw, canonical_topic)
    if subtopic_raw and not subtopic_resolution.confident:
        await redis_client.set_context(
            user_id,
            _pending_payload(entities, "subtopic"),
        )
        return await finish(
            _subtopic_clarification_message(canonical_topic, subtopic_raw, user_name),
            status="pending",
            expected_response="free_text",
            stage="subtopic",
        )

    roadmap_key = subtopic_resolution.roadmap_key

    conflicting = await find_conflicting_goal(user_id, canonical_topic, roadmap_key)
    if conflicting:
        existing_track = str(conflicting.get("roadmap_key") or "general").replace("_", " ")
        requested_track = roadmap_key.replace("_", " ")
        track_hint = (
            f" a {requested_track} roadmap"
            if requested_track and requested_track != "general"
            else " another roadmap"
        )
        msg = (
            f"You already have an active {canonical_topic} learning plan"
            f"{f' ({existing_track})' if existing_track and existing_track != 'general' else ''}. "
            f"Only one {canonical_topic} roadmap is allowed at a time. "
            f"Complete that plan first, or delete it, before creating{track_hint}."
        )
        return await finish(msg, status="error")

    start_s = _start_iso(entities)
    if not start_s:
        await redis_client.set_context(
            user_id,
            _pending_payload(entities, "start_date"),
        )
        msg = gemini_service.generate_reply(
            {"action": "learning_missing_start_date", "topic": canonical_topic},
            user_name,
            history,
        )
        if not msg or not str(msg).strip():
            msg = f"When would you like to start learning {canonical_topic}? (e.g. next Monday)"
        return await finish(msg, status="pending")

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", start_s):
        resolved = await duckling_client.resolve_date(start_s, timezone=tz)
        if resolved:
            start_s = resolved[:10]
        else:
            await redis_client.set_context(
                user_id,
                _pending_payload(entities, "start_date"),
            )
            msg = "I couldn't read that date. Try something like “June 10” or “next Monday”."
            return await finish(msg, status="pending")

    try:
        start_d = date.fromisoformat(start_s[:10])
    except ValueError:
        await redis_client.set_context(
            user_id,
            _pending_payload(entities, "start_date"),
        )
        msg = "That doesn't look like a valid start date. Try again with a clearer day."
        return await finish(msg, status="pending")

    today = _today_date(tz)
    if start_d < today:
        await redis_client.set_context(
            user_id,
            _pending_payload(entities, "start_date"),
        )
        msg = "That start date is in the past. Pick today or a future day."
        return await finish(msg, status="pending")

    entities["start_date"] = start_s[:10]

    used_schedule_ids = await used_learning_schedule_ids(user_id)
    chosen_schedule, schedule_err, schedule_pending = resolve_schedule_for_learning(
        entities=entities,
        schedules=labeled_schedules,
        used_ids=used_schedule_ids,
    )
    if schedule_pending:
        await redis_client.set_context(user_id, schedule_pending)
        return await finish(
            schedule_err or "Which learning schedule should I use? Reply with a number.",
            status="pending",
            expected_response="number",
            stage="schedule_choice",
        )
    if schedule_err or not chosen_schedule:
        return await finish(
            schedule_err or "I could not pick a learning schedule. Check Settings and try again.",
            status="error",
        )

    schedule_slots = list(chosen_schedule.get("slots") or [])
    chosen_schedule_id = str(chosen_schedule.get("id") or "")
    entities["learning_schedule_id"] = chosen_schedule_id

    dur_days = _duration_days_value(entities)
    if dur_days is None:
        await redis_client.set_context(
            user_id,
            _pending_payload(entities, "duration"),
        )
        msg = gemini_service.generate_reply(
            {"action": "learning_missing_duration", "topic": canonical_topic},
            user_name,
            history,
        )
        if not msg or not str(msg).strip():
            msg = "How long do you want this plan to run? (e.g. “2 weeks” or “1 month”, at least 7 days.)"
        return await finish(msg, status="pending")

    if dur_days < 7:
        msg = "Learning plans need at least 7 days. Try at least one week or longer."
        return await finish(msg, status="error")

    learning_days = _learning_days(schedule_slots)
    if not learning_days:
        msg = "Add at least one learning day in Settings, then try again."
        return await finish(msg, status="pending")

    sessions_needed = await get_sessions_required(canonical_topic, roadmap_key)
    available = calculate_available_sessions(start_d, int(dur_days), learning_days)
    if sessions_needed > 0 and available < sessions_needed:
        msg = (
            f"In {dur_days} days you only have {available} learning session(s) on your schedule, "
            f"but this roadmap needs {sessions_needed}. "
            "Try a longer period or add more learning days in Settings."
        )
        return await finish(msg, status="pending")

    collab_source = entities.get("person") or entities.get("collaborator")
    collab_names = _split_collaborators(collab_source)
    goal_collaborators: List[Dict[str, Any]] = []
    collab_validated: List[Dict[str, Any]] = []
    if collab_names:
        collab_validated, err = await _find_and_validate_collaborators(user_id, collab_names)
        if err:
            return await finish(err, status="error")
        goal_collaborators = [
            {"user_id": _to_object_id(c["user_id"]), "status": "pending"}
            for c in collab_validated
        ]

    topics_db = await get_roadmap(canonical_topic, roadmap_key)
    if not topics_db:
        logger.warning(
            "No roadmap_resources rows for language=%r level=%r (user_id=%s)",
            canonical_topic,
            roadmap_key,
            user_id,
        )
        track = roadmap_key.replace("_", " ") if roadmap_key else "that track"
        msg = (
            f"I do not have a ready lesson list for {canonical_topic} ({track}) on my side yet, "
            f"so I cannot build this plan right now. Please try a different focus (for example basics or intermediate), "
            f"or try again later once your study library has been refreshed."
        )
        return await finish(msg, status="error")

    scheduled_rows = build_schedule(
        start_d,
        topics_db,
        schedule_slots,
        default_duration_minutes=DEFAULT_DURATION_MINUTES,
        timezone_name=tz,
    )
    for row in scheduled_rows:
        session_dt = row.get("scheduled_date")
        if not isinstance(session_dt, datetime):
            continue
        session_dur = int(row.get("duration_minutes") or DEFAULT_DURATION_MINUTES)
        overlap_task = await find_overlapping_task_for_user(
            user_id,
            session_dt,
            session_dur,
        )
        if overlap_task:
            conflict_title = _coerce_text(overlap_task.get("title")) or "another task"
            session_label = _coerce_text(row.get("title")) or "a lesson"
            msg = (
                f"I can't create this plan because {session_label} would overlap "
                f"your existing task “{conflict_title}”. "
                "Move or delete that task, pick a different learning schedule, or adjust your plan dates."
            )
            return await finish(msg, status="error")

        quiet_matches = find_quiet_hour_matches_for_datetime(
            settings,
            session_dt,
            session_dur,
            timezone_name=tz,
        )
        if quiet_matches:
            session_label = _coerce_text(row.get("title")) or "A learning session"
            msg = format_quiet_hours_learning_block_message(
                quiet_matches,
                session_label=session_label,
                user_name=user_name,
            )
            return await finish(msg, status="error")

        for collab in collab_validated:
            collab_id = str(collab.get("user_id") or "")
            if not collab_id:
                continue
            collab_name = _coerce_text(collab.get("name")) or "Collaborator"
            collab_hit = await find_user_calendar_conflicts(
                collab_id,
                session_dt,
                session_dur,
            )
            if collab_hit:
                msg = format_collaborator_conflict_message(
                    collab_name,
                    collab_hit,
                    for_learning_plan=True,
                )
                return await finish(msg, status="error")

    if len(scheduled_rows) != len(topics_db):
        msg = (
            "I couldn't fit every lesson into that window with your current learning days. "
            "Extend the duration or add more weekly slots in Settings."
        )
        return await finish(msg, status="pending")

    last_dt = scheduled_rows[-1]["scheduled_date"]
    if isinstance(last_dt, datetime):
        end_date = last_dt.date()
    else:
        end_date = start_d + timedelta(days=max(0, int(dur_days) - 1))

    title = f"Learn {canonical_topic}"
    if roadmap_key and roadmap_key != "general":
        title = f"{title} — {roadmap_key}"

    now = datetime.now(dt_timezone.utc).replace(tzinfo=None)
    goal_payload: Dict[str, Any] = {
        "user_id": user_id,
        "title": title,
        "description": None,
        "subject": canonical_topic.lower(),
        "roadmap_key": roadmap_key,
        "learning_schedule_id": chosen_schedule_id or None,
        "start_date": datetime.combine(start_d, datetime.min.time()),
        "end_date": datetime.combine(end_date, datetime.min.time()),
        "duration_days": int(dur_days),
        "total_topics": len(topics_db),
        "completed_topics": 0,
        "status": "active",
        "collaborators": goal_collaborators,
        "generated_by": "eva",
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
    }

    goal_id = await insert_goal(goal_payload)

    bulk_topics: List[Dict[str, Any]] = []
    for idx, row in enumerate(topics_db):
        sch = scheduled_rows[idx]
        sd = sch.get("scheduled_date")
        if not isinstance(sd, datetime):
            sd = datetime.combine(start_d, datetime.min.time())
        row_dur = int(sch.get("duration_minutes") or DEFAULT_DURATION_MINUTES)
        bulk_topics.append(
            {
                "goal_id": goal_id,
                "order": int(row.get("order", 0)),
                "title": str(row.get("title") or ""),
                "resources": row.get("resources") if isinstance(row.get("resources"), list) else [],
                "scheduled_date": sd,
                "estimated_duration": row_dur,
            }
        )
    topic_ids = await insert_topics_bulk(bulk_topics)

    google_integration = await resolve_google_calendar_sync(user_id, integrations, settings)
    access_token = _coerce_text((google_integration or {}).get("access_token"))
    calendar_id = _coerce_text((google_integration or {}).get("calendar_id")) or "primary"
    calendar_any = False

    owner_oid = _to_object_id(user_id)
    for idx, sch in enumerate(scheduled_rows):
        tid = topic_ids[idx]
        due = sch["scheduled_date"]
        if not isinstance(due, datetime):
            continue
        task_title = f"Learn: {_coerce_text(sch.get('title')) or f'Session {idx + 1}'}"
        task_dur = int(sch.get("duration_minutes") or DEFAULT_DURATION_MINUTES)
        task_doc: Dict[str, Any] = {
            "owner_id": owner_oid,
            "title": task_title[:200],
            "due_datetime": due,
            "duration": task_dur,
            "priority": "medium",
            "status": "pending",
            "source": "eva",
            "scheduled_by": "manual",
            "collaborators": [],
            "learning_plan_id": _to_object_id(goal_id),
            "learning_topic_id": _to_object_id(tid),
            "is_deleted": False,
            "reminder_minutes_before": reminder_minutes,
            "created_at": now,
            "updated_at": now,
        }
        task_id = await insert_task(task_doc)

        await update_topic_task_id(tid, task_id)

        if google_integration and access_token:
            try:
                event_id = await google_calendar_client.create_event(
                    token=access_token,
                    calendar_id=calendar_id,
                    task_data={
                        "title": task_title,
                        "due_datetime": due,
                        "duration_minutes": task_dur,
                        "timezone": tz,
                        "description": f"Learning plan: {title}",
                        "reminder_minutes_before": reminder_minutes,
                    },
                )
                if event_id:
                    calendar_any = True
                    await update_task(task_id, {"google_calendar_event_id": event_id})
            except Exception as error:
                print(f"[LearningCreate] Calendar create failed: {error}")

    await insert_log(
        {
            "user_id": owner_oid,
            "action_type": "goal_created",
            "task_id": None,
            "reschedule_count": 0,
            "action_timestamp": now,
            "subject": title,
            "source": "learning_module",
        },
        settings=settings,
    )

    preview: List[str] = []
    for sch in scheduled_rows[:3]:
        dt = sch.get("scheduled_date")
        if isinstance(dt, datetime):
            label = _session_preview_label(dt, tz)
            if label:
                preview.append(label)

    preview_text = "; ".join(preview) if preview else "your first sessions"

    response_text = gemini_service.generate_reply(
        {
            "action": "learning_plan_created",
            "topic": canonical_topic,
            "roadmap_key": roadmap_key,
            "session_count": len(topics_db),
            "preview_sessions": preview_text,
            "collaborators": collab_names or None,
            "calendar_synced": calendar_any,
        },
        user_name,
        history,
    )
    if not response_text or not str(response_text).strip():
        collab_note = ""
        if collab_names:
            collab_note = f" I've invited {', '.join(collab_names)}."
        cal_note = " Sessions were added to your Google Calendar." if calendar_any else ""
        response_text = (
            f"Done — I set up {len(topics_db)} sessions for {canonical_topic} "
            f"starting {_format_date_display(start_s)}. "
            f"First sessions: {preview_text}.{collab_note}{cal_note}"
        )

    await redis_client.delete_context(user_id)

    await _save_turn(session_id, user_message, response_text, input_type, entities)

    notifications: List[Dict[str, Any]] = [
        {
            "user_id": str(user_id),
            "sender_id": None,
            "type": "learning_plan_created",
            "reference_type": "learning_goal",
            "reference_id": str(goal_id),
            "title": "Learning plan ready",
            "message": response_text[:500],
            "action_required": False,
            "delivery_channel": ["push", "in_app", "email"],
        }
    ]

    for c in collab_validated:
        notifications.append(
            {
                "user_id": str(c["user_id"]),
                "sender_id": str(user_id),
                "type": "learning_collaboration_invite",
                "reference_type": "learning_goal",
                "reference_id": str(goal_id),
                "title": "Learning plan invite",
                "message": f"{user_name or 'Your friend'} added you to “{title}”.",
                "action_required": True,
                "delivery_channel": ["push", "in_app", "email"],
            }
        )

    return {
        "status": "success",
        "intent": "learning_create",
        "response_text": response_text,
        "notifications": notifications,
        "learning_goal_id": goal_id,
        "topics_scheduled": len(scheduled_rows),
    }
