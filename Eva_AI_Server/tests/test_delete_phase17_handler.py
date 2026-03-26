"""
Phase 17 tests for scheduling delete handler (Step 5-7 confirmation path).
"""
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, patch

from handlers.scheduling.delete import handle_scheduling_delete


def _base_context():
    return {
        "user_id": "507f1f77bcf86cd799439011",
        "session_id": "69c0c6d79c98840a2697022f",
        "message": "yes",
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


class TestDeletePhase17Handler(unittest.IsolatedAsyncioTestCase):
    async def test_yes_single_deletes_task_with_log_calendar_and_collab_notification(self):
        context = _base_context()
        context["integrations"] = [
            {
                "provider": "google_calendar",
                "is_active": True,
                "access_token": "token123",
                "calendar_id": "primary",
            }
        ]
        context["pending_context"] = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["task1"],
                "tasks": [
                    {
                        "title": "Physics exam",
                        "due_datetime": "2026-03-23T12:35:00",
                        "priority": "high",
                    }
                ],
                "bulk": False,
                "entities": {"task_name": "physics exam"},
            },
        }
        context["pending_reply_type"] = "yes_no"
        context["pending_reply_value"] = "yes"

        task_doc = {
            "_id": "task1",
            "title": "Physics exam",
            "due_datetime": datetime(2026, 3, 23, 12, 35, 0),
            "priority": "high",
            "google_calendar_event_id": "evt_123",
            "collaborators": [
                {"user_id": "collab_accepted", "status": "accepted"},
                {"user_id": "collab_pending", "status": "pending"},
            ],
        }

        with patch(
            "handlers.scheduling.delete.get_task_by_id",
            new=AsyncMock(return_value=task_doc),
        ) as mock_get, patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(return_value=True),
        ) as mock_delete, patch(
            "handlers.scheduling.delete.insert_log",
            new=AsyncMock(return_value="log1"),
        ) as mock_insert_log, patch(
            "handlers.scheduling.delete.google_calendar_client.delete_event",
            new=AsyncMock(return_value=True),
        ) as mock_delete_event, patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete({}, context)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["response_text"], "ACTION:task_deleted")
        self.assertEqual(result["deleted"]["count"], 1)
        self.assertEqual(result["deleted"]["tasks"][0]["title"], "Physics exam")

        self.assertEqual(len(result["notifications"]), 1)
        self.assertEqual(result["notifications"][0]["user_id"], "collab_accepted")
        self.assertEqual(result["notifications"][0]["type"], "task_deleted")

        mock_get.assert_awaited_once_with("task1", context["user_id"])
        mock_delete.assert_awaited_once_with("task1")
        mock_insert_log.assert_awaited_once()
        mock_delete_event.assert_awaited_once_with(
            token="token123",
            calendar_id="primary",
            event_id="evt_123",
        )
        mock_clear.assert_awaited_once_with(context["user_id"])

    async def test_no_single_returns_cancelled_and_clears_context(self):
        context = _base_context()
        context["pending_context"] = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["task1"],
                "tasks": [{"title": "Physics exam"}],
                "bulk": False,
                "entities": {"task_name": "physics exam"},
            },
        }
        context["pending_reply_type"] = "yes_no"
        context["pending_reply_value"] = "no"

        with patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(return_value=True),
        ) as mock_delete, patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete({}, context)

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["response_text"], "ACTION:delete_cancel_single")
        self.assertEqual(result["notifications"], [])
        mock_delete.assert_not_awaited()
        mock_clear.assert_awaited_once_with(context["user_id"])

    async def test_yes_bulk_returns_bulk_success(self):
        context = _base_context()
        context["pending_context"] = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["task1", "task2"],
                "tasks": [
                    {"title": "Physics exam"},
                    {"title": "Physics quiz"},
                ],
                "bulk": True,
                "entities": {"priority": "high"},
            },
        }
        context["pending_reply_type"] = "yes_no"
        context["pending_reply_value"] = "yes"

        task1 = {
            "_id": "task1",
            "title": "Physics exam",
            "due_datetime": datetime(2026, 3, 23, 10, 0, 0),
            "priority": "high",
            "google_calendar_event_id": None,
            "collaborators": [],
        }
        task2 = {
            "_id": "task2",
            "title": "Physics quiz",
            "due_datetime": datetime(2026, 3, 23, 12, 0, 0),
            "priority": "high",
            "google_calendar_event_id": None,
            "collaborators": [],
        }

        with patch(
            "handlers.scheduling.delete.get_task_by_id",
            new=AsyncMock(side_effect=[task1, task2]),
        ), patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(side_effect=[True, True]),
        ), patch(
            "handlers.scheduling.delete.insert_log",
            new=AsyncMock(return_value="log"),
        ), patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete({}, context)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["response_text"], "ACTION:delete_bulk_completed")
        self.assertEqual(result["deleted"]["count"], 2)
        self.assertTrue(result["deleted"]["bulk"])
        mock_clear.assert_awaited_once_with(context["user_id"])

    async def test_yes_with_stale_task_ids_returns_not_found(self):
        context = _base_context()
        context["pending_context"] = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["missing_task"],
                "tasks": [{"title": "Physics exam"}],
                "bulk": False,
                "entities": {"task_name": "physics exam"},
            },
        }
        context["pending_reply_type"] = "yes_no"
        context["pending_reply_value"] = "yes"

        with patch(
            "handlers.scheduling.delete.get_task_by_id",
            new=AsyncMock(return_value=None),
        ), patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete({}, context)

        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["response_text"], "ACTION:delete_not_found")
        mock_clear.assert_awaited_once_with(context["user_id"])


if __name__ == "__main__":
    unittest.main()
