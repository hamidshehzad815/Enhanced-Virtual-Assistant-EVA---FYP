"""
Lightweight spell correction before NER inference.

Only whole-token replacements from a small typo map. Protected tokens
(topics, weekdays, months) are never modified.
"""
from __future__ import annotations

import re
from typing import Dict, Set

# Common user typos seen in EVA testing / NER improvement data.
_COMMON_TYPOS: Dict[str, str] = {
    "beginer": "beginner",
    "beginers": "beginners",
    "begginer": "beginner",
    "begginers": "beginners",
    "intermedate": "intermediate",
    "physcis": "physics",
    "pyton": "python",
    "javascrpt": "javascript",
    "munday": "monday",
    "tuseday": "tuesday",
    "wednsday": "wednesday",
    "thrusday": "thursday",
    "firday": "friday",
    "satuday": "saturday",
    "sundya": "sunday",
    "tommorow": "tomorrow",
    "tommorrow": "tomorrow",
    "leran": "learn",
    "creat": "create",
    "delet": "delete",
    "remov": "remove",
    "updat": "update",
    "shcedule": "schedule",
    "scheduel": "schedule",
}

_PROTECTED: Set[str] = {
    "python",
    "javascript",
    "typescript",
    "java",
    "mysql",
    "mongodb",
    "postgresql",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "today",
    "tomorrow",
    "yesterday",
}

_TOKEN_RE = re.compile(r"\S+")


def _preserve_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement.capitalize()
    return replacement


def apply_spell_corrections(text: str) -> str:
    """Return text with safe whole-token typo fixes applied."""
    if not text or not text.strip():
        return text

    parts: list[str] = []
    last = 0
    for match in _TOKEN_RE.finditer(text):
        parts.append(text[last : match.start()])
        token = match.group()
        core = token.strip(".,!?;:'\"")
        prefix = token[: len(token) - len(token.lstrip(".,!?;:'\""))]
        suffix = token[len(core) + len(prefix) :]

        low = core.lower()
        if low in _PROTECTED:
            corrected = core
        elif low in _COMMON_TYPOS:
            corrected = _preserve_case(core, _COMMON_TYPOS[low])
        else:
            corrected = core

        parts.append(f"{prefix}{corrected}{suffix}")
        last = match.end()
    parts.append(text[last:])
    return "".join(parts)
