"""
Phase 6 tests for scheduling add behavioral time suggestion flow.
"""
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, patch

from handlers.scheduling.add import handle_scheduling_add


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
        "history": [],
        "integrations": [],
        "settings": {
            "default_task_duration": 120,
            "default_task_priority": "medium",
            "default_reminder_minutes": 30,
            "behavioral_analytics_enabled": True,
        },
    }


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


class TestAddHandlerPhase6(unittest.IsolatedAsyncioTestCase):
    async def test_time_missing_with_sufficient_data_shows_range_suggestion(self):
        context = _base_context("add physics exam on 2099-01-05")

        with patch(
            "handlers.scheduling.add.get_total_completed",
            new=AsyncMock(return_value=25),
        ), patch(
            "handlers.scheduling.add.get_log_count_per_day",
            new=AsyncMock(return_value={0: 6, 1: 6, 2: 6, 3: 6, 4: 6, 5: 6, 6: 6}),
        ), patch(
            "handlers.scheduling.add.get_completed_logs_for_scoring",
            new=AsyncMock(return_value=[{"day_of_week": 0, "hour_of_day": 18}]),
        ), patch(
            "handlers.scheduling.add.get_tasks_for_day",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.scheduling.add.get_scheduling_suggestion",
            return_value={"best_range": "6PM-9PM", "start_hour": 18},
        ), patch(
            "handlers.scheduling.add.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set_context, patch(
            "handlers.scheduling.add._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_add(
                entities={"task_name": "physics exam", "date": "2099-01-05"},
                context=context,
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "number")
        self.assertEqual(result["pending"]["missing_entity"], "time")
        self.assertEqual(result["pending"]["suggested_range"], "6PM-9PM")
        self.assertEqual(result["pending"]["suggested_time"], "18:00:00")
        self.assertIn("best window", result["response_text"].lower())
        self.assertIn("6PM-9PM", result["response_text"])
        self.assertTrue(mock_set_context.awaited)

    async def test_time_missing_with_analytics_disabled_skips_suggestion(self):
        context = _base_context("add physics exam on 2099-01-05")
        context["settings"]["behavioral_analytics_enabled"] = False

        with patch(
            "handlers.scheduling.add.get_total_completed",
            new=AsyncMock(return_value=25),
        ) as mock_total, patch(
            "handlers.scheduling.add.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.add.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.add._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_add(
                entities={"task_name": "physics exam", "date": "2099-01-05"},
                context=context,
            )

        mock_total.assert_not_awaited()
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        self.assertEqual(result["pending"]["missing_entity"], "time")
        self.assertEqual(result["response_text"], "ACTION:missing_time")

    async def test_time_missing_with_insufficient_data_falls_back_to_manual_time(self):
        context = _base_context("add physics exam on 2099-01-05")

        with patch(
            "handlers.scheduling.add.get_total_completed",
            new=AsyncMock(return_value=3),
        ), patch(
            "handlers.scheduling.add.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.add.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.add._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_add(
                entities={"task_name": "physics exam", "date": "2099-01-05"},
                context=context,
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        self.assertEqual(result["pending"]["missing_entity"], "time")
        self.assertEqual(result["response_text"], "ACTION:missing_time")

    async def test_pick_option_1_uses_suggested_time_and_sets_behavioral_scheduled_by(self):
        context = _base_context("1")
        context["pending_context"] = {
            "pending_action": {
                "intent": "add",
                "entities": {
                    "task_name": "physics exam",
                    "date": "2099-01-05",
                },
            },
            "pending_reason": "time_suggestion",
            "suggested_range": "6PM-9PM",
            "suggested_time": "18:00:00",
        }
        context["pending_reply_type"] = "number"
        context["pending_reply_value"] = "1"

        with patch(
            "handlers.scheduling.add.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.add.local_datetime_to_utc_naive",
            return_value=datetime(2099, 1, 5, 13, 0, 0),
        ) as mock_to_utc, patch(
            "handlers.scheduling.add.find_overlapping_task_for_user",
            new=AsyncMock(return_value=None),
        ), patch(
            "handlers.scheduling.add.find_duplicate",
            new=AsyncMock(return_value=None),
        ), patch(
            "handlers.scheduling.add._find_and_validate_collaborators",
            new=AsyncMock(return_value=([], None)),
        ), patch(
            "handlers.scheduling.add.insert_task",
            new=AsyncMock(return_value="task_1"),
        ), patch(
            "handlers.scheduling.add.insert_log",
            new=AsyncMock(return_value="log_1"),
        ), patch(
            "handlers.scheduling.add.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.add._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_add(
                entities={},
                context=context,
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task"]["scheduled_by"], "behavioral_analytics")
        self.assertTrue(mock_to_utc.called)
        call_args = mock_to_utc.call_args.args
        self.assertGreaterEqual(len(call_args), 3)
        self.assertEqual(call_args[1], "18:00:00")

    async def test_pick_option_2_asks_for_manual_time(self):
        context = _base_context("2")
        context["pending_context"] = {
            "pending_action": {
                "intent": "add",
                "entities": {
                    "task_name": "physics exam",
                    "date": "2099-01-05",
                },
            },
            "pending_reason": "time_suggestion",
            "suggested_range": "6PM-9PM",
            "suggested_time": "18:00:00",
        }
        context["pending_reply_type"] = "number"
        context["pending_reply_value"] = "2"

        with patch(
            "handlers.scheduling.add.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set_context, patch(
            "handlers.scheduling.add.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.add._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_add(
                entities={},
                context=context,
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        self.assertEqual(result["pending"]["missing_entity"], "time")
        self.assertEqual(result["response_text"], "ACTION:missing_time")
        self.assertTrue(mock_set_context.awaited)
        saved_context = mock_set_context.await_args.args[1]
        self.assertEqual(saved_context["expected_response"], "free_text")
        self.assertNotIn("suggested_range", saved_context)
        self.assertNotIn("suggested_time", saved_context)


if __name__ == "__main__":
    unittest.main()
