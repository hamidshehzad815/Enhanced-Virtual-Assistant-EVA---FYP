"""
Phase 8 tests for behavioral handler scoring-based flow.
"""
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, patch

from handlers.behavioral.behavioral import _detect_sub_intent, handle_behavioral


USER_ID = "507f1f77bcf86cd799439011"
SESSION_ID = "69c0c6d79c98840a2697022f"


def _base_context(message: str) -> dict:
    return {
        "user_id": USER_ID,
        "session_id": SESSION_ID,
        "message": message,
        "input_type": "text",
        "user": {
            "name": "Hamid",
            "timezone": "Asia/Karachi",
        },
        "settings": {
            "analytics_min_tasks_threshold": 20,
            "analytics_min_tasks_per_day": 5,
        },
        "history": [],
    }


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


class TestBehavioralHandlerPhase8(unittest.IsolatedAsyncioTestCase):
    async def test_below_global_threshold_returns_not_enough_data(self):
        with patch(
            "handlers.behavioral.behavioral.get_total_completed",
            new=AsyncMock(return_value=9),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral({}, _base_context("when am i most productive"))

        self.assertEqual(result["status"], "not_enough_data")
        self.assertEqual(result["sub_intent"], "productive_hours")
        self.assertEqual(result["response_text"], "ACTION:behavioral_not_enough_data")

    async def test_productive_hours_uses_ranges_and_reliable_data(self):
        with patch(
            "handlers.behavioral.behavioral.get_total_completed",
            new=AsyncMock(return_value=30),
        ), patch(
            "handlers.behavioral.behavioral.get_completed_logs_for_scoring",
            new=AsyncMock(return_value=[{"day_of_week": 0, "hour_of_day": 18, "was_on_time": True, "action_timestamp": datetime(2026, 4, 1)}]),
        ), patch(
            "handlers.behavioral.behavioral.get_log_count_per_day",
            new=AsyncMock(return_value={0: 8, 1: 6, 2: 2, 3: 0, 4: 0, 5: 0, 6: 0}),
        ), patch(
            "handlers.behavioral.behavioral.get_productive_days",
            return_value={
                "reliable": [
                    {"day": "Monday", "day_num": 0, "score": 0.9, "log_count": 8, "on_time_rate": 0.9},
                    {"day": "Tuesday", "day_num": 1, "score": 0.85, "log_count": 6, "on_time_rate": 0.88},
                ],
                "unreliable": [],
            },
        ), patch(
            "handlers.behavioral.behavioral.get_best_time_for_day",
            side_effect=[
                {"best_range": "6PM-9PM", "start_hour": 18, "conflict_free": True, "day": "Monday", "day_num": 0, "score": 0.9},
                {"best_range": "4PM-6PM", "start_hour": 16, "conflict_free": True, "day": "Tuesday", "day_num": 1, "score": 0.85},
            ],
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral({}, _base_context("when am i most productive"))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "productive_hours")
        self.assertEqual(result["response_text"], "ACTION:behavioral_productive_hours")
        self.assertEqual(result["analytics"]["top_ranges"], ["Monday 6PM-9PM", "Tuesday 4PM-6PM"])

    async def test_productive_hours_day_filter_with_insufficient_day_data(self):
        with patch(
            "handlers.behavioral.behavioral.get_total_completed",
            new=AsyncMock(return_value=30),
        ), patch(
            "handlers.behavioral.behavioral.get_completed_logs_for_scoring",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.behavioral.behavioral.get_log_count_per_day",
            new=AsyncMock(return_value={0: 3, 1: 8, 2: 8, 3: 8, 4: 8, 5: 8, 6: 8}),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral({"day": "monday"}, _base_context("what are my best hours on monday"))

        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["sub_intent"], "productive_hours")
        self.assertEqual(result["response_text"], "ACTION:behavioral_no_data_for_filter")

    async def test_productive_days_returns_reliable_and_unreliable(self):
        with patch(
            "handlers.behavioral.behavioral.get_total_completed",
            new=AsyncMock(return_value=30),
        ), patch(
            "handlers.behavioral.behavioral.get_completed_logs_for_scoring",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.behavioral.behavioral.get_log_count_per_day",
            new=AsyncMock(return_value={0: 8, 1: 6, 2: 2, 3: 1, 4: 0, 5: 0, 6: 0}),
        ), patch(
            "handlers.behavioral.behavioral.get_productive_days",
            return_value={
                "reliable": [
                    {"day": "Monday", "day_num": 0, "score": 0.9, "log_count": 8, "on_time_rate": 0.9},
                    {"day": "Tuesday", "day_num": 1, "score": 0.85, "log_count": 6, "on_time_rate": 0.88},
                ],
                "unreliable": [
                    {"day": "Wednesday", "day_num": 2, "log_count": 2, "needed": 5},
                ],
            },
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral({}, _base_context("which days am i most focused"))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "productive_days")
        self.assertTrue(result["response_text"].startswith("ACTION:behavioral_productive_days"))
        self.assertEqual(len(result["analytics"]["days"]), 2)
        self.assertEqual(result["analytics"]["unreliable_days"][0]["day"], "Wednesday")

    async def test_best_time_for_day_conflict_free_range(self):
        with patch(
            "handlers.behavioral.behavioral.get_total_completed",
            new=AsyncMock(return_value=30),
        ), patch(
            "handlers.behavioral.behavioral.get_completed_logs_for_scoring",
            new=AsyncMock(return_value=[{"day_of_week": 0, "hour_of_day": 18, "was_on_time": True, "action_timestamp": datetime(2026, 4, 1)}]),
        ), patch(
            "handlers.behavioral.behavioral.get_log_count_per_day",
            new=AsyncMock(return_value={0: 8, 1: 8, 2: 8, 3: 8, 4: 8, 5: 8, 6: 8}),
        ), patch(
            "handlers.behavioral.behavioral.get_tasks_for_day",
            new=AsyncMock(return_value=[{"due_datetime": datetime(2026, 4, 14, 18, 0), "duration": 60}]),
        ) as mock_tasks, patch(
            "handlers.behavioral.behavioral.get_best_time_for_day",
            return_value={
                "day": "Monday",
                "day_num": 0,
                "best_range": "7PM-9PM",
                "start_hour": 19,
                "score": 0.82,
                "conflict_free": True,
            },
        ) as mock_best, patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral({"day": "monday"}, _base_context("find the best time on monday"))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "best_time_for_day")
        self.assertEqual(result["response_text"], "ACTION:behavioral_best_time")
        self.assertEqual(result["analytics"]["best_range"], "7PM-9PM")
        self.assertTrue(result["analytics"]["conflict_free"])
        mock_tasks.assert_awaited_once()
        mock_best.assert_called_once()

    def test_sub_intent_detection(self):
        self.assertEqual(_detect_sub_intent("find the best time for me on monday"), "best_time_for_day")
        self.assertEqual(_detect_sub_intent("show my completion rate"), "completion_rate")
        self.assertEqual(_detect_sub_intent("show my productivity report"), "productivity_report")
        self.assertEqual(_detect_sub_intent("which days am i most focused"), "productive_days")
        self.assertEqual(_detect_sub_intent("when am i most productive"), "productive_hours")


if __name__ == "__main__":
    unittest.main()

