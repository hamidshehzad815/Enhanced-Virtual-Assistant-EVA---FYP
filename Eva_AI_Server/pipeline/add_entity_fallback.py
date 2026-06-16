"""
Deterministic fallback extraction for scheduling_add entities.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

from pipeline.delete_entity_fallback import (
    _DAY_OF_WEEK_PATTERN,
    _ISO_DATE_PATTERN,
    _RELATIVE_DATE_PATTERN,
)
from utils.task_value_normalizer import (
    PRIORITY_USER_VALUES,
    build_value_regex,
    canonicalize_priority,
)

_ADD_VERB_PATTERN = re.compile(
    r"\b(add|schedule|book|set|create)\b",
    flags=re.IGNORECASE,
)
_TIME_PATTERN = re.compile(
    r"\b(?:[01]?\d(?::[0-5]\d)?\s*(?:am|pm)|noon|midnight)\b",
    flags=re.IGNORECASE,
)
_DURATION_PATTERN = re.compile(
    r"\b(\d+\s*(?:hour|hours|hr|hrs|minute|minutes|min|mins))\b",
    flags=re.IGNORECASE,
)
_PRIORITY_PATTERN = re.compile(
    rf"\b({build_value_regex(PRIORITY_USER_VALUES)})\s+priority\b",
    flags=re.IGNORECASE,
)

_STOPWORDS = {
    "my",
    "the",
    "a",
    "an",
    "please",
    "just",
    "for",
    "on",
    "at",
    "with",
    "to",
}


def _compact(value: str) -> str:
    return " ".join((value or "").strip().split())


def _extract_date(text: str) -> Optional[str]:
    iso = _ISO_DATE_PATTERN.search(text)
    if iso:
        return iso.group(0)
    rel = _RELATIVE_DATE_PATTERN.search(text)
    if rel:
        return rel.group(0)
    dow = _DAY_OF_WEEK_PATTERN.search(text)
    if dow:
        return dow.group(0)
    return None


def _extract_task_name(text: str) -> Optional[str]:
    verb = _ADD_VERB_PATTERN.search(text)
    if not verb:
        return None

    tail = text[verb.end() :]
    tail = re.split(
        r"\b(?:on|at|for|with|from|by)\b",
        tail,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    tail = _ISO_DATE_PATTERN.sub(" ", tail)
    tail = _RELATIVE_DATE_PATTERN.sub(" ", tail)
    tail = _DAY_OF_WEEK_PATTERN.sub(" ", tail)
    tail = _TIME_PATTERN.sub(" ", tail)
    tail = _DURATION_PATTERN.sub(" ", tail)
    tail = _PRIORITY_PATTERN.sub(" ", tail)
    tail = re.sub(r"[^\w\s-]", " ", tail)

    tokens = [t for t in tail.split() if t.lower() not in _STOPWORDS]
    if not tokens:
        return None
    return _compact(" ".join(tokens))


def extract_add_entities_fallback(text: str) -> Dict[str, str]:
    if not text:
        return {}

    entities: Dict[str, str] = {}
    task_name = _extract_task_name(text)
    if task_name:
        entities["task_name"] = task_name

    date_value = _extract_date(text)
    if date_value:
        entities["date"] = date_value

    time_match = _TIME_PATTERN.search(text)
    if time_match:
        entities["time"] = _compact(time_match.group(0))

    duration_match = _DURATION_PATTERN.search(text)
    if duration_match:
        entities["duration"] = _compact(duration_match.group(1))

    priority_match = _PRIORITY_PATTERN.search(text)
    if priority_match:
        normalized = canonicalize_priority(priority_match.group(1))
        if normalized:
            entities["priority"] = normalized

    return entities
