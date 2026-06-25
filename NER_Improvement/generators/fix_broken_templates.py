#!/usr/bin/env python3
"""One-off repair for template placeholder / entity mismatches."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# task_name only — status implied by verb, not tagged
TASK_ONLY = {
    "complete {task_name}",
    "finish {task_name}",
    "done with {task_name}",
    "I finished {task_name}",
    "I completed {task_name}",
    "I am done with {task_name}",
    "start {task_name}",
    "I started {task_name}",
    "begin {task_name}",
    "I am working on {task_name}",
    "tick off {task_name}",
    "check off {task_name}",
    "done {task_name}",
    "pause {task_name}",
    "resume {task_name}",
    "close {task_name}",
}

# explicit status token(s) in template text
LITERAL_STATUS = {
    "mark {task_name} done": "done",
    "mark {task_name} complete": "complete",
    "{task_name} is done": "done",
    "{task_name} completed": "completed",
    "mark {task_name} pending": "pending",
    "set {task_name} in progress": "in progress",
    "{task_name} done now": "done",
    "could you mark {task_name} as complete": "complete",
    "gonna mark {task_name} complete": "complete",
    "mark {task_name} complete right": "complete",
    "bhai {task_name} complete mark kar do": "complete",
    "{task_name} ko done mark kar do": "done",
}


def fix_scheduling_update(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0
    for group in data.get("groups", []):
        for tpl in group.get("templates", []):
            text = tpl.get("text", "")
            if text in TASK_ONLY:
                tpl["entities"] = ["task_name"]
                tpl.pop("literal_entities", None)
                fixed += 1
            elif text in LITERAL_STATUS:
                tpl["entities"] = ["task_name", "new_status"]
                tpl["literal_entities"] = {"new_status": LITERAL_STATUS[text]}
                fixed += 1
            elif text == "move {task_name} to {date}":
                tpl["text"] = "move {task_name} to {new_date}"
                tpl["entities"] = ["task_name", "new_date"]
                tpl.pop("literal_entities", None)
                fixed += 1
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return fixed


def fix_order_variants(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0
    for group in data.get("groups", []):
        for tpl in group.get("templates", []):
            if tpl.get("text") == "move {task_name} to {date}":
                tpl["text"] = "move {task_name} to {new_date}"
                tpl["entities"] = ["task_name", "new_date"]
                tpl["intent"] = "scheduling_update"
                fixed += 1
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return fixed


def fix_learning_create(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0
    for group in data.get("groups", []):
        for tpl in group.get("templates", []):
            if tpl.get("text") == "create a {topic} {subtopic} roadmap starting next week for {duration}":
                tpl["text"] = "create a {topic} {subtopic} roadmap starting {start_date} for {duration}"
                fixed += 1
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return fixed


if __name__ == "__main__":
    n = fix_scheduling_update(ROOT / "templates" / "scheduling" / "scheduling_update.json")
    n += fix_order_variants(ROOT / "templates" / "scheduling" / "order_variants.json")
    n += fix_learning_create(ROOT / "templates" / "learning" / "learning_create.json")
    print(f"Fixed {n} templates")
