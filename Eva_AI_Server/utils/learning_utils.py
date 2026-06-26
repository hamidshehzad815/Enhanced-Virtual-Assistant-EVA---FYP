"""
Learning roadmap helpers: topic/subtopic normalization, duration parsing, schedule building.
"""

from __future__ import annotations

import difflib
import json
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from config.settings import get_roadmaps_json_path, settings
from utils.timezone_utils import local_datetime_to_utc_naive

SUPPORTED_TOPICS: Set[str] = {
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C#",
    "C++",
    "Go",
    "Rust",
    "PHP",
    "Kotlin",
    "Swift",
    "Ruby",
    "Dart",
    "C",
    "Oracle",
    "MySQL",
    "Microsoft SQL Server",
    "PostgreSQL",
    "MongoDB",
    "SQL",
}

TOPIC_ALIAS_MAP: Dict[str, str] = {
    "py": "Python",
    "python3": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "golang": "Go",
    "go lang": "Go",
    "cpp": "C++",
    "c++": "C++",
    "c plus plus": "C++",
    "c sharp": "C#",
    "c#": "C#",
    "csharp": "C#",
    "mongo": "MongoDB",
    "mongo db": "MongoDB",
    "mongodb": "MongoDB",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgre": "PostgreSQL",
    "mssql": "Microsoft SQL Server",
    "sql server": "Microsoft SQL Server",
    "microsoft sql server": "Microsoft SQL Server",
    "my sql": "MySQL",
    "mysql": "MySQL",
}

SUBTOPIC_ALIAS_MAP: Dict[str, str] = {
    "beginner": "basics",
    "beginners": "basics",
    "fundamentals": "basics",
    "intro": "basics",
    "introduction": "basics",
    "mid": "intermediate",
    "mid level": "intermediate",
    "mid-level": "intermediate",
    "intermediate": "intermediate",
    "expert": "advanced",
    "pro": "advanced",
    "master": "advanced",
    "advanced": "advanced",
    "oop": "object oriented programming",
    "object oriented": "object oriented programming",
    "object-oriented": "object oriented programming",
    "oops": "object oriented programming",
    "async": "async await coroutines",
    "concurrency": "concurrency and parallelism",
    "decorators": "decorators and context managers",
    "generators": "generators and iterators",
    "file": "file handling",
    "files": "file handling",
    "testing": "testing and debugging",
    "type hints": "type hints and mypy",
    "comprehensions": "comprehensions and functional tools",
}

_TOPIC_ALIAS_LOWER = {k.lower(): v for k, v in TOPIC_ALIAS_MAP.items()}
_SUBTOPIC_ALIAS_LOWER = {k.lower(): v for k, v in SUBTOPIC_ALIAS_MAP.items()}

# NER noise tokens to drop when subtopic is emitted as a list (e.g. ["oop", "ma"]).
# Session phrasing words must not become roadmap_key filters (e.g. subtopic "next").
_SUBTOPIC_NER_NOISE: Set[str] = {
    "ma",
    "next",
    "session",
    "sessions",
    "today",
    "todays",
    "lesson",
    "lessons",
}

_ROADMAP_JSON_CACHE: Optional[Dict[str, Any]] = None

_OOP_MESSAGE_RE = re.compile(
    r"\b(oop|oops|object[- ]oriented(?:\s+programming)?)\b",
    flags=re.IGNORECASE,
)

# Sub-intent keyword patterns for learning_update (longest phrases first).
_LEARNING_UPDATE_SUB_INTENT_PATTERNS: Tuple[Tuple[str, str], ...] = tuple(
    sorted(
        [
            ("stop for now", "pause"),
            ("put on hold", "pause"),
            ("on hold", "pause"),
            ("take a break from", "pause"),
            ("mark next session", "complete"),
            ("mark today's session", "complete"),
            ("mark todays session", "complete"),
            ("mark session as done", "complete"),
            ("mark session done", "complete"),
            ("mark done", "complete"),
            ("mark complete", "complete"),
            ("done with", "complete"),
            ("i completed", "complete"),
            ("i finished", "complete"),
            ("skip this topic", "skip"),
            ("skip next session", "skip"),
            ("already know", "skip"),
            ("shift session to", "reschedule"),
            ("change date", "reschedule"),
            ("start again", "resume"),
            ("pick up", "resume"),
            ("unpause", "resume"),
            ("reschedule", "reschedule"),
            ("postpone", "reschedule"),
            ("pause", "pause"),
            ("halt", "pause"),
            ("resume", "resume"),
            ("continue", "resume"),
            ("restart", "resume"),
            ("finished", "complete"),
            ("completed", "complete"),
            ("i did", "complete"),
            ("skip", "skip"),
            ("bypass", "skip"),
            ("move", "reschedule"),
        ],
        key=lambda item: len(item[0]),
        reverse=True,
    ),
)

