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
    SUPPORTED_TOPICS,
    calculate_available_sessions,
    duration_entity_to_days,
    level_keys_for_language,
    map_subtopic,
    normalize_subtopic_entity,
    normalize_topic,
    resolve_subtopic_mapping,
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
    "don't",
    "leave it",
    "keep it",
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
    "all goals",
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
    return _parse_pending_number_choice(normalized, task_ids)


def handle_number_learning_delete(text: str, context: Dict[str, Any]) -> Any:
    """
    Parse learning-delete list choice from pending context.
    Returns selected goal_id, "all", "invalid_range", or "invalid".
    """
    normalized = _normalize_text(text)
    pending_action = context.get("pending_action") or {}
    goal_ids = list(pending_action.get("goal_ids") or [])
    return _parse_pending_number_choice(normalized, goal_ids)


def handle_number_learning_update(text: str, context: Dict[str, Any]) -> Any:
    """
    Parse learning-update list choice from pending context (no 'all' option).
    Returns selected goal_id, "invalid_range", or "invalid".
    """
    normalized = _normalize_text(text)
    pending_action = context.get("pending_action") or {}
    goal_ids = list(pending_action.get("goal_ids") or [])
    total = len(goal_ids)
    if total == 0:
        return "invalid"

    match = re.search(r"\b(\d+)\b", normalized)
    if not match:
        return "invalid"
    selected_index = int(match.group(1))
    if selected_index < 1 or selected_index > total:
        return "invalid_range"
    return goal_ids[selected_index - 1]


def _parse_pending_number_choice(normalized: str, option_ids: List[Any]) -> Any:
    total = len(option_ids)
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

    return option_ids[selected_index - 1]


def _goal_display_title(goal: Dict[str, Any]) -> str:
    title = str(goal.get("title") or "").strip()
    if title:
        return title
    topic = str(goal.get("subject") or goal.get("topic") or "").strip()
    roadmap_key = str(goal.get("roadmap_key") or "").strip()
    if topic and roadmap_key:
        return f"{topic} {roadmap_key}"
    return topic or roadmap_key or "that learning goal"


def _goal_progress_label(goal: Dict[str, Any]) -> str:
    done = int(goal.get("completed_topics") or 0)
    total = int(goal.get("total_topics") or 0)
    status = str(goal.get("status") or "active").strip().lower()
    if total > 0:
        return f"{status} with {done} of {total} sessions done"
    return status or "active"


def learning_delete_cancel_message(user_name: Optional[str] = None) -> str:
    if user_name:
        return f"No problem {user_name}, nothing was deleted."
    return "No problem, nothing was deleted."


def learning_update_cancel_message(user_name: Optional[str] = None) -> str:
    if user_name:
        return f"No problem {user_name}, nothing was changed."
    return "No problem, nothing was changed."


def learning_update_confirm_message(
    goal: Dict[str, Any],
    *,
    sub_intent: str,
    user_name: Optional[str] = None,
) -> str:
    title = _goal_display_title(goal)
    if sub_intent == "pause":
        if user_name:
            return f"Pause {title}, {user_name}? Your progress will be saved."
        return f"Pause {title}? Your progress will be saved."
    if sub_intent == "resume":
        if user_name:
            return f"Resume {title}, {user_name}? I'll rebase your schedule from today."
        return f"Resume {title}? I'll rebase your schedule from today."
    if user_name:
        return f"Confirm that change for {title}, {user_name}?"
    return f"Confirm that change for {title}?"


_WEEKDAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def _learning_days_from_settings(preferred_learning_schedule: Any) -> Set[int]:
    out: Set[int] = set()
    if not isinstance(preferred_learning_schedule, list):
        return out
    for slot in preferred_learning_schedule:
        if not isinstance(slot, dict):
            continue
        try:
            out.add(int(slot.get("day")))
        except (TypeError, ValueError):
            continue
    return out


def _learning_days_label(days: Set[int]) -> str:
    if not days:
        return "your learning days"
    labels = [_WEEKDAY_NAMES.get(d, str(d)) for d in sorted(days)]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


