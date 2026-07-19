"""
Gemini fallback for natural replies to pending yes/no and numbered-list prompts.

Deterministic resolvers always run first (see context_manager). This module is
only consulted on a miss, and only when USE_GEMINI_PENDING_REPLY is enabled.
It returns the *canonical* value the pipeline already expects so callers do not
need downstream handler changes.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date as _date
from typing import Any, Dict, List, Optional, Sequence

from config.settings import settings
from services.gemini import gemini_service

_YES_NO_PROMPT = """You map a user's free-form reply to a yes/no confirmation for EVA.

EVA just asked:
{eva_prompt}

User reply:
{user_reply}

Return ONLY raw JSON (no markdown):
{{"choice": "yes"|"no"|"none", "confidence": 0.0-1.0}}

Rules:
- "yes" if the user clearly agrees / confirms / wants EVA to proceed.
- "no" if the user clearly refuses / declines / wants to stop or keep things as-is.
- "none" if ambiguous, off-topic, a new unrelated request, or you are not sure.
- Never invent meaning. Prefer "none" over guessing.
"""

_LIST_PROMPT = """You map a user's free-form reply to exactly one option from a numbered list.

EVA just asked:
{eva_prompt}

Options (choose by id only):
{options_json}

allow_all={allow_all}

User reply:
{user_reply}

Return ONLY raw JSON (no markdown):
{{"choice": "<option id>"|"all"|"none", "confidence": 0.0-1.0}}

Rules:
- "choice" must be one of the provided option ids, or "all" only when allow_all is true
  and the user clearly wants every item, or "none" if unsure / ambiguous / off-topic.
- Use labels to resolve phrases like "the first", "the last", "the python one".
- If two labels are too similar to tell apart, return "none".
- Never invent an id that is not in the list.
"""

_DATE_PROMPT = """You resolve a user's free-form reply into a calendar date for EVA.

Today's date is {today} ({weekday}).

EVA just asked:
{eva_prompt}

User reply:
{user_reply}

Return ONLY raw JSON (no markdown):
{{"date": "YYYY-MM-DD"|"none", "confidence": 0.0-1.0}}

Rules:
- Resolve relative phrases ("monday", "from monday", "next friday", "in 3 days",
  "tomorrow") against today's date above.
- "date" must be a real calendar date in YYYY-MM-DD format.
- "none" if the reply has no resolvable date, is off-topic, or you are not sure.
- Never invent a date. Prefer "none" over guessing.
"""

_TIME_PROMPT = """You resolve a user's free-form reply into a time of day for EVA.

EVA just asked:
{eva_prompt}

User reply:
{user_reply}

Return ONLY raw JSON (no markdown):
{{"time": "HH:MM"|"none", "confidence": 0.0-1.0}}

Rules:
- "time" must be 24-hour HH:MM (e.g. "5pm" -> "17:00", "9:30 in the morning" -> "09:30").
- "none" if the reply has no resolvable time, is off-topic, or you are not sure.
- Never invent a time. Prefer "none" over guessing.
"""

_DURATION_PROMPT = """You resolve a user's free-form reply into a duration for EVA, in {unit}.

EVA just asked:
{eva_prompt}

User reply:
{user_reply}

Return ONLY raw JSON (no markdown):
{{"amount": <integer {unit}>|"none", "confidence": 0.0-1.0}}

Rules:
- Convert the reply to a whole number of {unit} (e.g. "2 weeks" -> 14 if unit is days;
  "an hour and a half" -> 90 if unit is minutes).
- "none" if the reply has no resolvable duration, is off-topic, or you are not sure.
- Never invent a number. Prefer "none" over guessing.
"""

_ENUM_PROMPT = """You map a user's free-form reply to exactly one value from a fixed set for EVA.

EVA just asked:
{eva_prompt}

Allowed values: {allowed_values}

User reply:
{user_reply}

Return ONLY raw JSON (no markdown):
{{"value": "<one of the allowed values>"|"none", "confidence": 0.0-1.0}}