_SESSION_UNLOCK_WINDOW = timedelta(hours=24)
_DEFAULT_SESSION_DURATION_MINUTES = 90


def session_duration_minutes(session: Dict[str, Any]) -> int:
    """Estimated session length used for ongoing vs overdue boundaries."""
    for key in ("estimated_duration", "duration"):
        try:
            value = int(session.get(key) or 0)
            if value > 0:
                return value
        except (TypeError, ValueError):
            continue
    return _DEFAULT_SESSION_DURATION_MINUTES


def session_window_end(session: Dict[str, Any], scheduled: datetime) -> datetime:
    """UTC-aware end of the scheduled session window."""
    start = _as_utc_aware(scheduled)
    return start + timedelta(minutes=session_duration_minutes(session))

# Typos: reschdule, reshedule, etc.
_RESCHEDULE_WORD_RE = re.compile(
    r"\b(?:re?sch[ae]?dul\w*|postpone)\b",
    re.IGNORECASE,
)
# "session to June 4" / "session to june4" — move date, not completion.
_SESSION_TO_DATE_RE = re.compile(
    r"\b(?:session|sessions|topic|lesson)\s+to\s+",
    re.IGNORECASE,
)

# Optional topic/track tokens between cue words (mark/skip/next/today) and "session".
# Handles both "mark next python session" and "mark python next session".
_OPTIONAL_TRACK_WORDS = (
    r"(?:\s+(?!next\b|today\b|today'?s?\b|session\b|sessions\b|as\b|to\b|done\b|complete\b|finished\b)"
    r"[\w#+.:-]+)*"
)

_MARK_NEXT_SESSION_COMPLETE_RE = re.compile(
    rf"\bmark{_OPTIONAL_TRACK_WORDS}\s+next{_OPTIONAL_TRACK_WORDS}\s+session"
    rf"(?:\s+as)?\s*(?:done|complete|finished)\b",
    re.IGNORECASE,
)
_MARK_TODAY_SESSION_COMPLETE_RE = re.compile(
    rf"\bmark{_OPTIONAL_TRACK_WORDS}\s+today'?s?{_OPTIONAL_TRACK_WORDS}\s+session\b",
    re.IGNORECASE,
)
_SKIP_NEXT_SESSION_RE = re.compile(
    rf"\bskip{_OPTIONAL_TRACK_WORDS}\s+next{_OPTIONAL_TRACK_WORDS}\s+session\b",
    re.IGNORECASE,
)


def _detect_flexible_session_sub_intent(text: str) -> Optional[str]:
    """
    Match natural phrasing where optional language/track words appear around
    'next'/'today' and 'session' (substring patterns cannot handle this).
    """
    if _SKIP_NEXT_SESSION_RE.search(text):
        return "skip"
    if _MARK_NEXT_SESSION_COMPLETE_RE.search(text):
        return "complete"
    if _MARK_TODAY_SESSION_COMPLETE_RE.search(text):
        return "complete"
    return None


