"""
Load rich slot pools from config/scheduling_slots.json and config/learning_slots.json.

Source arrays are extracted from DataSets/InshallahDataset/*.ipynb.
Refresh with: python3 sync_slots_from_notebooks.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SCHED_PATH = ROOT / "config" / "scheduling_slots.json"
LEARN_PATH = ROOT / "config" / "learning_slots.json"


def _load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for v in values:
        s = str(v).strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def build_clf_slot_pools(extra: Dict[str, List[str]] | None = None) -> Dict[str, List[str]]:
    sched = _load(SCHED_PATH)
    learn = _load(LEARN_PATH)

    task_names = _dedupe(list(sched.get("task_names") or []))
    dates = _dedupe(
        list(sched.get("dates") or [])
        + list(learn.get("start_dates") or [])
        + ["today", "tomorrow", "next week", "this week"]
    )
    times = _dedupe(list(sched.get("times") or []))
    durations = _dedupe(
        list(sched.get("durations") or []) + list(learn.get("durations") or [])
    )
    priorities = _dedupe(list(sched.get("priorities") or []))
    statuses = _dedupe(list(sched.get("statuses") or []))
    collaborators = _dedupe(
        list(sched.get("collaborators") or []) + list(learn.get("persons") or [])
    )
    topics = _dedupe(list(learn.get("topics") or []))
    subtopics = _dedupe(list(learn.get("subtopics") or []))
    start_dates = _dedupe(list(learn.get("start_dates") or []))

    scopes = _dedupe(
        [
            "my",
            "today's",
            "tomorrow's",
            "this week's",
            "next week's",
            "upcoming",
            "pending",
            "completed",
        ]
    )
    date_scopes = _dedupe(
        ["today", "tomorrow", "this week", "next week", "this month", "next month"]
    )
    update_actions = _dedupe(
        [
            "to friday",
            "to 3pm",
            "to {time}",
            "priority to high",
            "priority to low",
            "duration to 2 hours",
            "duration to {duration}",
            "rename to {task}",
            "status to completed",
            "status to pending",
        ]
    )

    pools: Dict[str, List[str]] = {
        "task": task_names,
        "task_name": task_names,
        "task_ref": task_names,
        "task_ref2": task_names,
        "date": dates,
        "date_phrase": dates,
        "date_scope": date_scopes,
        "start_when": start_dates,
        "time": times,
        "duration": durations,
        "priority": priorities,
        "status": statuses,
        "person": collaborators,
        "collaborator": collaborators,
        "topic": topics,
        "subtopic": subtopics,
        "scope": scopes,
        "update_action": update_actions,
        "day": _dedupe(list(sched.get("days") or [])),
    }

    if extra:
        for key, values in extra.items():
            pools[key] = _dedupe(list(pools.get(key) or []) + list(values or []))

    return pools


SLOT_POOLS = build_clf_slot_pools()
