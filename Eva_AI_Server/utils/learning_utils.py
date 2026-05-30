"""
Learning roadmap helpers: topic/subtopic normalization, duration parsing, schedule building.
"""

from __future__ import annotations

import difflib
import json
import math
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from config.settings import get_roadmaps_json_path, settings

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

_ROADMAP_JSON_CACHE: Optional[Dict[str, Any]] = None

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


def detect_learning_sub_intent(message: Optional[str]) -> Optional[str]:
    """
    Detect learning_update sub-intent from user message keywords.

    Returns one of: pause, resume, complete, skip, reschedule — or None if ambiguous.
    """
    text = str(message or "").strip().lower()
    if not text:
        return None

    for phrase, sub_intent in _LEARNING_UPDATE_SUB_INTENT_PATTERNS:
        if phrase in text:
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

    Returns: locked | unlocked_future | overdue | completed | skipped

    When the gap to the previous session is under 24 hours, the session unlocks when
    the previous session is resolved (completed/skipped), not 24h before schedule.
    """
    status = str(session.get("status") or "").strip().lower()
    if status in ("completed", "skipped"):
        return status

    scheduled = _coerce_datetime(session.get("scheduled_date"))
    if scheduled is None:
        return "locked"

    if now.tzinfo is not None and scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=now.tzinfo)
    elif now.tzinfo is None and scheduled.tzinfo is not None:
        now = now.replace(tzinfo=scheduled.tzinfo)

    unlock_time = scheduled - _SESSION_UNLOCK_WINDOW

    prev_scheduled = _coerce_datetime(previous_scheduled_date)
    prev_resolved = _coerce_datetime(previous_resolved_at)
    if prev_scheduled is not None:
        gap = scheduled - prev_scheduled
        if gap < _SESSION_UNLOCK_WINDOW:
            if prev_resolved is not None:
                unlock_time = prev_resolved
            else:
                unlock_time = scheduled

    if now < unlock_time:
        return "locked"
    if now < scheduled:
        return "unlocked_future"
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

    if len(user_norm) >= 3 and user_norm in kn:
        scores.append(0.86)
    if len(kn) >= 5 and kn in user_norm:
        scores.append(0.84)

    if len(user_norm) >= 3:
        try:
            if re.search(r"(?<![a-z0-9])" + re.escape(user_norm) + r"(?![a-z0-9])", kn):
                scores.append(0.92)
        except re.error:
            pass

    tokens = [t for t in re.split(r"[^a-z0-9]+", user_norm) if len(t) >= 2]
    if tokens:
        hits = sum(1 for t in tokens if t in kn)
        if hits:
            scores.append(0.38 + 0.5 * (hits / len(tokens)))

    scores.append(difflib.SequenceMatcher(None, user_norm, kn).ratio())
    return max(scores) if scores else 0.0


def map_subtopic(
    extracted: Optional[str],
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
    if not extracted or not str(extracted).strip():
        return "general"

    raw = str(extracted).strip()
    low = raw.lower()
    keys = list(level_keys) if level_keys is not None else level_keys_for_language(language)
    if not keys:
        return "general"

    keys_ci: Dict[str, str] = {k.lower(): k for k in keys}
    if low in keys_ci:
        return keys_ci[low]

    phrase_for_score = raw
    if low in _SUBTOPIC_ALIAS_LOWER:
        alias_target = str(_SUBTOPIC_ALIAS_LOWER[low]).strip()
        at_low = alias_target.lower()
        if at_low in keys_ci:
            return keys_ci[at_low]
        phrase_for_score = alias_target

    pn = re.sub(r"\s+", " ", phrase_for_score.strip().lower())
    if not pn:
        return "general"

    threshold = max(0.0, min(1.0, float(getattr(settings, "SUBTOPIC_MATCH_THRESHOLD", 0.56))))

    best_key: Optional[str] = None
    best_score = 0.0
    for key in keys:
        s = _subtopic_match_score(pn, key)
        if s > best_score:
            best_score = s
            best_key = key

    if best_key is not None and best_score >= threshold:
        return best_key
    return "general"


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


def build_schedule(
    start_date: date,
    topics: List[Dict[str, Any]],
    preferred_learning_schedule: List[Dict[str, Any]],
    *,
    default_duration_minutes: int = 90,
) -> List[Dict[str, Any]]:
    """
    Assign each roadmap topic to the next calendar learning slot.

    `preferred_learning_schedule`: [{ \"day\": 0-6, \"time\": \"HH:MM\", \"duration_minutes\"? }, ...]
    weekday 0 = Monday (matches Python date.weekday()).

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
            session_dt = datetime.combine(current, _parse_hhmm(tstr))
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
