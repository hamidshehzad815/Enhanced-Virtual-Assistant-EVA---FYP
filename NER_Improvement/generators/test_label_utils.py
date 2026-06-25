"""Tests for literal entity span assignment."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from label_utils import build_example


def test_literal_new_status():
    ex = build_example(
        "mark {task_name} complete",
        ["task_name", "new_status"],
        {"task_name": "physics exam"},
        {"new_status": "complete"},
    )
    assert ex["text"] == "mark physics exam complete"
    assert ex["labels"] == [
        "O",
        "B-task_name",
        "I-task_name",
        "B-new_status",
    ]


def test_task_only_status_verb():
    ex = build_example(
        "complete {task_name}",
        ["task_name"],
        {"task_name": "physics exam"},
    )
    assert ex["labels"] == ["O", "B-task_name", "I-task_name"]
