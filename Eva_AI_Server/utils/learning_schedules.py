"""
Labeled learning schedules (Settings) and selection during learning plan creation.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from db.learning_goals import get_active_goals_for_user

DEFAULT_DURATION_MINUTES = 90

_WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

# Sentinel in schedule_options when user wants different times (not a real schedule id).
CHOICE_NEW_SCHEDULE_IN_SETTINGS = "__new_schedule_in_settings__"


def _normalize_slot(slot: Any, default_duration: int) -> Optional[Dict[str, Any]]:
    if not isinstance(slot, dict):
        return None
    try:
        day = int(slot["day"])
    except (KeyError, TypeError, ValueError):
        return None
    if day < 0 or day > 6:
        return None
    time_raw = str(slot.get("time") or "").strip()
    if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_raw):
        return None
    dur = default_duration
    if slot.get("duration_minutes") is not None:
        try:
            dur = int(slot["duration_minutes"])
        except (TypeError, ValueError):
            return None
        if dur < 15 or dur > 240:
            return None
    return {"day": day, "time": time_raw, "duration_minutes": dur}


def schedules_from_settings(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return labeled schedules from user settings.

    Each entry: ``{ "id", "label", "slots": [{ "day", "time", "duration_minutes" }, ...] }``.
    Old Mongo docs may still store a flat slot array; that is migrated on read only.
    """
    default_dur = int(settings.get("preferred_learning_duration") or DEFAULT_DURATION_MINUTES)
    modern = settings.get("preferred_learning_schedules")
    if isinstance(modern, list) and modern:
        out: List[Dict[str, Any]] = []
        for entry in modern:
            if not isinstance(entry, dict):
                continue
            sid = str(entry.get("id") or "").strip() or str(uuid.uuid4())
            label = str(entry.get("label") or "").strip() or "Schedule"
            slots_in = entry.get("slots")
            if not isinstance(slots_in, list):
                continue
            slots: List[Dict[str, Any]] = []
            for raw in slots_in:
                norm = _normalize_slot(raw, default_dur)
                if norm:
                    slots.append(norm)
            if slots:
                out.append({"id": sid, "label": label, "slots": slots})
        return out

    legacy = settings.get("preferred_learning_schedule")
    if isinstance(legacy, list) and legacy:
        slots: List[Dict[str, Any]] = []
        for raw in legacy:
            norm = _normalize_slot(raw, default_dur)
            if norm:
                slots.append(norm)
        if slots:
            return [{"id": "default", "label": "Default", "slots": slots}]
    return []


async def used_learning_schedule_ids(user_id: str) -> Set[str]:
    """Schedule ids already tied to an active learning goal for this user."""
    used: Set[str] = set()
    for goal in await get_active_goals_for_user(user_id):
        sid = goal.get("learning_schedule_id")
        if sid is not None and str(sid).strip():
            used.add(str(sid).strip())
    return used


def schedule_by_id(
    schedules: List[Dict[str, Any]],
    schedule_id: str,
) -> Optional[Dict[str, Any]]:
    sid = str(schedule_id or "").strip()
    if not sid:
        return None
    for entry in schedules:
        if str(entry.get("id") or "").strip() == sid:
            return entry
    return None


def available_schedules(
    schedules: List[Dict[str, Any]],
    used_ids: Set[str],
) -> List[Dict[str, Any]]:
    return [s for s in schedules if str(s.get("id") or "").strip() not in used_ids]


def _format_time_12h(hhmm: str) -> str:
    """Display HH:MM as 12-hour clock (e.g. 6:00 PM)."""
    parts = str(hhmm or "").strip().split(":")
    if len(parts) != 2:
        return hhmm
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return hhmm
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d} {suffix}"


def _format_slot_line(slot: Dict[str, Any]) -> str:
    day = int(slot.get("day", 0))
    day_name = _WEEKDAY_NAMES[day] if 0 <= day <= 6 else f"Day {day}"
    time_s = _format_time_12h(str(slot.get("time") or ""))
    dur = int(slot.get("duration_minutes") or DEFAULT_DURATION_MINUTES)
    return f"   · {day_name} {time_s}, {dur} min per session"


def _format_schedule_block(index: int, entry: Dict[str, Any]) -> str:
    label = str(entry.get("label") or "Schedule").strip()
    slots = sorted(
        list(entry.get("slots") or []),
        key=lambda s: int(s.get("day", 0)),
    )
    slot_lines = [_format_slot_line(s) for s in slots if isinstance(s, dict)]
    body = "\n".join(slot_lines) if slot_lines else "   · (no days configured)"
    return f"{index}. {label}\n{body}"


