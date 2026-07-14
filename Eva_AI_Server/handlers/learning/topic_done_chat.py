"""
Natural-language completion for learning roadmap topics (Phase 10).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from db.learning_goals import get_goal_by_id, get_paused_goals_for_user
from db.readers import fetch_user
from db.roadmap_topics import (
    complete_topic,
    get_current_session,
    get_topics_for_goal,
    pick_pending_topic_for_chat_completion,
)
from utils.learning_utils import (
    SUPPORTED_TOPICS,
    TOPIC_ALIAS_MAP,
    compute_session_state,
    detect_learning_sub_intent,
    message_implies_reschedule,
)
from utils.timezone_utils import get_zoneinfo, resolve_timezone_name


_COMPLETION_RE = re.compile(
    r"(completed|finished|done)\s+(with\s+)?|"
    r"today'?s\s+(session|topic|lesson)|"
    r"mark(ed)?\s+.*\s+complete|session\s+done|topic\s+done",
    re.IGNORECASE,
)


def _implies_today(text_lc: str) -> bool:
    return "today" in text_lc or "todays" in text_lc


def extract_learning_subject_hint(message_lower: str) -> Optional[str]:
    """Return lowercase subject slug if a known topic name appears in the message."""
    for name in sorted(SUPPORTED_TOPICS, key=len, reverse=True):
        if name.lower() in message_lower:
            return name.lower()
    for alias in sorted(TOPIC_ALIAS_MAP.keys(), key=len, reverse=True):
        if alias in message_lower:
            canon = TOPIC_ALIAS_MAP[alias]
            return canon.lower()
    return None


def looks_like_learning_completion(message_lower: str) -> bool:
    if not message_lower or len(message_lower) < 10:
        return False
    # Scheduling reads/updates ("show completed tasks", "list done tasks") mention
    # "task" or start with a query verb — they are NOT learning-session completions.
    # Don't hijack them here; let the intent classifier route them (e.g. scheduling_show).
    if "task" in message_lower or re.search(
        r"\b(show|list|display|view|see|what|which)\b", message_lower
    ):
        return False
    if message_implies_reschedule(message_lower):
        return False
    # Let learning_update handle skip / reschedule / pause / resume.
    if detect_learning_sub_intent(message_lower) in {
        "skip",
        "reschedule",
        "pause",
        "resume",
    }:
        return False
    if re.search(r"\bskip\b", message_lower):
        return False
    cues = (
        "today's session",
        "todays session",
        "completed the session",
        "finished the session",
        "finished today's topic",
        "finished my session",
        "completed today's",
        "done with my learning",
        "done with ",
        "mark this complete",
        "marked complete",
        "session complete",
        "topic complete",
    )
    if any(c in message_lower for c in cues):
        return True
    return bool(_COMPLETION_RE.search(message_lower))


def _complete_blocked_message(session_state: str) -> Optional[str]:
    """Same rules as learning_update complete — ongoing or overdue may be completed."""
    if session_state in ("ongoing", "overdue"):
        return None
    if session_state == "locked":
        return (
            "That session is still locked. It unlocks within 24 hours of its scheduled time."
        )
    if session_state == "unlocked_future":
        return (
            "That session hasn't started yet, so I can't mark it complete. "
            "You can reschedule or skip it."
        )
    return "That session can't be completed right now."


async def _session_state_for_topic(
    goal_id: str,
    topic: Dict[str, Any],
    *,
    timezone_name: str,
) -> str:
    all_topics = await get_topics_for_goal(goal_id)
    prev_scheduled = None
    prev_resolved = None
    try:
        cur_order = int(topic.get("order") or 0)
        prev = next(
            (t for t in all_topics if int(t.get("order") or 0) == cur_order - 1),
            None,
        )
        if prev:
            prev_scheduled = prev.get("scheduled_date")
            prev_resolved = prev.get("completed_at") or prev.get("updated_at")
    except Exception:
        prev_scheduled = None
        prev_resolved = None

    return compute_session_state(
        topic,
        datetime.now(get_zoneinfo(timezone_name)),
        previous_scheduled_date=prev_scheduled,
        previous_resolved_at=prev_resolved,
    )


def _blocked_completion_response(
    *,
    msg: str,
    user_name: Optional[str],
    settings_data: Dict[str, Any],
    preprocessed: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "status": "ok",
        "too_short": False,
        "preprocessed": preprocessed,
        "context_handled": True,
        "learning_topic_completed": False,
        "response_text": msg,
        "user_name": user_name,
        "settings": settings_data,
    }


async def maybe_handle_learning_topic_done_chat(
    *,
    user_id: str,
    message_lower: str,
    user_name: Optional[str],
    history: List[Any],
    settings_data: Dict[str, Any],
    preprocessed: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    If the message sounds like the user finished a learning session, mark the
    next matching pending topic complete and return a chat response dict.
    Returns None when this path does not apply.
    """
    _ = history
    if not looks_like_learning_completion(message_lower):
        return None

    today_only = _implies_today(message_lower)
    hint = extract_learning_subject_hint(message_lower)

    picked = await pick_pending_topic_for_chat_completion(
        user_id,
        subject_hint=hint,
        today_only=today_only,
    )
    if not picked and today_only:
        picked = await pick_pending_topic_for_chat_completion(
            user_id,
            subject_hint=hint,
            today_only=False,
        )
    if not picked and hint:
        picked = await pick_pending_topic_for_chat_completion(
            user_id,
            subject_hint=None,
            today_only=today_only,
        )
        if not picked and today_only:
            picked = await pick_pending_topic_for_chat_completion(
                user_id,
                subject_hint=None,
                today_only=False,
            )

    if not picked:
        paused = await get_paused_goals_for_user(user_id, hint)
        if len(paused) == 1:
            from handlers.learning.update import start_resume_confirm_pending

            entities = {"topic": hint} if hint else {}
            msg = await start_resume_confirm_pending(
                user_id,
                paused[0],
                "complete",
                entities=entities,
                user_name=user_name,
            )
        else:
            msg = (
                "I couldn't find an active learning session to mark complete. "
                "Check your learning plan in the app, or tell me which topic you finished."
            )
        return {
            "status": "ok",
            "too_short": False,
            "preprocessed": preprocessed,
            "context_handled": True,
            "learning_topic_completed": False,
            "response_text": msg,
            "user_name": user_name,
            "settings": settings_data,
        }

    goal_id = str(picked["goal"]["_id"])
    user_doc = await fetch_user(user_id) or {}
    tz = resolve_timezone_name(user_doc.get("timezone"))

    current = await get_current_session(goal_id)
    if not current:
        return _blocked_completion_response(
            msg=(
                "I couldn't find a pending session on that plan to mark complete."
            ),
            user_name=user_name,
            settings_data=settings_data,
            preprocessed=preprocessed,
        )

    session_state = await _session_state_for_topic(goal_id, current, timezone_name=tz)
    blocked_msg = _complete_blocked_message(session_state)
    if blocked_msg:
        return _blocked_completion_response(
            msg=blocked_msg,
            user_name=user_name,
            settings_data=settings_data,
            preprocessed=preprocessed,
        )

    topic_id = str(current["_id"])
    ok = await complete_topic(topic_id)
    if not ok:
        msg = "I couldn't update your learning progress just now. Please try again from the app."
        return {
            "status": "ok",
            "too_short": False,
            "preprocessed": preprocessed,
            "context_handled": True,
            "learning_topic_completed": False,
            "response_text": msg,
            "user_name": user_name,
            "settings": settings_data,
        }

    goal = await get_goal_by_id(goal_id)
    topic_title = str(current.get("title") or "session")
    goal_title = str((goal or {}).get("title") or "your plan")
    done = int((goal or {}).get("completed_topics") or 0)
    total = int((goal or {}).get("total_topics") or 0)

    if (goal or {}).get("status") == "completed":
        body = f'Amazing — you finished "{goal_title}"! That was your last session in this plan.'
    else:
        body = (
            f'Nice work — I marked "{topic_title}" complete '
            f"({done}/{total} sessions in {goal_title})."
        )
    if user_name:
        body = f"{body} Keep going, {user_name}."

    notifications: List[Dict[str, Any]] = []
    if (goal or {}).get("status") == "completed":
        notifications = [
            {
                "user_id": str(user_id),
                "sender_id": None,
                "type": "goal_progress",
                "reference_type": "learning_goal",
                "reference_id": str(goal_id),
                "title": "Learning goal completed",
                "message": body[:500],
                "action_required": False,
                "delivery_channel": ["push", "in_app"],
            }
        ]

    return {
        "status": "ok",
        "too_short": False,
        "preprocessed": preprocessed,
        "context_handled": True,
        "learning_topic_completed": True,
        "response_text": body,
        "notifications": notifications,
        "user_name": user_name,
        "settings": settings_data,
    }
