"""
Deterministic fallback extraction for scheduling update entities.
Used to improve update intent robustness when model extraction misses fields.
"""
import re
from typing import Dict, Optional


_DATE_TOKEN_BODY = (
    r"(?:\d{4}-\d{2}-\d{2}|today|tomorrow|yesterday|tonight|"
    r"next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
)
_TIME_TOKEN_BODY = r"(?:[01]?\d(?::[0-5]\d)?\s*(?:am|pm))"

_PRIORITY_PATTERN = re.compile(r"\b(low|medium|high)\b", flags=re.IGNORECASE)
_STATUS_PATTERN = re.compile(r"\b(pending|ongoing|complete|completed)\b", flags=re.IGNORECASE)
_DATE_PATTERN = re.compile(rf"\b({_DATE_TOKEN_BODY})\b", flags=re.IGNORECASE)
_TIME_PATTERN = re.compile(rf"\b({_TIME_TOKEN_BODY})\b", flags=re.IGNORECASE)

_LEADING_STOPWORDS = {
    "the",
    "my",
    "a",
    "an",
    "please",
    "just",
}
_INVALID_TASK_NAMES = {"something", "anything", "it", "this", "that"}


def _compact(value: str) -> str:
    return " ".join((value or "").strip().split())


def _normalize_status(value: str) -> str:
    status = _compact(value).lower()
    if status == "completed":
        return "complete"
    return status


def _clean_task_name(value: str) -> Optional[str]:
    candidate = _compact(value)
    if not candidate:
        return None

    candidate = re.sub(r"[^\w\s-]", " ", candidate)
    candidate = _compact(candidate)
    if not candidate:
        return None

    tokens = candidate.split()
    while tokens and tokens[0].lower() in _LEADING_STOPWORDS:
        tokens.pop(0)

    if not tokens:
        return None

    cleaned = _compact(" ".join(tokens))
    if not cleaned:
        return None
    if cleaned.lower() in _INVALID_TASK_NAMES:
        return None
    return cleaned


def _extract_task_name_before_token(text: str, token_regex: str) -> Optional[str]:
    match = re.search(token_regex, text, flags=re.IGNORECASE)
    if not match:
        return None
    return _clean_task_name(match.group(1))


def _find_first(pattern: re.Pattern[str], text: str) -> Optional[str]:
    match = pattern.search(text)
    if not match:
        return None
    return _compact(match.group(1))


def _extract_identifier_date(text: str) -> Optional[str]:
    return _find_first(
        re.compile(rf"\bon\s+({_DATE_TOKEN_BODY})\b", flags=re.IGNORECASE),
        text,
    )


def _extract_new_date(text: str) -> Optional[str]:
    return _find_first(
        re.compile(rf"\bto\s+({_DATE_TOKEN_BODY})\b", flags=re.IGNORECASE),
        text,
    )


def _extract_new_time(text: str) -> Optional[str]:
    to_time = _find_first(
        re.compile(rf"\bto\s+({_TIME_TOKEN_BODY})\b", flags=re.IGNORECASE),
        text,
    )
    if to_time:
        return to_time

    at_time = _find_first(
        re.compile(rf"\bat\s+({_TIME_TOKEN_BODY})\b", flags=re.IGNORECASE),
        text,
    )
    return at_time


