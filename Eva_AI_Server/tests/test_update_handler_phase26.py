"""
Phase 26 tests for scheduling update handler (STEP 1-5).
"""
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, patch

from handlers.router import route_intent
from handlers.scheduling.update import handle_scheduling_update


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
    }


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


class TestUpdateHandlerPhase26(unittest.IsolatedAsyncioTestCase):
    async def test_step1_missing_identifier_sets_state_identify(self):
        with patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"new_priority": "high"},
                context=_base_context("change priority to high"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        self.assertEqual(result["pending"]["stage"], "identify")
        pending_payload = mock_set.await_args.args[1]
        self.assertEqual(pending_payload["pending_action"]["stage"], "identify")
        self.assertEqual(pending_payload["pending_action"]["entities"]["new_priority"], "high")

    async def test_step5_one_match_without_update_fields_sets_state_what_to_update(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
            }
        ]

        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics exam"},
                context=_base_context("update physics exam"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        self.assertEqual(result["pending"]["stage"], "what_to_update")
        self.assertEqual(result["pending"]["task_id"], "task1")
        pending_payload = mock_set.await_args.args[1]
        self.assertEqual(pending_payload["pending_action"]["stage"], "what_to_update")
        self.assertEqual(pending_payload["pending_action"]["task_id"], "task1")

    async def test_step5_one_match_with_update_fields_moves_to_confirm(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
            }
        ]

        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics exam", "new_priority": "high"},
                context=_base_context("change physics exam priority to high"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "yes_no")
        self.assertEqual(result["pending"]["stage"], "confirm")
        self.assertEqual(result["pending"]["task_id"], "task1")
        self.assertEqual(result["updates"]["priority"], "high")
        pending_payload = mock_set.await_args.args[1]
        self.assertEqual(pending_payload["pending_action"]["stage"], "confirm")

    async def test_step4_two_to_five_matches_sets_state_number(self):
        matches = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
            },
            {
                "_id": "task2",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 2, 12, 0, 0),
                "priority": "high",
                "status": "pending",
            },
        ]
        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=matches),
        ), patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics exam"},
                context=_base_context("update physics exam"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "number")
        self.assertEqual(result["pending"]["stage"], "identify")
        self.assertEqual(result["pending"]["task_count"], 2)
        pending_payload = mock_set.await_args.args[1]
        self.assertEqual(pending_payload["pending_action"]["stage"], "identify")
        self.assertEqual(len(pending_payload["pending_action"]["task_ids"]), 2)

    async def test_step4_no_matches_returns_not_found(self):
        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "calculus exam"},
                context=_base_context("update calculus exam"),
            )

        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["match_count"], 0)
        self.assertEqual(result["response_text"], "ACTION:update_not_found")

    async def test_step4_six_plus_matches_returns_too_broad(self):
        matches = [
            {
                "_id": f"task{index}",
                "title": f"Task {index}",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
            }
            for index in range(1, 8)
        ]
        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=matches),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "task"},
                context=_base_context("update tasks"),
            )

        self.assertEqual(result["status"], "too_broad")
        self.assertEqual(result["match_count"], 7)
        self.assertEqual(result["response_text"], "ACTION:update_too_broad")

    async def test_router_update_intent_uses_update_handler(self):
        mock_result = {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": "ok",
            "notifications": [],
        }
        with patch(
            "handlers.router.handle_scheduling_update",
            new=AsyncMock(return_value=mock_result),
        ) as mock_handler:
            result = await route_intent(
                "update",
                entities={"task_name": "physics exam"},
                context={"user_id": USER_ID, "session_id": SESSION_ID},
            )

        self.assertEqual(result["intent"], "scheduling_update")
        self.assertEqual(result["response_text"], "ok")
        mock_handler.assert_awaited_once()
