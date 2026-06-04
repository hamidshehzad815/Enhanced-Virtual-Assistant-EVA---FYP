"""Tests for utils/collaborator_calendar.py."""

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from utils import collaborator_calendar as cc


class FormatMessageTests(unittest.TestCase):
    def test_task_message(self):
        msg = cc.format_collaborator_conflict_message(
            "Ali",
            {"kind": "task", "title": "Exam prep"},
        )
        self.assertIn("Ali", msg)
        self.assertIn("Exam prep", msg)

    def test_learning_plan_message(self):
        msg = cc.format_collaborator_conflict_message(
            "Sara",
            {
                "kind": "learning_schedule",
                "schedule_label": "Evening",
                "slot": {"day": 1, "time": "18:00"},
            },
            for_learning_plan=True,
        )
        self.assertIn("Sara", msg)
        self.assertIn("Evening", msg)


class FindUserCalendarConflictsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_task_conflict_first(self):
        due = datetime(2026, 1, 6, 18, 0, tzinfo=timezone.utc)
        with patch.object(
            cc,
            "find_overlapping_task_for_user",
            new=AsyncMock(return_value={"_id": "t1", "title": "Busy"}),
        ), patch.object(
            cc,
            "fetch_user_settings",
            new=AsyncMock(return_value={"preferred_learning_schedules": []}),
        ):
            out = await cc.find_user_calendar_conflicts("uid", due, 60, timezone_name="UTC")
        self.assertEqual(out["kind"], "task")

    async def test_returns_learning_schedule_when_no_task(self):
        due = datetime(2026, 1, 6, 18, 0, tzinfo=timezone.utc)
        schedules = {
            "preferred_learning_schedules": [
                {
                    "id": "s1",
                    "label": "Study",
                    "slots": [{"day": 1, "time": "18:00", "duration_minutes": 60}],
                },
            ],
        }
        with patch.object(
            cc,
            "find_overlapping_task_for_user",
            new=AsyncMock(return_value=None),
        ), patch.object(
            cc,
            "fetch_user_settings",
            new=AsyncMock(return_value=schedules),
        ):
            out = await cc.find_user_calendar_conflicts("uid", due, 30, timezone_name="UTC")
        self.assertEqual(out["kind"], "learning_schedule")


if __name__ == "__main__":
    unittest.main()
