"""
EVA AI Server - FastAPI Entry Point
"""
from datetime import date, datetime, timedelta
import re
from typing import Any, Dict, Optional

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings
from config.database import database
from handlers.learning.topic_done_chat import maybe_handle_learning_topic_done_chat
from handlers.general_handler import (
    handle_confirmation_unexpected,
    handle_general,
    handle_help,
    handle_multiple_command,
    handle_out_of_scope,
)
from handlers.router import normalize_intent, route_intent
from handlers.unsupported_chat_intents import (
    build_unsupported_intent_response,
    is_legacy_unsupported_intent,
)
from db.activity_logs import (
    get_avg_time_taken,
    get_completed_logs_for_scoring,
    get_completion_rate,
    get_log_count_per_day,
    get_total_completed,
)
from db.readers import fetch_integrations, fetch_user, fetch_user_settings
from context.context_manager import (
    extract_update_fields,
    handle_free_text_reply,
    handle_number_delete,
    handle_number_learning_delete,
    handle_number_learning_update,
    handle_number_update,
    handle_number_reply,
    handle_yes_no_reply,
    is_cancel,
    learning_delete_blocked_command_message,
    learning_delete_bulk_confirm_message,
    learning_delete_cancel_message,
    learning_delete_single_confirm_message,
    learning_update_cancel_message,
    learning_update_confirm_message,
    process_learning_create_free_text_reply,
    process_learning_delete_free_text_reply,
    process_learning_update_free_text_reply,
    should_block_new_command,
)
from context.redis_client import redis_client
from pipeline.classifier1 import classifier1
from pipeline.classifier2 import classifier2
from pipeline.gemini_classifier import gemini_input_classifier
from pipeline.date_resolver import resolve_all
from pipeline.entity_scoper import scope_entities
from pipeline.ner import get_ner_extractor_for_intent, learning_ner_extractor, ner_extractor
from pipeline.preprocessor import is_too_short, preprocess
from services.self_fetch import self_fetch_all
from services.duckling import duckling_client
from services.gemini import gemini_service
from jobs.resource_refresh import (
    shutdown_refresh_scheduler,
    start_refresh_scheduler,
)
from services.productivity_scorer import get_productive_days, get_productive_hours
from utils.task_value_normalizer import canonicalize_priority, canonicalize_status
from utils.date_utils import weekday_name_to_number
from utils.timezone_utils import get_zoneinfo, resolve_timezone_name, utc_naive_to_local
from utils.api_datetime import localize_api_payload, with_api_timezone

# Learning update internal endpoints
from db.learning_goals import (
    complete_goal,
    get_goal_by_id,
    get_active_goals_for_user,
    update_end_date,
)
from db.roadmap_topics import (
    complete_topic,
    get_all_pending_sessions,
    get_current_session,
    get_topics_for_goal,
    reschedule_topic,
)
from handlers.learning.update import reschedule_session_for_api, skip_session_and_rebalance
from db.tasks import get_task_by_id, soft_delete_task, update_task
from services.google_calendar import google_calendar_client
from utils.google_calendar_sync import resolve_google_calendar_sync
from utils.learning_utils import build_schedule, next_rebase_start_date, normalize_subtopic_entity

_COMMAND_VERBS = {
    "add",
    "schedule",
    "set",
    "create",
    "delete",
    "remove",
    "update",
    "change",
    "move",
    "show",
    "list",
}

_SALUTATION_PATTERN = re.compile(
    r"^\s*(?:(?:hey|hi|hello|salam|assalamualaikum|aoa|yo|ok|okay)\b[\s,!:.-]*)*(?:eva\b[\s,!:.-]*)*",
    flags=re.IGNORECASE,
)
_WEEKDAY_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    flags=re.IGNORECASE,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    # Startup
    print("=" * 50)
    print("EVA AI Server Starting...")
    print("=" * 50)

    # Connect to MongoDB
    mongodb_ok = await database.connect()

    # Connect to Redis
    redis_ok = await redis_client.connect()

    # Check Duckling connection
    duckling_ok = await duckling_client.connect()

    # Load Model 1 (input type classifier)
    model1_ok = classifier1.load()

    # Load Model 2 (intent classifier)
    model2_ok = classifier2.load()

    # Load NER models (scheduling vs learning intents)
    ner_ok = ner_extractor.load()
    learning_ner_ok = learning_ner_extractor.load()

    print("=" * 50)
    if (
        mongodb_ok
        and redis_ok
        and duckling_ok
        and model1_ok
        and model2_ok
        and ner_ok
        and learning_ner_ok
    ):
        print("All services connected successfully!")
    else:
        print("WARNING: Some services failed to connect")
        if not mongodb_ok:
            print("  - MongoDB: FAILED")
        if not redis_ok:
            print("  - Redis: FAILED")
        if not duckling_ok:
            print("  - Duckling: FAILED")
        if not model1_ok:
            print("  - Model1: FAILED")
        if not model2_ok:
            print("  - Model2: FAILED")
        if not ner_ok:
            print("  - NER (scheduling): FAILED")
        if not learning_ner_ok:
            print("  - NER (learning): FAILED")
    print("=" * 50)

    if mongodb_ok:
        await start_refresh_scheduler()

    yield

    # Shutdown
    print("EVA AI Server Shutting down...")
    await shutdown_refresh_scheduler()
    await database.disconnect()
    await redis_client.disconnect()
    print("Shutdown complete.")


