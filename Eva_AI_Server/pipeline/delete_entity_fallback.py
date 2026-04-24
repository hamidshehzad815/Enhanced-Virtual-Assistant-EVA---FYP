"""
Deterministic fallback extraction for scheduling delete entities.
Used to improve delete intent robustness when model extraction misses fields.
"""
import re
from typing import Dict, Optional

from utils.task_value_normalizer import (
    PRIORITY_USER_VALUES,
    STATUS_USER_VALUES,
    build_value_regex,
    canonicalize_priority,
    canonicalize_status,
)


_DELETE_VERB_PATTERN = re.compile(r"\b(delete|remove)\b", flags=re.IGNORECASE)
_PRIORITY_VALUE_TOKEN = build_value_regex(PRIORITY_USER_VALUES)
_STATUS_VALUE_TOKEN = build_value_regex(STATUS_USER_VALUES)

_PRIORITY_PATTERN = re.compile(rf"\b({_PRIORITY_VALUE_TOKEN})\s+priority\b", flags=re.IGNORECASE)
_STATUS_PATTERN = re.compile(rf"\b({_STATUS_VALUE_TOKEN})\b", flags=re.IGNORECASE)
_RELATIVE_DATE_PATTERN = re.compile(
    r"\b(today|tomorrow|yesterday|tonight)\b",
    flags=re.IGNORECASE,
)
_DAY_OF_WEEK_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    flags=re.IGNORECASE,
)
_ISO_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

_TASK_NAME_STOPWORDS = {
    "all",
    "of",
    "them",
    "my",
    "the",
    "a",
    "an",
    "task",
    "tasks",
    "every",
    "everything",
    "please",
    "just",
}
_TASK_NAME_INVALID = {"something", "anything", "it", "this", "that"}


def _normalize_status(raw_status: str) -> str:
    return canonicalize_status(raw_status)


def _extract_date(text: str) -> Optional[str]:
    iso_match = _ISO_DATE_PATTERN.search(text)
    if iso_match:
        return iso_match.group(0)

    relative_match = _RELATIVE_DATE_PATTERN.search(text)
    if relative_match:
        return relative_match.group(0)

    dow_match = _DAY_OF_WEEK_PATTERN.search(text)
    if dow_match:
        return dow_match.group(0)

    return None


def _extract_task_name(text: str) -> Optional[str]:
    verb_match = _DELETE_VERB_PATTERN.search(text)
    if not verb_match:
        return None

    candidate = text[verb_match.end():]

    # Remove common filter fragments first.
    candidate = _PRIORITY_PATTERN.sub(" ", candidate)
    candidate = _STATUS_PATTERN.sub(" ", candidate)
    candidate = _ISO_DATE_PATTERN.sub(" ", candidate)
    candidate = _RELATIVE_DATE_PATTERN.sub(" ", candidate)
    candidate = _DAY_OF_WEEK_PATTERN.sub(" ", candidate)
    candidate = re.sub(r"\bon\b", " ", candidate, flags=re.IGNORECASE)

    # Remove punctuation and compact.
    candidate = re.sub(r"[^\w\s-]", " ", candidate)
    tokens = [
        token
        for token in candidate.split()
        if token.lower() not in _TASK_NAME_STOPWORDS
    ]
    if not tokens:
        return None

    task_name = " ".join(tokens).strip()
    if not task_name:
        return None
    if task_name.lower() in _TASK_NAME_INVALID:
        return None

    return task_name


def extract_delete_entities_fallback(text: str) -> Dict[str, str]:
    """
    Extract delete-related entities with lightweight deterministic rules.
    Returns only keys relevant to scheduling_delete.
    """
    if not text:
        return {}

    entities: Dict[str, str] = {}

    priority_match = _PRIORITY_PATTERN.search(text)
    if priority_match:
        normalized_priority = canonicalize_priority(priority_match.group(1))
        if normalized_priority:
            entities["priority"] = normalized_priority

    status_match = _STATUS_PATTERN.search(text)
    if status_match:
        normalized_status = _normalize_status(status_match.group(1))
        if normalized_status:
            entities["status"] = normalized_status

    date_value = _extract_date(text)
    if date_value:
        entities["date"] = date_value

    task_name = _extract_task_name(text)
    if task_name:
        entities["task_name"] = task_name

    return entities
