"""
Phase 5 tests for learning_update internal endpoints.
"""

import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from bson import ObjectId

# Stub pipeline.ner to avoid importing torch during tests.
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

# Stub torch to avoid hard dependency during import of main/classifiers.
if "torch" not in sys.modules:
    sys.modules["torch"] = types.ModuleType("torch")

# Stub transformers for classifier imports (models not used in these tests).
if "transformers" not in sys.modules:
    _t = types.ModuleType("transformers")

    class _StubAuto:
        @classmethod
        def from_pretrained(cls, *_args, **_kwargs):
            return cls()

        def eval(self):
            return self

        @property
        def config(self):
            return types.SimpleNamespace(id2label={})

    _t.AutoTokenizer = _StubAuto
    _t.AutoModelForSequenceClassification = _StubAuto
    _t.AutoModelForTokenClassification = _StubAuto
    sys.modules["transformers"] = _t

import main as ai_main


class LearningUpdateInternalEndpointsTests(unittest.IsolatedAsyncioTestCase):
    async def test_auto_complete_topic_success(self):
        uid = str(ObjectId())
        gid = str(ObjectId())
        tid = str(ObjectId())

        with patch.object(
            ai_main,
            "complete_topic",
            new=AsyncMock(return_value=True),
        ), patch.object(
            ai_main,
            "get_goal_by_id",
            new=AsyncMock(return_value={"_id": gid, "status": "active", "started_at": None}),
        ), patch.object(
            ai_main,
            "get_current_session",
            new=AsyncMock(return_value={"_id": str(ObjectId()), "order": 2}),
        ), patch.object(
            ai_main,
            "fetch_user",
            new=AsyncMock(return_value={"timezone": "UTC"}),
        ):
            req = ai_main.AutoCompleteTopicRequest(topic_id=tid, goal_id=gid, user_id=uid)
            out = await ai_main.internal_auto_complete_topic(req)

        self.assertEqual(out["status"], "success")
        self.assertFalse(out["goal_completed"])
        self.assertIsInstance(out["next_session"], dict)

    async def test_skip_topic_soft_deletes_task_when_present(self):
        uid = str(ObjectId())
        gid = str(ObjectId())
        tid = str(ObjectId())
        task_id = str(ObjectId())

        with patch.object(
            ai_main,
            "skip_session_and_rebalance",
            new=AsyncMock(return_value=(True, True)),
        ) as mock_skip, patch.object(
            ai_main,
            "get_topics_for_goal",
            new=AsyncMock(return_value=[{"_id": tid, "task_id": task_id}]),
        ), patch.object(
            ai_main,
            "fetch_user_settings",
            new=AsyncMock(return_value={}),
        ), patch.object(
            ai_main,
            "fetch_user",
            new=AsyncMock(return_value={"timezone": "UTC"}),
        ), patch.object(
            ai_main,
            "fetch_integrations",
            new=AsyncMock(return_value=[]),
        ):
            req = ai_main.SkipTopicRequest(topic_id=tid, goal_id=gid, user_id=uid)
            out = await ai_main.internal_skip_topic(req)

        self.assertEqual(out["status"], "success")
        self.assertEqual(mock_skip.await_count, 1)

    async def test_rebuild_schedule_updates_goals_count(self):
        uid = str(ObjectId())
        g1 = {"_id": str(ObjectId()), "subject": "python"}
        pending_topics = [
            {"_id": str(ObjectId()), "order": 1, "title": "A", "resources": [], "task_id": str(ObjectId())},
            {"_id": str(ObjectId()), "order": 2, "title": "B", "resources": [], "task_id": str(ObjectId())},
        ]
        schedule = [{"day": 0, "time": "18:00"}]

        with patch.object(ai_main, "get_active_goals_for_user", new=AsyncMock(return_value=[g1])), patch.object(
            ai_main,
            "get_all_pending_sessions",
            new=AsyncMock(return_value=pending_topics),
        ), patch.object(
            ai_main,
            "build_schedule",
            return_value=[
                {"scheduled_date": datetime(2026, 6, 1, 18, 0, tzinfo=timezone.utc).replace(tzinfo=None)},
                {"scheduled_date": datetime(2026, 6, 8, 18, 0, tzinfo=timezone.utc).replace(tzinfo=None)},
            ],
        ), patch.object(
            ai_main,
            "reschedule_topic",
            new=AsyncMock(return_value=True),
        ), patch.object(
            ai_main,
            "update_task",
            new=AsyncMock(return_value=True),
        ), patch.object(
            ai_main,
            "update_end_date",
            new=AsyncMock(return_value=True),
        ), patch.object(
            ai_main,
            "fetch_user_settings",
            new=AsyncMock(return_value={}),
        ), patch.object(
            ai_main,
            "fetch_integrations",
            new=AsyncMock(return_value=[]),
        ), patch.object(
            ai_main,
            "fetch_user",
            new=AsyncMock(return_value={"timezone": "UTC"}),
        ):
            req = ai_main.RebuildScheduleRequest(user_id=uid, new_schedule=schedule)
            out = await ai_main.internal_rebuild_schedule(req)

        self.assertEqual(out["status"], "success")
        self.assertEqual(out["goals_updated"], 1)


if __name__ == "__main__":
    unittest.main()

