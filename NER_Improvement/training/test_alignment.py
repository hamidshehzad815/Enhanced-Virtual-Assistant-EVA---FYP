"""
Unit tests for Phase 3 BIO subword alignment.
Run: python -m pytest test_alignment.py -q
Or:  python test_alignment.py
"""

from __future__ import annotations

import sys
from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TRAINING_DIR))

from train_ner import align_labels_with_tokens  # noqa: E402


def test_entity_continuation_gets_i_tag_not_ignored():
    """Multi-subword entity: only first subword was labeled in the buggy version."""
    word_labels = ["O", "B-task_name", "I-task_name", "O"]
    # word 0 = add, word 1 = physics (2 subwords), word 2 = exam, word 3 = on
    word_ids = [None, 0, 1, 1, 2, 3, None]  # [CLS] add physic ##s exam on [SEP]
    label2id = {
        "O": 0,
        "B-task_name": 1,
        "I-task_name": 2,
    }

    aligned = align_labels_with_tokens(word_labels, word_ids, label2id)

    assert aligned[0] == -100  # [CLS]
    assert aligned[1] == 0     # add -> O
    assert aligned[2] == 1     # physic -> B-task_name
    assert aligned[3] == 2     # ##s -> I-task_name  (THE FIX)
    assert aligned[4] == 2     # exam -> I-task_name
    assert aligned[5] == 0     # on -> O
    assert aligned[6] == -100  # [SEP]


def test_o_continuation_stays_ignored():
    word_labels = ["O", "O", "B-date"]
    word_ids = [None, 0, 0, 1, None]  # [CLS] ad ##d monday [SEP]
    label2id = {"O": 0, "B-date": 1, "I-date": 2}

    aligned = align_labels_with_tokens(word_labels, word_ids, label2id)

    assert aligned[1] == 0
    assert aligned[2] == -100  # continuation of O word still ignored


def test_b_continuation_becomes_i():
    word_labels = ["B-topic"]
    word_ids = [None, 0, 0, None]  # JavaScript -> Java ##Script
    label2id = {"O": 0, "B-topic": 1, "I-topic": 2}

    aligned = align_labels_with_tokens(word_labels, word_ids, label2id)

    assert aligned[1] == 1  # B-topic
    assert aligned[2] == 2  # I-topic (from B-topic continuation)


if __name__ == "__main__":
    test_entity_continuation_gets_i_tag_not_ignored()
    test_o_continuation_stays_ignored()
    test_b_continuation_becomes_i()
    print("All alignment tests passed.")