# Create FastAPI app
app = FastAPI(
    title="EVA AI Server",
    description="AI Server for EVA - Enhanced Virtual Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    message: str
    user_id: str
    session_id: str
    input_type: str
    timestamp: Optional[datetime] = None


class RebuildScheduleRequest(BaseModel):
    user_id: str
    new_schedule: list
    goal_id: Optional[str] = None


class AutoCompleteTopicRequest(BaseModel):
    topic_id: str
    goal_id: str
    user_id: str


class SkipTopicRequest(BaseModel):
    topic_id: str
    goal_id: str
    user_id: str


class RescheduleTopicRequest(BaseModel):
    topic_id: str
    goal_id: str
    user_id: str
    scheduled_date: str


def _safe_reply(
    action: str,
    user_name: Optional[str] = None,
    history=None,
    action_context=None,
) -> str:
    try:
        payload = {"action": action}
        if action_context:
            payload.update(action_context)
        return gemini_service.generate_reply(payload, user_name, history or [])
    except Exception:
        return "I am still here, but I could not process that clearly. Please try again."


def _looks_like_command_text(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return False
    first_token = normalized.split()[0]
    return first_token in _COMMAND_VERBS


def _nlu_text_for_classification(message: str) -> str:
    """
    Recover command intent for salutation-prefixed commands such as:
      "hey eva, add physics exam ..."
    while keeping pure greetings/general text unchanged.
    """
    original = (message or "").strip()
    if not original:
        return original

    candidate = _SALUTATION_PATTERN.sub("", original).strip()
    if candidate and _looks_like_command_text(candidate):
        return candidate
    return original


def _first_entity_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _repair_weekday_fragment_date(raw_entities: dict, source_text: str) -> dict:
    """
    Repair occasional NER artifact where date is extracted as bare 'day'
    while the utterance contains a weekday.
    """
    entities = dict(raw_entities or {})
    date_value = str(entities.get("date") or "").strip().lower()
    if date_value != "day":
        return entities

    match = _WEEKDAY_PATTERN.search(str(source_text or ""))
    if match:
        entities["date"] = str(match.group(1)).lower()
    return entities


def _classify_input_type(nlu_message: str, nlu_processed: str):
    """
    Classify input type, returning (classification, nlu_message, nlu_processed).

    EXPERIMENT (branch experiment/gemini-clf1): when USE_GEMINI_CLF1 is set,
    Gemini classifies the input type AND returns a spelling-cleaned message,
    which is then what CLF2 and NER see. The idea is to map off-distribution
    user text onto the clean, well-formed text the models were trained on.

    CLF1 stays the fallback for every failure path (disabled, timeout, bad
    label, rejected rewrite). Gemini sits in front of the whole pipeline here,
    so it must never be able to take EVA down — same lesson as the Duckling
    hard-dependency bug.
    """
    if gemini_input_classifier.enabled:
        result = gemini_input_classifier.predict(nlu_message)
        if result:
            cleaned = result.get("cleaned_text") or nlu_message
            return result, cleaned, preprocess(cleaned)["processed"]

    return classifier1.predict(nlu_processed), nlu_message, nlu_processed


def _normalize_priority_update(value) -> str:
    return canonicalize_priority(_first_entity_value(value))


def _normalize_status_update(value) -> str:
    return canonicalize_status(_first_entity_value(value))


def _parse_duration_update(value):
    raw = str(_first_entity_value(value) or "").strip().lower()
    if not raw:
        return None
    if raw.isdigit():
        return max(5, int(raw))

    match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not match:
        return None
    amount = float(match.group(1))
    if "hour" in raw or "hr" in raw:
        return max(5, int(amount * 60))
    if "min" in raw:
        return max(5, int(amount))
    return max(5, int(amount))


def _build_pending_update_payload(entities: dict):
    """
    Build a minimal, safe update payload for pending update confirmations.
    Supports deterministic fields only (title, priority, status, duration).
    Date/time updates are left to the full handler flow.
    """
    payload = {}
    parts = []
    entity_map = dict(entities or {})

    new_title = str(_first_entity_value(entity_map.get("new_title")) or "").strip()
    if new_title:
        payload["title"] = new_title
        parts.append(f'title to "{new_title}"')

    new_priority = _normalize_priority_update(entity_map.get("new_priority"))
    if new_priority:
        payload["priority"] = new_priority
        parts.append(f"priority to {new_priority}")

    new_status = _normalize_status_update(entity_map.get("new_status"))
    if new_status:
        payload["status"] = new_status
        parts.append(f"status to {new_status}")

    new_duration = _parse_duration_update(entity_map.get("new_duration"))
    if new_duration is not None:
        payload["duration"] = int(new_duration)
        parts.append(f"duration to {int(new_duration)} minutes")

    return payload, ", ".join(parts)


def _parse_analytics_day(day_value: Optional[str]) -> Optional[int]:
    if day_value is None:
        return None
    raw = str(day_value).strip()
    if not raw:
        return None
    if raw.isdigit():
        parsed = int(raw)
        return parsed if 0 <= parsed <= 6 else None
    return weekday_name_to_number(raw)


@app.get("/health")
async def health_check():
    """
    Health check endpoint - checks all service connections
    """
    mongodb_healthy = await database.health_check()
    redis_healthy = await redis_client.health_check()
    duckling_healthy = await duckling_client.health_check()
    model1_healthy = classifier1.loaded
    model2_healthy = classifier2.loaded
    ner_healthy = ner_extractor.loaded
    learning_ner_healthy = learning_ner_extractor.loaded

    all_healthy = (
        mongodb_healthy
        and redis_healthy
        and duckling_healthy
        and model1_healthy
        and model2_healthy
        and ner_healthy
        and learning_ner_healthy
    )

    return {
        "status": "ok" if all_healthy else "degraded",
        "service": "eva-ai",
        "connections": {
            "mongodb": "connected" if mongodb_healthy else "disconnected",
            "redis": "connected" if redis_healthy else "disconnected",
            "duckling": "connected" if duckling_healthy else "disconnected",
            "model1": "loaded" if model1_healthy else "not_loaded",
            "model2": "loaded" if model2_healthy else "not_loaded",
            "ner": "loaded" if ner_healthy else "not_loaded",
            "ner_learning": "loaded" if learning_ner_healthy else "not_loaded",
        }
    }


@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "service": "EVA AI Server",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/analytics")
async def analytics(
    user_id: str,
    type: str = "full",
    day: Optional[str] = None,
):
    """
    Behavioral analytics endpoint for dashboard clients.
    Returns scoring-based analytics payloads.
    """
    analytics_type = str(type or "full").strip().lower()
    if analytics_type == "productivity":
        analytics_type = "full"
    if analytics_type not in {"full", "hours", "days", "slots"}:
        return {
            "status": "error",
            "message": "Invalid analytics type. Use full|hours|days|slots.",
            "data": {},
        }

    from utils.analytics_constants import (
        ANALYTICS_MIN_TASKS_PER_DAY,
        ANALYTICS_MIN_TASKS_THRESHOLD,
    )
    from utils.behavioral_settings import is_behavioral_analytics_enabled

    settings_data = await fetch_user_settings(user_id)
    if not is_behavioral_analytics_enabled(settings_data):
        return {
            "status": "analytics_disabled",
            "message": "Behavioral analytics is disabled. Enable it in Settings to track and view productivity insights.",
            "data": {
                "type": analytics_type,
                "behavioral_analytics_enabled": False,
            },
        }

    global_threshold = ANALYTICS_MIN_TASKS_THRESHOLD
    per_day_threshold = ANALYTICS_MIN_TASKS_PER_DAY

    total_completed = await get_total_completed(user_id)
    day_counts = await get_log_count_per_day(user_id)
    logs = await get_completed_logs_for_scoring(user_id)
    day_num = _parse_analytics_day(day)

    has_enough_data = int(total_completed) >= int(global_threshold)
    base = {
        "status": "success",
        "data": {
            "type": analytics_type,
            "total_completed": int(total_completed),
            "thresholds": {
                "global": int(global_threshold),
                "per_day": int(per_day_threshold),
            },
            "has_enough_data": bool(has_enough_data),
            "day_filter": day_num,
            "day_log_counts": {int(k): int(v) for k, v in dict(day_counts or {}).items()},
        },
    }

    if not has_enough_data:
        base["data"].update(
            {
                "hours": [],
                "days": [],
                "unreliable_days": [],
                "completion_rate": {
                    "total_completed": int(total_completed),
                    "on_time": 0,
                    "late": 0,
                    "on_time_rate": 0.0,
                    "weekly_trend": [],
                },
                "avg_time_taken": None,
            }
        )
        return base

    if analytics_type in {"hours", "slots"}:
        # If a specific day is requested, enforce per-day reliability threshold.
        if day_num is not None and int(day_counts.get(day_num, 0)) < int(per_day_threshold):
            base["data"].update(
                {
                    "hours": [],
                    "message": "Insufficient day data for reliable hourly analytics.",
                }
            )
            return base

        hours_rows = get_productive_hours(logs, day=day_num)
        base["data"].update({"hours": hours_rows})
        return base

    if analytics_type == "days":
        day_result = get_productive_days(logs, day_counts, per_day_threshold)
        base["data"].update(
            {
                "days": list(day_result.get("reliable") or []),
                "unreliable_days": list(day_result.get("unreliable") or []),
            }
        )
        return base

    # full
    day_result = get_productive_days(logs, day_counts, per_day_threshold)
    completion = await get_completion_rate(user_id)
    avg_time_taken = await get_avg_time_taken(user_id)
    base["data"].update(
        {
            "days": list(day_result.get("reliable") or []),
            "unreliable_days": list(day_result.get("unreliable") or []),
            "hours": get_productive_hours(logs),
            "completion_rate": completion,
            "avg_time_taken": avg_time_taken,
        }
    )
    return base


def _learning_days_from_schedule(schedule: Any) -> set:
    days = set()
    if not isinstance(schedule, list):
        return days
    for slot in schedule:
        if not isinstance(slot, dict):
            continue
        try:
            days.add(int(slot.get("day")))
        except (TypeError, ValueError):
            continue
    return days


def _next_learning_day(start: date, learning_days: set) -> date:
    current = start
    for _ in range(30):
        if not learning_days or current.weekday() in learning_days:
            return current
        current = current + timedelta(days=1)
    return start


@app.post("/internal/rebuild-schedule")
async def internal_rebuild_schedule(payload: RebuildScheduleRequest):
    """
    Rebuild remaining pending sessions.

    When ``goal_id`` is set (plan resume), only that active goal is rebased with
    ``new_schedule``. Otherwise all active goals for the user are rebuilt (settings change).
    """
    user_id = str(payload.user_id or "").strip()
    schedule = list(payload.new_schedule or [])
    goal_id_filter = str(payload.goal_id or "").strip()
    if not user_id:
        return {"status": "error", "message": "user_id required"}

    if goal_id_filter:
        goal_doc = await get_goal_by_id(goal_id_filter)
        if not goal_doc:
            return {"status": "error", "message": "goal not found"}
        if str(goal_doc.get("user_id") or "") != user_id:
            return {"status": "error", "message": "goal not found"}
        if str(goal_doc.get("status") or "") != "active":
            return {"status": "error", "message": "goal is not active"}
        if goal_doc.get("is_deleted"):
            return {"status": "error", "message": "goal not found"}
        goals = [goal_doc]
    else:
        goals = await get_active_goals_for_user(user_id)
    user_doc = await fetch_user(user_id)
    tz_name = resolve_timezone_name((user_doc or {}).get("timezone"))
    now_local = datetime.now(get_zoneinfo(tz_name))
    start_from = next_rebase_start_date(now_local, schedule)

    user_settings = await fetch_user_settings(user_id)
    integrations = await fetch_integrations(user_id)
    google = await resolve_google_calendar_sync(user_id, integrations, user_settings)

    updated = 0
    for goal in goals:
        goal_id = str(goal.get("_id") or "").strip()
        if not goal_id:
            continue
        pending_topics = await get_all_pending_sessions(goal_id)
        if not pending_topics:
            continue
        # Build schedule rows for pending topics
        topics_for_builder = [
            {"order": int(t.get("order") or 0), "title": str(t.get("title") or ""), "resources": list(t.get("resources") or [])}
            for t in pending_topics
        ]
        rows = build_schedule(start_from, topics_for_builder, schedule, timezone_name=tz_name)
        if not rows or len(rows) != len(pending_topics):
            continue
        last_dt = None
        for topic, row in zip(pending_topics, rows):
            due_dt = row["scheduled_date"]
            duration = int(row.get("duration_minutes") or 90)
            last_dt = due_dt
            await reschedule_topic(
                str(topic.get("_id")),
                due_dt,
                estimated_duration_minutes=duration,
            )
            task_id = str(topic.get("task_id") or "").strip()
            if task_id:
                await update_task(task_id, {"due_datetime": due_dt, "duration": duration})
                try:
                    task_doc = await get_task_by_id(task_id, user_id)
                    if google and task_doc:
                        event_id = str(task_doc.get("google_calendar_event_id") or "").strip()
                        if event_id:
                            await google_calendar_client.update_event(
                                str(google.get("access_token") or ""),
                                str(google.get("calendar_id") or ""),
                                event_id,
                                {"due_datetime": due_dt, "title": task_doc.get("title") or "Learning session"},
                            )
                except Exception:
                    pass
        if last_dt:
            await update_end_date(goal_id, last_dt)
        updated += 1

    return {"status": "success", "goals_updated": updated}


@app.post("/internal/auto-complete-topic")
async def internal_auto_complete_topic(payload: AutoCompleteTopicRequest):
    """
    Auto-complete a specific roadmap topic (used by Node job).
    """
    goal_id = str(payload.goal_id or "").strip()
    topic_id = str(payload.topic_id or "").strip()
    user_id = str(payload.user_id or "").strip()
    if not goal_id or not topic_id or not user_id:
        return {"status": "error", "message": "topic_id, goal_id, user_id required"}

    ok = await complete_topic(topic_id)
    if not ok:
        return {"status": "error", "message": "topic not updated"}

    goal = await get_goal_by_id(goal_id)
    # Ensure goal completion metadata is updated if last session.
    if goal and goal.get("status") == "completed":
        started_at = goal.get("started_at")
        await complete_goal(goal_id, started_at)

    user_doc = await fetch_user(user_id)
    tz = resolve_timezone_name((user_doc or {}).get("timezone"))
    next_session = await get_current_session(goal_id)
    return with_api_timezone(
        {
            "status": "success",
            "goal_completed": bool(goal and goal.get("status") == "completed"),
            "next_session": next_session,
        },
        tz,
    )


@app.post("/internal/skip-topic")
async def internal_skip_topic(payload: SkipTopicRequest):
    """
    Skip a specific topic and cascade remaining pending sessions (chat + UI).
    """
    goal_id = str(payload.goal_id or "").strip()
    topic_id = str(payload.topic_id or "").strip()
    user_id = str(payload.user_id or "").strip()
    if not goal_id or not topic_id or not user_id:
        return {"status": "error", "message": "topic_id, goal_id, user_id required"}

    topics = await get_topics_for_goal(goal_id)
    topic_doc = next((t for t in topics if str(t.get("_id")) == topic_id), None)
    if not topic_doc:
        return {"status": "error", "message": "topic not found"}

    settings_data = await fetch_user_settings(user_id)
    user_doc = await fetch_user(user_id)
    integrations = await fetch_integrations(user_id)
    tz = resolve_timezone_name((user_doc or {}).get("timezone"))

    skip_ok, shifted = await skip_session_and_rebalance(
        user_id=user_id,
        goal_id=goal_id,
        topic_id=topic_id,
        settings=settings_data,
        integrations=integrations,
        timezone_name=tz,
        current_topic=topic_doc,
    )
    if not skip_ok:
        return {"status": "error", "message": "topic not updated"}

    return {
        "status": "success",
        "schedule_shifted": shifted,
    }


@app.post("/internal/reschedule-topic")
async def internal_reschedule_topic(payload: RescheduleTopicRequest):
    """
    Reschedule the current session to a new date (same rules as chat learning_update).
    """
    goal_id = str(payload.goal_id or "").strip()
    topic_id = str(payload.topic_id or "").strip()
    user_id = str(payload.user_id or "").strip()
    scheduled_date = str(payload.scheduled_date or "").strip()
    if not goal_id or not topic_id or not user_id or not scheduled_date:
        return {
            "status": "error",
            "message": "topic_id, goal_id, user_id, and scheduled_date are required",
        }

    settings_data = await fetch_user_settings(user_id)
    user_doc = await fetch_user(user_id)
    integrations = await fetch_integrations(user_id)
    tz = resolve_timezone_name((user_doc or {}).get("timezone"))

    result = await reschedule_session_for_api(
        user_id=user_id,
        goal_id=goal_id,
        topic_id=topic_id,
        scheduled_date=scheduled_date,
        settings=settings_data,
        integrations=integrations,
        timezone_name=tz,
    )
    return with_api_timezone(result, tz)


@app.post("/process")
async def process_message(payload: ProcessRequest):
    """
    Main conversational processing route.
    Always returns a safe natural response even when internals fail.
    """
    fetched = None
    processed = {"original": payload.message or "", "processed": (payload.message or "").strip().lower()}
    user_name = None
    history = []
    settings_data = {}

    try:
        message = (payload.message or "").strip()
        if not message:
            return {
                "status": "ok",
                "too_short": True,
                "preprocessed": processed,
                "response_text": _safe_reply("empty_input"),
                "user_name": None,
                "settings": {},
            }

        fetched = await self_fetch_all(payload.user_id, payload.session_id)
        history = fetched.history
        settings_data = fetched.settings
        user_name = fetched.user.get("name") if fetched.user else None
        processed = preprocess(message)
        nlu_message = _nlu_text_for_classification(message)
        nlu_processed = preprocess(nlu_message)["processed"]

        route_context_base = {
            "user_id": payload.user_id,
            "session_id": payload.session_id,
            "user": fetched.user,
            "settings": settings_data,
            "history": history,
            "integrations": fetched.integrations,
            "message": message,
            "input_type": payload.input_type,
            "timestamp": payload.timestamp.isoformat() if payload.timestamp else None,
        }

        pending_context = fetched.context
        if pending_context:
            pending_action = pending_context.get("pending_action") or {}
            pending_intent = pending_action.get("intent")
            expected_response = pending_context.get("expected_response")
            pending_stage = str(pending_action.get("stage") or "").lower()

            if is_cancel(processed["processed"]):
                await redis_client.delete_context(payload.user_id)
                cancel_text = (
                    learning_delete_cancel_message(user_name)
                    if pending_intent == "learning_delete"
                    else (
                        learning_update_cancel_message(user_name)
                        if pending_intent == "learning_update"
                        else _safe_reply("pending_cancelled", user_name, history)
                    )
                )
                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "context_handled": True,
                    "response_text": cancel_text,
                    "user_name": user_name,
                    "settings": settings_data,
                }

            if (
                expected_response == "number"
                and pending_intent == "learning_create"
                and pending_stage == "schedule_choice"
            ):
                from utils.learning_schedules import (
                    parse_schedule_choice_number,
                    schedule_choice_is_settings_redirect,
                )

                options = list(pending_action.get("schedule_options") or [])
                chosen_id = parse_schedule_choice_number(message, options)
                if not chosen_id:
                    await redis_client.set_context(payload.user_id, pending_context)
                    total = len(options)
                    if user_name:
                        prompt = (
                            f"Please pick a number from 1 to {total}, {user_name}, "
                            "or say cancel to stop."
                        )
                    else:
                        prompt = f"Please pick a number from 1 to {total}, or say cancel to stop."
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "expected_response": "number",
                        "stage": "schedule_choice",
                        "response_text": prompt,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if schedule_choice_is_settings_redirect(chosen_id):
                    await redis_client.delete_context(payload.user_id)
                    if user_name:
                        settings_msg = (
                            f"No problem, {user_name}. Add a schedule in Settings with the days, "
                            "times, and session lengths you want for this topic, then ask me to "
                            "create your learning plan again."
                        )
                    else:
                        settings_msg = (
                            "Add a schedule in Settings with the days, times, and session lengths "
                            "you want for this topic, then ask me to create your learning plan again."
                        )
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "expected_response": "free_text",
                        "stage": "schedule_choice",
                        "response_text": settings_msg,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                merged_learning = dict(pending_action.get("entities") or {})
                merged_learning["learning_schedule_id"] = chosen_id
                await redis_client.delete_context(payload.user_id)
                routed_result = await route_intent(
                    "learning_create",
                    entities=merged_learning,
                    context={
                        **route_context_base,
                        "pending_context": pending_context,
                        "pending_reply_type": "number",
                    },
                )
                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "context_handled": True,
                    "expected_response": "number",
                    "stage": "schedule_choice",
                    "merged_entities": merged_learning,
                    "route": routed_result,
                    "handler_status": routed_result.get("status"),
                    "notifications": routed_result.get("notifications", []),
                    "response_text": routed_result.get("response_text")
                    or _safe_reply("pending_number_processed", user_name, history),
                    "user_name": user_name,
                    "settings": settings_data,
                }

            if expected_response == "free_text":
                if pending_intent in {"update", "scheduling_update"} and pending_stage == "what_to_update":
                    if not ner_extractor.loaded:
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "response_text": _safe_reply("model_unavailable", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    raw_update_entities = ner_extractor.extract(
                        message,
                        intent_hint="scheduling_update",
                    )
                    scoped_update_entities = scope_entities(raw_update_entities, "scheduling_update")
                    user_timezone = resolve_timezone_name((fetched.user or {}).get("timezone"))
                    resolved_update_entities = await resolve_all(
                        scoped_update_entities,
                        timezone=user_timezone,
                    )
                    update_fields = extract_update_fields(resolved_update_entities)

                    if not update_fields:
                        await redis_client.set_context(payload.user_id, pending_context)
                        if user_name:
                            response_text = (
                                f"I didn't catch what to update, {user_name}. "
                                "Try something like 'priority to high' or 'move to Tuesday'."
                            )
                        else:
                            response_text = (
                                "I didn't catch what to update. "
                                "Try something like 'priority to high' or 'move to Tuesday'."
                            )
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "expected_response": "free_text",
                            "stage": "what_to_update",
                            "extracted_update_fields": {},
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    merged_entities = dict(pending_action.get("entities") or {})
                    merged_entities.update(update_fields)
                    pending_task_id = str(pending_action.get("task_id") or "").strip()
                    if pending_task_id:
                        merged_entities["task_id"] = pending_task_id
                    await redis_client.delete_context(payload.user_id)
                    routed_result = await route_intent(
                        "scheduling_update",
                        entities=merged_entities,
                        context={
                            **route_context_base,
                            "pending_context": pending_context,
                            "pending_reply_type": "free_text",
                            "pending_reply_value": update_fields,
                        },
                    )

                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "expected_response": "free_text",
                        "stage": "what_to_update",
                        "merged_entities": merged_entities,
                        "extracted_update_fields": update_fields,
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "notifications": routed_result.get("notifications", []),
                        "response_text": routed_result.get("response_text")
                        or _safe_reply("pending_free_text_captured", user_name, history),
                        "user_name": user_name,
                            "settings": settings_data,
                        }

                if pending_intent == "learning_create":
                    pending_stage_lc = str(
                        (pending_context.get("pending_action") or {}).get("stage") or "topic",
                    ).lower()
                    if pending_stage_lc == "topic" and not learning_ner_extractor.loaded:
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "response_text": _safe_reply("model_unavailable", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    from utils.learning_schedules import slots_for_plan_entities

                    pending_entities = (pending_context.get("pending_action") or {}).get(
                        "entities",
                    ) or {}
                    plan_slots = slots_for_plan_entities(settings_data, pending_entities)

                    lc_result = await process_learning_create_free_text_reply(
                        pending_context,
                        message,
                        user_timezone=resolve_timezone_name(
                            (fetched.user or {}).get("timezone"),
                        ),
                        preferred_learning_schedule=plan_slots,
                    )
                    outcome = lc_result.get("outcome")
                    if outcome == "retry":
                        await redis_client.set_context(payload.user_id, pending_context)
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "expected_response": "free_text",
                            "stage": pending_stage_lc,
                            "response_text": lc_result.get("message")
                            or _safe_reply("pending_free_text_captured", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }
                    if outcome == "unsupported_topic":
                        await redis_client.delete_context(payload.user_id)
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "expected_response": "free_text",
                            "response_text": lc_result.get("message")
                            or _safe_reply("unknown_input_type", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    merged_learning = lc_result.get("merged_entities") or {}
                    await redis_client.delete_context(payload.user_id)
                    routed_result = await route_intent(
                        "learning_create",
                        entities=merged_learning,
                        context={
                            **route_context_base,
                            "pending_context": pending_context,
                            "pending_reply_type": "free_text",
                            "pending_stage": pending_stage_lc,
                        },
                    )
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "expected_response": "free_text",
                        "stage": pending_stage_lc,
                        "merged_entities": merged_learning,
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "notifications": routed_result.get("notifications", []),
                        "response_text": routed_result.get("response_text")
                        or _safe_reply("pending_free_text_captured", user_name, history),
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if pending_intent == "learning_delete":
                    if not learning_ner_extractor.loaded:
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "response_text": _safe_reply("model_unavailable", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    ld_result = await process_learning_delete_free_text_reply(
                        pending_context,
                        message,
                        user_name=user_name,
                    )
                    ld_outcome = ld_result.get("outcome")
                    if ld_outcome == "retry":
                        await redis_client.set_context(payload.user_id, pending_context)
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "expected_response": "free_text",
                            "response_text": ld_result.get("message")
                            or _safe_reply("pending_free_text_captured", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }
                    if ld_outcome == "unsupported_topic":
                        await redis_client.delete_context(payload.user_id)
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "expected_response": "free_text",
                            "response_text": ld_result.get("message")
                            or _safe_reply("unknown_input_type", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    merged_learning_delete = ld_result.get("merged_entities") or {}
                    await redis_client.delete_context(payload.user_id)
                    routed_result = await route_intent(
                        "learning_delete",
                        entities=merged_learning_delete,
                        context={
                            **route_context_base,
                            "pending_context": pending_context,
                            "pending_reply_type": "free_text",
                        },
                    )
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "expected_response": "free_text",
                        "merged_entities": merged_learning_delete,
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "notifications": routed_result.get("notifications", []),
                        "response_text": routed_result.get("response_text")
                        or _safe_reply("pending_free_text_captured", user_name, history),
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if pending_intent == "learning_update":
                    lu_result = await process_learning_update_free_text_reply(
                        pending_context,
                        message,
                        user_name=user_name,
                        timezone_name=resolve_timezone_name((fetched.user or {}).get("timezone")),
                        preferred_learning_schedule=list(
                            (settings_data or {}).get("preferred_learning_schedule") or []
                        ),
                    )
                    outcome = lu_result.get("outcome")
                    if outcome == "retry":
                        await redis_client.set_context(payload.user_id, pending_context)
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "expected_response": "free_text",
                            "response_text": lu_result.get("message")
                            or _safe_reply("pending_free_text_captured", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    merged_learning_update = lu_result.get("merged_entities") or {}
                    await redis_client.delete_context(payload.user_id)
                    routed_result = await route_intent(
                        "learning_update",
                        entities=merged_learning_update,
                        context={
                            **route_context_base,
                            "pending_context": pending_context,
                            "pending_reply_type": "free_text",
                        },
                    )
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "expected_response": "free_text",
                        "merged_entities": merged_learning_update,
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "notifications": routed_result.get("notifications", []),
                        "response_text": routed_result.get("response_text")
                        or _safe_reply("pending_free_text_captured", user_name, history),
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if is_legacy_unsupported_intent(pending_intent):
                    await redis_client.delete_context(payload.user_id)
                    routed_result = build_unsupported_intent_response(
                        pending_intent,
                        {
                            "user": fetched.user,
                            "message": message,
                            "history": history,
                        },
                    )
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "expected_response": "free_text",
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "response_text": routed_result.get("response_text"),
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                merged_entities = await handle_free_text_reply(
                    payload.user_id,
                    pending_context,
                    message,
                )

                if pending_intent in {"add", "scheduling_add", "delete", "scheduling_delete", "update", "scheduling_update", "behavioral"}:
                    routed_intent = (
                        "scheduling_add"
                        if pending_intent in {"add", "scheduling_add"}
                        else (
                            "scheduling_delete"
                            if pending_intent in {"delete", "scheduling_delete"}
                            else ("scheduling_update" if pending_intent in {"update", "scheduling_update"} else "behavioral")
                        )
                    )
                    routed_result = await route_intent(
                        routed_intent,
                        entities=merged_entities,
                        context={
                            **route_context_base,
                            "pending_context": pending_context,
                            "pending_reply_type": "free_text",
                        },
                    )

                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "expected_response": "free_text",
                        "merged_entities": merged_entities,
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "notifications": routed_result.get("notifications", []),
                        "response_text": routed_result.get("response_text")
                        or _safe_reply("pending_free_text_captured", user_name, history),
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "context_handled": True,
                    "expected_response": "free_text",
                    "merged_entities": merged_entities,
                    "response_text": _safe_reply("pending_free_text_captured", user_name, history),
                    "user_name": user_name,
                    "settings": settings_data,
                }

            if not classifier1.loaded:
                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "context_handled": True,
                    "response_text": _safe_reply("model_unavailable", user_name, history),
                    "user_name": user_name,
                    "settings": settings_data,
                }

            classification = classifier1.predict(nlu_processed)
            label = classification["label"]

            if should_block_new_command(label):
                blocked_text = (
                    learning_delete_blocked_command_message(pending_context, user_name)
                    if pending_intent == "learning_delete"
                    else _safe_reply("pending_waiting_reply", user_name, history)
                )
                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "context_handled": True,
                    "classification": classification,
                    "response_text": blocked_text,
                    "user_name": user_name,
                    "settings": settings_data,
                }

            if expected_response == "yes_no":
                if label != "confirmation":
                    yes_no_prompt = _safe_reply("pending_yes_no_prompt", user_name, history)
                    if pending_intent == "learning_delete":
                        if user_name:
                            yes_no_prompt = f"Just a yes or no will do, {user_name}."
                        else:
                            yes_no_prompt = "Just a yes or no will do."
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "response_text": yes_no_prompt,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                yes_no_value = handle_yes_no_reply(processed["processed"])
                if (
                    pending_intent in {
                        "add",
                        "scheduling_add",
                        "delete",
                        "scheduling_delete",
                        "learning_delete",
                        "learning_update",
                    }
                    and yes_no_value in {"yes", "no"}
                ):
                    if pending_intent == "learning_delete":
                        routed_intent = "learning_delete"
                    elif pending_intent == "learning_update":
                        routed_intent = "learning_update"
                    elif pending_intent in {"add", "scheduling_add"}:
                        routed_intent = "scheduling_add"
                    else:
                        routed_intent = "scheduling_delete"
                    routed_result = await route_intent(
                        routed_intent,
                        entities=dict(pending_action.get("entities") or {}),
                        context={
                            **route_context_base,
                            "pending_context": pending_context,
                            "pending_reply_type": "yes_no",
                            "pending_reply_value": yes_no_value,
                        },
                    )

                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "expected_response": "yes_no",
                        "parsed_value": yes_no_value,
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "notifications": routed_result.get("notifications", []),
                        "response_text": routed_result.get("response_text")
                        or _safe_reply("pending_yes_no_processed", user_name, history),
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if pending_intent in {"update", "scheduling_update"}:
                    if yes_no_value == "invalid":
                        if user_name:
                            response_text = f"Just yes or no will do, {user_name}."
                        else:
                            response_text = "Just yes or no will do."
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "yes_no",
                            "parsed_value": yes_no_value,
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    if yes_no_value == "yes":
                        await redis_client.delete_context(payload.user_id)
                        routed_entities = dict(pending_action.get("entities") or {})
                        pending_task_id = str(pending_action.get("task_id") or "").strip()
                        if pending_task_id:
                            routed_entities["task_id"] = pending_task_id
                        routed_result = await route_intent(
                            "scheduling_update",
                            entities=routed_entities,
                            context={
                                **route_context_base,
                                "pending_context": pending_context,
                                "pending_reply_type": "yes_no",
                                "pending_reply_value": yes_no_value,
                            },
                        )

                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "yes_no",
                            "parsed_value": yes_no_value,
                            "route": routed_result,
                            "handler_status": routed_result.get("status"),
                            "notifications": routed_result.get("notifications", []),
                            "response_text": routed_result.get("response_text")
                            or _safe_reply("pending_yes_no_processed", user_name, history),
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    await redis_client.delete_context(payload.user_id)
                    task_title = str((pending_action.get("task") or {}).get("title") or "that task")
                    if user_name:
                        response_text = f"No problem, {user_name}. I kept {task_title} unchanged."
                    else:
                        response_text = f"No problem. I kept {task_title} unchanged."

                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "expected_response": "yes_no",
                        "parsed_value": yes_no_value,
                        "response_text": response_text,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if (
                    pending_intent in {"delete", "scheduling_delete", "learning_delete"}
                    and yes_no_value == "invalid"
                ):
                    if user_name:
                        response_text = f"Just a yes or no will do, {user_name}."
                    else:
                        response_text = "Just a yes or no will do."
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "expected_response": "yes_no",
                        "parsed_value": yes_no_value,
                        "response_text": response_text,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if yes_no_value in {"yes", "no"}:
                    await redis_client.delete_context(payload.user_id)

                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "context_handled": True,
                    "classification": classification,
                    "expected_response": "yes_no",
                    "parsed_value": yes_no_value,
                    "response_text": _safe_reply("pending_yes_no_processed", user_name, history),
                    "user_name": user_name,
                    "settings": settings_data,
                }

            if expected_response == "number":
                if label != "confirmation":
                    response_text = _safe_reply("pending_number_prompt", user_name, history)
                    if pending_intent in {"delete", "scheduling_delete", "learning_delete"}:
                        if user_name:
                            response_text = (
                                f"Pick a number from the list, or say 'all', {user_name}."
                            )
                        else:
                            response_text = "Pick a number from the list, or say 'all'."
                    if pending_intent in {"update", "scheduling_update"}:
                        if user_name:
                            response_text = f"Please pick a number from the list, {user_name}."
                        else:
                            response_text = "Please pick a number from the list."
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "response_text": response_text,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if pending_intent == "learning_delete":
                    delete_choice = handle_number_learning_delete(
                        processed["processed"],
                        pending_context,
                    )
                    pending_goal_ids = list(pending_action.get("goal_ids") or [])
                    pending_goals = list(pending_action.get("goals") or [])
                    pending_entities = dict(pending_action.get("entities") or {})

                    if delete_choice == "all":
                        updated_context = dict(pending_context)
                        updated_pending_action = dict(pending_action)
                        updated_pending_action["bulk"] = True
                        updated_context["pending_action"] = updated_pending_action
                        updated_context["expected_response"] = "yes_no"
                        await redis_client.set_context(payload.user_id, updated_context)

                        response_text = learning_delete_bulk_confirm_message(
                            pending_goals,
                            pending_entities,
                            user_name,
                        )
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "next_expected_response": "yes_no",
                            "parsed_value": "all",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    if delete_choice == "invalid_range":
                        total = len(pending_goal_ids)
                        if user_name:
                            response_text = (
                                f"That number is not on the list, {user_name}. "
                                f"Pick between 1 and {total}, or say 'all'."
                            )
                        else:
                            response_text = (
                                f"That number is not on the list. "
                                f"Pick between 1 and {total}, or say 'all'."
                            )
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "parsed_value": "invalid_range",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    if delete_choice == "invalid":
                        if user_name:
                            response_text = (
                                f"Pick a number from the list or say 'all' to delete "
                                f"everything, {user_name}."
                            )
                        else:
                            response_text = (
                                "Pick a number from the list or say 'all' to delete everything."
                            )
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "parsed_value": "invalid",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    selected_index = None
                    for index, goal_id in enumerate(pending_goal_ids):
                        if str(goal_id) == str(delete_choice):
                            selected_index = index
                            break

                    selected_goal: Dict[str, Any] = {}
                    if (
                        selected_index is not None
                        and selected_index < len(pending_goals)
                        and isinstance(pending_goals[selected_index], dict)
                    ):
                        selected_goal = dict(pending_goals[selected_index])

                    updated_context = dict(pending_context)
                    updated_pending_action = dict(pending_action)
                    updated_pending_action["goal_ids"] = [delete_choice]
                    updated_pending_action["bulk"] = False
                    if selected_goal:
                        updated_pending_action["goals"] = [selected_goal]
                    updated_context["pending_action"] = updated_pending_action
                    updated_context["expected_response"] = "yes_no"
                    await redis_client.set_context(payload.user_id, updated_context)

                    response_text = learning_delete_single_confirm_message(
                        selected_goal,
                        user_name,
                    )
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "expected_response": "number",
                        "next_expected_response": "yes_no",
                        "parsed_value": delete_choice,
                        "response_text": response_text,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if pending_intent == "learning_update":
                    update_choice = handle_number_learning_update(
                        processed["processed"],
                        pending_context,
                    )
                    pending_goal_ids = list(pending_action.get("goal_ids") or [])
                    pending_goals = list(pending_action.get("goals") or [])
                    sub_intent = str(pending_action.get("sub_intent") or "").strip().lower()
                    stage = str(pending_action.get("stage") or "").strip().lower()

                    if update_choice == "invalid_range":
                        total = len(pending_goal_ids)
                        if user_name:
                            response_text = f"That number is not on the list, {user_name}. Pick between 1 and {total}."
                        else:
                            response_text = f"That number is not on the list. Pick between 1 and {total}."
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "parsed_value": "invalid_range",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    if update_choice == "invalid":
                        if user_name:
                            response_text = f"Please pick a number from the list, {user_name}."
                        else:
                            response_text = "Please pick a number from the list."
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "parsed_value": "invalid",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    # Identify_language executes immediately in handler (Phase 5). For identify (pause/resume),
                    # move to State 3 (yes_no confirm) here.
                    if stage == "identify" and sub_intent in {"pause", "resume"}:
                        selected_index = None
                        for index, goal_id in enumerate(pending_goal_ids):
                            if str(goal_id) == str(update_choice):
                                selected_index = index
                                break

                        selected_goal: Dict[str, Any] = {}
                        if (
                            selected_index is not None
                            and selected_index < len(pending_goals)
                            and isinstance(pending_goals[selected_index], dict)
                        ):
                            selected_goal = dict(pending_goals[selected_index])

                        updated_context = dict(pending_context)
                        updated_pending_action = dict(pending_action)
                        updated_pending_action["goal_id"] = update_choice
                        updated_pending_action["goal_ids"] = [update_choice]
                        if selected_goal:
                            updated_pending_action["goal"] = selected_goal
                            updated_pending_action["goals"] = [selected_goal]
                        updated_context["pending_action"] = updated_pending_action
                        updated_context["expected_response"] = "yes_no"
                        await redis_client.set_context(payload.user_id, updated_context)

                        response_text = learning_update_confirm_message(
                            selected_goal,
                            sub_intent=sub_intent,
                            user_name=user_name,
                        )
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "next_expected_response": "yes_no",
                            "parsed_value": update_choice,
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    # Default: hand selection to handler with goal_id in entities
                    await redis_client.delete_context(payload.user_id)
                    routed_entities = dict(pending_action.get("entities") or {})
                    routed_entities["goal_id"] = str(update_choice)
                    routed_result = await route_intent(
                        "learning_update",
                        entities=routed_entities,
                        context={
                            **route_context_base,
                            "pending_context": pending_context,
                            "pending_reply_type": "number",
                            "pending_reply_value": str(update_choice),
                        },
                    )
                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "expected_response": "number",
                        "parsed_value": str(update_choice),
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "notifications": routed_result.get("notifications", []),
                        "response_text": routed_result.get("response_text")
                        or _safe_reply("pending_number_processed", user_name, history),
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if pending_intent in {"delete", "scheduling_delete"}:
                    delete_choice = handle_number_delete(processed["processed"], pending_context)
                    pending_task_ids = list(pending_action.get("task_ids") or [])
                    pending_tasks = list(pending_action.get("tasks") or [])

                    if delete_choice == "all":
                        updated_context = dict(pending_context)
                        updated_pending_action = dict(pending_action)
                        updated_pending_action["bulk"] = True
                        updated_context["pending_action"] = updated_pending_action
                        updated_context["expected_response"] = "yes_no"
                        await redis_client.set_context(payload.user_id, updated_context)

                        total = len(pending_task_ids)
                        if user_name:
                            response_text = (
                                f"Just to confirm, {user_name} — delete all {total} tasks? "
                                "This cannot be undone."
                            )
                        else:
                            response_text = (
                                f"Just to confirm — delete all {total} tasks? "
                                "This cannot be undone."
                            )

                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "next_expected_response": "yes_no",
                            "parsed_value": "all",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    if delete_choice == "invalid_range":
                        total = len(pending_task_ids)
                        response_text = (
                            f"That number is not on the list. Pick between 1 and {total}, or say 'all'."
                        )
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "parsed_value": "invalid_range",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    if delete_choice == "invalid":
                        if user_name:
                            response_text = (
                                f"Pick a number from the list or say 'all', {user_name}."
                            )
                        else:
                            response_text = "Pick a number from the list or say 'all'."
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "parsed_value": "invalid",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    selected_index = None
                    for index, task_id in enumerate(pending_task_ids):
                        if str(task_id) == str(delete_choice):
                            selected_index = index
                            break

                    selected_task = {}
                    if (
                        selected_index is not None
                        and selected_index < len(pending_tasks)
                        and isinstance(pending_tasks[selected_index], dict)
                    ):
                        selected_task = dict(pending_tasks[selected_index])

                    updated_context = dict(pending_context)
                    updated_pending_action = dict(pending_action)
                    updated_pending_action["task_ids"] = [delete_choice]
                    updated_pending_action["bulk"] = False
                    if selected_task:
                        updated_pending_action["tasks"] = [selected_task]
                    updated_context["pending_action"] = updated_pending_action
                    updated_context["expected_response"] = "yes_no"
                    await redis_client.set_context(payload.user_id, updated_context)

                    task_title = str(selected_task.get("title") or "that task")
                    due_text = ""
                    due_raw = selected_task.get("due_datetime")
                    user_timezone = resolve_timezone_name((fetched.user or {}).get("timezone"))
                    local_due = utc_naive_to_local(due_raw, user_timezone)
                    if local_due is not None:
                        due_text = local_due.strftime("%A at %I:%M %p").replace(" 0", " ")

                    if user_name:
                        if due_text:
                            response_text = (
                                f"I got it, {user_name}. Delete {task_title} on {due_text}?"
                            )
                        else:
                            response_text = f"I got it, {user_name}. Delete {task_title}?"
                    else:
                        if due_text:
                            response_text = f"I got it. Delete {task_title} on {due_text}?"
                        else:
                            response_text = f"I got it. Delete {task_title}?"

                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "expected_response": "number",
                        "next_expected_response": "yes_no",
                        "parsed_value": delete_choice,
                        "response_text": response_text,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if pending_intent in {"update", "scheduling_update"}:
                    update_choice = handle_number_update(processed["processed"], pending_context)
                    pending_task_ids = list(pending_action.get("task_ids") or [])
                    pending_tasks = list(pending_action.get("tasks") or [])

                    if update_choice == "invalid_range":
                        total = len(pending_task_ids)
                        response_text = (
                            f"That number is not on the list. Pick between 1 and {total}."
                        )
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "parsed_value": "invalid_range",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    if update_choice == "invalid":
                        if user_name:
                            response_text = f"Pick a number from the list, {user_name}."
                        else:
                            response_text = "Pick a number from the list."
                        return {
                            "status": "ok",
                            "too_short": False,
                            "preprocessed": processed,
                            "context_handled": True,
                            "classification": classification,
                            "expected_response": "number",
                            "parsed_value": "invalid",
                            "response_text": response_text,
                            "user_name": user_name,
                            "settings": settings_data,
                        }

                    selected_index = None
                    for index, task_id in enumerate(pending_task_ids):
                        if str(task_id) == str(update_choice):
                            selected_index = index
                            break

                    selected_task = {}
                    if (
                        selected_index is not None
                        and selected_index < len(pending_tasks)
                        and isinstance(pending_tasks[selected_index], dict)
                    ):
                        selected_task = dict(pending_tasks[selected_index])

                    updated_context = dict(pending_context)
                    updated_pending_action = dict(pending_action)
                    updated_pending_action["task_id"] = update_choice
                    if selected_task:
                        updated_pending_action["task"] = selected_task
                    updated_pending_action.pop("task_ids", None)
                    updated_pending_action.pop("tasks", None)

                    selected_entities = dict(updated_pending_action.get("entities") or {})
                    selected_entities["task_id"] = update_choice
                    if selected_task and not str(selected_entities.get("task_name") or "").strip():
                        selected_entities["task_name"] = str(selected_task.get("title") or "").strip()

                    candidate_updates, candidate_change_summary = _build_pending_update_payload(selected_entities)
                    stage = "confirm" if candidate_updates else "what_to_update"
                    updated_pending_action["entities"] = selected_entities
                    updated_pending_action["stage"] = stage
                    updated_context["pending_action"] = updated_pending_action
                    if stage == "confirm":
                        updated_pending_action["updates"] = candidate_updates
                        if candidate_change_summary:
                            updated_pending_action["change_summary"] = candidate_change_summary
                        updated_context["expected_response"] = "yes_no"
                    else:
                        updated_pending_action.pop("updates", None)
                        updated_pending_action.pop("change_summary", None)
                        updated_context["expected_response"] = "free_text"
                    await redis_client.set_context(payload.user_id, updated_context)

                    task_title = str(selected_task.get("title") or "that task")
                    due_text = ""
                    due_raw = selected_task.get("due_datetime")
                    user_timezone = resolve_timezone_name((fetched.user or {}).get("timezone"))
                    local_due = utc_naive_to_local(due_raw, user_timezone)
                    if local_due is not None:
                        due_text = local_due.strftime("%A at %I:%M %p").replace(" 0", " ")

                    if stage == "confirm":
                        if user_name:
                            response_text = (
                                f"I got it, {user_name}. Update {task_title}? Reply yes or no."
                            )
                        else:
                            response_text = f"I got it. Update {task_title}? Reply yes or no."
                    else:
                        if user_name:
                            response_text = (
                                f"What would you like to change about {task_title}, {user_name}? "
                                "You can update date, time, priority, status, duration, or title."
                            )
                        else:
                            response_text = (
                                f"What would you like to change about {task_title}? "
                                "You can update date, time, priority, status, duration, or title."
                            )

                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "expected_response": "number",
                        "next_expected_response": updated_context["expected_response"],
                        "parsed_value": update_choice,
                        "response_text": response_text,
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                number_value = handle_number_reply(processed["processed"])
                if pending_intent in {"add", "scheduling_add"} and number_value in {1, 2}:
                    routed_result = await route_intent(
                        "scheduling_add",
                        entities=dict(pending_action.get("entities") or {}),
                        context={
                            **route_context_base,
                            "pending_context": pending_context,
                            "pending_reply_type": "number",
                            "pending_reply_value": number_value,
                        },
                    )

                    return {
                        "status": "ok",
                        "too_short": False,
                        "preprocessed": processed,
                        "context_handled": True,
                        "classification": classification,
                        "expected_response": "number",
                        "parsed_value": number_value,
                        "route": routed_result,
                        "handler_status": routed_result.get("status"),
                        "notifications": routed_result.get("notifications", []),
                        "response_text": routed_result.get("response_text")
                        or _safe_reply("pending_number_processed", user_name, history),
                        "user_name": user_name,
                        "settings": settings_data,
                    }

                if number_value == 1:
                    await redis_client.delete_context(payload.user_id)

                if number_value == 2:
                    updated_context = dict(pending_context)
                    updated_context["expected_response"] = "free_text"
                    updated_context["missing_entity"] = "time"
                    updated_context.pop("suggested_time", None)
                    updated_context.pop("suggested_range", None)
                    await redis_client.set_context(payload.user_id, updated_context)

                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "context_handled": True,
                    "classification": classification,
                    "expected_response": "number",
                    "parsed_value": number_value,
                    "response_text": _safe_reply("pending_number_processed", user_name, history),
                    "user_name": user_name,
                    "settings": settings_data,
                }

        if not pending_context:
            learning_done = await maybe_handle_learning_topic_done_chat(
                user_id=payload.user_id,
                message_lower=processed["processed"],
                user_name=user_name,
                history=history,
                settings_data=settings_data,
                preprocessed=processed,
            )
            if learning_done is not None:
                return learning_done

        if is_too_short(processed["processed"]):
            return {
                "status": "ok",
                "too_short": True,
                "preprocessed": processed,
                "response_text": _safe_reply("too_short_input", user_name, history),
                "user_name": user_name,
                "settings": settings_data,
            }

        if not classifier1.loaded:
            return {
                "status": "ok",
                "too_short": False,
                "preprocessed": processed,
                "response_text": _safe_reply("model_unavailable", user_name, history),
                "user_name": user_name,
                "settings": settings_data,
            }

        classification, nlu_message, nlu_processed = _classify_input_type(
            nlu_message, nlu_processed
        )
        label = classification["label"]

        if label == "command":
            if not classifier2.loaded:
                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "classification": classification,
                    "intent_pending": False,
                    "response_text": _safe_reply("model_unavailable", user_name, history),
                    "user_name": user_name,
                    "settings": settings_data,
                }

            intent_classification = classifier2.predict(nlu_processed)
            canonical_intent = normalize_intent(intent_classification["label"])
            active_ner = get_ner_extractor_for_intent(canonical_intent)
            if not active_ner.loaded:
                return {
                    "status": "ok",
                    "too_short": False,
                    "preprocessed": processed,
                    "classification": classification,
                    "intent_pending": False,
                    "response_text": _safe_reply("model_unavailable", user_name, history),
                    "user_name": user_name,
                    "settings": settings_data,
                }

            raw_entities = active_ner.extract(nlu_message, intent_hint=canonical_intent)
            if "subtopic" in raw_entities:
                subtopic_norm = normalize_subtopic_entity(raw_entities.get("subtopic"))
                if subtopic_norm:
                    raw_entities["subtopic"] = subtopic_norm
                else:
                    raw_entities.pop("subtopic", None)
            raw_entities = _repair_weekday_fragment_date(raw_entities, nlu_message)
            scoped_entities = scope_entities(raw_entities, canonical_intent)
            user_timezone = resolve_timezone_name((fetched.user or {}).get("timezone"))
            resolved_entities = await resolve_all(scoped_entities, timezone=user_timezone)

            routed_result = await route_intent(
                intent_classification["label"],
                entities=resolved_entities,
                context=route_context_base,
            )
            return {
                "status": "ok",
                "too_short": False,
                "preprocessed": processed,
                "classification": classification,
                "intent_classification": intent_classification,
                "entities": {
                    "raw": raw_entities,
                    "scoped": scoped_entities,
                    "resolved": resolved_entities,
                },
                "intent_pending": False,
                "route": routed_result,
                "handler_status": routed_result.get("status"),
                "notifications": routed_result.get("notifications", []),
                "response_text": routed_result.get("response_text")
                or _safe_reply("unknown_input_type", user_name, history),
                "user_name": user_name,
                "settings": settings_data,
            }

        general_handlers = {
            "general": lambda: handle_general(fetched.user, history, message),
            "help": lambda: handle_help(fetched.user, history, message),
            "out_of_scope": lambda: handle_out_of_scope(fetched.user, history, message),
            "confirmation": lambda: handle_confirmation_unexpected(fetched.user, history, message),
            "multiple_command": lambda: handle_multiple_command(fetched.user, history, message),
        }
        general_result = general_handlers.get(
            label,
            lambda: {
                "route": "unknown_input_type",
                "response_text": _safe_reply("unknown_input_type", user_name, history),
            },
        )()

        return {
            "status": "ok",
            "too_short": False,
            "preprocessed": processed,
            "classification": classification,
            "intent_pending": False,
            "route": general_result,
            "response_text": general_result.get("response_text")
            or _safe_reply("unknown_input_type", user_name, history),
            "user_name": user_name,
            "settings": settings_data,
        }

    except Exception as error:
        print(f"[Process] Unexpected error handled safely: {error}")
        return {
            "status": "ok",
            "too_short": False,
            "preprocessed": processed,
            "intent_pending": False,
            "error_handled": True,
            "response_text": _safe_reply("system_error", user_name, history),
            "user_name": user_name,
            "settings": settings_data,
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True
    )
