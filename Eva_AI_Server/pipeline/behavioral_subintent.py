"""
Gemini-backed sub-intent classifier for behavioral analytics commands.

`_detect_sub_intent()` in handlers/behavioral/behavioral.py is a keyword
matcher with no "I don't know" signal — it always returns a default
(productive_hours), so unusual phrasing silently lands on the wrong report
type instead of surfacing a miss. This module lets Gemini map ANY phrasing of
a behavioral command directly onto one of the five canonical sub-intents; the
keyword matcher becomes the fallback only when this is disabled or Gemini is
unavailable/unsure.

Uses GEMINI_MODEL (see config.settings) — no separate model setting.
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional

from config.settings import settings
from services.gemini import gemini_service

SUB_INTENTS = (
    "productive_hours",
    "productive_days",
    "best_time_for_day",
    "completion_rate",
    "productivity_report",
)

_PROMPT = """You map a user's message to exactly ONE behavioral-analytics report type for EVA.

Report types:
- "productive_hours": which HOURS of the day the user is most productive, optionally filtered to one weekday. E.g. "when am i most productive", "what are my best hours", "best hours on tuesday".
- "productive_days": which WEEKDAYS the user is most productive, ranked against each other. No single specific day requested. E.g. "which days am i most focused", "best days for me", "my strongest days".
- "best_time_for_day": suggest a single conflict-free time SLOT on one specific weekday, for scheduling something new into. E.g. "find the best time on friday", "when should i schedule something on monday".
- "completion_rate": on-time vs late task completion percentage / trend over time. E.g. "show my completion rate", "how many tasks do i finish on time", "am i on track".
- "productivity_report": a full combined summary covering everything above at once. E.g. "show my productivity report", "give me a full summary", "how am i doing overall".

User message:
{message}

Return ONLY raw JSON (no markdown):
{{"sub_intent": "<one of the five report types above>", "confidence": 0.0-1.0}}

Rules:
- "sub_intent" must be exactly one of: productive_hours, productive_days, best_time_for_day, completion_rate, productivity_report.
- A single specific weekday plus a request to schedule/find a slot into it is "best_time_for_day", not "productive_hours".
- If unsure, pick the closest match but report a low confidence rather than guessing wildly.
"""


def _strip_fence(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def resolve_behavioral_sub_intent(message: str) -> Optional[str]:
    """
    Map free-form text to one of SUB_INTENTS via Gemini, or None to fall back
    to the keyword-based `_detect_sub_intent()`.
    """
    if not bool(getattr(settings, "USE_GEMINI_BEHAVIORAL_SUBINTENT", False)):
        return None

    text = (message or "").strip()
    if not text:
        return None

    started = time.monotonic()
    raw = gemini_service.generate_constrained_text(
        _PROMPT.format(message=text),
        model_name=str(settings.GEMINI_MODEL or "gemini-3.1-flash-lite"),
        log_tag="behavioral_subintent",
    )
    latency_ms = (time.monotonic() - started) * 1000

    if not raw:
        print(f"[BehavioralSubIntent] CALL  {latency_ms:.0f}ms  FAILED -> keyword fallback")
        return None

    try:
        data = json.loads(_strip_fence(raw))
    except json.JSONDecodeError:
        print(
            f"[BehavioralSubIntent] CALL  {latency_ms:.0f}ms  "
            f"UNPARSEABLE -> keyword fallback: {raw!r}"
        )
        return None

    if not isinstance(data, dict):
        return None

    sub_intent = str(data.get("sub_intent") or "").strip()
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0

    min_conf = float(getattr(settings, "GEMINI_PENDING_REPLY_MIN_CONFIDENCE", 0.7))
    if sub_intent not in SUB_INTENTS or confidence < min_conf:
        print(
            f"[BehavioralSubIntent] CALL  {latency_ms:.0f}ms  "
            f"REJECTED sub_intent={sub_intent!r} confidence={confidence} -> keyword fallback"
        )
        return None

    print(
        f"[BehavioralSubIntent] CALL  {latency_ms:.0f}ms  "
        f"-> {sub_intent} (confidence={confidence})"
    )
    return sub_intent


__all__ = ["resolve_behavioral_sub_intent", "SUB_INTENTS"]
