"""
Date utilities for show-flow date window building and local task presentation.
"""
from calendar import monthrange
from datetime import datetime, time, timezone
import re
from typing import Any, Dict, List, Optional

from utils.timezone_utils import get_zoneinfo, utc_naive_to_local


def _strip_leading_hour_zero(value: str) -> str:
    return re.sub(r"^0(\d:)", r"\1", value)


def _parse_duckling_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    if len(raw) == 10:
        try:
            return datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return None

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_value_and_grain(duckling_result: Any) -> Optional[Dict[str, Any]]:
    item = duckling_result
    if isinstance(item, list):
        item = item[0] if item else None
    if item is None:
        return None

    if isinstance(item, str):
        return {"value": item, "grain": "day"}

    if isinstance(item, dict):
        value_payload = item.get("value")
        if isinstance(value_payload, dict):
            value = value_payload.get("value")
            grain = value_payload.get("grain")
            return {"value": value, "grain": grain or item.get("grain") or "day"}
        value = item.get("value")
        grain = item.get("grain")
        if value:
            return {"value": value, "grain": grain or "day"}

    return None


def build_date_range(duckling_result: Any, user_timezone: str) -> Optional[Dict[str, Any]]:
    """
    Build UTC-naive date range boundaries from a Duckling time result.
    Supports day/week/month grain.
    """
    extracted = _extract_value_and_grain(duckling_result)
    if not extracted:
        return None

    parsed = _parse_duckling_value(extracted.get("value"))
    if parsed is None:
        return None

    zone = get_zoneinfo(user_timezone)
    if parsed.tzinfo is None:
        local_base = parsed.replace(tzinfo=zone)
    else:
        local_base = parsed.astimezone(zone)

    grain = str(extracted.get("grain") or "day").lower()
    if grain not in {"day", "week", "month"}:
        grain = "day"

    if grain == "day":
        local_start = datetime.combine(local_base.date(), time.min, tzinfo=zone)
        local_end = datetime.combine(local_base.date(), time.max, tzinfo=zone)
        display_label = local_base.strftime("%A, %d %b %Y").replace(" 0", " ")
    elif grain == "week":
        week_start_date = local_base.date().fromordinal(
            local_base.date().toordinal() - local_base.weekday()
        )
        week_end_date = week_start_date.fromordinal(week_start_date.toordinal() + 6)
        local_start = datetime.combine(week_start_date, time.min, tzinfo=zone)
        local_end = datetime.combine(week_end_date, time.max, tzinfo=zone)
        display_label = (
            f"Week of {week_start_date.strftime('%d %b %Y').replace(' 0', ' ')}"
        )
    else:
        month_start = local_base.date().replace(day=1)
        last_day = monthrange(month_start.year, month_start.month)[1]
        month_end = month_start.replace(day=last_day)
        local_start = datetime.combine(month_start, time.min, tzinfo=zone)
        local_end = datetime.combine(month_end, time.max, tzinfo=zone)
        display_label = local_base.strftime("%B %Y")

    start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = local_end.astimezone(timezone.utc).replace(tzinfo=None)

    return {
        "start_utc": start_utc,
        "end_utc": end_utc,
        "display_label": display_label,
        "grain": grain,
    }


def convert_tasks_to_local(tasks: List[Dict[str, Any]], user_timezone: str) -> List[Dict[str, Any]]:
    """
    Add local display datetime fields to task rows using user timezone.
    """
    localized: List[Dict[str, Any]] = []
    for task in list(tasks or []):
        row = dict(task)
        local_dt = utc_naive_to_local(row.get("due_datetime"), user_timezone)
        if local_dt is not None:
            row["local_datetime_str"] = (
                local_dt.strftime("%A %I:%M %p").replace(" 0", " ")
            )
            row["local_date_str"] = local_dt.strftime("%A, %d %b %Y").replace(" 0", " ")
            row["local_time_str"] = _strip_leading_hour_zero(
                local_dt.strftime("%I:%M %p")
            )
        else:
            row["local_datetime_str"] = ""
            row["local_date_str"] = ""
            row["local_time_str"] = ""
        localized.append(row)

    return localized
