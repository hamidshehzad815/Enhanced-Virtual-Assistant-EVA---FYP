"""
Unit tests for task priority/status normalization helpers.
"""
import unittest

from utils.task_value_normalizer import canonicalize_priority, canonicalize_status


class TestTaskValueNormalizer(unittest.TestCase):
    def test_priority_aliases_map_to_canonical_values(self):
        self.assertEqual(canonicalize_priority("urgent"), "high")
        self.assertEqual(canonicalize_priority("critical"), "high")
        self.assertEqual(canonicalize_priority("normal"), "medium")
        self.assertEqual(canonicalize_priority("moderate"), "medium")
        self.assertEqual(canonicalize_priority("backburner"), "low")
        self.assertEqual(canonicalize_priority("optional"), "low")

    def test_status_aliases_map_to_canonical_values(self):
        self.assertEqual(canonicalize_status("in progress"), "ongoing")
        self.assertEqual(canonicalize_status("in-progress"), "ongoing")
        self.assertEqual(canonicalize_status("active"), "ongoing")
        self.assertEqual(canonicalize_status("completed"), "complete")
        self.assertEqual(canonicalize_status("done"), "complete")
        self.assertEqual(canonicalize_status("resolved"), "complete")

    def test_invalid_values_return_empty(self):
        self.assertEqual(canonicalize_priority("random"), "")
        self.assertEqual(canonicalize_status("random"), "")


if __name__ == "__main__":
    unittest.main()

