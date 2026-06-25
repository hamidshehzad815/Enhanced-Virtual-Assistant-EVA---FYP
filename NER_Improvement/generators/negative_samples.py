"""
Zero-entity and partial-entity negative samples for NER training.

Teaches the model when NOT to tag — reduces trigger-happy overfitting.
Merged into raw datasets by build_dataset.py (~12% of scheduling, ~12% of learning).
"""

from __future__ import annotations

from typing import Any, Dict, List


def _ex(text: str, intent: str, labels: List[str]) -> Dict[str, Any]:
    tokens = text.split()
    assert len(tokens) == len(labels), f"{text!r}: {len(tokens)} tokens vs {len(labels)} labels"
    return {
        "text": text,
        "intent": intent,
        "tokens": tokens,
        "labels": labels,
        "negative_sample": True,
    }


def scheduling_negatives() -> List[Dict[str, Any]]:
    """All-O or intentionally sparse examples for scheduling NER."""
    items: List[Dict[str, Any]] = [
        # Pure negatives — no entities
        _ex("thanks eva", "scheduling_show", ["O", "O"]),
        _ex("thank you eva", "scheduling_show", ["O", "O", "O"]),
        _ex("what can you do", "scheduling_show", ["O", "O", "O", "O"]),
        _ex("hello eva", "scheduling_show", ["O", "O"]),
        _ex("hey how are you", "scheduling_show", ["O", "O", "O", "O"]),
        _ex("you're the best", "scheduling_show", ["O", "O", "O"]),
        _ex("ok got it", "scheduling_show", ["O", "O", "O"]),
        _ex("sounds good", "scheduling_show", ["O", "O"]),
        _ex("never mind", "scheduling_show", ["O", "O"]),
        _ex("cancel that", "scheduling_show", ["O", "O"]),
        _ex("show my calendar", "scheduling_show", ["O", "O", "O"]),
        _ex("open my schedule", "scheduling_show", ["O", "O", "O"]),
        _ex("what is eva", "scheduling_show", ["O", "O", "O"]),
        _ex("help me please", "scheduling_show", ["O", "O", "O"]),
        _ex("I need help", "scheduling_show", ["O", "O", "O"]),
        _ex("good morning", "scheduling_show", ["O", "O"]),
        _ex("see you later", "scheduling_show", ["O", "O", "O"]),
        _ex("yes please", "scheduling_show", ["O", "O"]),
        _ex("no thanks", "scheduling_show", ["O", "O"]),
        _ex("maybe later", "scheduling_show", ["O", "O"]),
        # Filler words must stay O
        _ex("delete my tasks", "scheduling_delete", ["O", "O", "O"]),
        _ex("remove my schedule", "scheduling_delete", ["O", "O", "O"]),
        _ex("add my task", "scheduling_add", ["O", "O", "O"]),
        _ex("update my tasks", "scheduling_update", ["O", "O", "O"]),
        _ex("show my tasks", "scheduling_show", ["O", "O", "O"]),
        _ex("show all my tasks", "scheduling_show", ["O", "O", "O", "O"]),
        _ex("list my tasks", "scheduling_show", ["O", "O", "O"]),
        _ex("can you help me", "scheduling_show", ["O", "O", "O", "O"]),
        _ex("what tasks do I have", "scheduling_show", ["O", "O", "O", "O", "O"]),
        _ex("do I have anything today", "scheduling_show", ["O", "O", "O", "O", "O"]),
        # Partial — only date, no task_name (my/task stay O)
        _ex("add my task for tomorrow", "scheduling_add", ["O", "O", "O", "O", "B-date"]),
        _ex("schedule my thing on Monday", "scheduling_add", ["O", "O", "O", "O", "B-date"]),
        _ex("add something for today", "scheduling_add", ["O", "O", "O", "B-date"]),
        _ex("remind me tomorrow", "scheduling_add", ["O", "O", "B-date"]),
        _ex("set a task for Friday", "scheduling_add", ["O", "O", "O", "O", "B-date"]),
        # Partial — only time
        _ex("add task at 5pm", "scheduling_add", ["O", "O", "O", "B-time"]),
        _ex("schedule something at noon", "scheduling_add", ["O", "O", "O", "B-time"]),
        # Behavioral with only day (valid sparse)
        _ex("when am I productive", "behavioral", ["O", "O", "O", "O"]),
        _ex("how focused am I", "behavioral", ["O", "O", "O", "O"]),
        _ex("am I productive", "behavioral", ["O", "O", "O"]),
        # with/person boundary — person absent, with is O
        _ex("add exam with friend", "scheduling_add", ["O", "B-task_name", "O", "O"]),
        _ex("schedule meeting with team", "scheduling_add", ["O", "B-task_name", "O", "O"]),
    ]
    return items


def learning_negatives() -> List[Dict[str, Any]]:
    """All-O or sparse examples for learning NER."""
    items: List[Dict[str, Any]] = [
        _ex("thanks eva", "learning_create", ["O", "O"]),
        _ex("what can you do", "learning_create", ["O", "O", "O", "O"]),
        _ex("hello eva", "learning_create", ["O", "O"]),
        _ex("ok got it", "learning_create", ["O", "O", "O"]),
        _ex("sounds good", "learning_create", ["O", "O"]),
        _ex("never mind", "learning_create", ["O", "O"]),
        _ex("help me please", "learning_create", ["O", "O", "O"]),
        _ex("good morning", "learning_create", ["O", "O"]),
        _ex("yes please", "learning_create", ["O", "O"]),
        _ex("no thanks", "learning_create", ["O", "O"]),
        # Delete without topic/subtopic
        _ex("delete my roadmap", "learning_delete", ["O", "O", "O"]),
        _ex("delete my plan", "learning_delete", ["O", "O", "O"]),
        _ex("remove my learning", "learning_delete", ["O", "O", "O"]),
        _ex("cancel my study plan", "learning_delete", ["O", "O", "O", "O"]),
        _ex("delete my study plan", "learning_delete", ["O", "O", "O", "O"]),
        _ex("get rid of my roadmap", "learning_delete", ["O", "O", "O", "O", "O"]),
        _ex("remove my course", "learning_delete", ["O", "O", "O"]),
        # Create without topic
        _ex("create a roadmap", "learning_create", ["O", "O", "O"]),
        _ex("make me a plan", "learning_create", ["O", "O", "O", "O"]),
        _ex("start learning", "learning_create", ["O", "O"]),
        _ex("I want to learn", "learning_create", ["O", "O", "O", "O"]),
        _ex("help me learn", "learning_create", ["O", "O", "O"]),
        # roadmap/session are O when no topic
        _ex("pause my roadmap", "learning_update", ["O", "O", "O"]),
        _ex("skip next session", "learning_update", ["O", "O", "O"]),
        _ex("mark session done", "learning_update", ["O", "O", "O"]),
        # Partial — duration only
        _ex("learn for 2 weeks", "learning_create", ["O", "O", "B-duration", "I-duration"]),
        _ex("study for 30 days", "learning_create", ["O", "O", "B-duration", "I-duration"]),
        # Partial — start_date only
        _ex("start learning today", "learning_create", ["O", "O", "B-start_date"]),
        _ex("begin tomorrow", "learning_create", ["O", "B-start_date"]),
        # with stays O when no person entity intended
        _ex("learn with friend", "learning_create", ["O", "O", "O"]),
        _ex("study with classmates", "learning_create", ["O", "O", "O"]),
    ]
    return items
