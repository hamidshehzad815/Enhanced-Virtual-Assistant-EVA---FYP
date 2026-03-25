"""
Unit tests for quiet-hours helpers used by the scheduling add handler.
"""
import unittest

from handlers.scheduling.add import (
    _find_quiet_hour_matches,
    _normalize_quiet_hour_blocks,
)


class TestQuietHoursHelpers(unittest.TestCase):
    def test_disabled_quiet_hours_return_empty_blocks(self):
        settings = {
            "has_quiet_hours": False,
            "quiet_hours_enabled": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
            "quiet_hours": [],
        }

        self.assertEqual(_normalize_quiet_hour_blocks(settings), [])
        self.assertEqual(_find_quiet_hour_matches(settings, "23:00:00"), [])

    def test_multiple_named_quiet_hour_blocks_supported(self):
        settings = {
            "has_quiet_hours": True,
            "quiet_hours": [
                {"label": "sleep", "start": "22:00", "end": "07:00", "enabled": True},
                {"label": "uni", "start": "09:00", "end": "13:00", "enabled": True},
                {"label": "gym", "start": "18:00", "end": "19:00", "enabled": False},
            ],
        }

        blocks = _normalize_quiet_hour_blocks(settings)

        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["label"], "sleep")
        self.assertEqual(blocks[1]["label"], "uni")

        sleep_matches = _find_quiet_hour_matches(settings, "23:30:00")
        self.assertEqual([item["label"] for item in sleep_matches], ["sleep"])

        uni_matches = _find_quiet_hour_matches(settings, "10:15:00")
        self.assertEqual([item["label"] for item in uni_matches], ["uni"])

        clear_matches = _find_quiet_hour_matches(settings, "15:00:00")
        self.assertEqual(clear_matches, [])

    def test_legacy_single_quiet_hours_window_still_supported(self):
        settings = {
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
            "quiet_hours": [],
        }

        matches_before_midnight = _find_quiet_hour_matches(settings, "23:00:00")
        matches_after_midnight = _find_quiet_hour_matches(settings, "06:30:00")
        non_match = _find_quiet_hour_matches(settings, "14:00:00")

        self.assertEqual(len(matches_before_midnight), 1)
        self.assertEqual(len(matches_after_midnight), 1)
        self.assertEqual(non_match, [])


if __name__ == "__main__":
    unittest.main()