def message_implies_reschedule(message: Optional[str]) -> bool:
    """True when user is trying to move a session date (incl. common typos)."""
    text = str(message or "").strip().lower()
    if not text:
        return False
    if _RESCHEDULE_WORD_RE.search(text):
        return True
    if _SESSION_TO_DATE_RE.search(text):
        return True
    return any(
        marker in text
        for marker in (
            "reschedule",
            "postpone",
            "shift session to",
            "change date",
            "change the date",
        )
    )


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min)
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _as_utc_aware(dt: datetime) -> datetime:
    """Normalize naive (assumed UTC) and aware datetimes for safe comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def detect_learning_sub_intent(message: Optional[str]) -> Optional[str]:
    """
    Detect learning_update sub-intent from user message keywords.

    Returns one of: pause, resume, complete, skip, reschedule — or None if ambiguous.
    """
    text = str(message or "").strip().lower()
    if not text:
        return None

    # Reschedule/skip/pause/resume win over incidental "finished"/"done" in the same sentence.
    if message_implies_reschedule(text):
        return "reschedule"
    if re.search(r"\bmove\b", text) and re.search(
        r"\b(session|sessions|lesson|topic|learning|plan|roadmap)\b",
        text,
    ):
        return "reschedule"

    flexible = _detect_flexible_session_sub_intent(text)
    if flexible:
        return flexible

    for phrase, sub_intent in _LEARNING_UPDATE_SUB_INTENT_PATTERNS:
        if phrase not in text:
            continue
        if sub_intent == "complete" and any(
            marker in text
            for marker in ("reschedule", "postpone", "shift session to", "change date")
        ):
            continue
        return sub_intent

    return None


def compute_session_state(
    session: Dict[str, Any],
    now: datetime,
    *,
    previous_resolved_at: Optional[datetime] = None,
    previous_scheduled_date: Optional[datetime] = None,
) -> str:
    """
    Runtime session lock state for learning_update interactions.

    Returns: locked | unlocked_future | ongoing | overdue | completed | skipped

    When the gap to the previous session is under 24 hours, the session unlocks when
    the previous session is resolved (completed/skipped), not 24h before schedule.

    ``ongoing`` covers scheduled start through scheduled start + estimated_duration.
    ``overdue`` begins once that window ends without completion.
    """
    status = str(session.get("status") or "").strip().lower()
    if status in ("completed", "skipped"):
        return status

    scheduled = _coerce_datetime(session.get("scheduled_date"))
    if scheduled is None:
        return "locked"

    now = _as_utc_aware(now)
    scheduled = _as_utc_aware(scheduled)

    unlock_time = scheduled - _SESSION_UNLOCK_WINDOW

    prev_scheduled = _coerce_datetime(previous_scheduled_date)
    prev_resolved = _coerce_datetime(previous_resolved_at)
    if prev_scheduled is not None:
        prev_scheduled = _as_utc_aware(prev_scheduled)
        gap = scheduled - prev_scheduled
        if gap < _SESSION_UNLOCK_WINDOW:
            if prev_resolved is not None:
                unlock_time = _as_utc_aware(prev_resolved)
            else:
                unlock_time = scheduled

    if now < unlock_time:
        return "locked"
    if now < scheduled:
        return "unlocked_future"
    if now < session_window_end(session, scheduled):
        return "ongoing"
    return "overdue"


def _roadmap_data() -> Dict[str, Any]:
    global _ROADMAP_JSON_CACHE
    if _ROADMAP_JSON_CACHE is None:
        path: Path = get_roadmaps_json_path()
        raw = path.read_text(encoding="utf-8")
        _ROADMAP_JSON_CACHE = json.loads(raw)
    return _ROADMAP_JSON_CACHE


def level_keys_for_language(language: str) -> List[str]:
    """Roadmap level keys for a canonical language (from roadmaps.json)."""
    data = _roadmap_data()
    block = data.get(language)
    if not isinstance(block, dict):
        return []
    topics = block.get("topics")
    if isinstance(topics, list) and topics and all(isinstance(k, str) for k in topics):
        return [str(k) for k in topics]
    # Alternate schema: levels are only child dicts with a ``topics`` array (no top-level key list).
    derived: List[str] = []
    for k, v in block.items():
        if not isinstance(k, str) or k == "topics":
            continue
        if isinstance(v, dict) and isinstance(v.get("topics"), list):
            derived.append(k)
    return sorted(derived)


def roadmap_sessions_per_calendar_day(
    session_count: int,
    calendar_days: Optional[int],
) -> Optional[float]:
    """
    Average roadmap sessions per calendar day for a level.

    ``session_count`` is the number of sessions (``len(topics)`` in JSON).
    ``calendar_days`` is the level's suggested calendar span (``days`` in JSON).

    Example: 10 sessions, 5 calendar days → ``2.0`` (two sessions per day on average).
    """
    if calendar_days is None or int(calendar_days) < 1 or session_count < 0:
        return None
    return session_count / float(calendar_days)


def normalize_topic(extracted: Optional[str]) -> Optional[str]:
    """Return canonical topic name or None if unsupported."""
    if extracted is None:
        return None
    s = str(extracted).strip()
    if not s:
        return None
    low = s.lower()
    if low in _TOPIC_ALIAS_LOWER:
        return _TOPIC_ALIAS_LOWER[low]
    for topic in SUPPORTED_TOPICS:
        if topic.lower() == low:
            return topic
    return None


def _token_in_key(token: str, key: str) -> bool:
    """True when token matches key as a whole word (avoids oop ⊂ loops false positives)."""
    if not token or not key:
        return False
    kn = key.lower()
    t = token.lower()
    if len(t) >= 5 and t in kn:
        return True
    try:
        if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", kn):
            return True
        # NER often emits singular "list" for roadmap keys like "lists …" (min length 4
        # so "oop" does not match inside "loops" via an unintended "oops" span).
        if len(t) >= 4 and re.search(
            r"(?<![a-z0-9])" + re.escape(t) + r"s(?![a-z0-9])",
            kn,
        ):
            return True
    except re.error:
        return False
    return False


def _subtopic_match_score(user_norm: str, key: str) -> float:
    """
    Score how well user subtopic text matches a roadmap track key (0–1).

    Uses exact containment, word-boundary match, token overlap, and difflib ratio.
    """
    if not user_norm or not key:
        return 0.0
    kn = key.lower()
    scores: List[float] = []

    if user_norm == kn:
        return 1.0

    if _token_in_key(user_norm, kn):
        scores.append(0.92)
    if len(kn) >= 5 and kn in user_norm:
        scores.append(0.84)

    tokens = [t for t in re.split(r"[^a-z0-9]+", user_norm) if len(t) >= 2]
    if tokens:
        hits = sum(1 for t in tokens if _token_in_key(t, kn))
        if hits:
            scores.append(0.38 + 0.5 * (hits / len(tokens)))

    scores.append(difflib.SequenceMatcher(None, user_norm, kn).ratio())
    return max(scores) if scores else 0.0


def _pick_subtopic_from_list(parts: List[str]) -> str:
    """Choose the best subtopic token when NER returns multiple values."""
    cleaned = [p for p in parts if p and p.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]

    for part in cleaned:
        if part.lower() in _SUBTOPIC_ALIAS_LOWER:
            return part

    return max(cleaned, key=lambda p: (len(p), p.lower()))


def normalize_subtopic_entity(value: Any) -> Optional[str]:
    """
    Coerce NER subtopic output to a single string for ``map_subtopic``.

    - Drops known noise tokens (e.g. ``ma``).
    - Flattens lists without ``str(list)`` (which caused ``oop`` to fuzzy-match ``loops``).
    """
    if value is None:
        return None

    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            text = str(item or "").strip()
            if not text:
                continue
            if text.lower() in _SUBTOPIC_NER_NOISE:
                continue
            parts.append(text)
        if not parts:
            return None
        return _pick_subtopic_from_list(parts)

    text = str(value).strip()
    if not text:
        return None
    if text.lower() in _SUBTOPIC_NER_NOISE:
        return None
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
        split_parts = [
            p.strip().strip("'\"")
            for p in inner.split(",")
            if p.strip().strip("'\"")
        ]
        filtered = [
            p
            for p in split_parts
            if p.lower() not in _SUBTOPIC_NER_NOISE
        ]
        if filtered:
            return _pick_subtopic_from_list(filtered)
    return text


def subtopic_hint_from_message(message: Optional[str]) -> Optional[str]:
    """Recover OOP intent from the user message when NER missed or mangled subtopic."""
    if not message or not str(message).strip():
        return None
    if _OOP_MESSAGE_RE.search(str(message)):
        return "oop"
    return None


def _fuzzy_subtopic_alias_key(low: str) -> Optional[str]:
    """Return the closest SUBTOPIC_ALIAS_MAP key when typo similarity is high enough."""
    if not low or low in _SUBTOPIC_ALIAS_LOWER:
        return None
    threshold = max(
        0.0,
        min(1.0, float(getattr(settings, "SUBTOPIC_ALIAS_FUZZY_THRESHOLD", 0.85))),
    )
    best_key: Optional[str] = None
    best_score = 0.0
    for alias_key in _SUBTOPIC_ALIAS_LOWER:
        score = difflib.SequenceMatcher(None, low, alias_key).ratio()
        if score > best_score:
            best_score = score
            best_key = alias_key
    if best_key is not None and best_score >= threshold:
        return best_key
    return None


def _roadmap_key_from_alias(
    alias_key: str,
    keys_ci: Dict[str, str],
) -> Tuple[Optional[str], str]:
    """Resolve alias key to roadmap level key; return (key, phrase_for_fuzzy)."""
    alias_target = str(_SUBTOPIC_ALIAS_LOWER[alias_key]).strip()
    at_low = alias_target.lower()
    if at_low in keys_ci:
        return keys_ci[at_low], alias_target
    return None, alias_target


@dataclass(frozen=True)
class SubtopicResolution:
    """Result of mapping user subtopic text to a roadmap track."""

    roadmap_key: str
    confident: bool
    normalized_subtopic: Optional[str] = None


def resolve_subtopic_mapping(
    extracted: Any,
    language: str,
    *,
    level_keys: Optional[Iterable[str]] = None,
) -> SubtopicResolution:
    """
    Map subtopic text to a roadmap key and whether the match is trustworthy.

    ``confident`` is False when the user supplied subtopic text but nothing matched
    well (caller should ask for clarification instead of defaulting to general).
    """
    normalized = normalize_subtopic_entity(extracted)
    if not normalized:
        return SubtopicResolution("general", True, None)

    raw = normalized
    low = raw.lower()
    keys = list(level_keys) if level_keys is not None else level_keys_for_language(language)
    if not keys:
        return SubtopicResolution("general", False, raw)

    keys_ci: Dict[str, str] = {k.lower(): k for k in keys}
    if low in keys_ci:
        return SubtopicResolution(keys_ci[low], True, raw)

    fuzzy_alias = _fuzzy_subtopic_alias_key(low)
    if fuzzy_alias:
        low = fuzzy_alias

    if low in _SUBTOPIC_ALIAS_LOWER:
        mapped, _ = _roadmap_key_from_alias(low, keys_ci)
        if mapped:
            return SubtopicResolution(mapped, True, raw)
        phrase_for_score = str(_SUBTOPIC_ALIAS_LOWER[low]).strip()
    else:
        phrase_for_score = raw

    pn = re.sub(r"\s+", " ", phrase_for_score.strip().lower())
    if not pn:
        return SubtopicResolution("general", False, raw)

    threshold = max(0.0, min(1.0, float(getattr(settings, "SUBTOPIC_MATCH_THRESHOLD", 0.56))))

    best_key: Optional[str] = None
    best_score = 0.0
    for key in keys:
        s = _subtopic_match_score(pn, key)
        if s > best_score:
            best_score = s
            best_key = key

    if best_key is not None and best_score >= threshold:
        return SubtopicResolution(best_key, True, raw)

    return SubtopicResolution("general", False, raw)


def map_subtopic(
    extracted: Any,
    language: str,
    *,
    level_keys: Optional[Iterable[str]] = None,
) -> str:
    """
    Map user subtopic text to a roadmap level key, or \"general\" if no confident match.

    Resolution order:
      1. Case-insensitive exact match against known track keys.
      2. Alias map only when the alias *target* is itself a valid track key for this language
         (e.g. beginner → basics). Otherwise the alias expands the phrase for fuzzy scoring only.
      3. Fuzzy / substring / token overlap scoring against each key; best score must reach
         ``settings.SUBTOPIC_MATCH_THRESHOLD`` (env ``SUBTOPIC_MATCH_THRESHOLD``).

    ``level_keys`` overrides JSON (used in unit tests).
    """
    return resolve_subtopic_mapping(
        extracted,
        language,
        level_keys=level_keys,
    ).roadmap_key


# Whole-string duration (after strip), e.g. "2 weeks", "1 month".
_DURATION_RE = re.compile(
    r"^\s*(\d+)\s*(day|days|week|weeks|month|months)\s*$",
    flags=re.IGNORECASE,
)
_DURATION_SCAN = re.compile(
    r"(\d+)\s*(day|days|week|weeks|month|months)\b",
    flags=re.IGNORECASE,
)


def parse_duration(text: Optional[str]) -> Optional[int]:
    """Parse phrases like '2 weeks', '1 month', '10 days' into calendar days."""
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    m = _DURATION_RE.match(s)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("day"):
        return n
    if unit.startswith("week"):
        return n * 7
    if unit.startswith("month"):
        return n * 30
    return None


def extract_duration_days(text: Optional[str]) -> Optional[int]:
    """
    Calendar days from a duration phrase, including when embedded in a longer sentence
    (e.g. ``for 1 month``, ``learn for 3 weeks``). Falls back to :func:`parse_duration`
    for whole-string matches.
    """
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    whole = parse_duration(s)
    if whole is not None:
        return whole
    m = _DURATION_SCAN.search(s)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("day"):
        return n
    if unit.startswith("week"):
        return n * 7
    if unit.startswith("month"):
        return n * 30
    return None


DEFAULT_LEARNING_REMINDER_MINUTES = 15
LEARNING_REMINDER_SETTING_KEY = "default_learning_reminder_minutes"


def resolve_learning_reminder_minutes(settings: Optional[Dict[str, Any]]) -> int:
    """
    Minutes before a learning session due time to send a reminder.

    Reads ``default_learning_reminder_minutes`` from user settings (default 15).
    """
    settings = settings or {}
    raw = settings.get(LEARNING_REMINDER_SETTING_KEY)
    try:
        minutes = int(raw if raw is not None else DEFAULT_LEARNING_REMINDER_MINUTES)
    except (TypeError, ValueError):
        minutes = DEFAULT_LEARNING_REMINDER_MINUTES
    return max(5, min(minutes, 1440))


def duration_entity_to_days(value: Any) -> Optional[int]:
    """
    Turn a post-resolution ``duration`` entity into calendar days.

    Duckling's duration dimension is normalized to **minutes** (see ``resolve_duration``);
    long spans become large integers that :func:`parse_duration` cannot read as text.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (list, tuple)) and value:
        return duration_entity_to_days(value[0])
    if isinstance(value, (int, float)):
        minutes = float(value)
        if minutes <= 0:
            return None
        if minutes >= 24 * 60:
            return max(1, int(round(minutes / (24 * 60))))
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        n = int(s)
        if n >= 24 * 60:
            return max(1, int(round(n / (24 * 60))))
    return extract_duration_days(s)