Rules:
- "value" must be exactly one of the allowed values listed above (verbatim, no others).
- "none" if the reply does not clearly map to one of them, is off-topic, or you are not sure.
- Never invent a value outside the allowed set. Prefer "none" over guessing.
"""


def _call_gemini_json(
    prompt: str,
    *,
    log_tag: str,
) -> tuple[Optional[Dict[str, Any]], float]:
    """Shared call+parse+latency boilerplate for the value-type resolvers below."""
    started = time.monotonic()
    raw = gemini_service.generate_constrained_text(
        prompt,
        model_name=_model_name(),
        log_tag=log_tag,
    )
    latency_ms = (time.monotonic() - started) * 1000
    return _parse_json_object(raw), latency_ms


def _strip_fence(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json_object(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    text = _strip_fence(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def _feature_enabled() -> bool:
    return bool(getattr(settings, "USE_GEMINI_PENDING_REPLY", False))


def _min_confidence(*, destructive: bool) -> float:
    if destructive:
        return float(
            getattr(settings, "GEMINI_PENDING_REPLY_MIN_CONFIDENCE_DESTRUCTIVE", 0.85)
        )
    return float(getattr(settings, "GEMINI_PENDING_REPLY_MIN_CONFIDENCE", 0.7))


def _model_name() -> str:
    """Shares GEMINI_MODEL with every other Gemini call site — one env var."""
    return str(settings.GEMINI_MODEL or "gemini-3.1-flash-lite")


def _log_attempt(
    *,
    kind: str,
    deterministic_miss: str,
    choice: Any,
    confidence: Any,
    accepted: bool,
    latency_ms: float,
    reason: str = "",
) -> None:
    print(
        "[GeminiPendingReply] "
        f"kind={kind} miss={deterministic_miss} choice={choice!r} "
        f"confidence={confidence!r} accepted={accepted} "
        f"latency_ms={latency_ms:.0f}"
        + (f" reason={reason}" if reason else "")
    )


def build_options_from_tasks(
    task_ids: Sequence[Any],
    tasks: Sequence[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Build [{id, index, label}] from parallel task_ids / tasks previews."""
    tasks = list(tasks or [])
    options: List[Dict[str, Any]] = []
    for index, task_id in enumerate(task_ids):
        label = ""
        if index < len(tasks) and isinstance(tasks[index], dict):
            label = str(tasks[index].get("title") or "").strip()
        if not label:
            label = f"Option {index + 1}"
        options.append(
            {
                "id": str(task_id),
                "index": index + 1,
                "label": label,
            }
        )
    return options


