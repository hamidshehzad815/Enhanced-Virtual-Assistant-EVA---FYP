"""
Context manager helpers for pending multi-turn flows.
"""
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from context.redis_client import redis_client
from db.roadmap_resources import get_sessions_required
from pipeline.entity_scoper import scope_entities
from pipeline.ner import learning_ner_extractor
from services.duckling import duckling_client
from utils.learning_utils import (
    calculate_available_sessions,
    map_subtopic,
    normalize_topic,
    parse_duration,
)
from utils.timezone_utils import get_zoneinfo, resolve_timezone_name


_CANCEL_KEYWORDS = {
    "cancel",
    "stop",
    "abort",
    "never mind",
    "nevermind",
    "forget it",
    "forget that",
    "leave it",
    "discard",
    "no cancel",
}

_YES_KEYWORDS = {
    "yes",
    "yeah",
    "yep",
    "sure",
    "go ahead",
    "do it",
    "confirm",
    "ok",
    "okay",
}

_NO_KEYWORDS = {
    "no",
    "nope",
    "nah",
    "reject",
}

_COMMAND_START_HINTS = {
    "add",
    "schedule",
    "set",
    "create",
    "delete",
    "remove",
    "update",
    "move",
    "show",
    "learn",
    "rename",
}

_ALL_KEYWORDS = {
    "all",
    "all of them",
    "delete all",
    "every one",
    "all tasks",
    "everything",
}

_UPDATE_FIELD_KEYS = {
    "new_title",
    "new_date",
    "new_time",
    "new_priority",
    "new_status",
    "new_duration",
}


