"""
Quiet hours helpers — full time-window overlap checks (shared across handlers).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone as dt_timezone
from typing import Any, Dict, List, Optional

from utils.timezone_utils import get_zoneinfo

MINUTES_PER_DAY = 24 * 60


def parse_clock_minutes(value: Any) -> Optional[int]:
    raw = str(value or "").strip()
    if not raw:
        return None

    match = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", raw)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    return hour * 60 + minute


def normalize_quiet_hour_blocks(settings: Dict[str, Any]) -> List[Dict[str, str]]:
    has_quiet_hours = bool(
        settings.get("has_quiet_hours")
        or settings.get("quiet_hours_enabled")
    )
    if not has_quiet_hours:
        return []

    blocks: List[Dict[str, str]] = []
    for block in settings.get("quiet_hours") or []:
        if not isinstance(block, dict):
            continue
        if block.get("enabled") is False:
            continue

        start = str(block.get("start") or "").strip()
        end = str(block.get("end") or "").strip()
        if parse_clock_minutes(start) is None or parse_clock_minutes(end) is None:
            continue

        label = str(block.get("label") or "").strip() or "quiet hours"
        blocks.append({"label": label, "start": start, "end": end})

    if blocks:
        return blocks

    legacy_start = str(settings.get("quiet_hours_start") or "").strip()
    legacy_end = str(settings.get("quiet_hours_end") or "").strip()
    if parse_clock_minutes(legacy_start) is not None and parse_clock_minutes(legacy_end) is not None:
        return [{"label": "quiet hours", "start": legacy_start, "end": legacy_end}]

    return []


def _intervals_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and end_a > start_b


def window_overlaps_quiet_block(
    start_minutes: int,
    duration_minutes: int,
    block_start: int,
    block_end: int,
) -> bool:
    """True when [start, start+duration) overlaps a quiet-hours block on one calendar day."""
    duration_minutes = max(1, int(duration_minutes or 1))
    task_end = int(start_minutes) + duration_minutes

    if block_start == block_end:
        return True

    task_parts: List[tuple[int, int]] = []
    if task_end <= MINUTES_PER_DAY:
        task_parts.append((start_minutes, task_end))
    else:
        task_parts.append((start_minutes, MINUTES_PER_DAY))
        task_parts.append((0, task_end - MINUTES_PER_DAY))

    if block_start < block_end:
        quiet_parts = [(block_start, block_end)]
    else:
        quiet_parts = [(block_start, MINUTES_PER_DAY), (0, block_end)]

    for ts, te in task_parts:
        for qs, qe in quiet_parts:
            if _intervals_overlap(ts, te, qs, qe):
                return True
    return False


def find_quiet_hour_matches(
    settings: Dict[str, Any],
    time_value: str,
    duration_minutes: int = 60,
) -> List[Dict[str, str]]:
    start_minutes = parse_clock_minutes(time_value)
    if start_minutes is None:
        return []

    duration_minutes = max(1, int(duration_minutes or 1))
    matches: List[Dict[str, str]] = []
    for block in normalize_quiet_hour_blocks(settings):
        block_start = parse_clock_minutes(block.get("start"))
        block_end = parse_clock_minutes(block.get("end"))
        if block_start is None or block_end is None:
            continue
        if window_overlaps_quiet_block(start_minutes, duration_minutes, block_start, block_end):
            matches.append(block)
    return matches


def find_quiet_hour_matches_for_datetime(
    settings: Dict[str, Any],
    due: datetime,
    duration_minutes: int,
    *,
    timezone_name: str = "UTC",
) -> List[Dict[str, str]]:
    if not isinstance(due, datetime):
        return []

    tz = get_zoneinfo(timezone_name or "UTC")
    if due.tzinfo is None:
        local = due.replace(tzinfo=dt_timezone.utc).astimezone(tz)
    else:
        local = due.astimezone(tz)

    return find_quiet_hour_matches(
        settings,
        local.strftime("%H:%M:%S"),
        duration_minutes,
    )


def weekly_slot_overlaps_quiet_hours(
    slot_time: str,
    slot_duration_minutes: int,
    quiet_blocks: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    start_minutes = parse_clock_minutes(slot_time)
    if start_minutes is None:
        return []

    slot_duration_minutes = max(1, int(slot_duration_minutes or 1))
    matches: List[Dict[str, str]] = []
    for block in quiet_blocks:
        block_start = parse_clock_minutes(block.get("start"))
        block_end = parse_clock_minutes(block.get("end"))
        if block_start is None or block_end is None:
            continue
        if window_overlaps_quiet_block(
            start_minutes,
            slot_duration_minutes,
            block_start,
            block_end,
        ):
            matches.append(block)
    return matches


def find_learning_slot_quiet_hour_conflicts(
    schedules: List[Dict[str, Any]],
    quiet_blocks: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    if not quiet_blocks:
        return conflicts

    for schedule in schedules or []:
        sid = str(schedule.get("id") or "").strip()
        label = str(schedule.get("label") or "Learning schedule").strip()
        for slot in schedule.get("slots") or []:
            if not isinstance(slot, dict):
                continue
            time_s = slot.get("time")
            if not time_s:
                continue
            dur = int(slot.get("duration_minutes") or 90)
            hits = weekly_slot_overlaps_quiet_hours(str(time_s), dur, quiet_blocks)
            for hit in hits:
                conflicts.append(
                    {
                        "schedule_id": sid,
                        "schedule_label": label,
                        "slot": {
                            "day": int(slot.get("day", 0)),
                            "time": str(time_s),
                            "duration_minutes": dur,
                        },
                        "quiet_hour": dict(hit),
                    },
                )
    return conflicts


def format_quiet_hour_labels(blocks: List[Dict[str, str]]) -> str:
    labels: List[str] = []
    for block in blocks:
        label = str(block.get("label") or "").replace("_", " ").strip()
        if label:
            labels.append(label)

    if not labels:
        return "quiet hours"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def format_quiet_hours_learning_block_message(
    matches: List[Dict[str, str]],
    *,
    session_label: str = "A learning session",
    user_name: Optional[str] = None,
) -> str:
    labels = format_quiet_hour_labels(matches)
    name_bit = f", {user_name}" if user_name else ""
    return (
        f"{session_label} would fall during your {labels}{name_bit}. "
        "Learning sessions cannot be scheduled in quiet hours. "
        "Change your learning schedule, quiet hours in Settings, or pick different plan dates."
    )


def format_quiet_hours_settings_conflict_message(conflicts: List[Dict[str, Any]]) -> str:
    first = conflicts[0] if conflicts else {}
    schedule_label = str(first.get("schedule_label") or "Learning schedule")
    slot = first.get("slot") or {}
    quiet = first.get("quiet_hour") or {}
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
    quiet_label = str(quiet.get("label") or "quiet hours")
    extra = f" ({len(conflicts)} overlaps)" if len(conflicts) > 1 else ""
    return (
        f'Learning schedule "{schedule_label}" ({day_name} {time_s}) overlaps '
        f'your "{quiet_label}" quiet hours{extra}. '
        "Adjust the schedule or quiet hours so they do not overlap."
    )