def calculate_available_sessions(
    start_date: date,
    duration_days: int,
    learning_days: Set[int],
) -> int:
    """
    Count learning_days (0=Mon .. 6=Sun, same as Python weekday()) in
    [start_date, start_date + duration_days - 1].
    """
    if duration_days < 1:
        return 0
    total = 0
    for i in range(int(duration_days)):
        d = start_date + timedelta(days=i)
        if d.weekday() in learning_days:
            total += 1
    return total


def calculate_min_weeks_needed(sessions_required: int, sessions_per_week: int) -> int:
    if sessions_required <= 0:
        return 0
    spw = max(1, int(sessions_per_week))
    return int(math.ceil(sessions_required / spw))


def _parse_hhmm(value: str) -> time:
    parts = str(value).strip().split(":")
    if len(parts) != 2:
        raise ValueError("time must be HH:MM")
    h, m = int(parts[0]), int(parts[1])
    return time(hour=h, minute=m)


def _schedule_slots_by_weekday(
    preferred_learning_schedule: List[Dict[str, Any]],
    *,
    default_duration_minutes: int = 90,
) -> Dict[int, Dict[str, Any]]:
    by_day: Dict[int, Dict[str, Any]] = {}
    for slot in preferred_learning_schedule or []:
        if not isinstance(slot, dict):
            continue
        try:
            day = int(slot.get("day"))
        except (TypeError, ValueError):
            continue
        dur = default_duration_minutes
        if slot.get("duration_minutes") is not None:
            try:
                dur = int(slot.get("duration_minutes"))
            except (TypeError, ValueError):
                dur = default_duration_minutes
        dur = max(15, min(240, dur))
        by_day[day] = {
            "time": str(slot.get("time") or "18:00"),
            "duration_minutes": dur,
        }
    return by_day


