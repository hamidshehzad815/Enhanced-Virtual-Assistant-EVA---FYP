"""
Load slot filler pools for NER dataset generation.

Merges vocab.json + scheduling_slots.json + learning_slots.json so training
data includes short/medium/long task names, full person lists, and rich topics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
VOCAB_PATH = ROOT / "config" / "vocab.json"
SCHEDULING_SLOTS_PATH = ROOT / "config" / "scheduling_slots.json"
LEARNING_SLOTS_PATH = ROOT / "config" / "learning_slots.json"

# Extra person names commonly typed but missing from notebook exports
EXTRA_PERSONS = [
    "Usama",
    "Hamza",
    "Hassan",
    "Hussain",
    "Fahad",
    "Saad",
    "Omar",
    "Zain",
    "Hira",
    "Sara",
    "Ahmed",
    "Ali",
    "Fatima",
]

# 1-word task names — underrepresented in old vocab-only pool
SHORT_TASK_NAMES = [
    "exam",
    "quiz",
    "lab",
    "viva",
    "test",
    "report",
    "assignment",
    "project",
    "lecture",
    "seminar",
    "DA",
    "OOP",
    "revision",
    "practice",
    "homework",
    "presentation",
    "deadline",
    "meeting",
    "workshop",
]


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _dedupe(values: List[str]) -> List[str]:
    return list(dict.fromkeys(v for v in values if v))


def _flatten_task_names(vocab: Dict[str, Any]) -> List[str]:
    task_names = vocab.get("task_names", {})
    values: List[str] = []
    for group in task_names.values():
        if isinstance(group, list):
            values.extend(group)
    return values


def _weighted_pool(short: List[str], medium: List[str], long: List[str]) -> List[str]:
    """Repeat tiers so random.choice favours short names (~30%), medium (~40%), long (~30%)."""
    short = _dedupe(short)
    medium = _dedupe([t for t in medium if t not in short])
    long = _dedupe([t for t in long if t not in short and t not in medium])
    pool: List[str] = []
    pool.extend(short * 6)
    pool.extend(medium * 4)
    pool.extend(long * 3)
    return pool or medium or short


def build_slot_pools() -> Dict[str, List[str]]:
    """Return entity slot name -> list of fill values (may contain repeats for weighting)."""
    vocab = _load_json(VOCAB_PATH)
    scheduling = _load_json(SCHEDULING_SLOTS_PATH) if SCHEDULING_SLOTS_PATH.exists() else {}
    learning = _load_json(LEARNING_SLOTS_PATH) if LEARNING_SLOTS_PATH.exists() else {}

    weekdays = list(vocab["days"]["weekdays"])
    relative_dates = list(vocab["days"]["relative"])
    dates = weekdays + relative_dates + list(vocab["days"]["abbreviations"].keys())
    if scheduling.get("dates"):
        dates = _dedupe(dates + list(scheduling["dates"]))

    topics_vocab = list(vocab["topics"]["canonical"]) + list(vocab["topics"]["aliases"].keys())
    topics_learning = list(learning.get("topics", []))
    topics = _dedupe(topics_vocab + topics_learning)

    subtopics_vocab = (
        list(vocab["subtopics"]["common_levels"])
        + list(vocab["subtopics"]["aliases"].keys())
        + list(vocab["subtopics"]["aliases"].values())
    )
    subtopics_learning = list(learning.get("subtopics", []))
    subtopics = _dedupe(subtopics_vocab + subtopics_learning)

    durations_vocab = list(vocab["durations"]["examples"]) + list(vocab["durations"]["abbreviations"])
    durations_learning = list(learning.get("durations", []))
    durations = _dedupe(durations_vocab + durations_learning)

    start_dates = _dedupe(dates + list(learning.get("start_dates", [])))

    times = list(vocab["times"]["examples"])
    if scheduling.get("times"):
        times = _dedupe(times + list(scheduling["times"]))

    priorities = list(vocab["priorities"]["user_values"])
    if scheduling.get("priorities"):
        priorities = _dedupe(priorities + list(scheduling["priorities"]))

    statuses = list(vocab["statuses"]["user_values"])
    if scheduling.get("statuses"):
        statuses = _dedupe(statuses + list(scheduling["statuses"]))

    persons = _dedupe(
        list(vocab["collaborator_names"]["examples"])
        + list(scheduling.get("collaborators", []))
        + list(learning.get("persons", []))
        + EXTRA_PERSONS
    )

    days = weekdays + list(vocab["days"]["abbreviations"].keys())

    medium_tasks = _flatten_task_names(vocab)
    long_tasks = list(scheduling.get("task_names", []))
    task_names = _weighted_pool(SHORT_TASK_NAMES, medium_tasks, long_tasks)

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
        "start_date": start_dates,
        "new_taskname": task_names,
        "new_date": dates,
        "new_time": times,
        "new_priority": priorities,
        "new_status": statuses,
        "new_duration": durations,
    }
    return pools


SLOT_POOLS = build_slot_pools()
