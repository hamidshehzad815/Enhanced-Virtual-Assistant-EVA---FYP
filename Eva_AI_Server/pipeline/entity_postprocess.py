"""
Post-processing for raw NER entity dicts (Phase 6).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set

from utils.learning_utils import normalize_subtopic_entity, subtopic_hint_from_message

_ENTITY_FILLER_VALUES: Set[str] = {
    "a",
    "an",
    "ma",
    "me",
    "my",
    "roadmap",
    "plan",
    "learning",
    "study",
    "session",
    "sessions",
    "next",
    "today",
    "todays",
    "lesson",
    "lessons",
    "course",
    "track",
}

_LEARNING_INTENTS = frozenset(
    {
        "learning_create",
        "learning_update",
        "learning_delete",
    }
)

_DATE_ENTITY_KEYS = frozenset({"start_date", "date", "new_start_date"})


def _first_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        return str(value[0]).strip() or None
    text = str(value).strip()
    return text or None


def _is_filler(value: str) -> bool:
    return value.strip().lower() in _ENTITY_FILLER_VALUES


def _clean_value(
    value: Any,
    *,
    min_len: int = 1,
    max_len: int = 120,
    skip_filler: bool = False,
) -> Optional[str]:
    text = _first_value(value)
    if not text:
        return None
    text = " ".join(text.split())
    if len(text) < min_len or len(text) > max_len:
        return None
    if not skip_filler and _is_filler(text):
        return None
    return text


def _merge_fallback(entities: Dict[str, Any], fallback: Dict[str, str]) -> Dict[str, Any]:
    merged = dict(entities)
    for key, value in fallback.items():
        current = merged.get(key)
        if current in (None, "", [], {}):
            merged[key] = value
    return merged


def postprocess_ner_entities(
    entities: Dict[str, Any],
    intent_hint: str,
    source_text: str,
) -> Dict[str, Any]:
    """Strip filler mis-tags and apply learning subtopic recovery hints."""
    cleaned: Dict[str, Any] = {}

    for key, value in (entities or {}).items():
        if key == "subtopic" and intent_hint in _LEARNING_INTENTS:
            normalized = normalize_subtopic_entity(value)
            if normalized:
                cleaned[key] = normalized
            continue

        skip_filler = key in _DATE_ENTITY_KEYS

        if isinstance(value, list):
            parts = [_clean_value(v, skip_filler=skip_filler) for v in value]
            parts = [p for p in parts if p]
            if not parts:
                continue
            cleaned[key] = parts[0] if len(parts) == 1 else parts
            continue

        kept = _clean_value(value, skip_filler=skip_filler)
        if kept:
            cleaned[key] = kept

    if intent_hint in _LEARNING_INTENTS and not cleaned.get("subtopic"):
        hint = subtopic_hint_from_message(source_text)
        if hint:
            cleaned["subtopic"] = hint

    return cleaned


def apply_entity_fallbacks(
    entities: Dict[str, Any],
    intent_hint: str,
    source_text: str,
    fallbacks: Iterable[Dict[str, str]],
) -> Dict[str, Any]:
    merged = dict(entities or {})
    for fb in fallbacks:
        merged = _merge_fallback(merged, fb)
    return postprocess_ner_entities(merged, intent_hint, source_text)
