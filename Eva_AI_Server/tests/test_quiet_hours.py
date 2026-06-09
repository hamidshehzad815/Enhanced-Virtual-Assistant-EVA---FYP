"""Unit tests for utils/quiet_hours.py."""

import unittest

from utils.quiet_hours import (
    find_learning_slot_quiet_hour_conflicts,
    find_quiet_hour_matches,
    normalize_quiet_hour_blocks,
    window_overlaps_quiet_block,
)


class TestQuietHoursHelpers(unittest.TestCase):
    def test_disabled_quiet_hours_return_empty_blocks(self):
        settings = {
            "has_quiet_hours": False,
            "quiet_hours_enabled": False,
            "quiet_hours": [],
        }
        self.assertEqual(normalize_quiet_hour_blocks(settings), [])
        self.assertEqual(find_quiet_hour_matches(settings, "23:00:00", 60), [])

    def test_start_only_inside_block_matches(self):
        settings = {
            "quiet_hours_enabled": True,
            "quiet_hours": [
                {"label": "uni", "start": "09:00", "end": "13:00", "enabled": True},
            ],
        }
        matches = find_quiet_hour_matches(settings, "10:15:00", 60)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["label"], "uni")

    def test_full_window_overlap_when_start_is_outside(self):
        settings = {
            "quiet_hours_enabled": True,
            "quiet_hours": [
                {"label": "uni", "start": "10:00", "end": "12:00", "enabled": True},
            ],
        }
        matches = find_quiet_hour_matches(settings, "09:30:00", 90)
        self.assertEqual(len(matches), 1)

    def test_no_overlap_when_window_is_clear(self):
        settings = {
            "quiet_hours_enabled": True,
            "quiet_hours": [
                {"label": "sleep", "start": "22:00", "end": "07:00", "enabled": True},
            ],
        }
        self.assertEqual(find_quiet_hour_matches(settings, "15:00:00", 60), [])

    def test_overnight_quiet_block_matches_late_task(self):
        self.assertTrue(window_overlaps_quiet_block(23 * 60, 60, 22 * 60, 7 * 60))

    def test_learning_slot_conflicts_with_quiet_hours(self):
        schedules = [
            {
                "id": "s1",
                "label": "Evening study",
                "slots": [{"day": 1, "time": "22:30", "duration_minutes": 60}],
            },
        ]
        quiet_blocks = [{"label": "sleep", "start": "22:00", "end": "07:00"}]
        conflicts = find_learning_slot_quiet_hour_conflicts(schedules, quiet_blocks)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["schedule_label"], "Evening study")


if __name__ == "__main__":
    unittest.main()
