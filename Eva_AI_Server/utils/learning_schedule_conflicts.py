"""
Learning schedule slot vs task time conflicts (recurring weekly slots vs concrete tasks).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from utils.learning_schedules import schedules_from_settings
from utils.timezone_utils import get_zoneinfo

_WEEKDAY_LONG_TO_MON0 = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_DEFAULT_SLOT_DURATION = 90
_DEFAULT_TASK_DURATION = 120


def _parse_hhmm(value: str) -> int:
    parts = str(value or "").strip().split(":")
    if len(parts) != 2:
        return 0
    return int(parts[0]) * 60 + int(parts[1])


def _weekday_and_minutes(due: datetime, tz_name: str) -> tuple[Optional[int], int]:
    tz = get_zoneinfo(tz_name or "UTC")
    if due.tzinfo is None:
        local = due.replace(tzinfo=tz)
    else:
        local = due.astimezone(tz)
    wd = local.weekday()
    return wd, local.hour * 60 + local.minute


def weekly_slot_overlaps_task(
    due: datetime,
    task_duration_minutes: int,
    slot_day: int,
    slot_time: str,
    slot_duration_minutes: int,
    *,
    timezone_name: str = "UTC",
) -> bool:
    """True when a task window overlaps a recurring learning slot on that weekday."""
    wd, task_start = _weekday_and_minutes(due, timezone_name)
    if wd is None or wd != int(slot_day):
        return False
    task_dur = max(1, int(task_duration_minutes or _DEFAULT_TASK_DURATION))
    slot_dur = max(1, int(slot_duration_minutes or _DEFAULT_SLOT_DURATION))
    task_end = task_start + task_dur
    slot_start = _parse_hhmm(slot_time)
    slot_end = slot_start + slot_dur
    return task_start < slot_end and task_end > slot_start


def find_task_conflicts_with_learning_schedules(
    due: datetime,
    task_duration_minutes: int,
    schedules: Sequence[Dict[str, Any]],
    *,
    timezone_name: str = "UTC",
) -> List[Dict[str, Any]]:
    """Return learning schedule slots that overlap a proposed task window."""
    conflicts: List[Dict[str, Any]] = []
    for schedule in schedules or []:
        sid = str(schedule.get("id") or "").strip()
        label = str(schedule.get("label") or "Learning schedule").strip()
        for slot in schedule.get("slots") or []:
            if not isinstance(slot, dict):
                continue
            day = slot.get("day")
            time_s = slot.get("time")
            if day is None or not time_s:
                continue
            slot_dur = int(slot.get("duration_minutes") or _DEFAULT_SLOT_DURATION)
            if weekly_slot_overlaps_task(
                due,
                task_duration_minutes,
                int(day),
                str(time_s),
                slot_dur,
                timezone_name=timezone_name,
            ):
                conflicts.append(
                    {
                        "schedule_id": sid,
                        "schedule_label": label,
                        "slot": {
                            "day": int(day),
                            "time": str(time_s),
                            "duration_minutes": slot_dur,
                        },
                    },
                )
    return conflicts


def find_task_conflicts_from_settings(
    due: datetime,
    task_duration_minutes: int,
    settings: Dict[str, Any],
    *,
    timezone_name: str = "UTC",
) -> List[Dict[str, Any]]:
    schedules = schedules_from_settings(settings or {})
    return find_task_conflicts_with_learning_schedules(
        due,
        task_duration_minutes,
        schedules,
        timezone_name=timezone_name,
    )


def format_learning_schedule_conflict_message(
    conflicts: List[Dict[str, Any]],
    *,
    user_name: Optional[str] = None,
) -> str:
    first = conflicts[0] if conflicts else {}
    label = str(first.get("schedule_label") or "your learning schedule")
    slot = first.get("slot") or {}
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
    name_bit = f", {user_name}" if user_name else ""
    extra = ""
    if len(conflicts) > 1:
        extra = f" ({len(conflicts)} learning slots overlap)"
    return (
        f"That time overlaps your learning schedule “{label}” "
        f"({day_name} {time_s}){extra}{name_bit}. "
        "Pick a different time or change your learning schedule in Settings."
    )
