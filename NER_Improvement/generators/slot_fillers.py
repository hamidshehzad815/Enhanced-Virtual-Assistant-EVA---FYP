"""
Load slot filler pools from config/vocab.json for dataset generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
VOCAB_PATH = ROOT / "config" / "vocab.json"


def _load_vocab() -> Dict[str, Any]:
    with VOCAB_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _flatten_task_names(vocab: Dict[str, Any]) -> List[str]:
    task_names = vocab.get("task_names", {})
    values: List[str] = []
    for group in task_names.values():
        if isinstance(group, list):
            values.extend(group)
    return values


def build_slot_pools() -> Dict[str, List[str]]:
    """Return entity slot name -> list of fill values."""
    vocab = _load_vocab()

    weekdays = list(vocab["days"]["weekdays"])
    relative_dates = list(vocab["days"]["relative"])
    dates = weekdays + relative_dates + list(vocab["days"]["abbreviations"].keys())

    topics = list(vocab["topics"]["canonical"]) + list(vocab["topics"]["aliases"].keys())
    subtopics = (
        list(vocab["subtopics"]["common_levels"])
        + list(vocab["subtopics"]["aliases"].keys())
        + list(vocab["subtopics"]["aliases"].values())
    )
    # dedupe preserving order
    subtopics = list(dict.fromkeys(subtopics))

    durations = list(vocab["durations"]["examples"]) + list(vocab["durations"]["abbreviations"])
    times = list(vocab["times"]["examples"])
    priorities = list(vocab["priorities"]["user_values"])
    statuses = list(vocab["statuses"]["user_values"])
    persons = list(vocab["collaborator_names"]["examples"])
    days = weekdays + list(vocab["days"]["abbreviations"].keys())

    task_names = _flatten_task_names(vocab)

    # new_* slots reuse same pools as base fields
    pools: Dict[str, List[str]] = {
        "task_name": task_names,
        "date": dates,
        "time": times,
        "priority": priorities,
        "status": statuses,
        "duration": durations,
        "person": persons,
        "day": days,
        "topic": topics,
        "subtopic": subtopics,
        "start_date": dates,
        "new_taskname": task_names,
        "new_date": dates,
        "new_time": times,
        "new_priority": priorities,
        "new_status": statuses,
        "new_duration": durations,
    }
    return pools


SLOT_POOLS = build_slot_pools()
