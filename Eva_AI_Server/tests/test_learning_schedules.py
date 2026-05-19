"""Tests for utils/learning_schedules.py."""

import unittest
from unittest.mock import AsyncMock, patch

from utils import learning_schedules as ls


class SchedulesFromSettingsTests(unittest.TestCase):
    def test_modern_labeled_schedules(self):
        settings = {
            "preferred_learning_schedules": [
                {
                    "id": "a",
                    "label": "Morning",
                    "slots": [{"day": 0, "time": "08:00", "duration_minutes": 45}],
                },
            ],
        }
        out = ls.schedules_from_settings(settings)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["label"], "Morning")
        self.assertEqual(out[0]["slots"][0]["duration_minutes"], 45)

    def test_legacy_flat_migrates(self):
        settings = {
            "preferred_learning_schedule": [{"day": 1, "time": "10:00"}],
            "preferred_learning_duration": 75,
        }
        out = ls.schedules_from_settings(settings)
        self.assertEqual(out[0]["id"], "default")
        self.assertEqual(out[0]["slots"][0]["duration_minutes"], 75)


class ResolveScheduleTests(unittest.TestCase):
    def test_single_available_still_prompts_with_timings(self):
        schedules = [
            {
                "id": "s1",
                "label": "Only",
                "slots": [{"day": 0, "time": "09:00", "duration_minutes": 60}],
            },
        ]
        chosen, err, pending = ls.resolve_schedule_for_learning(
            entities={},
            schedules=schedules,
            used_ids=set(),
        )
        self.assertIsNone(chosen)
        self.assertIsNotNone(err)
        self.assertIn("Monday", err)
        self.assertIn("60 min", err)
        self.assertIn("Reply 1", err)
        self.assertIn("Reply 2", err)
        self.assertIsNotNone(pending)
        self.assertEqual(len(pending["pending_action"]["schedule_options"]), 2)

    def test_multiple_available_prompts_choice_with_details(self):
        schedules = [
            {"id": "s1", "label": "Morning", "slots": [{"day": 0, "time": "08:00", "duration_minutes": 60}]},
            {"id": "s2", "label": "Evening", "slots": [{"day": 1, "time": "18:00", "duration_minutes": 90}]},
        ]
        chosen, err, pending = ls.resolve_schedule_for_learning(
            entities={},
            schedules=schedules,
            used_ids=set(),
        )
        self.assertIsNone(chosen)
        self.assertIsNotNone(err)
        self.assertIn("Morning", err)
        self.assertIn("Evening", err)
        self.assertIsNotNone(pending)
        self.assertEqual(pending["expected_response"], "number")
        self.assertEqual(len(pending["pending_action"]["schedule_options"]), 2)

    def test_multiple_options_include_labels_not_only_when_many(self):
        schedules = [
            {"id": "s1", "label": "Morning", "slots": [{"day": 0, "time": "08:00", "duration_minutes": 60}]},
            {"id": "s2", "label": "Evening", "slots": [{"day": 1, "time": "18:00", "duration_minutes": 90}]},
        ]
        _, err, _ = ls.resolve_schedule_for_learning(
            entities={},
            schedules=schedules,
            used_ids=set(),
        )
        self.assertIn("1. Morning", err)
        self.assertIn("2. Evening", err)

    def test_settings_redirect_choice(self):
        self.assertTrue(
            ls.schedule_choice_is_settings_redirect(ls.CHOICE_NEW_SCHEDULE_IN_SETTINGS),
        )

    def test_all_schedules_in_use_errors(self):
        schedules = [
            {"id": "s1", "label": "A", "slots": [{"day": 0, "time": "08:00", "duration_minutes": 60}]},
        ]
        chosen, err, pending = ls.resolve_schedule_for_learning(
            entities={},
            schedules=schedules,
            used_ids={"s1"},
        )
        self.assertIsNone(chosen)
        self.assertIn("Settings", err or "")
        self.assertIsNone(pending)

    def test_parse_schedule_choice_number(self):
        options = [{"id": "s1", "label": "A"}, {"id": "s2", "label": "B"}]
        self.assertEqual(ls.parse_schedule_choice_number("2", options), "s2")
        self.assertIsNone(ls.parse_schedule_choice_number("9", options))

    def test_format_time_12h(self):
        self.assertEqual(ls._format_time_12h("18:00"), "6:00 PM")
        self.assertEqual(ls._format_time_12h("09:30"), "9:30 AM")


class UsedScheduleIdsTests(unittest.IsolatedAsyncioTestCase):
    async def test_collects_from_active_goals(self):
        with patch(
            "utils.learning_schedules.get_active_goals_for_user",
            new=AsyncMock(
                return_value=[
                    {"learning_schedule_id": "s1"},
                    {"learning_schedule_id": None},
                ],
            ),
        ):
            used = await ls.used_learning_schedule_ids("user1")
        self.assertEqual(used, {"s1"})


if __name__ == "__main__":
    unittest.main()