def build_options_from_goals(
    goal_ids: Sequence[Any],
    goals: Sequence[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Build [{id, index, label}] from parallel goal_ids / goals previews."""
    goals = list(goals or [])
    options: List[Dict[str, Any]] = []
    for index, goal_id in enumerate(goal_ids):
        label = ""
        if index < len(goals) and isinstance(goals[index], dict):
            goal = goals[index]
            label = str(goal.get("title") or "").strip()
            if not label:
                topic = str(goal.get("subject") or goal.get("topic") or "").strip()
                roadmap_key = str(goal.get("roadmap_key") or "").strip()
                if topic and roadmap_key:
                    label = f"{topic} {roadmap_key}"
                else:
                    label = topic or roadmap_key
        if not label:
            label = f"Option {index + 1}"
        options.append(
            {
                "id": str(goal_id),
                "index": index + 1,
                "label": label,
            }
        )
    return options


def build_options_from_schedule_options(
    schedule_options: Sequence[Dict[str, Any]] | None,
) -> List[Dict[str, Any]]:
    """Normalize learning-create schedule_options into [{id, index, label}]."""
    options: List[Dict[str, Any]] = []
    for index, row in enumerate(schedule_options or []):
        if not isinstance(row, dict):
            continue
        option_id = str(row.get("id") or "").strip()
        if not option_id:
            continue
        label = str(row.get("label") or "").strip() or f"Option {index + 1}"
        options.append({"id": option_id, "index": index + 1, "label": label})
    return options


def resolve_yes_no_fallback(
    user_reply: str,
    *,
    eva_prompt: str = "",
    destructive: bool = False,
    deterministic_miss: str = "invalid",
) -> Optional[str]:
    """
    Map a free-form reply to "yes" / "no", or None to re-ask.

    Never returns a destructive "yes" below the destructive confidence bar.
    """
    if not _feature_enabled():
        return None

    reply = (user_reply or "").strip()
    if not reply:
        return None

    prompt = _YES_NO_PROMPT.format(
        eva_prompt=(eva_prompt or "Please confirm with yes or no.").strip(),
        user_reply=reply,
    )
    started = time.monotonic()
    raw = gemini_service.generate_constrained_text(
        prompt,
        model_name=_model_name(),
        log_tag="pending_yes_no",
    )
    latency_ms = (time.monotonic() - started) * 1000
    data = _parse_json_object(raw)
    if not data:
        _log_attempt(
            kind="yes_no",
            deterministic_miss=deterministic_miss,
            choice=None,
            confidence=None,
            accepted=False,
            latency_ms=latency_ms,
            reason="parse_failed",
        )
        return None

    choice = str(data.get("choice") or "").strip().lower()
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0

    if choice not in {"yes", "no", "none"}:
        _log_attempt(
            kind="yes_no",
            deterministic_miss=deterministic_miss,
            choice=choice,
            confidence=confidence,
            accepted=False,
            latency_ms=latency_ms,
            reason="invalid_choice",
        )
        return None

    if choice == "none":
        _log_attempt(
            kind="yes_no",
            deterministic_miss=deterministic_miss,
            choice=choice,
            confidence=confidence,
            accepted=False,
            latency_ms=latency_ms,
            reason="none",
        )
        return None

    min_conf = _min_confidence(destructive=destructive and choice == "yes")
    if confidence < min_conf:
        _log_attempt(
            kind="yes_no",
            deterministic_miss=deterministic_miss,
            choice=choice,
            confidence=confidence,
            accepted=False,
            latency_ms=latency_ms,
            reason=f"low_confidence<{min_conf}",
        )
        return None

    _log_attempt(
        kind="yes_no",
        deterministic_miss=deterministic_miss,
        choice=choice,
        confidence=confidence,
        accepted=True,
        latency_ms=latency_ms,
    )
    return choice


def resolve_list_choice_fallback(
    user_reply: str,
    options: Sequence[Dict[str, Any]],
    *,
    allow_all: bool = False,
    eva_prompt: str = "",
    deterministic_miss: str = "invalid",
) -> Optional[str]:
    """
    Map a free-form reply to an option id (or "all"), or None to re-ask.

    Always validates the returned id against the provided option set.
    """
    if not _feature_enabled():
        return None

    reply = (user_reply or "").strip()
    if not reply:
        return None

    normalized_options: List[Dict[str, Any]] = []
    allowed_ids = set()
    for row in options:
        if not isinstance(row, dict):
            continue
        option_id = str(row.get("id") or "").strip()
        if not option_id:
            continue
        index = row.get("index")
        try:
            index_int = int(index) if index is not None else len(normalized_options) + 1
        except (TypeError, ValueError):
            index_int = len(normalized_options) + 1
        label = str(row.get("label") or "").strip() or f"Option {index_int}"
        normalized_options.append(
            {"id": option_id, "index": index_int, "label": label}
        )
        allowed_ids.add(option_id)

    if not normalized_options:
        return None

    prompt = _LIST_PROMPT.format(
        eva_prompt=(eva_prompt or "Please pick an option from the list.").strip(),
        options_json=json.dumps(normalized_options, ensure_ascii=True),
        allow_all=str(bool(allow_all)).lower(),
        user_reply=reply,
    )
    started = time.monotonic()
    raw = gemini_service.generate_constrained_text(
        prompt,
        model_name=_model_name(),
        log_tag="pending_list_choice",
    )
    latency_ms = (time.monotonic() - started) * 1000
    data = _parse_json_object(raw)
    if not data:
        _log_attempt(
            kind="list_choice",
            deterministic_miss=deterministic_miss,
            choice=None,
            confidence=None,
            accepted=False,
            latency_ms=latency_ms,
            reason="parse_failed",
        )
        return None

    choice = str(data.get("choice") or "").strip()
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0

    if choice.lower() == "none" or not choice:
        _log_attempt(
            kind="list_choice",
            deterministic_miss=deterministic_miss,
            choice=choice,
            confidence=confidence,
            accepted=False,
            latency_ms=latency_ms,
            reason="none",
        )
        return None

    if choice.lower() == "all":
        if not allow_all:
            _log_attempt(
                kind="list_choice",
                deterministic_miss=deterministic_miss,
                choice=choice,
                confidence=confidence,
                accepted=False,
                latency_ms=latency_ms,
                reason="all_not_allowed",
            )
            return None
        choice = "all"
    elif choice not in allowed_ids:
        # Tolerate returning an index as a string.
        matched = None
        if choice.isdigit():
            idx = int(choice)
            for opt in normalized_options:
                if opt["index"] == idx:
                    matched = opt["id"]
                    break
        if matched is None:
            _log_attempt(
                kind="list_choice",
                deterministic_miss=deterministic_miss,
                choice=choice,
                confidence=confidence,
                accepted=False,
                latency_ms=latency_ms,
                reason="id_not_in_set",
            )
            return None
        choice = matched

    min_conf = _min_confidence(destructive=False)
    if confidence < min_conf:
        _log_attempt(
            kind="list_choice",
            deterministic_miss=deterministic_miss,
            choice=choice,
            confidence=confidence,
            accepted=False,
            latency_ms=latency_ms,
            reason=f"low_confidence<{min_conf}",
        )
        return None

    _log_attempt(
        kind="list_choice",
        deterministic_miss=deterministic_miss,
        choice=choice,
        confidence=confidence,
        accepted=True,
        latency_ms=latency_ms,
    )
    return choice


def resolve_date_fallback(
    user_reply: str,
    *,
    eva_prompt: str = "",
    reference_date: Optional[_date] = None,
    allow_past: bool = False,
    deterministic_miss: str = "invalid",
) -> Optional[str]:
    """
    Map a free-form reply to an ISO date (YYYY-MM-DD), or None to re-ask.

    ``reference_date`` (defaults to real today) is given to Gemini so relative
    phrases ("monday", "from monday", "next friday") resolve correctly, and is
    also used to reject a resolved date that falls in the past unless
    ``allow_past`` is set (e.g. a "show tasks on ..." filter may allow it).
    """
    if not _feature_enabled():
        return None

    reply = (user_reply or "").strip()
    if not reply:
        return None

    today = reference_date or _date.today()
    prompt = _DATE_PROMPT.format(
        today=today.isoformat(),
        weekday=today.strftime("%A"),
        eva_prompt=(eva_prompt or "Please give me a date.").strip(),
        user_reply=reply,
    )
    data, latency_ms = _call_gemini_json(prompt, log_tag="pending_date")
    if not data:
        _log_attempt(
            kind="date", deterministic_miss=deterministic_miss, choice=None,
            confidence=None, accepted=False, latency_ms=latency_ms,
            reason="parse_failed",
        )
        return None

    raw_date = str(data.get("date") or "").strip()
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0

    if not raw_date or raw_date.lower() == "none":
        _log_attempt(
            kind="date", deterministic_miss=deterministic_miss, choice=raw_date,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason="none",
        )
        return None

    try:
        parsed = _date.fromisoformat(raw_date[:10])
    except ValueError:
        _log_attempt(
            kind="date", deterministic_miss=deterministic_miss, choice=raw_date,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason="unparseable_date",
        )
        return None

    if not allow_past and parsed < today:
        _log_attempt(
            kind="date", deterministic_miss=deterministic_miss, choice=raw_date,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason="past_date",
        )
        return None

    min_conf = _min_confidence(destructive=False)
    if confidence < min_conf:
        _log_attempt(
            kind="date", deterministic_miss=deterministic_miss, choice=raw_date,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason=f"low_confidence<{min_conf}",
        )
        return None

    _log_attempt(
        kind="date", deterministic_miss=deterministic_miss, choice=raw_date,
        confidence=confidence, accepted=True, latency_ms=latency_ms,
    )
    return parsed.isoformat()


def resolve_time_fallback(
    user_reply: str,
    *,
    eva_prompt: str = "",
    deterministic_miss: str = "invalid",
) -> Optional[str]:
    """Map a free-form reply to an "HH:MM:SS" time, or None to re-ask."""
    if not _feature_enabled():
        return None

    reply = (user_reply or "").strip()
    if not reply:
        return None

    prompt = _TIME_PROMPT.format(
        eva_prompt=(eva_prompt or "Please give me a time.").strip(),
        user_reply=reply,
    )
    data, latency_ms = _call_gemini_json(prompt, log_tag="pending_time")
    if not data:
        _log_attempt(
            kind="time", deterministic_miss=deterministic_miss, choice=None,
            confidence=None, accepted=False, latency_ms=latency_ms,
            reason="parse_failed",
        )
        return None

    raw_time = str(data.get("time") or "").strip()
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0

    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", raw_time)
    if not match:
        _log_attempt(
            kind="time", deterministic_miss=deterministic_miss, choice=raw_time,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason="none" if raw_time.lower() in {"", "none"} else "unparseable_time",
        )
        return None

    min_conf = _min_confidence(destructive=False)
    if confidence < min_conf:
        _log_attempt(
            kind="time", deterministic_miss=deterministic_miss, choice=raw_time,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason=f"low_confidence<{min_conf}",
        )
        return None

    _log_attempt(
        kind="time", deterministic_miss=deterministic_miss, choice=raw_time,
        confidence=confidence, accepted=True, latency_ms=latency_ms,
    )
    return f"{int(match.group(1)):02d}:{match.group(2)}:00"


def resolve_duration_fallback(
    user_reply: str,
    *,
    unit: str,
    eva_prompt: str = "",
    min_value: int = 1,
    max_value: Optional[int] = None,
    deterministic_miss: str = "invalid",
) -> Optional[int]:
    """
    Map a free-form reply to an integer duration in ``unit`` ("days" or
    "minutes"), or None to re-ask. Bounds mirror the caller's own limits
    (e.g. task duration is 5-1440 minutes; a learning plan is 1-365 days).
    """
    if not _feature_enabled():
        return None

    reply = (user_reply or "").strip()
    if not reply:
        return None

    prompt = _DURATION_PROMPT.format(
        unit=unit,
        eva_prompt=(eva_prompt or f"Please give me a duration in {unit}.").strip(),
        user_reply=reply,
    )
    data, latency_ms = _call_gemini_json(prompt, log_tag="pending_duration")
    if not data:
        _log_attempt(
            kind="duration", deterministic_miss=deterministic_miss, choice=None,
            confidence=None, accepted=False, latency_ms=latency_ms,
            reason="parse_failed",
        )
        return None

    raw_amount = data.get("amount")
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0

    try:
        amount = int(raw_amount)
    except (TypeError, ValueError):
        _log_attempt(
            kind="duration", deterministic_miss=deterministic_miss, choice=raw_amount,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason="none" if str(raw_amount).lower() in {"none", ""} else "unparseable_amount",
        )
        return None

    if amount < min_value or (max_value is not None and amount > max_value):
        _log_attempt(
            kind="duration", deterministic_miss=deterministic_miss, choice=amount,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason="out_of_range",
        )
        return None

    min_conf = _min_confidence(destructive=False)
    if confidence < min_conf:
        _log_attempt(
            kind="duration", deterministic_miss=deterministic_miss, choice=amount,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason=f"low_confidence<{min_conf}",
        )
        return None

    _log_attempt(
        kind="duration", deterministic_miss=deterministic_miss, choice=amount,
        confidence=confidence, accepted=True, latency_ms=latency_ms,
    )
    return amount


def resolve_enum_fallback(
    user_reply: str,
    allowed_values: Sequence[str],
    *,
    eva_prompt: str = "",
    kind: str = "enum",
    deterministic_miss: str = "invalid",
) -> Optional[str]:
    """
    Map a free-form reply to exactly one value from a small fixed set (a
    topic, subtopic key, priority, status, weekday name, ...), or None to
    re-ask. The returned value is always validated against ``allowed_values``.
    """
    if not _feature_enabled():
        return None

    reply = (user_reply or "").strip()
    values = [str(v) for v in allowed_values if str(v).strip()]
    if not reply or not values:
        return None

    prompt = _ENUM_PROMPT.format(
        eva_prompt=(eva_prompt or "Please choose one of the listed options.").strip(),
        allowed_values=json.dumps(values, ensure_ascii=True),
        user_reply=reply,
    )
    data, latency_ms = _call_gemini_json(prompt, log_tag=f"pending_{kind}")
    if not data:
        _log_attempt(
            kind=kind, deterministic_miss=deterministic_miss, choice=None,
            confidence=None, accepted=False, latency_ms=latency_ms,
            reason="parse_failed",
        )
        return None

    choice = str(data.get("value") or "").strip()
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0

    if not choice or choice.lower() == "none":
        _log_attempt(
            kind=kind, deterministic_miss=deterministic_miss, choice=choice,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason="none",
        )
        return None

    if choice not in values:
        # Tolerate a case mismatch before rejecting outright.
        lower_map = {v.lower(): v for v in values}
        matched = lower_map.get(choice.lower())
        if matched is None:
            _log_attempt(
                kind=kind, deterministic_miss=deterministic_miss, choice=choice,
                confidence=confidence, accepted=False, latency_ms=latency_ms,
                reason="value_not_in_set",
            )
            return None
        choice = matched

    min_conf = _min_confidence(destructive=False)
    if confidence < min_conf:
        _log_attempt(
            kind=kind, deterministic_miss=deterministic_miss, choice=choice,
            confidence=confidence, accepted=False, latency_ms=latency_ms,
            reason=f"low_confidence<{min_conf}",
        )
        return None

    _log_attempt(
        kind=kind, deterministic_miss=deterministic_miss, choice=choice,
        confidence=confidence, accepted=True, latency_ms=latency_ms,
    )
    return choice


def is_destructive_yes_no_intent(intent: Optional[str]) -> bool:
    return str(intent or "").strip().lower() in {
        "delete",
        "scheduling_delete",
        "learning_delete",
    }
