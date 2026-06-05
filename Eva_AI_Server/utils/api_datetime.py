"""
Serialize UTC-naive stored datetimes for API responses in the user's timezone.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from utils.timezone_utils import utc_naive_to_local

INSTANT_DATETIME_KEYS: Set[str] = {
    "due_datetime",
    "scheduled_date",
    "scheduled_datetime",
    "unlock_at",
    "completed_at",
    "created_at",
    "updated_at",
    "deleted_at",
    "started_at",
    "paused_at",
    "reminder_sent_at",
    "overdue_notified_at",
}

DATE_ONLY_KEYS: Set[str] = {"start_date", "end_date"}


def serialize_stored_datetime(
    value: Any,
    timezone_name: Optional[str],
) -> Optional[str]:
    """UTC-naive instant → local ISO with offset (e.g. 2026-06-05T09:40:00+05:00)."""
    local_dt = utc_naive_to_local(value, timezone_name)
    if local_dt is None:
        if value is None:
            return None
        return str(value).strip() or None
    return local_dt.isoformat()


def serialize_stored_date_only(
    value: Any,
    timezone_name: Optional[str],
) -> Optional[str]:
    local_dt = utc_naive_to_local(value, timezone_name)
    if local_dt is None:
        if value is None:
            return None
        raw = str(value).strip()
        return raw[:10] if len(raw) >= 10 else raw or None
    return local_dt.date().isoformat()


def localize_value_for_api(key: str, value: Any, timezone_name: Optional[str]) -> Any:
    if value is None:
        return None
    if key in DATE_ONLY_KEYS:
        return serialize_stored_date_only(value, timezone_name)
    if key in INSTANT_DATETIME_KEYS:
        return serialize_stored_datetime(value, timezone_name)
    return value


def localize_api_payload(value: Any, timezone_name: Optional[str], depth: int = 0) -> Any:
    if value is None or depth > 10:
        return value

    if isinstance(value, datetime):
        return serialize_stored_datetime(value, timezone_name)

    if isinstance(value, list):
        return [localize_api_payload(item, timezone_name, depth + 1) for item in value]

    if isinstance(value, dict):
        output: Dict[str, Any] = {}
        for key, nested in value.items():
            if isinstance(nested, datetime) or key in INSTANT_DATETIME_KEYS or key in DATE_ONLY_KEYS:
                output[key] = localize_value_for_api(key, nested, timezone_name)
            elif isinstance(nested, (dict, list)):
                output[key] = localize_api_payload(nested, timezone_name, depth + 1)
            else:
                output[key] = nested
        return output

    return value


def localize_task_for_api(task: Dict[str, Any], timezone_name: Optional[str]) -> Dict[str, Any]:
    return localize_api_payload(dict(task or {}), timezone_name)


def localize_tasks_for_api(
    tasks: List[Dict[str, Any]],
    timezone_name: Optional[str],
) -> List[Dict[str, Any]]:
    return [localize_task_for_api(task, timezone_name) for task in list(tasks or [])]


def with_api_timezone(payload: Any, timezone_name: Optional[str]) -> Any:
    """Localize datetimes and attach timezone field on dict payloads."""
    localized = localize_api_payload(payload, timezone_name)
    if isinstance(localized, dict):
        localized["timezone"] = timezone_name or "UTC"
    return localized
