"""
Phase 31 tests for behavioral handler core flow.
"""
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, patch

from handlers.behavioral.behavioral import _detect_sub_intent, handle_behavioral
from utils.date_utils import hour_to_12h_format, weekday_name_to_number


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
            "analytics_min_tasks_threshold": 10,
        },
        "history": [],
    }


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


class TestBehavioralHandlerPhase31(unittest.IsolatedAsyncioTestCase):
    async def test_not_enough_data_returns_early(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=3),
        ), patch(
            "handlers.behavioral.behavioral.get_hours_distribution",
            new=AsyncMock(return_value=[]),
        ) as mock_hours, patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral({}, _base_context("when am i most productive"))

        self.assertEqual(result["status"], "not_enough_data")
        self.assertEqual(result["response_text"], "ACTION:behavioral_not_enough_data")
        mock_hours.assert_not_awaited()

    async def test_best_time_without_day_sets_pending_context(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set_context, patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral({}, _base_context("find the best time for me"))

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["sub_intent"], "best_time_for_day")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        self.assertEqual(result["response_text"], "ACTION:behavioral_ask_day")
        mock_set_context.assert_awaited_once()

    async def test_productive_hours_with_day_filter(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_hours_distribution",
            new=AsyncMock(
                return_value=[
                    {"hour": 18, "count": 7, "on_time_rate": 0.86},
                    {"hour": 10, "count": 5, "on_time_rate": 0.8},
                ]
            ),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {"day": "monday"},
                _base_context("what are my best hours on monday"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "productive_hours")
        self.assertEqual(result["response_text"], "ACTION:behavioral_productive_hours")
        self.assertEqual(len(result["analytics"]["top_hours"]), 2)

    async def test_productive_hours_general(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_hours_distribution",
            new=AsyncMock(
                return_value=[
                    {"hour": 18, "count": 7, "on_time_rate": 0.86},
                    {"hour": 10, "count": 5, "on_time_rate": 0.8},
                ]
            ),
        ) as mock_hours, patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {},
                _base_context("when am i most productive"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "productive_hours")
        self.assertEqual(result["response_text"], "ACTION:behavioral_productive_hours")
        mock_hours.assert_awaited_once_with(USER_ID, None)

    async def test_productive_hours_with_day_filter_no_data(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_hours_distribution",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {"day": "monday"},
                _base_context("what are my best hours on monday"),
            )

        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["sub_intent"], "productive_hours")
        self.assertEqual(result["response_text"], "ACTION:behavioral_no_data_for_filter")

    async def test_productive_days_ranked(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_days_distribution",
            new=AsyncMock(
                return_value=[
                    {"day_name": "Tuesday", "day_num": 1, "count": 10, "on_time_rate": 0.9},
                    {"day_name": "Thursday", "day_num": 3, "count": 8, "on_time_rate": 0.75},
                    {"day_name": "Monday", "day_num": 0, "count": 6, "on_time_rate": 0.5},
                ]
            ),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {},
                _base_context("which days am i most focused"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "productive_days")
        self.assertEqual(result["response_text"], "ACTION:behavioral_productive_days")
        self.assertEqual(result["analytics"]["days"][0]["day_name"], "Tuesday")

    async def test_productive_days_with_some_zero_days(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_days_distribution",
            new=AsyncMock(
                return_value=[
                    {"day_name": "Monday", "day_num": 0, "count": 3, "on_time_rate": 0.67},
                    {"day_name": "Tuesday", "day_num": 1, "count": 0, "on_time_rate": 0.0},
                    {"day_name": "Wednesday", "day_num": 2, "count": 0, "on_time_rate": 0.0},
                ]
            ),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {},
                _base_context("what are my best days"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "productive_days")

    async def test_best_time_for_day_applies_conflict_check(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_hours_distribution",
            new=AsyncMock(
                return_value=[
                    {"hour": 18, "count": 8, "on_time_rate": 0.9},
                    {"hour": 10, "count": 6, "on_time_rate": 0.8},
                ]
            ),
        ), patch(
            "handlers.behavioral.behavioral.get_tasks_for_day",
            new=AsyncMock(
                return_value=[
                    {
                        "due_datetime": datetime(2026, 4, 13, 18, 30, 0),
                        "duration": 60,
                    }
                ]
            ),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {"day": "monday"},
                _base_context("find the best time for me on monday"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "best_time_for_day")
        self.assertEqual(result["response_text"], "ACTION:behavioral_best_time")
        self.assertEqual(result["analytics"]["best_hour"], 10)
        self.assertTrue(result["analytics"]["conflict_free"])

    async def test_best_time_for_day_present_no_conflict_stays_best_hour(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_hours_distribution",
            new=AsyncMock(
                return_value=[
                    {"hour": 18, "count": 8, "on_time_rate": 0.9},
                    {"hour": 10, "count": 6, "on_time_rate": 0.8},
                ]
            ),
        ), patch(
            "handlers.behavioral.behavioral.get_tasks_for_day",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {"day": "tuesday"},
                _base_context("find the best time for me on tuesday"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "best_time_for_day")
        self.assertEqual(result["analytics"]["best_hour"], 18)
        self.assertTrue(result["analytics"]["conflict_free"])

    async def test_completion_rate_flow(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_completion_rate",
            new=AsyncMock(
                return_value={
                    "total_completed": 20,
                    "on_time": 15,
                    "late": 5,
                    "on_time_rate": 75.0,
                    "weekly_trend": [{"week": 14, "count": 4}, {"week": 15, "count": 6}],
                }
            ),
        ), patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {},
                _base_context("show my completion rate"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "completion_rate")
        self.assertEqual(result["response_text"], "ACTION:behavioral_completion_rate")
        self.assertEqual(result["analytics"]["completion_rate"]["total_completed"], 20)
        self.assertEqual(result["analytics"]["completion_rate"]["on_time_rate"], 75.0)
        self.assertEqual(
            result["analytics"]["completion_rate"]["weekly_trend"],
            [{"week": 14, "count": 4}, {"week": 15, "count": 6}],
        )

    async def test_productivity_report_combines_all_queries(self):
        with patch(
            "handlers.behavioral.behavioral.count_completed",
            new=AsyncMock(return_value=20),
        ), patch(
            "handlers.behavioral.behavioral.get_hours_distribution",
            new=AsyncMock(return_value=[{"hour": 18, "count": 7, "on_time_rate": 0.86}]),
        ) as mock_hours, patch(
            "handlers.behavioral.behavioral.get_days_distribution",
            new=AsyncMock(return_value=[{"day_name": "Tuesday", "day_num": 1, "count": 9, "on_time_rate": 0.78}]),
        ) as mock_days, patch(
            "handlers.behavioral.behavioral.get_completion_rate",
            new=AsyncMock(
                return_value={
                    "total_completed": 20,
                    "on_time": 15,
                    "late": 5,
                    "on_time_rate": 75.0,
                    "weekly_trend": [{"week": 14, "count": 4}],
                }
            ),
        ) as mock_completion, patch(
            "handlers.behavioral.behavioral.get_avg_time_taken",
            new=AsyncMock(return_value=82.5),
        ) as mock_avg, patch(
            "handlers.behavioral.behavioral.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.behavioral.behavioral._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_behavioral(
                {},
                _base_context("show my productivity report"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sub_intent"], "productivity_report")
        self.assertEqual(result["response_text"], "ACTION:behavioral_productivity_report")
        self.assertEqual(result["analytics"]["completion_rate"]["total_completed"], 20)
        self.assertEqual(result["analytics"]["avg_time_taken"], 82.5)
        mock_hours.assert_awaited_once()
        mock_days.assert_awaited_once()
        mock_completion.assert_awaited_once()
        mock_avg.assert_awaited_once()

    def test_sub_intent_detection_all_five_paths(self):
        self.assertEqual(_detect_sub_intent("find the best time for me on monday"), "best_time_for_day")
        self.assertEqual(_detect_sub_intent("show my completion rate"), "completion_rate")
        self.assertEqual(_detect_sub_intent("show my productivity report"), "productivity_report")
        self.assertEqual(_detect_sub_intent("which days am i most focused"), "productive_days")
        self.assertEqual(_detect_sub_intent("when am i most productive"), "productive_hours")

    def test_behavioral_date_util_helpers_edge_cases(self):
        self.assertEqual(hour_to_12h_format(0), "12AM")
        self.assertEqual(hour_to_12h_format(12), "12PM")
        self.assertEqual(hour_to_12h_format(23), "11PM")
        self.assertIsNone(hour_to_12h_format(24))

        self.assertEqual(weekday_name_to_number("monday"), 0)
        self.assertEqual(weekday_name_to_number("SUNDAY"), 6)
        self.assertIsNone(weekday_name_to_number("noday"))


if __name__ == "__main__":
    unittest.main()
