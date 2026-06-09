"""
Calendar conflict checks for a user (tasks + learning schedule slots).
Used for collaborators on tasks and shared learning plans.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from db.readers import fetch_user, fetch_user_settings
from db.tasks import find_overlapping_task_for_user
from utils.learning_schedule_conflicts import find_task_conflicts_from_settings
from utils.quiet_hours import find_quiet_hour_matches_for_datetime, format_quiet_hour_labels
from utils.timezone_utils import resolve_timezone_name


async def find_user_calendar_conflicts(
    user_id: str,
    due: datetime,
    duration_minutes: int,
    *,
    timezone_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Return a conflict descriptor if the user has a task or learning-slot clash.

    ``None`` means the window is free for that user.
    """
    if not user_id or not isinstance(due, datetime):
        return None

    tz = timezone_name
    if not tz:
        user_doc = await fetch_user(user_id)
        tz = resolve_timezone_name((user_doc or {}).get("timezone"))

    overlap_task = await find_overlapping_task_for_user(
        user_id,
        due,
        duration_minutes,
    )
    if overlap_task:
        return {
            "kind": "task",
            "title": str(overlap_task.get("title") or "another task"),
            "task_id": str(overlap_task.get("_id") or ""),
        }

    settings = await fetch_user_settings(user_id)
    quiet_matches = find_quiet_hour_matches_for_datetime(
        settings,
        due,
        duration_minutes,
        timezone_name=tz,
    )
    if quiet_matches:
        return {
            "kind": "quiet_hours",
            "labels": format_quiet_hour_labels(quiet_matches),
            "blocks": quiet_matches,
        }

    schedule_conflicts = find_task_conflicts_from_settings(
        due,
        duration_minutes,
        settings,
        timezone_name=tz,
    )
    if schedule_conflicts:
        first = schedule_conflicts[0]
        return {
            "kind": "learning_schedule",
            "schedule_label": str(first.get("schedule_label") or "learning schedule"),
            "slot": first.get("slot") or {},
            "conflicts": schedule_conflicts,
        }

    return None


def format_collaborator_conflict_message(
    collaborator_name: str,
    conflict: Dict[str, Any],
    *,
    for_learning_plan: bool = False,
) -> str:
    """User-facing message when a collaborator cannot use a time window."""
    name = (collaborator_name or "Your collaborator").strip()
    if conflict.get("kind") == "quiet_hours":
        labels = str(conflict.get("labels") or "quiet hours")
        if for_learning_plan:
            return (
                f"{name} has {labels} at that time, so a lesson in this plan would "
                "fall in their quiet hours. Adjust the plan, remove that collaborator, "
                "or ask them to change their quiet hours."
            )
        return (
            f"{name} has {labels} at that time. "
            "Please choose a different time for this task."
        )

    if conflict.get("kind") == "task":
        title = str(conflict.get("title") or "another task")
        if for_learning_plan:
            return (
                f"{name} already has “{title}” scheduled when a lesson in this plan would run. "
                "Pick different plan dates, remove that collaborator, or ask them to free that time."
            )
        return (
            f"{name} is busy — they already have “{title}” at that time. "
            "Please choose a different time."
        )

    label = str(conflict.get("schedule_label") or "a learning schedule")
    slot = conflict.get("slot") or {}
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    day_i = int(slot.get("day", 0))
    day_name = day_names[day_i] if 0 <= day_i < 7 else f"day {day_i}"
    time_s = str(slot.get("time") or "")
    if for_learning_plan:
        return (
            f"{name} has learning time reserved on {day_name} {time_s} (“{label}”), "
            "which clashes with a lesson in this plan. "
            "Adjust the plan, remove that collaborator, or ask them to change their learning schedule."
        )
    return (
        f"{name} has learning time reserved on {day_name} {time_s} (“{label}”). "
        "Please choose a different time for this task."
    )