def next_rebase_start_date(
    now_local: datetime,
    preferred_learning_schedule: List[Dict[str, Any]],
) -> date:
    """
    First calendar date whose schedule slot start is still at or after ``now_local``.

    Walks forward from today so resume/rebuild can use a same-day slot when it has
    not started yet (instead of always skipping to tomorrow).
    """
    by_day = _schedule_slots_by_weekday(preferred_learning_schedule)
    if not by_day:
        return now_local.date() + timedelta(days=1)

    now_cmp = now_local.replace(tzinfo=None) if now_local.tzinfo is not None else now_local
    current = now_local.date()
    for _ in range(14):
        wd = current.weekday()
        if wd in by_day:
            slot_start = datetime.combine(current, _parse_hhmm(str(by_day[wd]["time"])))
            if now_cmp <= slot_start:
                return current
        current = current + timedelta(days=1)

    return now_local.date() + timedelta(days=1)


def build_schedule(
    start_date: date,
    topics: List[Dict[str, Any]],
    preferred_learning_schedule: List[Dict[str, Any]],
    *,
    default_duration_minutes: int = 90,
    timezone_name: Optional[str] = "UTC",
) -> List[Dict[str, Any]]:
    """
    Assign each roadmap topic to the next calendar learning slot.

    `preferred_learning_schedule`: [{ \"day\": 0-6, \"time\": \"HH:MM\", \"duration_minutes\"? }, ...]
    weekday 0 = Monday (matches Python date.weekday()).

    Slot times are interpreted in ``timezone_name`` (user profile), then stored as UTC-naive
    datetimes — same convention as ``scheduling_add`` task ``due_datetime``.

    Each output row: { order, title, resources, scheduled_date, duration_minutes }.
    """
    if not topics:
        return []

    by_day: Dict[int, Dict[str, Any]] = {}
    fallback_dur = max(15, min(240, int(default_duration_minutes or 90)))
    for slot in preferred_learning_schedule or []:
        if not isinstance(slot, dict):
            continue
        day = int(slot["day"])
        dur = fallback_dur
        if slot.get("duration_minutes") is not None:
            try:
                dur = max(15, min(240, int(slot["duration_minutes"])))
            except (TypeError, ValueError):
                dur = fallback_dur
        by_day[day] = {
            "time": str(slot["time"]),
            "duration_minutes": dur,
        }

    learning_days = set(by_day.keys())
    if not learning_days:
        return []

    out: List[Dict[str, Any]] = []
    current = start_date
    topic_index = 0

    while topic_index < len(topics):
        wd = current.weekday()
        if wd in learning_days:
            row = topics[topic_index]
            title = str(row.get("title") or "")
            resources = row.get("resources") if isinstance(row.get("resources"), list) else []
            order = int(row.get("order", topic_index + 1))
            slot_info = by_day[wd]
            tstr = slot_info["time"]
            parsed_time = _parse_hhmm(tstr)
            time_str = f"{parsed_time.hour:02d}:{parsed_time.minute:02d}:00"
            session_dt = local_datetime_to_utc_naive(
                current.isoformat(),
                time_str,
                timezone_name,
            )
            if session_dt is None:
                session_dt = datetime.combine(current, parsed_time)
            out.append(
                {
                    "order": order,
                    "title": title,
                    "resources": resources,
                    "scheduled_date": session_dt,
                    "duration_minutes": int(slot_info["duration_minutes"]),
                },
            )
            topic_index += 1
        current = current + timedelta(days=1)

    return out
