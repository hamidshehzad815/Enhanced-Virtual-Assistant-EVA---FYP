"""
Learning roadmap helpers: topic/subtopic normalization, duration parsing, schedule building.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from config.settings import settings

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


def _roadmap_data() -> Dict[str, Any]:
    global _ROADMAP_JSON_CACHE
    if _ROADMAP_JSON_CACHE is None:
        path: Path = settings.BASE_DIR / "data" / "roadmaps.json"
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
    if not isinstance(topics, list):
        return []
    return [str(k) for k in topics if isinstance(k, str)]


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


def map_subtopic(
    extracted: Optional[str],
    language: str,
    *,
    level_keys: Optional[Iterable[str]] = None,
) -> str:
    """
    Map user subtopic text to a roadmap level key, or \"general\" if no match.

    `level_keys` overrides JSON (used in unit tests).
    """
    if not extracted or not str(extracted).strip():
        return "general"

    raw = str(extracted).strip()
    low = raw.lower()
    phrase = _SUBTOPIC_ALIAS_LOWER.get(low, raw.strip())

    keys = list(level_keys) if level_keys is not None else level_keys_for_language(language)
    if not keys:
        return "general"

    for key in keys:
        if key.lower() == phrase.lower():
            return key

    esc = re.escape(phrase)
    for key in keys:
        if re.search(esc, key, flags=re.IGNORECASE):
            return key

    for key in keys:
        if re.search(re.escape(key), phrase, flags=re.IGNORECASE):
            return key

    return "general"


_DURATION_RE = re.compile(
    r"^\s*(\d+)\s*(day|days|week|weeks|month|months)\s*$",
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
) -> List[Dict[str, Any]]:
    """
    Assign each roadmap topic to the next calendar learning slot.

    `preferred_learning_schedule`: [{ \"day\": 0-6, \"time\": \"HH:MM\" }, ...]
    weekday 0 = Monday (matches Python date.weekday()).

    Each output row: { order, title, resources, scheduled_date }.
    """
    if not topics:
        return []

    by_day: Dict[int, str] = {}
    for slot in preferred_learning_schedule or []:
        if not isinstance(slot, dict):
            continue
        day = int(slot["day"])
        by_day[day] = str(slot["time"])

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
            tstr = by_day[wd]
            session_dt = datetime.combine(current, _parse_hhmm(tstr))
            out.append(
                {
                    "order": order,
                    "title": title,
                    "resources": resources,
                    "scheduled_date": session_dt,
                },
            )
            topic_index += 1
        current = current + timedelta(days=1)

    return out
