"""
Phase 5 tests for learning_update handler (core paths).
"""

import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from bson import ObjectId


if "pipeline.ner" not in sys.modules:
    _ner_mod = types.ModuleType("pipeline.ner")

    class _StubExtractor:
        loaded = True

        def extract(self, *args, **kwargs):
            return {}

        def load(self):
            return True

    _stub = _StubExtractor()
    _ner_mod.learning_ner_extractor = _stub
    _ner_mod.ner_extractor = _stub
    _ner_mod.get_ner_extractor_for_intent = lambda _intent: _stub
    sys.modules["pipeline.ner"] = _ner_mod


from handlers.learning.update import handle_learning_update


def _base_context(**overrides):
    ctx = {
        "user_id": str(ObjectId()),
        "session_id": str(ObjectId()),
        "message": "pause my Python",
        "input_type": "text",
        "user": {"name": "Ali", "timezone": "UTC"},
        "history": [],
        "integrations": [],
        "settings": {"preferred_learning_schedule": [{"day": 0, "time": "18:00"}]},
    }
    ctx.update(overrides)
    return ctx


class LearningUpdateHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_pause_no_topic_sets_free_text_state(self):
        with patch(
            "handlers.learning.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.learning.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_update(
                entities={},
                context=_base_context(message="pause my roadmap"),
            )

        self.assertEqual(result["status"], "pending")
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["expected_response"], "free_text")
        self.assertEqual(payload["pending_action"]["sub_intent"], "pause")

    async def test_pause_single_match_sets_yes_no(self):
        gid = str(ObjectId())
        match = {
            "_id": gid,
            "title": "Python basics",
            "roadmap_key": "basics",
            "status": "active",
            "completed_topics": 2,
            "total_topics": 8,
            "subject": "python",
        }
        with patch(
            "handlers.learning.update.find_goals_for_update",
            new=AsyncMock(return_value=[match]),
        ), patch(
            "handlers.learning.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.learning.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_update(
                entities={"topic": "Python"},
                context=_base_context(message="pause my Python"),
            )

        self.assertEqual(result["status"], "pending")
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["expected_response"], "yes_no")
        self.assertEqual(payload["pending_action"]["goal_id"], gid)

    async def test_pause_yes_executes_pause_goal(self):
        gid = str(ObjectId())
        goal = {"_id": gid, "title": "Python basics", "roadmap_key": "basics", "status": "active"}
        context = _base_context(
            message="yes",
            pending_context={
                "expected_response": "yes_no",
                "pending_action": {"intent": "learning_update", "sub_intent": "pause", "goal_id": gid, "goal": goal},
            },
            pending_reply_type="yes_no",
            pending_reply_value="yes",
        )

        with patch(
            "handlers.learning.update.pause_goal",
            new=AsyncMock(return_value=True),
        ) as mock_pause, patch(
            "handlers.learning.update.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.learning.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_update(entities={}, context=context)

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_pause.await_count, 1)

    async def test_complete_blocked_when_unlocked_future(self):
        gid = str(ObjectId())
        now = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
        # Scheduled later same day => within 24h, unlocked_future.
        current = {"_id": str(ObjectId()), "order": 1, "status": "pending", "scheduled_date": now.replace(hour=18)}
        goal = {"_id": gid, "title": "Python basics", "subject": "python"}

        with patch(
            "handlers.learning.update.find_goals_for_update",
            new=AsyncMock(return_value=[goal]),
        ), patch(
            "handlers.learning.update.get_goal_by_id",
            new=AsyncMock(return_value=goal),
        ), patch(
            "handlers.learning.update.get_current_session",
            new=AsyncMock(return_value=current),
        ), patch(
            "handlers.learning.update.get_topics_for_goal",
            new=AsyncMock(return_value=[current]),
        ), patch(
            "handlers.learning.update.compute_session_state",
            return_value="unlocked_future",
        ), patch(
            "handlers.learning.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_update(
                entities={"topic": "Python"},
                context=_base_context(message="mark next session done"),
            )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("can't mark it complete", result["response_text"].lower())


if __name__ == "__main__":
    unittest.main()

