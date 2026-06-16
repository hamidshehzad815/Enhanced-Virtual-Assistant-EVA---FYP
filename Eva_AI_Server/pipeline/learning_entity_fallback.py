"""
Deterministic fallback extraction for learning_* entities.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

from utils.learning_utils import (
    SUBTOPIC_ALIAS_MAP,
    SUPPORTED_TOPICS,
    TOPIC_ALIAS_MAP,
    subtopic_hint_from_message,
)

_DURATION_PATTERN = re.compile(
    r"\b(\d+\s*(?:day|days|week|weeks|wk|wks|month|months))\b",
    flags=re.IGNORECASE,
)
_START_DATE_PATTERN = re.compile(
    r"\b(?:starting|from|beginning)\s+"
    r"(today|tomorrow|next\s+week|next\s+month|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    flags=re.IGNORECASE,
)
_DATE_PATTERN = re.compile(
    r"\b(?:to|on)\s+"
    r"(today|tomorrow|next\s+week|next\s+month|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    flags=re.IGNORECASE,
)

_TOPIC_TERMS = sorted(
    set(TOPIC_ALIAS_MAP.keys())
    | {t.lower() for t in SUPPORTED_TOPICS}
    | set(TOPIC_ALIAS_MAP.values()),
    key=len,
    reverse=True,
)
_SUBTOPIC_TERMS = sorted(SUBTOPIC_ALIAS_MAP.keys(), key=len, reverse=True)

_FILLER_AFTER_TOPIC = re.compile(
    r"\b(roadmap|plan|learning|course|track|study)\b",
    flags=re.IGNORECASE,
)


def _compact(value: str) -> str:
    return " ".join((value or "").strip().split())


def _find_topic(text: str) -> Optional[str]:
    low = text.lower()
    for term in _TOPIC_TERMS:
        if re.search(r"(?<![a-z0-9#+])" + re.escape(term.lower()) + r"(?![a-z0-9])", low):
            return term
    return None


def _find_subtopic(text: str) -> Optional[str]:
    low = text.lower()
    for term in _SUBTOPIC_TERMS:
        if re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", low):
            return term
    hint = subtopic_hint_from_message(text)
    if hint:
        return hint
    return None


def extract_learning_entities_fallback(text: str, intent_hint: str = "") -> Dict[str, str]:
    if not text:
        return {}

    entities: Dict[str, str] = {}
    topic = _find_topic(text)
    if topic:
        entities["topic"] = topic

    subtopic = _find_subtopic(text)
    if subtopic:
        entities["subtopic"] = subtopic

    if intent_hint in {"learning_create", "learning_update", "learning_delete", "learning_show"}:
        start_match = _START_DATE_PATTERN.search(text)
        if start_match:
            entities["start_date"] = _compact(start_match.group(1))

        if intent_hint == "learning_update":
            date_match = _DATE_PATTERN.search(text)
            if date_match:
                entities["date"] = _compact(date_match.group(1))

        duration_match = _DURATION_PATTERN.search(text)
        if duration_match:
            entities["duration"] = _compact(duration_match.group(1))

    # Strip roadmap/plan words accidentally captured with topic — fallback only sets topic term.
    if entities.get("topic") and _FILLER_AFTER_TOPIC.fullmatch(
        str(entities["topic"]).strip()
    ):
        entities.pop("topic", None)

    return entities
