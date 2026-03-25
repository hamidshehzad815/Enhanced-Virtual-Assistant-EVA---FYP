"""
Entity scoping for Phase 7.
Filters and normalizes extracted entities according to detected intent.
"""
from typing import Any, Dict, Set

_INTENT_ENTITY_SCOPE: Dict[str, Set[str]] = {
    "scheduling_add": {"task_name", "date", "time", "priority", "duration", "collaborator"},
    "scheduling_delete": {"task_name", "date", "priority", "status"},
    "scheduling_update": {
        "task_name",
        "date",
        "time",
        "priority",
        "status",
        "duration",
        "new_task_name",
        "new_date",
        "new_time",
        "new_priority",
        "new_status",
        "new_duration",
        "new_start_date",
    },
    "scheduling_show": {"date", "priority", "status", "subject", "task_name"},
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
    "behavioral": {"date", "time", "priority", "status", "subject"},
}

_ENTITY_ALIASES: Dict[str, str] = {
    "new_taskname": "new_task_name",
    "new_scheduled_date": "new_date",
    "new_start_date": "new_start_date",
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
    "status": "status",
    "topic": "topic",
    "subtopic": "subtopic",
    "start_date": "start_date",
    "next_topic": "next_topic",
}


def _normalize_key(key: str) -> str:
    return _ENTITY_ALIASES.get(key, key)


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
        if allowed and key not in allowed:
            continue
        scoped[key] = value

    return scoped
