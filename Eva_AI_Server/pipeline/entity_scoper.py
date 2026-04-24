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
    "learning_create": {"topic", "subtopic", "duration", "start_date", "collaborator"},
    "learning_update": {
        "topic",
        "subtopic",
        "date",
        "new_date",
        "new_duration",
        "next_topic",
        "new_start_date",
    },
    "learning_delete": {"topic", "subtopic", "date", "start_date"},
    "learning_show": {"topic", "subtopic", "date", "status", "start_date"},
    "behavioral": {"day"},
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
    "day": "day",
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
    "topic": "topic",
    "subtopic": "subtopic",
    "start_date": "start_date",
    "next_topic": "next_topic",
}

_WEEKDAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}


def _normalize_key(key: str) -> str:
    return _ENTITY_ALIASES.get(key, key)


def _extract_weekday(value: Any) -> Any:
    if isinstance(value, list):
        weekdays = []
        for item in value:
            extracted = _extract_weekday(item)
            if extracted:
                weekdays.append(extracted)
        if not weekdays:
            return None
        return weekdays[0] if len(weekdays) == 1 else weekdays

    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None

    if normalized in _WEEKDAYS:
        return normalized

    for weekday in _WEEKDAYS:
        if re.search(rf"\b{re.escape(weekday)}\b", normalized):
            return weekday

    return None


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
        if intent == "scheduling_show" and key == "subject":
            # Backward-compatible normalization: show now uses task_name as
            # canonical title-keyword filter.
            key = "task_name"

        if (
            intent == "behavioral"
            and settings.BEHAVIORAL_DATE_AS_DAY_FALLBACK
            and key == "date"
        ):
            weekday = _extract_weekday(value)
            if weekday:
                key = "day"
                value = weekday

        if intent == "behavioral" and key == "day":
            value = _extract_weekday(value) or value

        if allowed and key not in allowed:
            continue
        scoped[key] = value

    return scoped
