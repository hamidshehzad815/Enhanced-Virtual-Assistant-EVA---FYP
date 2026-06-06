"""
Date/time/duration resolver for Phase 7.
Uses Duckling client to normalize natural-language entity values.
"""
from typing import Any, Dict

from services.duckling import duckling_client
from utils.timezone_utils import resolve_timezone_name


async def _resolve_single_date(value: Any, timezone: str) -> Any:
    if not isinstance(value, str):
        return value
    resolved = await duckling_client.resolve_date(value, timezone=timezone)
    return resolved or value


async def _resolve_single_time(value: Any, timezone: str) -> Any:
    if not isinstance(value, str):
        return value
    resolved = await duckling_client.resolve_time(value, timezone=timezone)
    return resolved or value


async def _resolve_single_duration(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    resolved = await duckling_client.resolve_duration(value)
    return resolved if resolved is not None else value


async def _resolve_value_list(values: Any, resolver, *resolver_args):
    if isinstance(values, list):
        return [await resolver(item, *resolver_args) for item in values]
    return await resolver(values, *resolver_args)


async def resolve_all(entities: Dict[str, Any], timezone: str = "UTC") -> Dict[str, Any]:
    """
    Resolve date/time/duration fields using Duckling.
    Returns updated entities dict.
    """
    if not entities:
        return {}

    resolved = dict(entities)

    # Update-intent compatibility normalization:
    # keep canonical key `new_title` even if model emits `new_taskname`/`new_task_name`.
    if "new_title" not in resolved:
        if "new_taskname" in resolved:
            resolved["new_title"] = resolved["new_taskname"]
        elif "new_task_name" in resolved:
            resolved["new_title"] = resolved["new_task_name"]
    resolved.pop("new_taskname", None)
    resolved.pop("new_task_name", None)

    normalized_timezone = resolve_timezone_name(timezone)

    if "date" in resolved:
        resolved["date"] = await _resolve_value_list(
            resolved["date"],
            _resolve_single_date,
            normalized_timezone,
        )

    if "new_date" in resolved:
        resolved["new_date"] = await _resolve_value_list(
            resolved["new_date"],
            _resolve_single_date,
            normalized_timezone,
        )

    if "start_date" in resolved:
        resolved["start_date"] = await _resolve_value_list(
            resolved["start_date"],
            _resolve_single_date,
            normalized_timezone,
        )

    if "new_start_date" in resolved:
        resolved["new_start_date"] = await _resolve_value_list(
            resolved["new_start_date"],
            _resolve_single_date,
            normalized_timezone,
        )

    if "time" in resolved:
        resolved["time"] = await _resolve_value_list(
            resolved["time"],
            _resolve_single_time,
            normalized_timezone,
        )

    if "new_time" in resolved:
        resolved["new_time"] = await _resolve_value_list(
            resolved["new_time"],
            _resolve_single_time,
            normalized_timezone,
        )

    if "duration" in resolved:
        resolved["duration"] = await _resolve_value_list(resolved["duration"], _resolve_single_duration)

    if "new_duration" in resolved:
        resolved["new_duration"] = await _resolve_value_list(resolved["new_duration"], _resolve_single_duration)

    return resolved