async def process_learning_update_free_text_reply(
    pending_context: Dict[str, Any],
    reply: str,
    *,
    user_name: Optional[str] = None,
    timezone_name: str = "UTC",
    preferred_learning_schedule: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Handle learning_update free_text replies for:
      - State 1 (stage=identify): extract topic/subtopic via learning NER.
      - State 5 (stage=new_date): resolve date via Duckling and validate learning day.
    """
    pending_action = pending_context.get("pending_action") or {}
    stage = str(pending_action.get("stage") or "").strip().lower()
    cleaned = str(reply or "").strip()
    if not cleaned:
        msg = "I didn't catch that. Can you try again?"
        if user_name:
            msg = f"I didn't catch that, {user_name}. Can you try again?"
        return {"outcome": "retry", "message": msg}

    if stage == "new_date":
        iso_date = await duckling_client.resolve_date(cleaned, timezone=timezone_name or "UTC")
        if not iso_date:
            msg = "I couldn't understand that date. Try something like 'next Monday'."
            if user_name:
                msg = f"I couldn't understand that date, {user_name}. Try something like 'next Monday'."
            return {"outcome": "retry", "message": msg}

        try:
            parsed = datetime.strptime(iso_date, "%Y-%m-%d").date()
        except ValueError:
            return {"outcome": "retry", "message": "That date format looks invalid. Try again."}

        today = datetime.now(get_zoneinfo(timezone_name or "UTC")).date()
        if parsed < today:
            msg = "That date is in the past. Pick a future learning day."
            if user_name:
                msg = f"That date is in the past, {user_name}. Pick a future learning day."
            return {"outcome": "retry", "message": msg}

        days = _learning_days_from_settings(preferred_learning_schedule or [])
        if days and parsed.weekday() not in days:
            label = _learning_days_label(days)
            msg = f"That isn't one of your learning days. Your learning days are {label}."
            if user_name:
                msg = f"That isn't one of your learning days, {user_name}. Your learning days are {label}."
            return {"outcome": "retry", "message": msg}

        merged = dict(pending_action.get("entities") or {})
        merged["date"] = iso_date
        return {"outcome": "merged", "merged_entities": merged}

    # stage=identify (pause/resume with no identifier)
    if not learning_ner_extractor.loaded:
        learning_ner_extractor.load()

    raw = learning_ner_extractor.extract(cleaned, intent_hint="learning_update")
    scoped = scope_entities(raw or {}, "learning_update")
    topic_raw = scoped.get("topic")
    topic = normalize_topic(topic_raw) if topic_raw else None
    if not topic:
        msg = "I didn't catch the learning topic. Say something like Python or MySQL."
        if user_name:
            msg = f"I didn't catch the learning topic, {user_name}. Say something like Python or MySQL."
        return {"outcome": "retry", "message": msg}

    subtopic_raw = normalize_subtopic_entity(scoped.get("subtopic"))
    roadmap_key = "general"
    if subtopic_raw:
        try:
            roadmap_key = map_subtopic(subtopic_raw, topic, level_keys=level_keys_for_language(topic))
        except Exception:
            roadmap_key = map_subtopic(subtopic_raw, topic)

    merged = dict(pending_action.get("entities") or {})
    merged.update(scoped)
    merged["topic"] = topic
    if subtopic_raw:
        merged["subtopic"] = subtopic_raw
    merged["roadmap_key"] = roadmap_key
    return {"outcome": "merged", "merged_entities": merged}


def learning_delete_no_message(
    goals: List[Dict[str, Any]],
    *,
    bulk: bool,
    user_name: Optional[str] = None,
) -> str:
    if bulk:
        if user_name:
            return f"No problem, I left all those goals as they are, {user_name}."
        return "No problem, I left all those goals as they are."

    title = _goal_display_title(goals[0] if goals else {})
    if user_name:
        return f"No problem, I left {title} as it is, {user_name}."
    return f"No problem, I left {title} as it is."


def learning_delete_blocked_command_message(
    pending_context: Dict[str, Any],
    user_name: Optional[str] = None,
) -> str:
    expected = str(pending_context.get("expected_response") or "").lower()
    pending_action = pending_context.get("pending_action") or {}
    goals = list(pending_action.get("goals") or [])

    if expected == "yes_no":
        title = _goal_display_title(goals[0] if goals else {})
        if user_name:
            return (
                f"I'm still waiting — want me to delete {title}? "
                f"Just yes or no, {user_name}."
            )
        return f"I'm still waiting — want me to delete {title}? Just yes or no."

    if expected == "number":
        if user_name:
            return f"I'm still waiting for your choice. Say cancel to stop, {user_name}."
        return "I'm still waiting for your choice. Say cancel to stop."

    if user_name:
        return (
            f"I'm still waiting for your reply, {user_name}. "
            "Say cancel if you want to start fresh."
        )
    return "I'm still waiting for your reply. Say cancel if you want to start fresh."


def learning_delete_single_confirm_message(
    goal: Dict[str, Any],
    user_name: Optional[str] = None,
) -> str:
    title = _goal_display_title(goal)
    progress = _goal_progress_label(goal)
    if user_name:
        return f"Got it — delete {title}, {progress}?"
    return f"Got it — delete {title}, {progress}?"


def learning_delete_bulk_confirm_message(
    goals: List[Dict[str, Any]],
    entities: Optional[Dict[str, Any]] = None,
    user_name: Optional[str] = None,
) -> str:
    total = len(goals)
    topic = str((entities or {}).get("topic") or "").strip()
    topic_part = f"{topic} " if topic else ""
    goal_word = "goal" if total == 1 else "goals"
    if user_name:
        return (
            f"Just to confirm — delete all {total} {topic_part}{goal_word}? "
            "Completed sessions will be kept."
        )
    return (
        f"Just to confirm — delete all {total} {topic_part}{goal_word}? "
        "Completed sessions will be kept."
    )


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
    Handle a free-text reply for pending ``learning_create`` (stages: topic, subtopic, start_date, duration).

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
        sub = normalize_subtopic_entity(scoped.get("subtopic"))
        if sub:
            merged["subtopic"] = sub
        return {"outcome": "merged", "merged_entities": merged}

    if stage == "subtopic":
        topic = entities.get("topic")
        if not topic:
            return {
                "outcome": "retry",
                "message": "Something went wrong (missing topic). Start your learning request again.",
            }
        sub = normalize_subtopic_entity(cleaned) or cleaned
        if not str(sub).strip():
            return {
                "outcome": "retry",
                "message": (
                    "Please tell me which level or focus you want — "
                    "e.g. basics, intermediate, advanced, or OOP."
                ),
            }
        resolution = resolve_subtopic_mapping(sub, str(topic))
        if not resolution.confident:
            heard = str(sub).strip()
            return {
                "outcome": "retry",
                "message": (
                    f"I still couldn't match \"{heard}\" to a {topic} track. "
                    "Try basics (beginner), intermediate, advanced, or a clear topic like OOP or loops."
                ),
            }
        merged = {**entities, "subtopic": str(sub).strip()}
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
        days = duration_entity_to_days(cleaned)
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


async def process_learning_delete_free_text_reply(
    context: Dict[str, Any],
    reply: str,
    *,
    user_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle free-text reply when waiting for a learning goal identifier (State 1).

    Returns:
      - ``{"outcome": "retry", "message": str}`` — keep Redis context
      - ``{"outcome": "unsupported_topic", "message": str}`` — clear context
      - ``{"outcome": "merged", "merged_entities": dict}`` — caller clears context and re-runs handler
    """
    pending_action = context.get("pending_action") or {}
    entities = dict(pending_action.get("entities") or {})
    cleaned = (reply or "").strip()

    if not learning_ner_extractor.loaded:
        return {
            "outcome": "retry",
            "message": "The learning model is not available right now. Please try again shortly.",
        }

    raw = learning_ner_extractor.extract(cleaned, intent_hint="learning_delete")
    scoped = scope_entities(raw, "learning_delete")
    topic_raw = scoped.get("topic")
    if not topic_raw or not str(topic_raw).strip():
        if user_name:
            return {
                "outcome": "retry",
                "message": (
                    "I didn't catch that. Which learning goal would you like to delete? "
                    f"Try saying something like 'Python' or 'MySQL', {user_name}."
                ),
            }
        return {
            "outcome": "retry",
            "message": (
                "I didn't catch that. Which learning goal would you like to delete? "
                "Try saying something like 'Python' or 'MySQL'."
            ),
        }

    topic_label = str(topic_raw).strip()
    canonical = normalize_topic(topic_label)
    if not canonical or canonical not in SUPPORTED_TOPICS:
        if user_name:
            return {
                "outcome": "unsupported_topic",
                "message": (
                    f"I couldn't find a learning goal for {topic_label}, {user_name}. "
                    "Check the topic name and try again."
                ),
            }
        return {
            "outcome": "unsupported_topic",
            "message": (
                f"I couldn't find a learning goal for {topic_label}. "
                "Check the topic name and try again."
            ),
        }

    merged = {**entities, "topic": canonical}
    subtopic = normalize_subtopic_entity(scoped.get("subtopic"))
    if subtopic:
        merged["subtopic"] = subtopic
        resolution = resolve_subtopic_mapping(subtopic, canonical)
        if resolution.confident and resolution.roadmap_key != "general":
            merged["roadmap_key"] = resolution.roadmap_key

    return {"outcome": "merged", "merged_entities": merged}
