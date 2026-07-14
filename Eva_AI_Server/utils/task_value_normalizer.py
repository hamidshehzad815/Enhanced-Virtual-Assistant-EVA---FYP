"""
Task enum normalization helpers.
Maps user-facing priority/status variants to DB-safe canonical values.
"""
import re
from typing import Any, Dict, Iterable, List, Tuple


PRIORITY_CANONICAL: Tuple[str, ...] = ("low", "medium", "high")
STATUS_CANONICAL: Tuple[str, ...] = ("pending", "ongoing", "complete")

PRIORITY_USER_VALUES: Tuple[str, ...] = (
    "high",
    "medium",
    "low",
    "urgent",
    "critical",
    "immediate",
    "asap",
    "important",
    "normal",
    "standard",
    "moderate",
    "average",
    "regular",
    "minor",
    "trivial",
    "backburner",
    "back burner",
    "background",
    "optional",
)

STATUS_USER_VALUES: Tuple[str, ...] = (
    "pending",
    "ongoing",
    "complete",
    "completed",
    "in progress",
    "in-progress",
    "inprogress",
    "active",
    "done",
    "finished",
    "resolved",
    "closed",
    "delivered",
    "fulfilled",
)

_PRIORITY_MAP: Dict[str, str] = {
    "high": "high",
    "high priority": "high",
    "urgent": "high",
    "urgent priority": "high",
    "top": "high",
    "top priority": "high",
    "critical": "high",
    "immediate": "high",
    "asap": "high",
    "important": "high",
    "medium": "medium",
    "medium priority": "medium",
    "normal": "medium",
    "standard": "medium",
    "moderate": "medium",
    "average": "medium",
    "regular": "medium",
    "low": "low",
    "low priority": "low",
    "minor": "low",
    "trivial": "low",
    "backburner": "low",
    "back burner": "low",
    "background": "low",
    "optional": "low",
}

_STATUS_MAP: Dict[str, str] = {
    "pending": "pending",
    "ongoing": "ongoing",
    "in progress": "ongoing",
    "inprogress": "ongoing",
    "active": "ongoing",
    "complete": "complete",
    "completed": "complete",
    "done": "complete",
    "finished": "complete",
    "resolved": "complete",
    "closed": "complete",
    "delivered": "complete",
    "fulfilled": "complete",
}


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def canonicalize_priority(value: Any) -> str:
    """Return canonical priority: low | medium | high, or empty if unknown."""
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    return _PRIORITY_MAP.get(normalized, "")


def canonicalize_status(value: Any) -> str:
    """Return canonical status: pending | ongoing | complete, or empty if unknown."""
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    return _STATUS_MAP.get(normalized, "")


_TASK_NAME_TRAILING_NOISE: frozenset = frozenset({
    "task", "tasks", "item", "items", "event", "events",
})


def clean_task_name(value: Any) -> str:
    """Strip generic trailing noise words from a NER-extracted task name.

    "physics task" -> "physics"   "cs lab tasks" -> "cs lab"
    "task" / "tasks" alone -> "" so handlers treat task_name as missing.
    """
    text = str(value or "").strip()
    if not text:
        return text
    words = text.split()
    while words and words[-1].lower() in _TASK_NAME_TRAILING_NOISE:
        words.pop()
    return " ".join(words) if words else ""


def build_value_regex(values: Iterable[str]) -> str:
    """
    Build a regex alternation for phrase values.
    Spaces/hyphens/underscores are treated as interchangeable separators.
    """
    patterns: List[str] = []
    seen = set()

    for raw in values:
        normalized = _normalize_text(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        parts = [re.escape(part) for part in normalized.split() if part]
        if not parts:
            continue
        patterns.append(r"[\s_-]+".join(parts))

    # Longer phrases first so "in progress" matches before "progress"-like fragments.
    patterns.sort(key=len, reverse=True)
    return "|".join(patterns)

