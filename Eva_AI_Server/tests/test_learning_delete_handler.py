"""
Phase 5 tests for learning_delete handler.
"""

import sys
import types
import unittest
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

from handlers.learning.delete import handle_learning_delete


def _base_context(**overrides):
    ctx = {
        "user_id": str(ObjectId()),
        "session_id": str(ObjectId()),
        "message": "delete Python basics",
        "input_type": "text",
        "user": {"name": "Ali", "timezone": "UTC"},
        "history": [],
        "integrations": [],
    }
    ctx.update(overrides)
    return ctx


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


class LearningDeleteHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_step1_no_topic_sets_free_text_state(self):
        with patch(
            "handlers.learning.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(entities={}, context=_base_context())

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "free_text")
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["expected_response"], "free_text")
        self.assertEqual(payload["pending_action"]["intent"], "learning_delete")

    async def test_step4_single_match_sets_yes_no(self):
        goal_id = str(ObjectId())
        match = [
            {
                "_id": goal_id,
                "title": "Python basics",
                "roadmap_key": "basics",
                "status": "active",
                "completed_topics": 3,
                "total_topics": 8,
                "collaborators": [],
            }
        ]
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=match),
        ), patch(
            "handlers.learning.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "Python", "subtopic": "basics"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "yes_no")
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["pending_action"]["goal_ids"], [goal_id])

    async def test_step4_zero_matches_not_found(self):
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "MySQL"},
                context=_base_context(message="delete MySQL roadmap"),
            )

        self.assertEqual(result["status"], "not_found")
        self.assertIn("learning_delete_not_found", result["response_text"])

    async def test_step4_multi_match_sets_number_state(self):
        goals = [
            {
                "_id": str(ObjectId()),
                "title": "Python basics",
                "roadmap_key": "basics",
                "status": "active",
                "completed_topics": 3,
                "total_topics": 8,
            },
            {
                "_id": str(ObjectId()),
                "title": "Python functions",
                "roadmap_key": "functions",
                "status": "active",
                "completed_topics": 0,
                "total_topics": 5,
            },
        ]
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=goals),
        ), patch(
            "handlers.learning.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "Python"},
                context=_base_context(message="delete Python roadmap"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "number")
        payload = mock_set.await_args.args[1]
        self.assertEqual(len(payload["pending_action"]["goal_ids"]), 2)

    async def test_step6_yes_deletes_goal_and_logs(self):
        goal_id = str(ObjectId())
        collab_id = str(ObjectId())
        owner_id = str(ObjectId())
        goal = {
            "_id": goal_id,
            "title": "Python basics",
            "roadmap_key": "basics",
            "subject": "python",
            "status": "active",
            "completed_topics": 2,
            "total_topics": 5,
            "collaborators": [{"user_id": collab_id, "status": "accepted"}],
        }
        context = _base_context(
            user_id=owner_id,
            message="yes",
            pending_context={
                "pending_action": {
                    "intent": "learning_delete",
                    "goal_ids": [goal_id],
                    "goals": [
                        {
                            "title": "Python basics",
                            "roadmap_key": "basics",
                            "status": "active",
                            "completed_topics": 2,
                            "total_topics": 5,
                        }
                    ],
                    "bulk": False,
                    "entities": {"topic": "Python"},
                }
            },
            pending_reply_type="yes_no",
            pending_reply_value="yes",
        )

        with patch(
            "handlers.learning.delete.get_goal_by_id",
            new=AsyncMock(return_value=goal),
        ), patch(
            "handlers.learning.delete.soft_delete_goal",
            new=AsyncMock(return_value=True),
        ) as mock_soft_goal, patch(
            "handlers.learning.delete.soft_delete_pending_topics",
            new=AsyncMock(return_value=3),
        ), patch(
            "handlers.learning.delete.soft_delete_pending_learning_tasks",
            new=AsyncMock(return_value=2),
        ), patch(
            "handlers.learning.delete.get_pending_learning_tasks",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.learning.delete.insert_log",
            new=AsyncMock(return_value="log1"),
        ) as mock_log, patch(
            "handlers.learning.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(entities={"topic": "Python"}, context=context)

        self.assertEqual(result["status"], "success")
        mock_soft_goal.assert_awaited_once_with(goal_id)
        mock_log.assert_awaited()
        self.assertEqual(mock_log.await_args.args[0]["action_type"], "goal_deleted")
        self.assertEqual(len(result["notifications"]), 1)
        self.assertEqual(result["notifications"][0]["type"], "learning_goal_deleted")

    async def test_step6_no_cancels_without_delete(self):
        goal_id = str(ObjectId())
        context = _base_context(
            message="no",
            pending_context={
                "pending_action": {
                    "intent": "learning_delete",
                    "goal_ids": [goal_id],
                    "goals": [{"title": "Python basics"}],
                    "bulk": False,
                    "entities": {"topic": "Python"},
                }
            },
            pending_reply_type="yes_no",
            pending_reply_value="no",
        )

        with patch(
            "handlers.learning.delete.soft_delete_goal",
            new=AsyncMock(return_value=True),
        ) as mock_soft, patch(
            "handlers.learning.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(entities={}, context=context)

        self.assertEqual(result["status"], "cancelled")
        mock_soft.assert_not_awaited()
        self.assertIn("left", result["response_text"].lower())

    async def test_too_broad_when_six_or_more(self):
        matches = [
            {
                "_id": str(ObjectId()),
                "title": f"Python plan {i}",
                "roadmap_key": f"level{i}",
                "status": "active",
                "completed_topics": 0,
                "total_topics": 3,
            }
            for i in range(6)
        ]
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=matches),
        ), patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "Python"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "too_broad")
        self.assertIn("learning_delete_too_broad", result["response_text"])

    async def test_bulk_yes_deletes_all_with_one_log_per_goal(self):
        owner_id = str(ObjectId())
        gid1, gid2 = str(ObjectId()), str(ObjectId())
        goal1 = {
            "_id": gid1,
            "title": "Python basics",
            "roadmap_key": "basics",
            "subject": "python",
            "status": "active",
            "completed_topics": 1,
            "total_topics": 5,
            "collaborators": [],
        }
        goal2 = {
            "_id": gid2,
            "title": "Python functions",
            "roadmap_key": "functions",
            "subject": "python",
            "status": "active",
            "completed_topics": 0,
            "total_topics": 4,
            "collaborators": [],
        }

        context = _base_context(
            user_id=owner_id,
            message="yes",
            pending_context={
                "pending_action": {
                    "intent": "learning_delete",
                    "goal_ids": [gid1, gid2],
                    "goals": [goal1, goal2],
                    "bulk": True,
                    "entities": {"topic": "Python"},
                }
            },
            pending_reply_type="yes_no",
            pending_reply_value="yes",
        )

        get_goal_results = {gid1: goal1, gid2: goal2}

        with patch(
            "handlers.learning.delete.get_goal_by_id",
            new=AsyncMock(side_effect=lambda gid: get_goal_results.get(gid)),
        ), patch(
            "handlers.learning.delete.soft_delete_goal",
            new=AsyncMock(return_value=True),
        ) as mock_soft_goal, patch(
            "handlers.learning.delete.soft_delete_pending_topics",
            new=AsyncMock(return_value=2),
        ) as mock_soft_topics, patch(
            "handlers.learning.delete.soft_delete_pending_learning_tasks",
            new=AsyncMock(return_value=2),
        ) as mock_soft_tasks, patch(
            "handlers.learning.delete.get_pending_learning_tasks",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.learning.delete.insert_log",
            new=AsyncMock(return_value="log"),
        ) as mock_log, patch(
            "handlers.learning.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(entities={}, context=context)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["deleted"]["count"], 2)
        self.assertTrue(result["deleted"]["bulk"])
        self.assertEqual(mock_soft_goal.await_count, 2)
        self.assertEqual(mock_soft_topics.await_count, 2)
        self.assertEqual(mock_soft_tasks.await_count, 2)
        self.assertEqual(mock_log.await_count, 2)
        for call in mock_log.await_args_list:
            self.assertEqual(call.args[0]["action_type"], "goal_deleted")

    async def test_calendar_failure_does_not_block_deletion(self):
        gid = str(ObjectId())
        goal = {
            "_id": gid,
            "title": "Python basics",
            "roadmap_key": "basics",
            "subject": "python",
            "status": "active",
            "completed_topics": 0,
            "total_topics": 5,
            "collaborators": [],
        }
        pending_tasks = [
            {"_id": str(ObjectId()), "google_calendar_event_id": "evt1"},
            {"_id": str(ObjectId()), "google_calendar_event_id": "evt2"},
        ]

        context = _base_context(
            message="yes",
            integrations=[
                {
                    "provider": "google_calendar",
                    "is_active": True,
                    "access_token": "tok",
                    "calendar_id": "primary",
                }
            ],
            pending_context={
                "pending_action": {
                    "intent": "learning_delete",
                    "goal_ids": [gid],
                    "goals": [goal],
                    "bulk": False,
                    "entities": {"topic": "Python"},
                }
            },
            pending_reply_type="yes_no",
            pending_reply_value="yes",
        )

        async def _calendar_fail(**_kwargs):
            raise RuntimeError("calendar offline")

        with patch(
            "handlers.learning.delete.get_goal_by_id",
            new=AsyncMock(return_value=goal),
        ), patch(
            "handlers.learning.delete.soft_delete_goal",
            new=AsyncMock(return_value=True),
        ) as mock_soft_goal, patch(
            "handlers.learning.delete.soft_delete_pending_topics",
            new=AsyncMock(return_value=1),
        ), patch(
            "handlers.learning.delete.soft_delete_pending_learning_tasks",
            new=AsyncMock(return_value=2),
        ), patch(
            "handlers.learning.delete.get_pending_learning_tasks",
            new=AsyncMock(return_value=pending_tasks),
        ), patch(
            "handlers.learning.delete.google_calendar_client.delete_event",
            new=AsyncMock(side_effect=_calendar_fail),
        ) as mock_calendar, patch(
            "handlers.learning.delete.insert_log",
            new=AsyncMock(return_value="log"),
        ), patch(
            "handlers.learning.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(entities={}, context=context)

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_soft_goal.await_count, 1)
        self.assertEqual(mock_calendar.await_count, 2)

    async def test_completed_goal_can_be_deleted(self):
        gid = str(ObjectId())
        completed_goal = {
            "_id": gid,
            "title": "Python basics",
            "roadmap_key": "basics",
            "status": "completed",
            "completed_topics": 5,
            "total_topics": 5,
            "collaborators": [],
        }
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=[completed_goal]),
        ), patch(
            "handlers.learning.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "Python"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "yes_no")
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["pending_action"]["goals"][0]["status"], "completed")

    async def test_paused_goal_can_be_deleted(self):
        gid = str(ObjectId())
        paused_goal = {
            "_id": gid,
            "title": "Python basics",
            "roadmap_key": "basics",
            "status": "paused",
            "completed_topics": 2,
            "total_topics": 5,
            "collaborators": [],
        }
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=[paused_goal]),
        ), patch(
            "handlers.learning.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "Python"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "pending")
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["pending_action"]["goals"][0]["status"], "paused")

    async def test_unsupported_topic_returns_not_found(self):
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=[]),
        ) as mock_find, patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "klingon"},
                context=_base_context(),
            )

        self.assertEqual(result["status"], "not_found")
        mock_find.assert_not_awaited()

    async def test_near_miss_wrong_subtopic_offers_existing_plan(self):
        goal_id = str(ObjectId())
        basics_goal = {
            "_id": goal_id,
            "title": "Python basics",
            "roadmap_key": "basics",
            "status": "active",
            "completed_topics": 2,
            "total_topics": 8,
            "collaborators": [],
        }

        async def _find_side_effect(user_id, topic, roadmap_key=None):
            if roadmap_key == "advanced":
                return []
            return [basics_goal]

        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(side_effect=_find_side_effect),
        ), patch(
            "handlers.learning.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "Python", "subtopic": "advance"},
                context=_base_context(message="delete python advance roadmap"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "yes_no")
        self.assertTrue(result["pending"].get("near_miss"))
        self.assertIn("learning_delete_near_miss_confirm", result["response_text"])
        payload = mock_set.await_args.args[1]
        self.assertEqual(payload["pending_action"]["goal_ids"], [goal_id])

    async def test_ner_noise_subtopic_ma_does_not_filter_roadmap(self):
        match = [
            {
                "_id": str(ObjectId()),
                "title": "Python basics",
                "roadmap_key": "basics",
                "status": "active",
                "completed_topics": 1,
                "total_topics": 5,
                "collaborators": [],
            }
        ]
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=match),
        ) as mock_find, patch(
            "handlers.learning.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_learning_delete(
                entities={"topic": "Python", "subtopic": "ma"},
                context=_base_context(message="delete python roadmap"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["expected_response"], "yes_no")
        call_kwargs = mock_find.await_args.kwargs
        self.assertIsNone(call_kwargs.get("roadmap_key"))

    async def test_topic_alias_normalized_for_query(self):
        with patch(
            "handlers.learning.delete.find_goals_for_delete",
            new=AsyncMock(return_value=[]),
        ) as mock_find, patch(
            "handlers.learning.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.learning.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            await handle_learning_delete(
                entities={"topic": "py", "subtopic": "beginner"},
                context=_base_context(),
            )

        # First call should use the mapped roadmap_key; second call may fall back to topic-only.
        call_args = mock_find.await_args_list[0]
        self.assertEqual(call_args.args[1], "Python")
        self.assertEqual(call_args.kwargs.get("roadmap_key"), "basics")


if __name__ == "__main__":
    unittest.main()
