"""
Timezone helpers for converting user-local schedule values to UTC-naive datetimes.
"""
from datetime import date, datetime, time, timezone, tzinfo
from typing import Optional, Tuple, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_TIMEZONE_ALIASES = {
    "UTC": "UTC",
    "GMT": "UTC",
    "ASIA/KARACHI": "Asia/Karachi",
    "PKT": "Asia/Karachi",
    "IST": "Asia/Kolkata",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "EST": "America/New_York",
    "EDT": "America/New_York",
}


def resolve_timezone_name(raw_timezone: Optional[str]) -> str:
    normalized = (raw_timezone or "").strip()
    if not normalized:
        return "UTC"

    alias_key = normalized.upper()
    return _TIMEZONE_ALIASES.get(alias_key, normalized)


def get_zoneinfo(raw_timezone: Optional[str]) -> tzinfo:
    timezone_name = resolve_timezone_name(raw_timezone)
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        try:
            return ZoneInfo("UTC")
        except ZoneInfoNotFoundError:
            # Last-resort fallback when IANA timezone data is unavailable
            # (common on some Windows Python setups without `tzdata`).
            return timezone.utc


def local_datetime_to_utc_naive(
    date_value: str,
    time_value: str,
    raw_timezone: Optional[str],
) -> Optional[datetime]:
    try:
        local_naive = datetime.strptime(
            f"{date_value} {time_value}",
            "%Y-%m-%d %H:%M:%S",
        )
    except ValueError:
        return None

    zone = get_zoneinfo(raw_timezone)
    local_aware = local_naive.replace(tzinfo=zone)
    utc_aware = local_aware.astimezone(timezone.utc)
    return utc_aware.replace(tzinfo=None)


def local_day_bounds_to_utc_naive(
    day_value: Union[str, date, datetime],
    raw_timezone: Optional[str],
) -> Tuple[Optional[datetime], Optional[datetime]]:
    if isinstance(day_value, datetime):
        local_day = day_value.date()
    elif isinstance(day_value, date):
        local_day = day_value
    elif isinstance(day_value, str):
        try:
            local_day = datetime.strptime(day_value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None, None
    else:
        return None, None

    zone = get_zoneinfo(raw_timezone)
    local_start = datetime.combine(local_day, time.min).replace(tzinfo=zone)
    local_end = datetime.combine(local_day, time.max).replace(tzinfo=zone)

    utc_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = local_end.astimezone(timezone.utc).replace(tzinfo=None)
    return utc_start, utc_end


def utc_naive_to_local(
    value: Union[str, datetime],
    raw_timezone: Optional[str],
) -> Optional[datetime]:
    if isinstance(value, datetime):
        base_dt = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        normalized = raw.replace("Z", "+00:00")
        try:
            base_dt = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None

    if base_dt.tzinfo is None:
        utc_aware = base_dt.replace(tzinfo=timezone.utc)
    else:
        utc_aware = base_dt.astimezone(timezone.utc)

    zone = get_zoneinfo(raw_timezone)
    return utc_aware.astimezone(zone)
