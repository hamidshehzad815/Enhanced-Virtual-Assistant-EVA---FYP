"""Tests for Phase 5 balance utilities."""

import unittest

from balance_utils import (
    count_examples_per_entity,
    merge_unique_examples,
    oversample_entities,
)


class BalanceTests(unittest.TestCase):
    def test_oversample_increases_rare_entity(self):
        examples = [
            {
                "text": "mark physics exam as complete",
                "tokens": ["mark", "physics", "exam", "as", "complete"],
                "labels": ["O", "B-task_name", "I-task_name", "O", "B-new_status"],
                "intent": "scheduling_update",
            },
            {
                "text": "add physics exam on Monday",
                "tokens": ["add", "physics", "exam", "on", "Monday"],
                "labels": ["O", "B-task_name", "I-task_name", "O", "B-date"],
                "intent": "scheduling_add",
            },
        ]
        result, plan = oversample_entities(
            examples,
            priority_entities=["new_status"],
            target_pct=1.0,
            max_oversample=10,
            seed=0,
        )
        self.assertGreater(len(result), len(examples))
        self.assertIn("new_status", plan)

    def test_merge_dedupes_text(self):
        a = [{"text": "x", "tokens": ["x"], "labels": ["O"]}]
        b = [{"text": "x", "tokens": ["x"], "labels": ["O"]}]
        c = [{"text": "y", "tokens": ["y"], "labels": ["O"]}]
        merged = merge_unique_examples([a, b, c])
        self.assertEqual(len(merged), 2)

    def test_count_entities(self):
        ex = [
            {
                "labels": ["O", "B-task_name", "I-task_name", "B-date"],
            }
        ]
        counts = count_examples_per_entity(ex)
        self.assertEqual(counts["task_name"], 1)
        self.assertEqual(counts["date"], 1)


if __name__ == "__main__":
    unittest.main()