def extract_update_entities_fallback(text: str) -> Dict[str, str]:
    """
    Extract update-related entities with lightweight deterministic rules.
    Returns only keys relevant to scheduling_update.
    """
    if not text:
        return {}

    raw_text = _compact(text)
    entities: Dict[str, str] = {}

    # rename <old> to <new>
    rename_match = re.search(r"\brename\s+(.+?)\s+to\s+(.+)$", raw_text, flags=re.IGNORECASE)
    if rename_match:
        task_name = _clean_task_name(rename_match.group(1))
        new_title = _clean_task_name(rename_match.group(2))
        if task_name:
            entities["task_name"] = task_name
        if new_title:
            entities["new_title"] = new_title
        return entities

    # mark <task> as <status>
    mark_match = re.search(
        r"\bmark\s+(.+?)\s+as\s+(pending|ongoing|complete|completed)\b",
        raw_text,
        flags=re.IGNORECASE,
    )
    if mark_match:
        task_name = _clean_task_name(mark_match.group(1))
        if task_name:
            entities["task_name"] = task_name
        entities["new_status"] = _normalize_status(mark_match.group(2))
        return entities

    # change/update <task> priority to <priority>
    priority_match = re.search(
        r"\b(?:change|update)\s+(.+?)\s+priority\s+(?:to|as)\s+(low|medium|high)\b",
        raw_text,
        flags=re.IGNORECASE,
    )
    if priority_match:
        task_name = _clean_task_name(priority_match.group(1))
        if task_name:
            entities["task_name"] = task_name
        entities["new_priority"] = priority_match.group(2).lower()
        return entities

    # change/update <task> duration to <duration>
    duration_match = re.search(
        r"\b(?:change|update)\s+(.+?)\s+duration\s+to\s+(.+)$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if duration_match:
        task_name = _clean_task_name(duration_match.group(1))
        if task_name:
            entities["task_name"] = task_name
        entities["new_duration"] = _compact(duration_match.group(2))
        return entities

    # reschedule/move <task> ... to ...
    move_match = re.search(
        r"\b(?:reschedule|move)\s+(.+?)\s+to\s+(.+)$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if move_match:
        lhs = _compact(move_match.group(1))
        rhs = _compact(move_match.group(2))

        identifier_date = _extract_identifier_date(lhs)
        if identifier_date:
            entities["date"] = identifier_date
            lhs = re.sub(
                rf"\bon\s+{re.escape(identifier_date)}\b",
                " ",
                lhs,
                flags=re.IGNORECASE,
            )
            lhs = _compact(lhs)

        task_name = _clean_task_name(lhs)
        if task_name:
            entities["task_name"] = task_name

        new_date = _find_first(_DATE_PATTERN, rhs)
        if new_date:
            entities["new_date"] = new_date

        new_time = _find_first(_TIME_PATTERN, rhs)
        if new_time:
            entities["new_time"] = new_time

        return entities

    # change the time of <task> on <date> to <time>
    time_change_match = re.search(
        rf"\b(?:change|update)\s+the\s+time\s+of\s+(.+?)\s+on\s+({_DATE_TOKEN_BODY})\s+to\s+({_TIME_TOKEN_BODY})\b",
        raw_text,
        flags=re.IGNORECASE,
    )
    if time_change_match:
        task_name = _clean_task_name(time_change_match.group(1))
        if task_name:
            entities["task_name"] = task_name
        entities["date"] = _compact(time_change_match.group(2))
        entities["new_time"] = _compact(time_change_match.group(3))
        return entities

    # generic light parsing for update-like sentences
    task_name_generic = _extract_task_name_before_token(
        raw_text,
        r"\b(?:change|update|reschedule|move)\s+(.+?)(?:\s+to\b|\s+on\b|\s+priority\b|\s+duration\b|$)",
    )
    if task_name_generic:
        entities["task_name"] = task_name_generic

    identifier_date = _extract_identifier_date(raw_text)
    if identifier_date:
        entities.setdefault("date", identifier_date)

    new_date = _extract_new_date(raw_text)
    if new_date:
        entities.setdefault("new_date", new_date)

    new_time = _extract_new_time(raw_text)
    if new_time:
        entities.setdefault("new_time", new_time)

    status_match = _STATUS_PATTERN.search(raw_text)
    if status_match and re.search(r"\b(?:to|as)\b", raw_text, flags=re.IGNORECASE):
        entities.setdefault("new_status", _normalize_status(status_match.group(1)))

    priority_match_generic = _PRIORITY_PATTERN.search(raw_text)
    if priority_match_generic and "priority" in raw_text.lower():
        entities.setdefault("new_priority", priority_match_generic.group(1).lower())

    duration_generic = _find_first(
        re.compile(
            r"\bto\s+(\d+\s*(?:hour|hours|hr|hrs|minute|minutes|min|mins))\b",
            flags=re.IGNORECASE,
        ),
        raw_text,
    )
    if duration_generic and "duration" in raw_text.lower():
        entities.setdefault("new_duration", duration_generic)

    return entities

