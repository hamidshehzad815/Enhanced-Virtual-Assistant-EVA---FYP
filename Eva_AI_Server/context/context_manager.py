"""
Context manager helpers for pending multi-turn flows.
"""
import re
from typing import Any, Dict, Optional

from context.redis_client import redis_client


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
