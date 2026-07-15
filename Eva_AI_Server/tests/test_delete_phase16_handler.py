"""
Phase 16 tests for scheduling delete handler (Step 1-4).
"""
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, patch

from handlers.scheduling.delete import handle_scheduling_delete


def _base_context():
    return {
        "user_id": "507f1f77bcf86cd799439011",
        "session_id": "69c0c6d79c98840a2697022f",
        "message": "delete physics exam",
        "input_type": "text",
        "user": {
            "name": "Hamid",
            "timezone": "Asia/Karachi",
        },
        "history": [],
    }


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


class TestDeletePhase16Handler(unittest.IsolatedAsyncioTestCase):
    async def test_step1_no_entities_sets_free_text_state(self):
        with patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete(
                entities={},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["expected_response"], "free_text")
        self.assertEqual(payload["pending_action"]["intent"], "delete")
        self.assertEqual(payload["pending_action"]["task_ids"], [])
        self.assertEqual(payload["pending_action"]["tasks"], [])
        self.assertFalse(payload["pending_action"]["bulk"])

    async def test_step2_invalid_date_asks_for_date_again(self):
        with patch(
            "handlers.scheduling.delete.duckling_client.resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete(
                entities={"task_name": "physics exam", "date": "funday"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        self.assertEqual(result["pending"]["missing_entity"], "date")
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["expected_response"], "free_text")
        self.assertEqual(payload["missing_entity"], "date")
        self.assertEqual(payload["pending_action"]["entities"]["task_name"], "physics exam")
        self.assertNotIn("date", payload["pending_action"]["entities"])

    async def test_step4_single_match_sets_yes_no_state(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 3, 23, 12, 35, 0),
                "priority": "high",
            }
        ]

        with patch(
            "handlers.scheduling.delete.duckling_client.resolve_date",
            new=AsyncMock(return_value="2026-03-23"),
        ), patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(return_value=one_match),
        ) as mock_find, patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete(
                entities={"task_name": "physics exam", "date": "Monday"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "yes_no")
        self.assertEqual(result["pending"]["task_ids"], ["task1"])

        query_filters = mock_find.await_args.args[1]
        self.assertEqual(query_filters["task_name"], "physics exam")
        self.assertIn("date_range", query_filters)

        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["expected_response"], "yes_no")
        self.assertEqual(payload["pending_action"]["task_ids"], ["task1"])
        self.assertFalse(payload["pending_action"]["bulk"])
        self.assertEqual(payload["pending_action"]["tasks"][0]["title"], "Physics exam")

    async def test_step4_multi_match_sets_number_state(self):
        three_matches = [
            {
                "_id": "id1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 3, 23, 9, 0, 0),
                "priority": "high",
            },
            {
                "_id": "id2",
                "title": "Physics lab",
                "due_datetime": datetime(2026, 3, 23, 10, 0, 0),
                "priority": "high",
            },
            {
                "_id": "id3",
                "title": "Physics quiz",
                "due_datetime": datetime(2026, 3, 23, 11, 0, 0),
                "priority": "high",
            },
        ]

        with patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(return_value=three_matches),
        ), patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete(
                entities={"priority": "high"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "number")
        self.assertEqual(result["pending"]["task_count"], 3)
        self.assertIn("1.", result["response_text"])
        self.assertIn("all", result["response_text"].lower())

        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["expected_response"], "number")
        self.assertEqual(payload["pending_action"]["task_ids"], ["id1", "id2", "id3"])

    async def test_step4_zero_match_returns_not_found_without_state(self):
        with patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete(
                entities={"task_name": "unknown task"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "not_found")
        mock_set.assert_not_awaited()

    async def test_step4_too_broad_returns_no_state(self):
        many_matches = [
            {
                "_id": f"id{index}",
                "title": f"Task {index}",
                "due_datetime": datetime(2026, 3, 23, 8 + index, 0, 0),
                "priority": "medium",
            }
            for index in range(1, 7)
        ]

        with patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(return_value=many_matches),
        ), patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete(
                entities={"status": "pending"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "too_broad")
        mock_set.assert_not_awaited()

    async def test_delete_by_date_and_time_without_task_name(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 7, 15, 9, 0, 0),
                "priority": "medium",
            }
        ]

        with patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(return_value=one_match),
        ) as mock_find, patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete(
                entities={"date": "2026-07-15", "time": "14:00:00"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "yes_no")
        query_filters = mock_find.await_args.args[1]
        self.assertNotIn("task_name", query_filters)
        self.assertIn("date_range", query_filters)


if __name__ == "__main__":
    unittest.main()