def _build_schedule_choice_message(free: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Build prompt text and options for pending schedule_choice.

    Always lists timings; even one schedule requires an explicit reply (1 = use it).
  """
    blocks = [_format_schedule_block(i, s) for i, s in enumerate(free, start=1)]
    options: List[Dict[str, Any]] = [
        {
            "id": str(s.get("id") or ""),
            "label": str(s.get("label") or "Schedule"),
        }
        for s in free
    ]

    n = len(free)
    if n == 1:
        intro = (
            "You have one learning schedule available for this plan:\n\n"
            + blocks[0]
            + "\n\nReply 1 to use this schedule.\n\n"
            "If you want different days or session lengths for this topic, "
            "add another schedule in Settings (Learning schedule), then ask me to create the plan again."
        )
        options.append(
            {
                "id": CHOICE_NEW_SCHEDULE_IN_SETTINGS,
                "label": "I want different learning times (set up in Settings)",
            },
        )
        intro += "\n\nReply 2 if you will set up a different schedule in Settings first."
        return intro, options

    intro = (
        "Which learning schedule should I use for this plan?\n\n"
        + "\n\n".join(blocks)
        + f"\n\nReply with the number (1–{n})."
    )
    tip = (
        "\n\nIf none of these fit this topic, add another schedule in Settings (Learning schedule) "
        "with the days, times, and session lengths you want, then try again."
    )
    return intro + tip, options


def resolve_schedule_for_learning(
    *,
    entities: Dict[str, Any],
    schedules: List[Dict[str, Any]],
    used_ids: Set[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    """
    Pick a schedule for plan creation.

    Returns:
      (chosen_schedule, user_error_message, pending_context)
      pending_context is set when the user must pick by number (multiple options).
    """
    if not schedules:
        return (
            None,
            "Set up at least one learning schedule in Settings (with a label and your weekly times), then try again.",
            None,
        )

    chosen_id = str(entities.get("learning_schedule_id") or "").strip()
    if chosen_id:
        entry = schedule_by_id(schedules, chosen_id)
        if not entry:
            return (
                None,
                "That learning schedule was not found. Open Settings and check your schedules, or pick another option.",
                None,
            )
        if chosen_id in used_ids:
            return (
                None,
                "That schedule is already tied to another active learning plan. "
                "If this topic needs different days or session lengths, add a new schedule in "
                "Settings → Learning schedule, or finish your other plan first.",
                None,
            )
        return entry, None, None

    free = available_schedules(schedules, used_ids)
    if not free:
        return (
            None,
            "Every learning schedule you saved is already linked to an active plan. "
            "To study this topic on different days or times, open Settings (Learning schedule), "
            "create a new schedule with the times you want, then ask me to set up this plan again.",
            None,
        )

    # Always ask — even one schedule: reply 1 = use it, 2 = set up different times in Settings.
    message, options = _build_schedule_choice_message(free)
    pending = {
        "pending_action": {
            "intent": "learning_create",
            "stage": "schedule_choice",
            "entities": dict(entities),
            "schedule_options": options,
        },
        "expected_response": "number",
    }
    return None, message, pending


def slots_for_plan_entities(
    settings: Dict[str, Any],
    entities: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Resolve slot list for feasibility / pending duration using chosen schedule id when set."""
    schedules = schedules_from_settings(settings)
    sid = str(entities.get("learning_schedule_id") or "").strip()
    if sid:
        entry = schedule_by_id(schedules, sid)
        if entry:
            return list(entry.get("slots") or [])
    if len(schedules) == 1:
        return list(schedules[0].get("slots") or [])
    return []


def parse_schedule_choice_number(message: str, options: List[Dict[str, Any]]) -> Optional[str]:
    """Return schedule id for 1-based choice, or None if invalid."""
    text = (message or "").strip().lower()
    if not text or not options:
        return None
    m = re.search(r"\b(\d+)\b", text)
    if not m:
        return None
    try:
        idx = int(m.group(1))
    except ValueError:
        return None
    if idx < 1 or idx > len(options):
        return None
    chosen = str(options[idx - 1].get("id") or "").strip()
    return chosen or None


def schedule_choice_is_settings_redirect(schedule_id: Optional[str]) -> bool:
    return schedule_id == CHOICE_NEW_SCHEDULE_IN_SETTINGS
