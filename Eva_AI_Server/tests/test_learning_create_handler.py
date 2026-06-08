"""
Unit tests for handlers.learning.create (mocked DB / Redis / calendar).
"""

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from handlers.learning.create import handle_learning_create


def _ctx(**kwargs):
    base = {
        "user_id": "507f1f77bcf86cd799439011",
        "session_id": "sess1",
        "user": {"name": "Test", "timezone": "UTC"},
        "settings": {
            "preferred_learning_schedules": [
                {
                    "id": "default",
                    "label": "Default",
                    "slots": [{"day": 0, "time": "09:00", "duration_minutes": 60}],
                },
            ],
            "default_reminder_minutes": 30,
            "default_learning_reminder_minutes": 15,
        },
        "history": [],
        "integrations": [],
        "message": "learn Python basics in 2 weeks starting Monday",
        "input_type": "text",
    }
    base.update(kwargs)
    return base


class LearningCreateHandlerTests(unittest.IsolatedAsyncioTestCase):
    # Keep dates safely in the future relative to real execution time.
    _FUTURE_START = "2026-06-10"

    async def test_topic_missing_sets_redis_and_pending(self):
        mock_redis = AsyncMock(return_value=True)
        with (
            patch(
                "handlers.learning.create.redis_client.set_context",
                mock_redis,
            ),
            patch(
                "handlers.learning.create.gemini_service.generate_reply",
                return_value="What topic?",
            ),
        ):
            out = await handle_learning_create({}, _ctx())
        self.assertEqual(out["status"], "pending")
        mock_redis.assert_awaited()
        call_kw = mock_redis.call_args[0][1]
        self.assertEqual(call_kw["pending_action"]["stage"], "topic")

    async def test_start_date_missing_sets_redis(self):
        mock_redis = AsyncMock(return_value=True)
        with (
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.redis_client.set_context",
                mock_redis,
            ),
            patch(
                "handlers.learning.create.gemini_service.generate_reply",
                return_value="When to start?",
            ),
        ):
            out = await handle_learning_create(
                {"topic": "Python", "subtopic": "basics"},
                _ctx(),
            )
        self.assertEqual(out["status"], "pending")
        self.assertEqual(mock_redis.call_args[0][1]["pending_action"]["stage"], "start_date")

    async def test_duration_missing_sets_redis(self):
        mock_redis = AsyncMock(return_value=True)
        with (
            patch(
                "handlers.learning.create.used_learning_schedule_ids",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.redis_client.set_context",
                mock_redis,
            ),
            patch(
                "handlers.learning.create.gemini_service.generate_reply",
                return_value="How long?",
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "start_date": self._FUTURE_START,
                    "learning_schedule_id": "default",
                },
                _ctx(),
            )
        self.assertEqual(out["status"], "pending")
        self.assertEqual(mock_redis.call_args[0][1]["pending_action"]["stage"], "duration")

    async def test_not_feasible_sessions_returns_pending_message(self):
        with (
            patch(
                "handlers.learning.create.used_learning_schedule_ids",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.get_sessions_required",
                new=AsyncMock(return_value=20),
            ),
            patch(
                "handlers.learning.create.calculate_available_sessions",
                return_value=2,
            ),
            patch(
                "handlers.learning.create.gemini_service.generate_reply",
                return_value="",
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "start_date": self._FUTURE_START,
                    "duration_days": 14,
                    "learning_schedule_id": "default",
                },
                _ctx(),
            )
        self.assertEqual(out["status"], "pending")
        self.assertIn("20", out["response_text"])
        self.assertIn("2", out["response_text"])

    async def test_collaborator_validation_error_stops(self):
        with (
            patch(
                "handlers.learning.create.used_learning_schedule_ids",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.get_sessions_required",
                new=AsyncMock(return_value=2),
            ),
            patch(
                "handlers.learning.create._find_and_validate_collaborators",
                new=AsyncMock(return_value=([], "That user is not on EVA yet.")),
            ),
            patch(
                "handlers.learning.create.gemini_service.generate_reply",
                return_value="",
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "start_date": self._FUTURE_START,
                    "duration_days": 14,
                    "learning_schedule_id": "default",
                    "person": "ghost_user",
                },
                _ctx(),
            )
        self.assertEqual(out["status"], "error")
        self.assertIn("not on EVA", out["response_text"])

    async def test_schedule_build_mismatch_returns_pending(self):
        topics = [
            {"order": 1, "title": "A", "resources": []},
            {"order": 2, "title": "B", "resources": []},
        ]
        with (
            patch(
                "handlers.learning.create.used_learning_schedule_ids",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.get_roadmap",
                new=AsyncMock(return_value=topics),
            ),
            patch(
                "handlers.learning.create.get_sessions_required",
                new=AsyncMock(return_value=2),
            ),
            patch(
                "handlers.learning.create.build_schedule",
                return_value=[
                    {
                        "order": 1,
                        "title": "A",
                        "resources": [],
                        "scheduled_date": datetime(2026, 6, 1, 9, 0, 0),
                    }
                ],
            ),
            patch(
                "handlers.learning.create.find_overlapping_task_for_user",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.gemini_service.generate_reply",
                return_value="",
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "start_date": self._FUTURE_START,
                    "duration_days": 14,
                    "learning_schedule_id": "default",
                },
                _ctx(),
            )
        self.assertEqual(out["status"], "pending")
        self.assertIn("couldn't fit", out["response_text"].lower())

    async def test_requires_learning_schedule(self):
        out = await handle_learning_create(
            {"topic": "Python", "start_date": self._FUTURE_START, "duration_days": 14},
            _ctx(settings={}),
        )
        self.assertEqual(out["status"], "pending")
        self.assertIn("Settings", out["response_text"])

    async def test_single_schedule_prompts_choice_before_duration(self):
        mock_redis = AsyncMock(return_value=True)
        with (
            patch(
                "handlers.learning.create.used_learning_schedule_ids",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.redis_client.set_context",
                mock_redis,
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "start_date": self._FUTURE_START,
                    "duration_days": 14,
                },
                _ctx(),
            )
        self.assertEqual(out["status"], "pending")
        self.assertEqual(out.get("stage"), "schedule_choice")
        self.assertIn("Monday", out["response_text"])
        self.assertIn("Reply 1", out["response_text"])
        self.assertIn("Reply 2", out["response_text"])
        self.assertEqual(
            mock_redis.call_args[0][1]["pending_action"]["stage"],
            "schedule_choice",
        )

    async def test_unsupported_topic_stops(self):
        out = await handle_learning_create(
            {"topic": "Klingon", "start_date": self._FUTURE_START, "duration_days": 14},
            _ctx(),
        )
        self.assertEqual(out["status"], "error")

    async def test_duration_too_short(self):
        with (
            patch(
                "handlers.learning.create.used_learning_schedule_ids",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "start_date": self._FUTURE_START,
                    "duration_days": 3,
                    "learning_schedule_id": "default",
                },
                _ctx(),
            )
        self.assertEqual(out["status"], "error")
        self.assertIn("7 days", out["response_text"])

    async def test_duplicate_goal(self):
        with patch(
            "handlers.learning.create.find_conflicting_goal",
            new=AsyncMock(
                return_value={
                    "roadmap_key": "functions",
                    "subject": "python",
                },
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "start_date": self._FUTURE_START,
                    "duration_days": 14,
                },
                _ctx(),
            )
        self.assertEqual(out["status"], "error")
        self.assertIn("already have an active Python learning plan", out["response_text"])
        self.assertIn("Complete that plan first, or delete it", out["response_text"])
        self.assertNotIn("Pause", out["response_text"])

    async def test_success_path_creates_goal_and_tasks(self):
        topics = [
            {"order": 1, "title": "Intro", "resources": []},
            {"order": 2, "title": "Types", "resources": []},
        ]
        scheduled = [
            {
                "order": 1,
                "title": "Intro",
                "resources": [],
                "scheduled_date": datetime(2026, 6, 1, 9, 0, 0),
            },
            {
                "order": 2,
                "title": "Types",
                "resources": [],
                "scheduled_date": datetime(2026, 6, 8, 9, 0, 0),
            },
        ]

        with (
            patch(
                "handlers.learning.create.used_learning_schedule_ids",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.get_roadmap",
                new=AsyncMock(return_value=topics),
            ),
            patch(
                "handlers.learning.create.get_sessions_required",
                new=AsyncMock(return_value=2),
            ),
            patch(
                "handlers.learning.create.build_schedule",
                return_value=scheduled,
            ),
            patch(
                "handlers.learning.create.find_overlapping_task_for_user",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.insert_goal",
                new=AsyncMock(return_value="goalid1"),
            ),
            patch(
                "handlers.learning.create.insert_topics_bulk",
                new=AsyncMock(return_value=["t1", "t2"]),
            ),
            patch(
                "handlers.learning.create.insert_task",
                new=AsyncMock(side_effect=["task1", "task2"]),
            ),
            patch(
                "handlers.learning.create.update_topic_task_id",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "handlers.learning.create.update_task",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "handlers.learning.create.insert_log",
                new=AsyncMock(return_value="log1"),
            ),
            patch(
                "handlers.learning.create.redis_client.delete_context",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "handlers.learning.create.gemini_service.generate_reply",
                return_value="",
            ),
            patch(
                "handlers.learning.create.insert_message",
                new=AsyncMock(),
            ),
            patch(
                "handlers.learning.create.update_last_message",
                new=AsyncMock(),
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "subtopic": "basics",
                    "start_date": self._FUTURE_START,
                    "duration_days": 14,
                    "learning_schedule_id": "default",
                },
                _ctx(),
            )

        self.assertEqual(out["status"], "success")
        self.assertEqual(out["learning_goal_id"], "goalid1")
        self.assertEqual(out["topics_scheduled"], 2)
        self.assertTrue(len(out["notifications"]) >= 1)

    async def test_success_calls_log_and_messages(self):
        topics = [{"order": 1, "title": "Intro", "resources": []}]
        scheduled = [
            {
                "order": 1,
                "title": "Intro",
                "resources": [],
                "scheduled_date": datetime(2026, 6, 1, 9, 0, 0),
            },
        ]
        mock_insert_msg = AsyncMock()
        mock_log = AsyncMock(return_value="log1")
        mock_cal = AsyncMock(return_value="evt-1")
        with (
            patch(
                "handlers.learning.create.used_learning_schedule_ids",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "handlers.learning.create.find_conflicting_goal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.get_roadmap",
                new=AsyncMock(return_value=topics),
            ),
            patch(
                "handlers.learning.create.get_sessions_required",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "handlers.learning.create.build_schedule",
                return_value=scheduled,
            ),
            patch(
                "handlers.learning.create.find_overlapping_task_for_user",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "handlers.learning.create.insert_goal",
                new=AsyncMock(return_value="goal-x"),
            ),
            patch(
                "handlers.learning.create.insert_topics_bulk",
                new=AsyncMock(return_value=["t1"]),
            ),
            patch(
                "handlers.learning.create.insert_task",
                new=AsyncMock(return_value="task-x"),
            ),
            patch(
                "handlers.learning.create.update_topic_task_id",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "handlers.learning.create.update_task",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "handlers.learning.create.insert_log",
                mock_log,
            ),
            patch(
                "handlers.learning.create.redis_client.delete_context",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "handlers.learning.create.gemini_service.generate_reply",
                return_value="All set.",
            ),
            patch(
                "handlers.learning.create.insert_message",
                mock_insert_msg,
            ),
            patch(
                "handlers.learning.create.update_last_message",
                new=AsyncMock(),
            ),
            patch(
                "handlers.learning.create._pick_active_google_integration",
                return_value={"access_token": "tok", "calendar_id": "primary"},
            ),
            patch(
                "handlers.learning.create.google_calendar_client.create_event",
                mock_cal,
            ),
        ):
            out = await handle_learning_create(
                {
                    "topic": "Python",
                    "start_date": self._FUTURE_START,
                    "duration_days": 14,
                    "learning_schedule_id": "default",
                },
                _ctx(integrations=[{"provider": "google", "status": "active"}]),
            )
        self.assertEqual(out["status"], "success")
        mock_log.assert_awaited()
        self.assertGreaterEqual(mock_insert_msg.await_count, 2)
        mock_cal.assert_awaited()

    def test_session_preview_label_uses_user_timezone(self):
        from datetime import datetime

        from handlers.learning.create import _session_preview_label

        # Fri 10:50 Asia/Karachi stored as 05:50 UTC-naive
        stored = datetime(2026, 6, 5, 5, 50, 0)
        label = _session_preview_label(stored, "Asia/Karachi")
        self.assertIn("10:50 AM", label)
        self.assertNotIn("5:50 AM", label)
        self.assertIn("Friday", label)


if __name__ == "__main__":
    unittest.main()
