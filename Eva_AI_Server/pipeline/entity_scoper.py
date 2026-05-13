"""
Entity scoping for Phase 7.
Filters and normalizes extracted entities according to detected intent.
"""
import re
from typing import Any, Dict, Set

from config.settings import settings

_INTENT_ENTITY_SCOPE: Dict[str, Set[str]] = {
    "scheduling_add": {"task_name", "date", "time", "priority", "duration", "collaborator"},
    "scheduling_delete": {"task_name", "date", "priority", "status"},
    "scheduling_update": {
        "task_name",
        "date",
        "priority",
        "status",
        "new_title",
        "new_date",
        "new_time",
        "new_priority",
        "new_status",
        "new_duration",
    },
    "scheduling_show": {"date", "priority", "status", "task_name"},
    "behavioral": {"day"},
    "learning_create": {
        "topic",
        "subtopic",
        "start_date",
        "duration",
        "person",
    },
}

_ENTITY_ALIASES: Dict[str, str] = {
    # Update-intent title aliases:
    # NER model commonly emits `new_taskname`; we normalize all variants to
    # canonical `new_title` for downstream handler consistency.
    "new_taskname": "new_title",
    "new_task_name": "new_title",
    "new_title": "new_title",
    "new_scheduled_date": "new_date",
    "new_start_date": "new_date",
    "new_time": "new_time",
    "new_priority": "new_priority",
    "new_status": "new_status",
    "new_duration": "new_duration",
    "task_name": "task_name",
    "date": "date",
    "time": "time",
    "priority": "priority",
    "duration": "duration",
    "collaborator": "collaborator",
    # NER compatibility: some model versions emit `person` for collaborator
    # mentions (e.g., "with Ahmed"). Normalize to canonical collaborator key.
    "person": "collaborator",
    "person_name": "collaborator",
    "people": "collaborator",
    "status": "status",
    "subject": "task_name",
}


def _normalize_key(key: str) -> str:
    return _ENTITY_ALIASES.get(key, key)


_WEEKDAY_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    flags=re.IGNORECASE,
)


def _extract_weekday(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    match = _WEEKDAY_PATTERN.search(text)
    if not match:
        return ""
    return str(match.group(1)).lower()


def scope_entities(entities: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """
    Keep only entities relevant to an intent and normalize entity keys.
    """
    if not entities:
        return {}

    allowed = _INTENT_ENTITY_SCOPE.get(intent, set())
    scoped: Dict[str, Any] = {}

    for raw_key, value in entities.items():
        key = _normalize_key(raw_key)

        if intent == "learning_create":
            if raw_key == "subject":
                key = "topic"
            if key == "collaborator":
                key = "person"
            if key == "date":
                key = "start_date"

        if raw_key == "subject" and "task_name" in scoped:
            # Do not allow a generic subject alias to override a strong task_name.
            continue

        if intent == "behavioral":
            if key == "day":
                day_value = _extract_weekday(value) or str(value or "").strip().lower()
                if day_value:
                    scoped["day"] = day_value
                continue

            if key == "date" and bool(getattr(settings, "BEHAVIORAL_DATE_AS_DAY_FALLBACK", False)):
                day_value = _extract_weekday(value)
                if day_value:
                    scoped["day"] = day_value
                continue
            continue

        if allowed and key not in allowed:
            continue

        if key == "date" and intent == "scheduling_delete":
            weekday = _extract_weekday(value)
            if weekday:
                scoped[key] = weekday
                continue

        scoped[key] = value

    return scoped
