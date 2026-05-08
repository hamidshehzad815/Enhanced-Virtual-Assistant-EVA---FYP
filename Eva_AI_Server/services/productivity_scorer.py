"""
Core productivity scoring engine.
"""
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from utils.analytics_utils import (
    aggregate_day_scores,
    build_hour_ranges,
    compute_slot_score,
    compute_time_decay,
    filter_reliable_days,
    get_best_day_overall,
    normalize_scores,
)
from utils.date_utils import days_since, hour_to_12h_format, weekday_name_to_number


_DAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _slot_from_log(log: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    try:
        day = log.get("scheduled_day")
        hour = log.get("scheduled_hour")
        if day is None:
            day = log.get("day_of_week")
        if hour is None:
            hour = log.get("hour_of_day")
        day_int = int(day)
        hour_int = int(hour)
    except (TypeError, ValueError):
        return None

    if day_int < 0 or day_int > 6 or hour_int < 0 or hour_int > 23:
        return None
    return (day_int, hour_int)


def _duration_for_efficiency(log: Dict[str, Any]) -> Optional[int]:
    for key in ("task_duration_minutes", "task_duration", "duration"):
        try:
            value = int(log.get(key))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None


def _normalize_day(day: Any) -> Optional[int]:
    if day is None:
        return None
    if isinstance(day, int):
        return day if 0 <= day <= 6 else None
    if isinstance(day, str):
        stripped = day.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            day_int = int(stripped)
            return day_int if 0 <= day_int <= 6 else None
        return weekday_name_to_number(stripped)
    return None


def _slot_stats(logs: Iterable[Dict[str, Any]]) -> Dict[Tuple[int, int], Dict[str, Any]]:
    stats: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for raw in list(logs or []):
        if not isinstance(raw, dict):
            continue
        slot = _slot_from_log(raw)
        if slot is None:
            continue

        ts = _coerce_datetime(raw.get("action_timestamp"))
        weight = compute_time_decay(days_since(ts)) if ts else 1.0
        was_on_time = raw.get("was_on_time") is True
        reschedule_count = int(raw.get("reschedule_count") or 0)

        item = stats.setdefault(
            slot,
            {
                "volume_raw": 0.0,
                "on_time_raw": 0.0,
                "eff_weighted_sum": 0.0,
                "eff_weight_sum": 0.0,
                "reschedule_total": 0.0,
                "log_count": 0,
                "on_time_count": 0,
            },
        )
        item["volume_raw"] += weight
        if was_on_time:
            item["on_time_raw"] += weight
            item["on_time_count"] += 1

        time_taken = raw.get("time_taken_minutes")
        duration = _duration_for_efficiency(raw)
        try:
            time_taken_num = float(time_taken)
        except (TypeError, ValueError):
            time_taken_num = None

        if duration and time_taken_num and time_taken_num > 0:
            ratio = min(float(duration) / time_taken_num, 1.0)
            item["eff_weighted_sum"] += ratio * weight
            item["eff_weight_sum"] += weight

        item["reschedule_total"] += max(0, reschedule_count)
        item["log_count"] += 1

    return stats


def _candidate_ranges_for_day(
    day_slot_scores: Dict[int, float],
    threshold: float = 0.6,
    merge_threshold: float = 0.6,
) -> List[Dict[str, Any]]:
    hours = [
        (int(hour), float(score))
        for hour, score in day_slot_scores.items()
        if float(score) >= float(threshold) and 0 <= int(hour) <= 23
    ]
    if not hours:
        return []

    hours.sort(key=lambda item: item[0])
    groups: List[List[Tuple[int, float]]] = []
    current: List[Tuple[int, float]] = []

    for hour, score in hours:
        if not current:
            current = [(hour, score)]
            continue
        prev_hour, prev_score = current[-1]
        can_merge = (
            hour == prev_hour + 1
            and prev_score >= float(merge_threshold)
            and score >= float(merge_threshold)
        )
        if can_merge:
            current.append((hour, score))
        else:
            groups.append(current)
            current = [(hour, score)]
    if current:
        groups.append(current)

    candidates: List[Dict[str, Any]] = []
    for group in groups:
        group_hours = [hour for hour, _score in group]
        max_score = max(score for _hour, score in group)
        ranges = build_hour_ranges(group, threshold=threshold, merge_threshold=merge_threshold)
        label = ranges[0] if ranges else (hour_to_12h_format(group_hours[0]) or str(group_hours[0]))
        candidates.append(
            {
                "hours": group_hours,
                "best_range": label,
                "start_hour": group_hours[0],
                "score": float(max_score),
            }
        )

    candidates.sort(key=lambda item: (-float(item["score"]), int(item["start_hour"])))
    return candidates


def _hour_conflicts(existing_tasks: List[Dict[str, Any]], hour: int) -> bool:
    candidate_start = int(hour) * 60
    candidate_end = (int(hour) + 1) * 60

    for task in list(existing_tasks or []):
        if not isinstance(task, dict):
            continue
        due = _coerce_datetime(task.get("due_datetime"))
        if not due:
            continue
        duration = int(task.get("duration") or 60)
        if duration <= 0:
            duration = 60
        start_minutes = due.hour * 60 + due.minute
        end_minutes = start_minutes + duration
        if start_minutes < candidate_end and end_minutes > candidate_start:
            return True
    return False


def score_all_slots(logs: List[Dict[str, Any]]) -> Dict[Tuple[int, int], float]:
    """
    Score each (day, hour) slot using volume/reliability/efficiency/reschedule penalty.
    """
    slot_stats = _slot_stats(logs)
    if not slot_stats:
        return {}

    volume_raw = {
        slot: float(values["volume_raw"])
        for slot, values in slot_stats.items()
    }
    volume_scores = normalize_scores(volume_raw)

    scored: Dict[Tuple[int, int], float] = {}
    for slot, values in slot_stats.items():
        volume = float(volume_scores.get(slot, 0.0))
        volume_raw_value = float(values["volume_raw"])
        reliability = (float(values["on_time_raw"]) / volume_raw_value) if volume_raw_value > 0 else 0.0

        if float(values["eff_weight_sum"]) > 0:
            efficiency = float(values["eff_weighted_sum"]) / float(values["eff_weight_sum"])
        else:
            efficiency = 0.5

        log_count = max(1, int(values["log_count"]))
        avg_reschedule = float(values["reschedule_total"]) / log_count
        penalty = 1.0 - min(avg_reschedule / 3.0, 0.5)

        scored[slot] = compute_slot_score(volume, reliability, efficiency, penalty)

    return scored


def get_productive_hours(
    logs: List[Dict[str, Any]],
    day: Any = None,
) -> List[Dict[str, Any]]:
    """
    Return productive slot rows sorted by score descending.
    """
    target_day = _normalize_day(day)
    scoped_logs = list(logs or [])
    if target_day is not None:
        scoped_logs = [log for log in scoped_logs if _slot_from_log(log) and _slot_from_log(log)[0] == target_day]

    slot_scores = score_all_slots(scoped_logs)
    if target_day is not None:
        slot_scores = {
            slot: score for slot, score in slot_scores.items()
            if slot[0] == target_day
        }
        _ = build_hour_ranges([(slot[1], score) for slot, score in slot_scores.items()])

    if not slot_scores:
        return []

    stats = _slot_stats(scoped_logs)
    result: List[Dict[str, Any]] = []
    for (day_num, hour), score in slot_scores.items():
        item_stats = stats.get((day_num, hour), {})
        log_count = max(0, int(item_stats.get("log_count") or 0))
        on_time_count = max(0, int(item_stats.get("on_time_count") or 0))
        on_time_rate = (on_time_count / log_count) if log_count > 0 else 0.0
        result.append(
            {
                "day_num": int(day_num),
                "day": _DAY_NAMES.get(int(day_num), str(day_num)),
                "hour": int(hour),
                "hour_display": hour_to_12h_format(hour) or str(hour),
                "score": float(score),
                "on_time_rate": float(round(on_time_rate, 4)),
                "log_count": log_count,
            }
        )

    result.sort(key=lambda row: (-float(row["score"]), int(row["day_num"]), int(row["hour"])))
    return result


def get_productive_days(
    logs: List[Dict[str, Any]],
    day_log_counts: Dict[int, int],
    per_day_threshold: int,
) -> Dict[str, Any]:
    """
    Return reliable/unreliable day breakdown with scores and metadata.
    """
    slot_scores = score_all_slots(logs)
    day_scores = aggregate_day_scores(slot_scores)
    reliable_days, unreliable_days = filter_reliable_days(day_log_counts, per_day_threshold)

    on_time_by_day: Dict[int, Tuple[int, int]] = {}
    for log in list(logs or []):
        slot = _slot_from_log(log)
        if slot is None:
            continue
        day_num = slot[0]
        total, on_time = on_time_by_day.get(day_num, (0, 0))
        total += 1
        if log.get("was_on_time") is True:
            on_time += 1
        on_time_by_day[day_num] = (total, on_time)

    reliable_rows: List[Dict[str, Any]] = []
    for day_num in sorted(reliable_days):
        if int(day_log_counts.get(day_num, 0)) <= 0:
            continue
        total, on_time = on_time_by_day.get(day_num, (0, 0))
        on_time_rate = (on_time / total) if total > 0 else 0.0
        reliable_rows.append(
            {
                "day": _DAY_NAMES.get(day_num, str(day_num)),
                "day_num": day_num,
                "score": float(day_scores.get(day_num, 0.0)),
                "log_count": int(day_log_counts.get(day_num, 0)),
                "on_time_rate": float(round(on_time_rate, 4)),
            }
        )
    reliable_rows.sort(key=lambda row: (-float(row["score"]), int(row["day_num"])))

    threshold = max(0, int(per_day_threshold or 0))
    unreliable_rows = [
        {
            "day": _DAY_NAMES.get(day_num, str(day_num)),
            "day_num": day_num,
            "log_count": int(day_log_counts.get(day_num, 0)),
            "needed": threshold,
        }
        for day_num in sorted(unreliable_days)
    ]

    return {
        "reliable": reliable_rows,
        "unreliable": unreliable_rows,
    }


def get_best_time_for_day(
    logs: List[Dict[str, Any]],
    day: Any,
    existing_tasks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Return best conflict-free range for a specific day.
    """
    day_num = _normalize_day(day)
    if day_num is None:
        return {
            "day": str(day),
            "day_num": None,
            "best_range": None,
            "start_hour": None,
            "score": 0.0,
            "conflict_free": False,
        }

    day_logs = [log for log in list(logs or []) if _slot_from_log(log) and _slot_from_log(log)[0] == day_num]
    day_slot_scores_full = score_all_slots(day_logs)
    day_slot_scores = {
        slot[1]: float(score)
        for slot, score in day_slot_scores_full.items()
        if slot[0] == day_num
    }

    if not day_slot_scores:
        return {
            "day": _DAY_NAMES.get(day_num, str(day_num)),
            "day_num": day_num,
            "best_range": None,
            "start_hour": None,
            "score": 0.0,
            "conflict_free": False,
        }

    _ = build_hour_ranges([(hour, score) for hour, score in day_slot_scores.items()])
    candidates = _candidate_ranges_for_day(day_slot_scores)
    tasks = list(existing_tasks or [])

    for candidate in candidates:
        hours = list(candidate["hours"])
        conflict = any(_hour_conflicts(tasks, hour) for hour in hours)
        if conflict:
            continue
        return {
            "day": _DAY_NAMES.get(day_num, str(day_num)),
            "day_num": day_num,
            "best_range": str(candidate["best_range"]),
            "start_hour": int(candidate["start_hour"]),
            "score": float(candidate["score"]),
            "conflict_free": True,
        }

    return {
        "day": _DAY_NAMES.get(day_num, str(day_num)),
        "day_num": day_num,
        "best_range": None,
        "start_hour": None,
        "score": 0.0,
        "conflict_free": False,
    }


def get_scheduling_suggestion(
    logs: List[Dict[str, Any]],
    day_log_counts: Dict[int, int],
    existing_tasks: Any,
    day: Any = None,
) -> Dict[str, Any]:
    """
    Return scheduling suggestion used by add handler when time/date is missing.
    """
    target_day = _normalize_day(day)
    if target_day is not None:
        reliable_days, _ = filter_reliable_days(day_log_counts or {}, 5)
        if target_day not in reliable_days:
            return {
                "day": _DAY_NAMES.get(target_day, str(target_day)),
                "day_num": target_day,
                "best_range": None,
                "start_hour": None,
                "has_data": False,
            }

        tasks_for_day = (
            list((existing_tasks or {}).get(target_day) or [])
            if isinstance(existing_tasks, dict)
            else list(existing_tasks or [])
        )
        best = get_best_time_for_day(logs, target_day, tasks_for_day)
        return {
            "day": best.get("day"),
            "day_num": best.get("day_num"),
            "best_range": best.get("best_range"),
            "start_hour": best.get("start_hour"),
            "has_data": bool(best.get("best_range")),
        }

    productive_days = get_productive_days(logs, day_log_counts or {}, 5)
    reliable_rows = list(productive_days.get("reliable") or [])
    if not reliable_rows:
        return {
            "day": None,
            "day_num": None,
            "best_range": None,
            "start_hour": None,
            "has_data": False,
        }

    day_scores = {
        int(row["day_num"]): float(row["score"])
        for row in reliable_rows
    }
    reliable_set = {int(row["day_num"]) for row in reliable_rows}
    best_day = get_best_day_overall(day_scores, reliable_set)
    if best_day is None:
        return {
            "day": None,
            "day_num": None,
            "best_range": None,
            "start_hour": None,
            "has_data": False,
        }

    tasks_for_day = (
        list((existing_tasks or {}).get(best_day) or [])
        if isinstance(existing_tasks, dict)
        else list(existing_tasks or [])
    )
    best_time = get_best_time_for_day(logs, best_day, tasks_for_day)
    return {
        "day": best_time.get("day"),
        "day_num": best_time.get("day_num"),
        "best_range": best_time.get("best_range"),
        "start_hour": best_time.get("start_hour"),
        "has_data": bool(best_time.get("best_range")),
    }
