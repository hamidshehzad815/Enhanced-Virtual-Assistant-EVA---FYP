"""
Natural-language completion for learning roadmap topics (Phase 10).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from db.learning_goals import get_goal_by_id
from db.roadmap_topics import (
    pick_pending_topic_for_chat_completion,
    update_topic_status,
)
from utils.learning_utils import SUPPORTED_TOPICS, TOPIC_ALIAS_MAP


_COMPLETION_RE = re.compile(
    r"(completed|finished|done)\s+(with\s+)?|(today'?s\s+)?(session|topic|lesson)|"
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

    topic_id = str(picked["topic"]["_id"])
    ok = await update_topic_status(topic_id, "completed")
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

    goal = await get_goal_by_id(str(picked["goal"]["_id"]))
    topic_title = str(picked["topic"].get("title") or "session")
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

    return {
        "status": "ok",
        "too_short": False,
        "preprocessed": preprocessed,
        "context_handled": True,
        "learning_topic_completed": True,
        "response_text": body,
        "user_name": user_name,
        "settings": settings_data,
    }
