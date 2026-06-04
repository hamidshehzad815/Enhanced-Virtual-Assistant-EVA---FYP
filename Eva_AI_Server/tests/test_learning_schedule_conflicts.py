"""Tests for utils/learning_schedule_conflicts.py."""

import unittest
from datetime import datetime, timezone

from utils import learning_schedule_conflicts as lsc


class WeeklySlotOverlapTests(unittest.TestCase):
    def test_exact_start_still_overlaps(self):
        due = datetime(2026, 1, 5, 10, 30, tzinfo=timezone.utc)
        self.assertTrue(
            lsc.weekly_slot_overlaps_task(due, 60, 0, "10:30", 60, timezone_name="UTC"),
        )

    def test_partial_overlap_different_start(self):
        due = datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)
        self.assertTrue(
            lsc.weekly_slot_overlaps_task(due, 120, 0, "11:00", 60, timezone_name="UTC"),
        )

    def test_no_overlap_different_weekday(self):
        due = datetime(2026, 1, 6, 10, 30, tzinfo=timezone.utc)
        self.assertFalse(
            lsc.weekly_slot_overlaps_task(due, 60, 0, "10:30", 60, timezone_name="UTC"),
        )

    def test_begginers_not_needed_here(self):
        schedules = [
            {
                "id": "s1",
                "label": "Study",
                "slots": [{"day": 0, "time": "18:00", "duration_minutes": 60}],
            },
        ]
        due = datetime(2026, 1, 5, 18, 15, tzinfo=timezone.utc)
        conflicts = lsc.find_task_conflicts_with_learning_schedules(
            due,
            30,
            schedules,
            timezone_name="UTC",
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["schedule_label"], "Study")


class MapBegginersStyleTests(unittest.TestCase):
    def test_unused_schedule_blocks_task(self):
        settings = {
            "preferred_learning_schedules": [
                {
                    "id": "x",
                    "label": "Python learning2",
                    "slots": [{"day": 1, "time": "18:00", "duration_minutes": 60}],
                },
            ],
        }
        due = datetime(2026, 3, 10, 18, 0, tzinfo=timezone.utc)
        conflicts = lsc.find_task_conflicts_from_settings(
            due,
            120,
            settings,
            timezone_name="UTC",
        )
        self.assertTrue(conflicts)


if __name__ == "__main__":
    unittest.main()