def _normalize_text(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def _looks_like_full_command(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False

    tokens = normalized.split()
    if len(tokens) < 4:
        return False

    return tokens[0] in _COMMAND_START_HINTS


def _should_assign_directly(missing_entity: str, reply: str) -> bool:
    """
    For date/time prompts, avoid storing a full command sentence as the value.
    """
    if missing_entity in {"date", "time"} and _looks_like_full_command(reply):
        return False
    return True


def is_cancel(text: str) -> bool:
    """Return True if user text indicates cancel/abort intent."""
    normalized = _normalize_text(text)
    if not normalized:
        return False

    if normalized in _CANCEL_KEYWORDS:
        return True

    return any(keyword in normalized for keyword in _CANCEL_KEYWORDS)


async def handle_free_text_reply(user_id: str, context: Dict[str, Any], reply: str) -> Dict[str, Any]:
    """
    Merge free-text reply into pending entities and clear Redis context.
    """
    pending_action = context.get("pending_action") or {}
    merged_entities = dict(pending_action.get("entities") or {})
    cleaned_reply = (reply or "").strip()

    missing_entity: Optional[str] = context.get("missing_entity")
    pending_intent = str(pending_action.get("intent") or "").lower()
    pending_stage = str(pending_action.get("stage") or "").lower()
    if missing_entity:
        if _should_assign_directly(missing_entity, cleaned_reply):
            merged_entities[missing_entity] = cleaned_reply
        else:
            merged_entities["free_text_reply"] = cleaned_reply
    else:
        if pending_intent in {"delete", "scheduling_delete"}:
            merged_entities["task_name"] = cleaned_reply
        elif pending_intent in {"update", "scheduling_update"} and pending_stage == "identify":
            merged_entities["task_name"] = cleaned_reply
        else:
            merged_entities["free_text_reply"] = cleaned_reply

    await redis_client.delete_context(user_id)
    return merged_entities


def handle_yes_no_reply(text: str) -> str:
    """Classify reply as yes/no/invalid."""
    normalized = _normalize_text(text)
    if not normalized:
        return "invalid"

    if normalized in _YES_KEYWORDS or any(keyword in normalized for keyword in _YES_KEYWORDS):
        return "yes"

    if normalized in _NO_KEYWORDS or any(keyword in normalized for keyword in _NO_KEYWORDS):
        return "no"

    return "invalid"


def handle_number_reply(text: str) -> Optional[int]:
    """Parse a pending numeric choice. Only 1 or 2 are valid."""
    normalized = _normalize_text(text)
    if normalized == "1":
        return 1
    if normalized == "2":
        return 2
    return None


def is_all_keyword(text: str) -> bool:
    """Return True when user intends selecting all items in multi-delete flow."""
    normalized = _normalize_text(text)
    if not normalized:
        return False

    if normalized in _ALL_KEYWORDS:
        return True

    return any(keyword in normalized for keyword in _ALL_KEYWORDS)


def handle_number_delete(text: str, context: Dict[str, Any]) -> Any:
    """
    Parse delete-list choice from pending context.
    Returns selected task_id, "all", "invalid_range", or "invalid".
    """
    normalized = _normalize_text(text)
    pending_action = context.get("pending_action") or {}
    task_ids = list(pending_action.get("task_ids") or [])
    total = len(task_ids)
    if total == 0:
        return "invalid"

    if is_all_keyword(normalized):
        return "all"

    match = re.search(r"\b(\d+)\b", normalized)
    if not match:
        return "invalid"

    selected_index = int(match.group(1))
    if selected_index < 1 or selected_index > total:
        return "invalid_range"

    return task_ids[selected_index - 1]


def handle_number_update(text: str, context: Dict[str, Any]) -> Any:
    """
    Parse update-list choice from pending context.
    Returns selected task_id, "invalid_range", or "invalid".
    """
    normalized = _normalize_text(text)
    pending_action = context.get("pending_action") or {}
    task_ids = list(pending_action.get("task_ids") or [])
    total = len(task_ids)
    if total == 0:
        return "invalid"

    match = re.search(r"\b(\d+)\b", normalized)
    if not match:
        return "invalid"

    selected_index = int(match.group(1))
    if selected_index < 1 or selected_index > total:
        return "invalid_range"

    return task_ids[selected_index - 1]


def extract_update_fields(entities: Dict[str, Any]) -> Dict[str, Any]:
    """Return only update-field entities from a candidate entity dict."""
    payload = dict(entities or {})
    return {key: value for key, value in payload.items() if key in _UPDATE_FIELD_KEYS}


def has_update_fields(entities: Dict[str, Any]) -> bool:
    """True when any update-field entity is present."""
    return bool(extract_update_fields(entities))


def should_block_new_command(model1_label: str) -> bool:
    """Block fresh commands while waiting for pending confirmation/choice."""
    return model1_label in {"command", "multiple_command"}


def _learning_weekday_set(schedule: Any) -> Set[int]:
    days: Set[int] = set()
    if not isinstance(schedule, list):
        return days
    for slot in schedule:
        if isinstance(slot, dict) and "day" in slot:
            try:
                days.add(int(slot["day"]))
            except (TypeError, ValueError):
                continue
    return days


def _today_in_user_tz(tz_name: str) -> date:
    tz = get_zoneinfo(tz_name)
    return datetime.now(tz).date()


async def process_learning_create_free_text_reply(
    context: Dict[str, Any],
    reply: str,
    *,
    user_timezone: str,
    preferred_learning_schedule: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Handle a free-text reply for pending ``learning_create`` (stages: topic, start_date, duration).

    Returns:
      - ``{"outcome": "retry", "message": str}`` — keep Redis context
      - ``{"outcome": "unsupported_topic", "message": str}`` — clear context
      - ``{"outcome": "merged", "merged_entities": dict}`` — caller clears context and re-runs handler
    """
    pending_action = context.get("pending_action") or {}
    stage = str(pending_action.get("stage") or "topic").lower()
    entities = dict(pending_action.get("entities") or {})
    cleaned = (reply or "").strip()
    tz_resolved = resolve_timezone_name(user_timezone or "UTC")

    if stage == "topic":
        if not learning_ner_extractor.loaded:
            return {
                "outcome": "retry",
                "message": "The learning model is not available right now. Please try again shortly.",
            }
        raw = learning_ner_extractor.extract(cleaned, intent_hint="learning_create")
        scoped = scope_entities(raw, "learning_create")
        topic_raw = scoped.get("topic")
        if not topic_raw or not str(topic_raw).strip():
            return {
                "outcome": "retry",
                "message": "I didn't catch which topic you want to learn. Try something like “Python” or “MySQL”.",
            }
        canonical = normalize_topic(str(topic_raw).strip())
        if not canonical:
            return {
                "outcome": "unsupported_topic",
                "message": "That topic isn't in our roadmaps yet. Pick one of the supported languages or databases (say “Python”, “JavaScript”, “MySQL”, …).",
            }
        merged = {**entities, "topic": canonical}
        sub = scoped.get("subtopic")
        if sub and str(sub).strip():
            merged["subtopic"] = str(sub).strip()
        return {"outcome": "merged", "merged_entities": merged}

    if stage == "start_date":
        iso = await duckling_client.resolve_date(cleaned, timezone=tz_resolved)
        if not iso:
            return {
                "outcome": "retry",
                "message": "I couldn't parse that date. Try “next Monday”, “May 20”, or a clear day.",
            }
        try:
            start = date.fromisoformat(str(iso)[:10])
        except ValueError:
            return {
                "outcome": "retry",
                "message": "I couldn't parse that date. Try a specific day like “next Monday”.",
            }
        today = _today_in_user_tz(tz_resolved)
        if start < today:
            return {
                "outcome": "retry",
                "message": "That date is in the past. Pick today or a future day to start.",
            }
        merged = {**entities, "start_date": str(iso)[:10]}
        return {"outcome": "merged", "merged_entities": merged}

    if stage == "duration":
        days = parse_duration(cleaned)
        if days is None:
            return {
                "outcome": "retry",
                "message": "Please give a duration like “2 weeks”, “1 month”, or “14 days”.",
            }
        if days < 7:
            return {
                "outcome": "retry",
                "message": "Learning plans need at least 7 days. Try a longer window.",
            }
        topic = entities.get("topic")
        if not topic:
            return {
                "outcome": "retry",
                "message": "Something went wrong (missing topic). Start your learning request again.",
            }
        roadmap_key = map_subtopic(entities.get("subtopic"), str(topic))
        start_iso = entities.get("start_date")
        if not start_iso:
            return {
                "outcome": "retry",
                "message": "Something went wrong (missing start date). Start your learning request again.",
            }
        try:
            start_d = date.fromisoformat(str(start_iso)[:10])
        except ValueError:
            return {
                "outcome": "retry",
                "message": "Something went wrong with the saved date. Try picking the start date again.",
            }

        learning_days = _learning_weekday_set(preferred_learning_schedule)
        if not learning_days:
            return {
                "outcome": "retry",
                "message": "Set at least one weekly learning slot in Settings first, then try again.",
            }

        sessions_needed = await get_sessions_required(str(topic), roadmap_key)
        available = calculate_available_sessions(start_d, int(days), learning_days)
        if sessions_needed > 0 and available < sessions_needed:
            return {
                "outcome": "retry",
                "message": (
                    f"That period only has {available} learning session(s) on your schedule, "
                    f"but this roadmap needs {sessions_needed}. "
                    "Try a longer duration or add more learning days in Settings."
                ),
                "feasibility_failed": True,
            }

        merged = {
            **entities,
            "duration_days": int(days),
            "duration": cleaned,
        }
        return {"outcome": "merged", "merged_entities": merged}

    return {
        "outcome": "retry",
        "message": "I'm not sure which step we're on. Try your learning request again from the start.",
    }
