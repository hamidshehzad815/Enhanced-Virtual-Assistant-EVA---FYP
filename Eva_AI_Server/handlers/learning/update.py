"""
Learning goal update handler (learning_update intent).
Supports sub-intents: pause, resume, complete, skip, reschedule.

Phase 5: handler orchestration and DB operations.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from bson import ObjectId

from context.redis_client import redis_client
from db.activity_logs import insert_log
from db.chat_sessions import update_last_message
from db.conversation_history import insert_message
from db.learning_goals import (
    complete_goal,
    find_goals_for_update,
    get_active_goals_for_user,
    get_goal_by_id,
    pause_goal,
    resume_goal,
    set_started_at,
    update_end_date,
)
from db.roadmap_topics import (
    complete_topic,
    get_all_pending_sessions,
    get_current_session,
    get_pending_sessions_after,
    get_topics_for_goal,
    skip_topic,
)
from db.tasks import get_task_by_id, soft_delete_task, update_task
from handlers.scheduling.add import _coerce_text, _pick_active_google_integration
from services.gemini import gemini_service
from services.google_calendar import google_calendar_client
from utils.learning_utils import (
    SUPPORTED_TOPICS,
    build_schedule,
    compute_session_state,
    detect_learning_sub_intent,
    level_keys_for_language,
    map_subtopic,
    normalize_topic,
)
from utils.timezone_utils import get_zoneinfo, resolve_timezone_name


def _to_object_id(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))
    except Exception:
        return value


def _now_naive_utc() -> datetime:
    return datetime.now(dt_timezone.utc).replace(tzinfo=None)


def _topic_label(entities: Dict[str, Any]) -> str:
    return _coerce_text(entities.get("topic")) or "that topic"


def _goal_preview(goal: Dict[str, Any]) -> Dict[str, Any]:
    title = _coerce_text(goal.get("title"))
    roadmap_key = _coerce_text(goal.get("roadmap_key"))
    subject = _coerce_text(goal.get("subject"))
    if not title:
        if subject and roadmap_key:
            title = f"{subject} {roadmap_key}"
        else:
            title = subject or roadmap_key or "Learning goal"
    return {
        "_id": _coerce_text(goal.get("_id")),
        "title": title,
        "roadmap_key": roadmap_key,
        "subject": subject,
        "status": _coerce_text(goal.get("status")) or "active",
        "completed_topics": int(goal.get("completed_topics") or 0),
        "total_topics": int(goal.get("total_topics") or 0),
    }


def _pending_payload(
    sub_intent: str,
    stage: str,
    entities: Dict[str, Any],
    *,
    expected_response: str,
    goal_ids: Optional[List[str]] = None,
    goals: Optional[List[Dict[str, Any]]] = None,
    goal_id: Optional[str] = None,
    goal: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    action: Dict[str, Any] = {
        "intent": "learning_update",
        "sub_intent": sub_intent,
        "stage": stage,
        "goal_ids": list(goal_ids or []),
        "goals": list(goals or []),
        "goal_id": goal_id,
        "goal": goal,
        "entities": dict(entities or {}),
    }
    return {"expected_response": expected_response, "pending_action": action}


async def _save_turn(
    session_id: str,
    user_message: str,
    eva_reply: str,
    input_type: str,
    entities: Optional[Dict[str, Any]] = None,
    *,
    sub_intent: Optional[str] = None,
) -> None:
    if not session_id:
        return
    now = _now_naive_utc()
    try:
        await insert_message(
            {
                "session_id": session_id,
                "role": "user",
                "content": user_message,
                "input_type": input_type or "text",
                "intent": "learning_update",
                "entities": entities or {},
                "status": "processed",
                "created_at": now,
                "sub_intent": sub_intent,
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
        print(f"[LearningUpdate] Failed to save turn: {error}")


def _missing_sub_intent_prompt(user_name: Optional[str], history: List[Dict[str, Any]]) -> str:
    msg = gemini_service.generate_reply(
        {
            "action": "validation_error",
            "detail": "learning_update_missing_sub_intent",
        },
        user_name,
        history,
    )
    if msg and str(msg).strip():
        return msg
    if user_name:
        return (
            f"I can pause, resume, mark complete, skip, or reschedule a learning session, {user_name}. "
            "What would you like to do?"
        )
    return "I can pause, resume, mark complete, skip, or reschedule a learning session. What would you like to do?"


def _unsupported_topic_prompt(user_name: Optional[str], topic_raw: str) -> str:
    sample = ", ".join(sorted(SUPPORTED_TOPICS)[:8])
    if user_name:
        return (
            f"I couldn't find a learning roadmap for {topic_raw}, {user_name}. "
            f"Try one of the supported topics — e.g. {sample}."
        )
    return f"I couldn't find a learning roadmap for {topic_raw}. Try one of: {sample}."


def _too_broad_prompt(user_name: Optional[str], sub_intent: str) -> str:
    if user_name:
        return f"That matches quite a few goals, {user_name}. Can you add the level (like 'basics')?"
    return "That matches quite a few goals. Can you add the level (like 'basics')?"


def _list_prompt(
    user_name: Optional[str],
    goals: List[Dict[str, Any]],
    *,
    intro: str,
) -> str:
    lines: List[str] = [intro]
    for idx, goal in enumerate(goals, start=1):
        p = _goal_preview(goal)
        progress = (
            f"{p['completed_topics']}/{p['total_topics']} done" if p["total_topics"] > 0 else p["status"]
        )
        lines.append(f"{idx}. {p['title']} — {p['status']} — {progress}")
    return "\n".join(lines)


def _confirm_prompt(user_name: Optional[str], sub_intent: str, goal: Dict[str, Any]) -> str:
    p = _goal_preview(goal)
    title = p["title"]
    if sub_intent == "pause":
        if user_name:
            return f"Pause {title}, {user_name}? Your progress will be saved."
        return f"Pause {title}? Your progress will be saved."
    if sub_intent == "resume":
        if user_name:
            return f"Resume {title}, {user_name}? I'll rebase your schedule from today."
        return f"Resume {title}? I'll rebase your schedule from today."
    if user_name:
        return f"Confirm that change for {title}, {user_name}?"
    return f"Confirm that change for {title}?"


def _learning_days(preferred_learning_schedule: Any) -> Set[int]:
    out: Set[int] = set()
    if not isinstance(preferred_learning_schedule, list):
        return out
    for slot in preferred_learning_schedule:
        if not isinstance(slot, dict):
            continue
        try:
            out.add(int(slot.get("day")))
        except (TypeError, ValueError):
            continue
    return out


def _next_learning_date(start: date, days: Set[int]) -> date:
    current = start
    for _ in range(14):
        if current.weekday() in days:
            return current
        current = current + timedelta(days=1)
    return start


def _schedule_slot_for_day(schedule: List[Dict[str, Any]], weekday: int) -> Tuple[time, int]:
    """
    Return (time, duration_minutes) for a given weekday from preferred_learning_schedule.
    """
    for slot in schedule or []:
        if not isinstance(slot, dict):
            continue
        try:
            if int(slot.get("day")) != int(weekday):
                continue
        except (TypeError, ValueError):
            continue
        t_raw = str(slot.get("time") or "18:00").strip()
        hh, mm = t_raw.split(":") if ":" in t_raw else (t_raw, "00")
        t_val = time(hour=int(hh), minute=int(mm))
        dur = int(slot.get("duration_minutes") or 90)
        return t_val, max(15, min(240, dur))
    return time(hour=18, minute=0), 90


async def _update_task_and_calendar(
    *,
    user_id: str,
    task_id: str,
    due_dt: datetime,
    timezone_name: str,
    google_integration: Optional[Dict[str, Any]],
) -> None:
    # Update task
    await update_task(task_id, {"due_datetime": due_dt})

    if not google_integration:
        return
    token = str(google_integration.get("access_token") or "")
    cal_id = str(google_integration.get("calendar_id") or "")
    if not token or not cal_id:
        return

    try:
        task_doc = await get_task_by_id(task_id, user_id)
        event_id = str((task_doc or {}).get("google_calendar_event_id") or "").strip()
        if not event_id:
            return
        ok = await google_calendar_client.update_event(
            token,
            cal_id,
            event_id,
            {
                "due_datetime": due_dt,
                "title": (task_doc or {}).get("title") or "Learning session",
                "duration_minutes": (task_doc or {}).get("duration") or 90,
                "timezone": timezone_name,
            },
        )
        _ = ok
    except Exception as error:
        print(f"[LearningUpdate] calendar update failed: {error}")


async def _rebuild_pending_schedule(
    *,
    user_id: str,
    goal_id: str,
    pending_topics: List[Dict[str, Any]],
    start_from: date,
    preferred_learning_schedule: List[Dict[str, Any]],
    timezone_name: str,
    google_integration: Optional[Dict[str, Any]],
) -> Optional[datetime]:
    """
    Recompute scheduled_date for pending topics sequentially from start_from using preferred schedule.
    Updates linked tasks and calendar events (best-effort).
    Returns last session datetime (for updating goal end_date).
    """
    if not pending_topics or not preferred_learning_schedule:
        return None

    # build_schedule expects {order,title,resources}
    topics_for_builder: List[Dict[str, Any]] = []
    for row in pending_topics:
        topics_for_builder.append(
            {
                "order": int(row.get("order") or 0),
                "title": str(row.get("title") or ""),
                "resources": list(row.get("resources") or []),
            }
        )

    schedule_rows = build_schedule(start_from, topics_for_builder, preferred_learning_schedule)
    if not schedule_rows or len(schedule_rows) != len(pending_topics):
        return None

    last_dt: Optional[datetime] = None
    for topic, scheduled in zip(pending_topics, schedule_rows):
        due_dt = scheduled["scheduled_date"]
        last_dt = due_dt
        await rt_reschedule_topic(str(topic.get("_id")), due_dt)
        task_id = str(topic.get("task_id") or "").strip()
        if task_id:
            await _update_task_and_calendar(
                user_id=user_id,
                task_id=task_id,
                due_dt=due_dt,
                timezone_name=timezone_name,
                google_integration=google_integration,
            )

    return last_dt


# Local import to avoid circular reference (roadmap_topics imports learning_goals).
from db.roadmap_topics import reschedule_topic as rt_reschedule_topic  # noqa: E402


async def handle_learning_update(
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
    preferred_learning_schedule = list(settings.get("preferred_learning_schedule") or [])

    pending_reply_type = str(context.get("pending_reply_type") or "").strip().lower()
    pending_reply_value = context.get("pending_reply_value")
    pending_context = context.get("pending_context") or {}
    pending_action = pending_context.get("pending_action") or {}

    async def finish(reply: str, **extra: Any) -> Dict[str, Any]:
        await _save_turn(
            session_id,
            user_message,
            reply,
            input_type,
            entities,
            sub_intent=str(extra.get("sub_intent") or "") or None,
        )
        out: Dict[str, Any] = {
            "status": extra.pop("status", "ok"),
            "intent": "learning_update",
            "response_text": reply,
            "notifications": extra.pop("notifications", []),
        }
        out.update(extra)
        return out

    if not user_id:
        return await finish("I need a signed-in user to update a learning plan.", status="error")

    # Step 0: detect sub-intent (unless coming from pending confirmation)
    sub_intent = str(entities.get("sub_intent") or "").strip().lower()
    if not sub_intent:
        sub_intent = detect_learning_sub_intent(user_message)
    if not sub_intent and pending_action.get("intent") == "learning_update":
        sub_intent = str(pending_action.get("sub_intent") or "").strip().lower()
    if sub_intent not in {"pause", "resume", "complete", "skip", "reschedule"}:
        return await finish(_missing_sub_intent_prompt(user_name, history), status="error")

    # Step 1: handle yes/no confirmation for pause/resume
    if (
        pending_action.get("intent") == "learning_update"
        and pending_reply_type == "yes_no"
        and pending_reply_value in {"yes", "no"}
    ):
        pending_goal_id = str(pending_action.get("goal_id") or "").strip() or (
            str((pending_action.get("goal_ids") or [""])[0])
        )
        goal = pending_action.get("goal") or {}
        pending_sub = str(pending_action.get("sub_intent") or sub_intent).strip().lower()
        if pending_reply_value == "no":
            await redis_client.delete_context(user_id)
            msg = f"No problem {user_name}, nothing was changed." if user_name else "No problem, nothing was changed."
            return await finish(msg, status="cancelled", sub_intent=pending_sub)

        # yes
        await redis_client.delete_context(user_id)
        if pending_sub == "pause":
            ok = await pause_goal(pending_goal_id)
            if not ok:
                return await finish("I couldn't pause that plan right now. Please try again.", status="error")
            title = _goal_preview(goal).get("title") or "that plan"
            msg = f"{title} is paused, {user_name}. Your progress is saved." if user_name else f"{title} is paused. Your progress is saved."
            return await finish(msg, status="success", sub_intent="pause")

        if pending_sub == "resume":
            ok = await resume_goal(pending_goal_id)
            if not ok:
                return await finish("I couldn't resume that plan right now. Please try again.", status="error")

            google = _pick_active_google_integration(integrations)
            days = _learning_days(preferred_learning_schedule)
            today = datetime.now(get_zoneinfo(tz)).date()
            start_from = _next_learning_date(today + timedelta(days=1), days) if days else today + timedelta(days=1)
            pending_topics = await get_all_pending_sessions(pending_goal_id)
            last_dt = await _rebuild_pending_schedule(
                user_id=user_id,
                goal_id=pending_goal_id,
                pending_topics=pending_topics,
                start_from=start_from,
                preferred_learning_schedule=preferred_learning_schedule,
                timezone_name=tz,
                google_integration=google,
            )
            if last_dt:
                await update_end_date(pending_goal_id, last_dt)
            title = _goal_preview(goal).get("title") or "that plan"
            next_session = await get_current_session(pending_goal_id)
            next_dt = next_session.get("scheduled_date") if isinstance(next_session, dict) else None
            next_text = ""
            if isinstance(next_dt, datetime):
                next_text = f" Next session: {next_dt.strftime('%Y-%m-%d %H:%M')}."
            msg = (
                f"{title} is active again, {user_name}. I rebased your schedule from today.{next_text}"
                if user_name
                else f"{title} is active again. I rebased your schedule from today.{next_text}"
            )
            return await finish(msg, status="success", sub_intent="resume")

        return await finish("Got it.", status="ok", sub_intent=pending_sub)

    # Step 2: identify topic/subtopic (when present)
    raw_topic = _coerce_text(entities.get("topic"))
    canonical_topic = normalize_topic(raw_topic) if raw_topic else None
    if raw_topic and not canonical_topic:
        return await finish(_unsupported_topic_prompt(user_name, raw_topic), status="error", sub_intent=sub_intent)
    if canonical_topic:
        entities["topic"] = canonical_topic
    if entities.get("subtopic") and canonical_topic:
        try:
            entities["roadmap_key"] = map_subtopic(
                entities.get("subtopic"),
                canonical_topic,
                level_keys=level_keys_for_language(canonical_topic),
            )
        except Exception:
            entities["roadmap_key"] = map_subtopic(entities.get("subtopic"), canonical_topic)

    # Pause/resume: require topic (or free_text State 1)
    if sub_intent in {"pause", "resume"} and not canonical_topic:
        await redis_client.set_context(
            user_id,
            _pending_payload(
                sub_intent,
                "identify",
                entities,
                expected_response="free_text",
            ),
        )
        ask = (
            f"Which learning goal would you like to {sub_intent}, {user_name}?"
            if user_name
            else f"Which learning goal would you like to {sub_intent}?"
        )
        return await finish(ask, status="pending", sub_intent=sub_intent)

    # Step 3: query matching goals for sub-intent
    status_filter = None
    if sub_intent == "pause":
        status_filter = "active"
    if sub_intent == "resume":
        status_filter = "paused"

    roadmap_key = str(entities.get("roadmap_key") or "").strip().lower() or None
    matches: List[Dict[str, Any]] = []
    if canonical_topic:
        matches = await find_goals_for_update(
            user_id,
            canonical_topic,
            roadmap_key=roadmap_key,
            status_filter=status_filter,
        )

    # For complete/skip/reschedule with no topic: if exactly one active goal, pick it; else prompt State 4.
    if sub_intent in {"complete", "skip", "reschedule"} and not canonical_topic:
        active = await get_active_goals_for_user(user_id)
        if len(active) == 1:
            matches = active
        else:
            if not active:
                msg = "I couldn't find any active learning goals to update."
                return await finish(msg, status="not_found", sub_intent=sub_intent)
            previews = [_goal_preview(g) for g in active][:5]
            goal_ids = [p["_id"] for p in previews]
            await redis_client.set_context(
                user_id,
                _pending_payload(
                    sub_intent,
                    "identify_language",
                    entities,
                    expected_response="number",
                    goal_ids=goal_ids,
                    goals=previews,
                ),
            )
            intro = (
                f"You have multiple active learning goals, {user_name}. Which one?"
                if user_name
                else "You have multiple active learning goals. Which one?"
            )
            return await finish(_list_prompt(user_name, previews, intro=intro), status="pending", sub_intent=sub_intent)

    # Handle no matches for topic-specific queries
    if canonical_topic and not matches:
        msg = (
            f"I couldn't find any {status_filter or ''} {canonical_topic} learning goals.".strip()
            if not user_name
            else f"I couldn't find any {status_filter or ''} {canonical_topic} learning goals, {user_name}.".strip()
        )
        return await finish(msg, status="not_found", sub_intent=sub_intent)

    if len(matches) >= 6:
        return await finish(_too_broad_prompt(user_name, sub_intent), status="too_broad", sub_intent=sub_intent)

    # 2-5 matches → number list
    if 2 <= len(matches) <= 5:
        previews = [_goal_preview(g) for g in matches]
        goal_ids = [p["_id"] for p in previews]
        stage = "identify" if sub_intent in {"pause", "resume"} else "identify_language"
        await redis_client.set_context(
            user_id,
            _pending_payload(
                sub_intent,
                stage,
                entities,
                expected_response="number",
                goal_ids=goal_ids,
                goals=previews,
            ),
        )
        intro = (
            f"I found {len(previews)} {_topic_label(entities)} goals, {user_name}. Which one?"
            if user_name
            else f"I found {len(previews)} {_topic_label(entities)} goals. Which one?"
        )
        return await finish(_list_prompt(user_name, previews, intro=intro), status="pending", sub_intent=sub_intent)

    # 1 match
    goal = matches[0] if matches else {}
    goal_id = _coerce_text(goal.get("_id"))

    if sub_intent in {"pause", "resume"}:
        await redis_client.set_context(
            user_id,
            _pending_payload(
                sub_intent,
                "confirm",
                entities,
                expected_response="yes_no",
                goal_ids=[goal_id],
                goals=[_goal_preview(goal)],
                goal_id=goal_id,
                goal=_goal_preview(goal),
            ),
        )
        return await finish(_confirm_prompt(user_name, sub_intent, goal), status="pending", sub_intent=sub_intent)

    # Sub-intents: complete / skip / reschedule execute immediately on identified goal
    goal_full = await get_goal_by_id(goal_id)
    if not goal_full:
        return await finish("I couldn't load that learning plan right now.", status="error", sub_intent=sub_intent)

    # Find current session (pending topic)
    current = await get_current_session(goal_id)
    if not current:
        return await finish("I couldn't find a pending session for that plan.", status="not_found", sub_intent=sub_intent)

    # Gap-aware state computation
    all_topics = await get_topics_for_goal(goal_id)
    prev_scheduled = None
    prev_resolved = None
    try:
        cur_order = int(current.get("order") or 0)
        prev = next((t for t in all_topics if int(t.get("order") or 0) == cur_order - 1), None)
        if prev:
            prev_scheduled = prev.get("scheduled_date")
            prev_resolved = prev.get("completed_at") or prev.get("updated_at")
    except Exception:
        prev_scheduled = None
        prev_resolved = None

    state = compute_session_state(
        current,
        datetime.now(get_zoneinfo(tz)),
        previous_scheduled_date=prev_scheduled,
        previous_resolved_at=prev_resolved,
    )

    if sub_intent == "complete":
        if state != "overdue":
            if state == "locked":
                return await finish("That session is still locked. It unlocks within 24 hours of its scheduled time.", status="blocked")
            if state == "unlocked_future":
                return await finish("That session hasn't started yet, so I can't mark it complete. You can reschedule or skip it.", status="blocked")
            return await finish("That session can't be completed right now.", status="blocked")

        ok = await complete_topic(str(current.get("_id")))
        if not ok:
            return await finish("I couldn't mark that session complete right now. Please try again.", status="error")

        # Ensure started_at exists once.
        await set_started_at(goal_id)

        # Activity log (one per completion)
        try:
            task_id = current.get("task_id")
            await insert_log(
                {
                    "user_id": _to_object_id(user_id),
                    "task_id": _to_object_id(task_id) if task_id else None,
                    "action_type": "task_completed",
                    "subject": (canonical_topic or (goal_full.get("subject") or "")).strip().lower(),
                    "source": "learning_module",
                }
            )
        except Exception as error:
            print(f"[LearningUpdate] insert_log failed: {error}")

        refreshed_goal = await get_goal_by_id(goal_id)
        done = int((refreshed_goal or {}).get("completed_topics") or 0)
        total = int((refreshed_goal or {}).get("total_topics") or 0)
        title = str((refreshed_goal or {}).get("title") or _goal_preview(goal_full).get("title") or "your plan")
        if (refreshed_goal or {}).get("status") == "completed":
            msg = f'Amazing — you finished "{title}"!'
            if user_name:
                msg = f"{msg} Great work, {user_name}."
            return await finish(msg, status="success", sub_intent="complete")
        msg = f'Nice — I marked the session complete ({done}/{total} in "{title}").'
        if user_name:
            msg = f"{msg} Keep going, {user_name}."
        return await finish(msg, status="success", sub_intent="complete")

    if sub_intent == "skip":
        if state != "unlocked_future":
            if state == "locked":
                return await finish("That session is still locked, so it can't be skipped yet.", status="blocked")
            if state == "overdue":
                return await finish("That session is overdue — you can mark it complete or reschedule it, but not skip it.", status="blocked")
            return await finish("That session can't be skipped right now.", status="blocked")

        ok = await skip_topic(str(current.get("_id")))
        if not ok:
            return await finish("I couldn't skip that session right now. Please try again.", status="error")

        # Soft-delete linked task + delete calendar event best-effort
        google = _pick_active_google_integration(integrations)
        task_id = str(current.get("task_id") or "").strip()
        if task_id:
            try:
                task_doc = await get_task_by_id(task_id, user_id)
                await soft_delete_task(task_id)
                if google and task_doc:
                    event_id = str(task_doc.get("google_calendar_event_id") or "").strip()
                    if event_id:
                        await google_calendar_client.delete_event(
                            str(google.get("access_token") or ""),
                            str(google.get("calendar_id") or ""),
                            event_id,
                        )
            except Exception as error:
                print(f"[LearningUpdate] skip calendar/task cleanup failed: {error}")

        # Cascade remaining sessions (pending after current) from current scheduled date.
        start_date = (
            current.get("scheduled_date").date()
            if isinstance(current.get("scheduled_date"), datetime)
            else datetime.now(get_zoneinfo(tz)).date()
        )
        later = await get_pending_sessions_after(goal_id, int(current.get("order") or 0))
        last_dt = await _rebuild_pending_schedule(
            user_id=user_id,
            goal_id=goal_id,
            pending_topics=later,
            start_from=start_date,
            preferred_learning_schedule=preferred_learning_schedule,
            timezone_name=tz,
            google_integration=google,
        )
        if last_dt:
            await update_end_date(goal_id, last_dt)

        msg = "Done — I skipped that session and shifted the rest of your schedule forward."
        if user_name:
            msg = f"{msg} You're all set, {user_name}."
        return await finish(msg, status="success", sub_intent="skip")

    if sub_intent == "reschedule":
        if state == "locked":
            return await finish("That session is still locked. It unlocks within 24 hours of its scheduled time.", status="blocked")

        # Date must be present (from NER or from State 5)
        iso = _coerce_text(entities.get("date"))
        if not iso:
            await redis_client.set_context(
                user_id,
                _pending_payload(
                    "reschedule",
                    "new_date",
                    entities,
                    expected_response="free_text",
                    goal_id=goal_id,
                    goal=_goal_preview(goal_full),
                ),
            )
            days = _learning_days(preferred_learning_schedule)
            days_hint = ""
            if days:
                days_hint = f" Your learning days are {', '.join(str(d) for d in sorted(days))}."
            ask = f"What date would you like to move your session to, {user_name}?" if user_name else "What date would you like to move your session to?"
            return await finish(ask + days_hint, status="pending", sub_intent="reschedule")

        try:
            new_d = datetime.strptime(iso[:10], "%Y-%m-%d").date()
        except ValueError:
            return await finish("I couldn't understand that date. Try again like 'next Monday'.", status="error")

        days = _learning_days(preferred_learning_schedule)
        if days and new_d.weekday() not in days:
            return await finish("That isn't one of your learning days. Pick a valid learning day.", status="error")

        slot_time, _dur = _schedule_slot_for_day(preferred_learning_schedule, new_d.weekday())
        new_dt = datetime.combine(new_d, slot_time)

        # Decide cascade vs single move
        later = await get_pending_sessions_after(goal_id, int(current.get("order") or 0))
        next_dt = None
        if later and isinstance(later[0].get("scheduled_date"), datetime):
            next_dt = later[0]["scheduled_date"]

        google = _pick_active_google_integration(integrations)

        if next_dt is None or new_dt < next_dt:
            ok = await rt_reschedule_topic(str(current.get("_id")), new_dt)
            if not ok:
                return await finish("I couldn't move that session right now. Please try again.", status="error")
            task_id = str(current.get("task_id") or "").strip()
            if task_id:
                await _update_task_and_calendar(
                    user_id=user_id,
                    task_id=task_id,
                    due_dt=new_dt,
                    timezone_name=tz,
                    google_integration=google,
                )
            msg = "Done — I moved just your next session."
            if user_name:
                msg = f"{msg} All set, {user_name}."
            return await finish(msg, status="success", sub_intent="reschedule")

        # Cascade: rebuild current + later starting from new date
        pending_all = [current] + later
        last_dt = await _rebuild_pending_schedule(
            user_id=user_id,
            goal_id=goal_id,
            pending_topics=pending_all,
            start_from=new_d,
            preferred_learning_schedule=preferred_learning_schedule,
            timezone_name=tz,
            google_integration=google,
        )
        if last_dt:
            await update_end_date(goal_id, last_dt)
        msg = "Done — I moved your next session and rebased the remaining sessions after it."
        if user_name:
            msg = f"{msg} You're all set, {user_name}."
        return await finish(msg, status="success", sub_intent="reschedule")

    return await finish("Ok.", status="ok", sub_intent=sub_intent)

