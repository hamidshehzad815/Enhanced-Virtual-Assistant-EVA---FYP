"""
Analytics utility helpers for productivity scoring.
"""
from math import exp
from typing import Dict, Iterable, List, Optional, Set, Tuple

from utils.date_utils import hour_to_12h_format


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_time_decay(days_ago: float, lambda_val: float = 0.01) -> float:
    """
    Exponential time decay weight: e^(-lambda * days_ago)
    """
    days = max(0.0, float(days_ago))
    lam = max(0.0, float(lambda_val))
    if lam == 0.0:
        return 1.0
    return float(exp(-lam * days))


def normalize_scores(scores_dict: Dict[Tuple[int, int], float]) -> Dict[Tuple[int, int], float]:
    """
    Normalize raw scores by max value into [0, 1].
    """
    if not scores_dict:
        return {}

    values = [float(value) for value in scores_dict.values()]
    max_value = max(values) if values else 0.0
    if max_value <= 0:
        return {key: 0.0 for key in scores_dict.keys()}

    return {
        key: float(value) / max_value
        for key, value in scores_dict.items()
    }


def compute_slot_score(
    volume: float,
    reliability: float,
    efficiency: float,
    penalty: float,
) -> float:
    """
    Weighted slot score formula in [0, 1].
    """
    v = _clamp_01(volume)
    r = _clamp_01(reliability)
    e = _clamp_01(efficiency)
    p = _clamp_01(penalty)
    return _clamp_01((0.35 * v + 0.40 * r + 0.25 * e) * p)


def build_hour_ranges(
    scored_hours: Iterable[Tuple[int, float]],
    threshold: float = 0.6,
    merge_threshold: float = 0.6,
) -> List[str]:
    """
    Convert scored hours into merged display ranges.
    """
    candidates: List[Tuple[int, float]] = []
    for hour, score in list(scored_hours or []):
        try:
            hour_int = int(hour)
            score_float = float(score)
        except (TypeError, ValueError):
            continue
        if hour_int < 0 or hour_int > 23:
            continue
        if score_float >= float(threshold):
            candidates.append((hour_int, score_float))

    if not candidates:
        return []

    candidates.sort(key=lambda item: item[0])

    groups: List[List[Tuple[int, float]]] = []
    current: List[Tuple[int, float]] = []

    for hour, score in candidates:
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
            continue

        groups.append(current)
        current = [(hour, score)]

    if current:
        groups.append(current)

    ranges: List[str] = []
    for group in groups:
        start_hour = group[0][0]
        if len(group) == 1:
            start_label = hour_to_12h_format(start_hour)
            if start_label:
                ranges.append(start_label)
            continue

        end_hour_exclusive = (group[-1][0] + 1) % 24
        start_label = hour_to_12h_format(start_hour)
        end_label = hour_to_12h_format(end_hour_exclusive)
        if start_label and end_label:
            ranges.append(f"{start_label}-{end_label}")

    return ranges


def aggregate_day_scores(slot_scores: Dict[Tuple[int, int], float]) -> Dict[int, float]:
    """
    Average slot scores into per-day scores.
    """
    grouped: Dict[int, List[float]] = {}
    for key, score in (slot_scores or {}).items():
        if not isinstance(key, tuple) or len(key) != 2:
            continue
        day = int(key[0])
        grouped.setdefault(day, []).append(float(score))

    return {
        day: (sum(values) / len(values))
        for day, values in grouped.items()
        if values
    }


def filter_reliable_days(
    day_log_counts: Dict[int, int],
    per_day_threshold: int,
) -> Tuple[Set[int], Set[int]]:
    """
    Split days into reliable/unreliable by per-day threshold.
    """
    threshold = max(0, int(per_day_threshold or 0))
    reliable: Set[int] = set()
    unreliable: Set[int] = set()

    for day in range(7):
        count = int((day_log_counts or {}).get(day, 0))
        if count >= threshold:
            reliable.add(day)
        else:
            unreliable.add(day)

    return reliable, unreliable


def get_top_slots(slot_scores: Dict[Tuple[int, int], float], n: int = 3) -> List[Tuple[int, int]]:
    """
    Return top-N slots (day, hour) by score descending.
    """
    limit = max(0, int(n))
    ranked = sorted(
        (slot_scores or {}).items(),
        key=lambda item: (-float(item[1]), int(item[0][0]), int(item[0][1])),
    )
    return [slot for slot, _score in ranked[:limit]]


def get_top_days(
    day_scores: Dict[int, float],
    reliable_days: Set[int],
    n: int = 3,
) -> List[Dict[str, float]]:
    """
    Return top-N reliable days with score metadata.
    """
    limit = max(0, int(n))
    reliable = set(reliable_days or set())
    ranked = [
        (int(day), float(score))
        for day, score in (day_scores or {}).items()
        if int(day) in reliable
    ]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return [
        {"day": day, "score": score}
        for day, score in ranked[:limit]
    ]


def get_best_range_for_day(
    slot_scores: Dict[Tuple[int, int], float],
    day: int,
) -> Optional[str]:
    """
    Return the best hour range string for the given day, else None.
    """
    day_int = int(day)
    hours = [
        (int(hour), float(score))
        for (slot_day, hour), score in (slot_scores or {}).items()
        if int(slot_day) == day_int
    ]
    ranges = build_hour_ranges(hours)
    return ranges[0] if ranges else None


def get_best_day_overall(
    day_scores: Dict[int, float],
    reliable_days: Set[int],
) -> Optional[int]:
    """
    Return the best reliable day by score, else None.
    """
    reliable = set(reliable_days or set())
    candidates = [
        (int(day), float(score))
        for day, score in (day_scores or {}).items()
        if int(day) in reliable
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[1], item[0]))
    return int(candidates[0][0])
