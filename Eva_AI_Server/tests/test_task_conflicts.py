"""
Unit tests for task window overlap detection.
"""
import unittest
from datetime import datetime

from db.tasks import task_windows_overlap


class TestTaskWindowConflicts(unittest.TestCase):
    def test_partial_overlap_is_blocked(self):
        existing_start = datetime(2026, 3, 23, 17, 0, 0)
        new_start = datetime(2026, 3, 23, 17, 30, 0)

        self.assertTrue(
            task_windows_overlap(existing_start, 60, new_start, 60)
        )

    def test_same_start_time_is_blocked(self):
        existing_start = datetime(2026, 3, 23, 17, 0, 0)
        new_start = datetime(2026, 3, 23, 17, 0, 0)

        self.assertTrue(
            task_windows_overlap(existing_start, 60, new_start, 45)
        )

    def test_back_to_back_tasks_are_allowed(self):
        existing_start = datetime(2026, 3, 23, 17, 0, 0)
        new_start = datetime(2026, 3, 23, 18, 0, 0)

        self.assertFalse(
            task_windows_overlap(existing_start, 60, new_start, 30)
        )


if __name__ == "__main__":
    unittest.main()
