"""
Phase 27 tests for scheduling update handler (STEP 6-12).
"""
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, patch

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


class TestUpdateHandlerPhase27(unittest.IsolatedAsyncioTestCase):
    async def test_step6_overlap_conflict_sets_state_what_to_update(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 7, 15, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
            }
        ]

        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.check_update_overlap",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ), patch(
            "handlers.scheduling.update._utc_now_naive",
            return_value=datetime(2026, 7, 15, 10, 0, 0),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics exam", "new_time": "6pm"},
                context=_base_context("change physics exam to 6pm"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["stage"], "what_to_update")
        self.assertEqual(result["response_text"], "ACTION:update_overlap_conflict")
        self.assertTrue(mock_set.await_count >= 1)

    async def test_step6_status_backward_blocked_for_completed_task(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Biology assignment",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "complete",
                "duration": 60,
            }
        ]

        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "biology assignment", "new_status": "pending"},
                context=_base_context("mark biology assignment pending"),
            )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["response_text"], "ACTION:update_status_locked")

    async def test_step8_yes_executes_update_and_logs(self):
        context = _base_context("yes")
        context["pending_context"] = {
            "pending_action": {
                "intent": "update",
                "stage": "confirm",
                "task_id": "task1",
                "entities": {"task_id": "task1", "task_name": "Physics exam"},
                "updates": {"priority": "high"},
                "change_summary": "priority from medium to high",
            }
        }
        context["pending_reply_type"] = "yes_no"
        context["pending_reply_value"] = "yes"

        current_task = {
            "_id": "task1",
            "title": "Physics exam",
            "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
            "priority": "medium",
            "status": "pending",
            "duration": 120,
        }
        updated_task = {
            "_id": "task1",
            "title": "Physics exam",
            "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
            "priority": "high",
            "status": "pending",
            "duration": 120,
        }

        with patch(
            "handlers.scheduling.update.get_task_by_id",
            new=AsyncMock(side_effect=[current_task, updated_task]),
        ), patch(
            "handlers.scheduling.update.update_task",
            new=AsyncMock(return_value=True),
        ) as mock_update, patch(
            "handlers.scheduling.update.insert_log",
            new=AsyncMock(return_value="log1"),
        ) as mock_log, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_id": "task1"},
                context=context,
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task"]["priority"], "high")
        self.assertEqual(result["response_text"], "ACTION:task_updated")
        mock_update.assert_awaited_once_with("task1", {"priority": "high"})
        mock_log.assert_awaited_once()

    async def test_step10_calendar_sync_called_when_schedule_changed(self):
        context = _base_context("yes")
        context["integrations"] = [
            {
                "provider": "google_calendar",
                "is_active": True,
                "access_token": "token_1",
                "calendar_id": "primary",
            }
        ]
        context["settings"] = {"google_calendar_sync_enabled": True}
        context["pending_context"] = {
            "pending_action": {
                "intent": "update",
                "stage": "confirm",
                "task_id": "task1",
                "entities": {"task_id": "task1", "task_name": "Physics exam"},
                "updates": {
                    "title": "Physics final",
                    "duration": 90,
                    "due_datetime": "2026-04-02T09:00:00",
                },
                "change_summary": "title, duration, and schedule updated",
            }
        }
        context["pending_reply_type"] = "yes_no"
        context["pending_reply_value"] = "yes"

        current_task = {
            "_id": "task1",
            "title": "Physics exam",
            "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
            "priority": "medium",
            "status": "pending",
            "duration": 120,
            "google_calendar_event_id": "evt_1",
        }
        updated_task = {
            "_id": "task1",
            "title": "Physics final",
            "due_datetime": datetime(2026, 4, 2, 9, 0, 0),
            "priority": "medium",
            "status": "pending",
            "duration": 90,
            "google_calendar_event_id": "evt_1",
        }

        with patch(
            "handlers.scheduling.update.get_task_by_id",
            new=AsyncMock(side_effect=[current_task, updated_task]),
        ), patch(
            "handlers.scheduling.update.update_task",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.update.insert_log",
            new=AsyncMock(return_value="log1"),
        ), patch(
            "handlers.scheduling.update.google_calendar_client.update_event",
            new=AsyncMock(return_value=True),
        ) as mock_calendar_update, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_id": "task1"},
                context=context,
            )

        self.assertEqual(result["status"], "success")
        mock_calendar_update.assert_awaited_once()

    async def test_reschedule_to_past_date_is_rejected(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 7, 15, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
            }
        ]
        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.check_update_overlap",
            new=AsyncMock(return_value=False),
        ) as mock_overlap, patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ), patch(
            "handlers.scheduling.update._utc_now_naive",
            return_value=datetime(2026, 7, 15, 10, 0, 0),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics exam", "new_date": "2026-07-10"},
                context=_base_context("move physics exam to 10 july"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["reason"], "past_datetime")
        self.assertIn("cannot schedule", result["response_text"].lower())
        mock_overlap.assert_not_awaited()
        mock_set.assert_awaited()

    async def test_reschedule_to_past_time_today_is_rejected(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 7, 15, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
            }
        ]
        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.check_update_overlap",
            new=AsyncMock(return_value=False),
        ) as mock_overlap, patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ), patch(
            "handlers.scheduling.update._utc_now_naive",
            return_value=datetime(2026, 7, 15, 11, 0, 0),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics exam", "new_time": "15:00:00"},
                context=_base_context("move physics exam to 3pm"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["reason"], "past_datetime")
        self.assertIn("already passed today", result["response_text"].lower())
        mock_overlap.assert_not_awaited()
        mock_set.assert_awaited()
