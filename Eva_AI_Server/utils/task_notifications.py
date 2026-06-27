"""Notification payloads for task lifecycle events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from utils.api_datetime import utc_naive_to_local


def notification_display_name(user_name: Optional[str]) -> str:
    if not user_name or not str(user_name).strip():
        return "there"
    return str(user_name).strip().split()[0]


def format_due_display(value: Any, timezone_name: str) -> str:
    local_dt = utc_naive_to_local(value, timezone_name)
    if local_dt is None:
        return str(value or "").strip() or "the new time"
    return local_dt.strftime("%A, %d %b %Y at %I:%M %p").replace(" 0", " ")


def build_task_rescheduled_notification(
    *,
    user_id: str,
    user_name: Optional[str],
    task_title: str,
    due_datetime: Any,
    timezone_name: str,
    reference_type: str = "task",
    reference_id: str,
) -> Dict[str, Any]:
    when = format_due_display(due_datetime, timezone_name)
    who = notification_display_name(user_name)
    title = str(task_title or "Your task").strip() or "Your task"

    return {
        "user_id": str(user_id),
        "sender_id": None,
        "type": "task_rescheduled",
        "reference_type": reference_type,
        "reference_id": str(reference_id),
        "title": "Task rescheduled",
        "message": f"Hey {who}, {title} was rescheduled to {when}.",
        "action_required": False,
        "delivery_channel": ["push", "in_app", "email"],
        "scheduled_at": datetime.utcnow().isoformat(),
    }
