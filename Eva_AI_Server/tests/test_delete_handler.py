"""
Phase 18 integration-style tests for full delete flow behavior.
"""
from datetime import datetime
from types import SimpleNamespace
import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from context.context_manager import handle_free_text_reply
from handlers.scheduling.delete import handle_scheduling_delete


def _import_ai_main_with_stubs():
    """
    Import main.py while tolerating local environments without torch.
    """
    try:
        return importlib.import_module("main")
    except ModuleNotFoundError as error:
        if getattr(error, "name", "") != "torch":
            raise

        class _StubModel:
            def __init__(self):
                self.loaded = True

            def load(self):
                self.loaded = True
                return True

            def predict(self, _text):
                return {"label": "general"}

            def extract(self, _text, intent_hint=""):
                _ = intent_hint
                return {}

        fake_classifier1 = types.ModuleType("pipeline.classifier1")
        fake_classifier1.classifier1 = _StubModel()

        fake_classifier2 = types.ModuleType("pipeline.classifier2")
        fake_classifier2.classifier2 = _StubModel()

        fake_ner = types.ModuleType("pipeline.ner")
        fake_ner.ner_extractor = _StubModel()

        sys.modules["pipeline.classifier1"] = fake_classifier1
        sys.modules["pipeline.classifier2"] = fake_classifier2
        sys.modules["pipeline.ner"] = fake_ner
        sys.modules.pop("main", None)
        return importlib.import_module("main")


ai_main = _import_ai_main_with_stubs()


USER_ID = "507f1f77bcf86cd799439011"
SESSION_ID = "69c0c6d79c98840a2697022f"


def _base_handler_context(message: str) -> dict:
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


def _fetched(context=None):
    return SimpleNamespace(
        user={
            "name": "Hamid",
            "timezone": "Asia/Karachi",
        },
        settings={},
        history=[],
        integrations=[],
        context=context,
    )


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


class TestDeleteHandlerPhase18(unittest.IsolatedAsyncioTestCase):
    async def test_no_entity_then_free_text_reply_reenters_and_finds_one_match(self):
        context = _base_handler_context("delete something")

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
            first = await handle_scheduling_delete(entities={}, context=context)

        self.assertEqual(first["status"], "pending")
        self.assertEqual(first["pending"]["expected_response"], "free_text")
        pending_context = mock_set.await_args.args[1]

        with patch(
            "context.context_manager.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ):
            merged = await handle_free_text_reply(USER_ID, pending_context, "physics exam")

        self.assertEqual(merged["task_name"], "physics exam")

        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 3, 26, 17, 0, 0),
                "priority": "high",
            }
        ]

        with patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set_second, patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            second = await handle_scheduling_delete(
                entities=merged,
                context=_base_handler_context("physics exam"),
            )

        self.assertEqual(second["status"], "pending")
        self.assertEqual(second["pending"]["expected_response"], "yes_no")
        second_payload = mock_set_second.await_args.args[1]
        self.assertEqual(second_payload["pending_action"]["task_ids"], ["task1"])

    async def test_one_match_yes_deletes_and_triggers_calendar_and_collab_notification(self):
        context = _base_handler_context("yes")
        context["integrations"] = [
            {
                "provider": "google_calendar",
                "is_active": True,
                "access_token": "token_1",
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
                        "due_datetime": "2026-03-26T17:00:00",
                        "priority": "high",
                    }
                ],
                "bulk": False,
                "entities": {"task_name": "physics exam"},
            },
        }
        context["pending_reply_type"] = "yes_no"
        context["pending_reply_value"] = "yes"

        task = {
            "_id": "task1",
            "title": "Physics exam",
            "due_datetime": datetime(2026, 3, 26, 17, 0, 0),
            "priority": "high",
            "google_calendar_event_id": "evt_123",
            "collaborators": [
                {"user_id": "friend_ok", "status": "accepted"},
                {"user_id": "friend_wait", "status": "pending"},
            ],
        }

        with patch(
            "handlers.scheduling.delete.get_task_by_id",
            new=AsyncMock(return_value=task),
        ), patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(return_value=True),
        ) as mock_delete, patch(
            "handlers.scheduling.delete.insert_log",
            new=AsyncMock(return_value="log1"),
        ) as mock_log, patch(
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
        self.assertEqual(result["deleted"]["count"], 1)
        self.assertEqual(result["response_text"], "ACTION:task_deleted")
        self.assertEqual(len(result["notifications"]), 1)
        self.assertEqual(result["notifications"][0]["user_id"], "friend_ok")
        mock_delete.assert_awaited_once_with("task1")
        mock_log.assert_awaited_once()
        mock_delete_event.assert_awaited_once()
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_one_match_no_not_deleted(self):
        context = _base_handler_context("no")
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
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(return_value=True),
        ) as mock_delete, patch(
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

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["notifications"], [])
        mock_delete.assert_not_awaited()
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_pick_number_then_confirm_yes_deletes_selected_task(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["id1", "id2", "id3"],
                "tasks": [
                    {"title": "Physics exam", "due_datetime": "2026-03-26T10:00:00", "priority": "high"},
                    {"title": "Physics lab", "due_datetime": "2026-03-26T12:00:00", "priority": "medium"},
                    {"title": "Physics quiz", "due_datetime": "2026-03-26T15:00:00", "priority": "low"},
                ],
                "bulk": False,
                "entities": {"priority": "high"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1, "loaded", True
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set:
            pick = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="2",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertEqual(pick["parsed_value"], "id2")
        updated_pending = mock_set.await_args.args[1]["pending_action"]
        self.assertEqual(updated_pending["task_ids"], ["id2"])
        self.assertFalse(updated_pending["bulk"])

        context_yes = _base_handler_context("yes")
        context_yes["pending_context"] = {
            "expected_response": "yes_no",
            "pending_action": updated_pending,
        }
        context_yes["pending_reply_type"] = "yes_no"
        context_yes["pending_reply_value"] = "yes"

        task = {
            "_id": "id2",
            "title": "Physics lab",
            "due_datetime": datetime(2026, 3, 26, 12, 0, 0),
            "priority": "medium",
            "google_calendar_event_id": None,
            "collaborators": [],
        }
        with patch(
            "handlers.scheduling.delete.get_task_by_id",
            new=AsyncMock(return_value=task),
        ), patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.delete.insert_log",
            new=AsyncMock(return_value="log"),
        ), patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            deleted = await handle_scheduling_delete({}, context_yes)

        self.assertEqual(deleted["status"], "success")
        self.assertEqual(deleted["deleted"]["count"], 1)
        self.assertEqual(deleted["deleted"]["tasks"][0]["_id"], "id2")

    async def test_pick_all_then_confirm_yes_deletes_all(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["id1", "id2", "id3"],
                "tasks": [
                    {"title": "A", "due_datetime": "2026-03-26T10:00:00", "priority": "high"},
                    {"title": "B", "due_datetime": "2026-03-26T12:00:00", "priority": "high"},
                    {"title": "C", "due_datetime": "2026-03-26T14:00:00", "priority": "high"},
                ],
                "bulk": False,
                "entities": {"priority": "high"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1, "loaded", True
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set:
            all_choice = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="all",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertEqual(all_choice["parsed_value"], "all")
        updated_context = mock_set.await_args.args[1]
        self.assertEqual(updated_context["expected_response"], "yes_no")
        self.assertTrue(updated_context["pending_action"]["bulk"])

        context_yes = _base_handler_context("yes")
        context_yes["pending_context"] = updated_context
        context_yes["pending_reply_type"] = "yes_no"
        context_yes["pending_reply_value"] = "yes"

        tasks = [
            {
                "_id": "id1",
                "title": "A",
                "due_datetime": datetime(2026, 3, 26, 10, 0, 0),
                "priority": "high",
                "google_calendar_event_id": None,
                "collaborators": [],
            },
            {
                "_id": "id2",
                "title": "B",
                "due_datetime": datetime(2026, 3, 26, 12, 0, 0),
                "priority": "high",
                "google_calendar_event_id": None,
                "collaborators": [],
            },
            {
                "_id": "id3",
                "title": "C",
                "due_datetime": datetime(2026, 3, 26, 14, 0, 0),
                "priority": "high",
                "google_calendar_event_id": None,
                "collaborators": [],
            },
        ]
        with patch(
            "handlers.scheduling.delete.get_task_by_id",
            new=AsyncMock(side_effect=tasks),
        ), patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(side_effect=[True, True, True]),
        ), patch(
            "handlers.scheduling.delete.insert_log",
            new=AsyncMock(return_value="log"),
        ), patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            deleted = await handle_scheduling_delete({}, context_yes)

        self.assertEqual(deleted["status"], "success")
        self.assertTrue(deleted["deleted"]["bulk"])
        self.assertEqual(deleted["deleted"]["count"], 3)
        self.assertEqual(deleted["response_text"], "ACTION:delete_bulk_completed")

    async def test_pick_all_then_no_deletes_nothing(self):
        context_no = _base_handler_context("no")
        context_no["pending_context"] = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["id1", "id2", "id3"],
                "tasks": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
                "bulk": True,
                "entities": {"priority": "high"},
            },
        }
        context_no["pending_reply_type"] = "yes_no"
        context_no["pending_reply_value"] = "no"

        with patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(return_value=True),
        ) as mock_delete, patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete({}, context_no)

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["response_text"], "ACTION:delete_cancel_bulk")
        mock_delete.assert_not_awaited()

    async def test_out_of_range_number_asks_again(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["id1", "id2", "id3"],
                "tasks": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
                "bulk": False,
                "entities": {"priority": "high"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1, "loaded", True
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ):
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="5",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertEqual(result["parsed_value"], "invalid_range")
        self.assertIn("Pick between 1 and 3", result["response_text"])

    async def test_too_broad_has_no_redis_state(self):
        matches = [
            {
                "_id": f"id{i}",
                "title": f"Task {i}",
                "due_datetime": datetime(2026, 3, 26, 8 + i, 0, 0),
                "priority": "medium",
            }
            for i in range(1, 7)
        ]

        with patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(return_value=matches),
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
                {"status": "pending"},
                _base_handler_context("delete pending tasks"),
            )

        self.assertEqual(result["status"], "too_broad")
        mock_set.assert_not_awaited()

    async def test_not_found_when_zero_matches(self):
        with patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_delete(
                {"task_name": "xyz"},
                _base_handler_context("delete xyz"),
            )

        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["response_text"], "ACTION:delete_not_found")

    async def test_cancel_mid_flow_after_yes_no_shown(self):
        pending_context = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["task1"],
                "tasks": [{"title": "Physics exam"}],
                "bulk": False,
                "entities": {"task_name": "physics exam"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "main.route_intent",
            new=AsyncMock(return_value={}),
        ) as mock_route, patch(
            "main.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ):
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="cancel",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["response_text"], "ACTION:pending_cancelled")
        mock_route.assert_not_awaited()
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_cancel_mid_flow_after_list_shown(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["id1", "id2", "id3"],
                "tasks": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
                "bulk": False,
                "entities": {"priority": "high"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "main.route_intent",
            new=AsyncMock(return_value={}),
        ) as mock_route, patch(
            "main.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ):
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="stop",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["response_text"], "ACTION:pending_cancelled")
        mock_route.assert_not_awaited()
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_new_command_while_yes_no_pending_is_blocked(self):
        pending_context = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "delete",
                "task_ids": ["task1"],
                "tasks": [{"title": "Physics exam"}],
                "bulk": False,
                "entities": {"task_name": "physics exam"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1, "loaded", True
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "command"},
        ), patch(
            "main.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ):
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="delete math exam",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["response_text"], "ACTION:pending_waiting_reply")

    async def test_ttl_expiry_fresh_start_with_no_pending_context(self):
        route_result = {
            "status": "not_found",
            "intent": "scheduling_delete",
            "response_text": "Delete flow started fresh",
            "notifications": [],
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(context=None)),
        ), patch.object(
            ai_main.classifier1, "loaded", True
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "command"},
        ), patch.object(
            ai_main.classifier2, "loaded", True
        ), patch.object(
            ai_main.classifier2,
            "predict",
            return_value={"label": "delete"},
        ), patch.object(
            ai_main.ner_extractor, "loaded", True
        ), patch.object(
            ai_main.ner_extractor,
            "extract",
            return_value={"task_name": "physics exam"},
        ), patch(
            "main.scope_entities",
            return_value={"task_name": "physics exam"},
        ), patch(
            "main.resolve_all",
            new=AsyncMock(return_value={"task_name": "physics exam"}),
        ), patch(
            "main.route_intent",
            new=AsyncMock(return_value=route_result),
        ) as mock_route:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="delete physics exam",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertFalse(result.get("context_handled", False))
        self.assertEqual(result["response_text"], "Delete flow started fresh")
        mock_route.assert_awaited_once()

    async def test_phase13_delete_process_scopes_entities_without_leak(self):
        route_result = {
            "status": "pending",
            "intent": "scheduling_delete",
            "response_text": "Delete confirm prompt",
            "notifications": [],
        }

        raw_entities = {
            "task_name": "physics exam",
            "date": "Monday",
            "time": "5pm",
            "duration": "2 hours",
            "collaborator": "Ali",
            "topic": "physics",
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(context=None)),
        ), patch.object(
            ai_main.classifier1, "loaded", True
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "command"},
        ), patch.object(
            ai_main.classifier2, "loaded", True
        ), patch.object(
            ai_main.classifier2,
            "predict",
            return_value={"label": "delete"},
        ), patch.object(
            ai_main.ner_extractor, "loaded", True
        ), patch.object(
            ai_main.ner_extractor,
            "extract",
            return_value=raw_entities,
        ), patch(
            "main.resolve_all",
            new=AsyncMock(return_value={"task_name": "physics exam", "date": "2026-03-30"}),
        ), patch(
            "main.route_intent",
            new=AsyncMock(return_value=route_result),
        ) as mock_route:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="delete physics exam on Monday",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertEqual(result["entities"]["raw"]["task_name"], "physics exam")
        self.assertEqual(result["entities"]["scoped"], {"task_name": "physics exam", "date": "Monday"})
        self.assertNotIn("time", result["entities"]["scoped"])
        self.assertNotIn("duration", result["entities"]["scoped"])
        self.assertNotIn("collaborator", result["entities"]["scoped"])
        self.assertNotIn("topic", result["entities"]["scoped"])

        routed_entities = mock_route.await_args.kwargs["entities"]
        self.assertEqual(routed_entities, {"task_name": "physics exam", "date": "2026-03-30"})

    async def test_phase18_e2e_seeded_single_task_deleted_via_chat(self):
        tasks_store = [
            {
                "_id": "task1",
                "owner_id": USER_ID,
                "title": "Physics exam",
                "due_datetime": datetime(2026, 3, 26, 17, 0, 0),
                "priority": "medium",
                "status": "pending",
                "is_deleted": False,
                "google_calendar_event_id": None,
                "collaborators": [],
            }
        ]
        inserted_logs = []
        pending_state = {"context": None}

        async def fake_fetch(_user_id, _session_id):
            return _fetched(context=pending_state["context"])

        async def fake_set_context(_user_id, payload):
            pending_state["context"] = payload
            return True

        async def fake_delete_context(_user_id):
            pending_state["context"] = None
            return True

        async def fake_find_tasks_for_delete(_user_id, filters):
            task_name = str(filters.get("task_name") or "").lower()
            rows = []
            for task in tasks_store:
                if task.get("is_deleted"):
                    continue
                if task_name and task_name not in str(task.get("title") or "").lower():
                    continue
                rows.append(
                    {
                        "_id": task["_id"],
                        "title": task["title"],
                        "due_datetime": task["due_datetime"],
                        "priority": task["priority"],
                    }
                )
            return rows

        async def fake_get_task_by_id(task_id, user_id):
            for task in tasks_store:
                if (
                    str(task.get("_id")) == str(task_id)
                    and str(task.get("owner_id")) == str(user_id)
                    and not task.get("is_deleted")
                ):
                    return dict(task)
            return None

        async def fake_soft_delete_task(task_id):
            for task in tasks_store:
                if str(task.get("_id")) == str(task_id) and not task.get("is_deleted"):
                    task["is_deleted"] = True
                    return True
            return False

        async def fake_insert_log(payload):
            inserted_logs.append(dict(payload))
            return f"log_{len(inserted_logs)}"

        def classifier1_predict(text):
            normalized = text.strip().lower()
            if normalized in {"yes", "no", "all", "1", "2", "3", "4", "5"}:
                return {"label": "confirmation"}
            return {"label": "command"}

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(side_effect=fake_fetch),
        ), patch.object(
            ai_main.classifier1, "loaded", True
        ), patch.object(
            ai_main.classifier1,
            "predict",
            side_effect=classifier1_predict,
        ), patch.object(
            ai_main.classifier2, "loaded", True
        ), patch.object(
            ai_main.classifier2,
            "predict",
            return_value={"label": "delete"},
        ), patch.object(
            ai_main.ner_extractor, "loaded", True
        ), patch.object(
            ai_main.ner_extractor,
            "extract",
            return_value={"task_name": "physics exam"},
        ), patch(
            "main.resolve_all",
            new=AsyncMock(return_value={"task_name": "physics exam"}),
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(side_effect=fake_set_context),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(side_effect=fake_delete_context),
        ), patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(side_effect=fake_set_context),
        ), patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(side_effect=fake_delete_context),
        ), patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(side_effect=fake_find_tasks_for_delete),
        ), patch(
            "handlers.scheduling.delete.get_task_by_id",
            new=AsyncMock(side_effect=fake_get_task_by_id),
        ), patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(side_effect=fake_soft_delete_task),
        ), patch(
            "handlers.scheduling.delete.insert_log",
            new=AsyncMock(side_effect=fake_insert_log),
        ), patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "main.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            first = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="delete physics exam",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )
            second = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="yes",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertEqual(first["route"]["status"], "pending")
        self.assertEqual(first["route"]["pending"]["expected_response"], "yes_no")
        self.assertEqual(second["route"]["status"], "success")
        self.assertEqual(second["route"]["deleted"]["count"], 1)
        self.assertTrue(tasks_store[0]["is_deleted"])
        self.assertEqual(len(inserted_logs), 1)

    async def test_phase18_e2e_seeded_three_tasks_deleted_all_via_chat(self):
        tasks_store = [
            {
                "_id": "id1",
                "owner_id": USER_ID,
                "title": "Physics exam",
                "due_datetime": datetime(2026, 3, 26, 10, 0, 0),
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
                "google_calendar_event_id": None,
                "collaborators": [],
            },
            {
                "_id": "id2",
                "owner_id": USER_ID,
                "title": "Physics lab",
                "due_datetime": datetime(2026, 3, 26, 12, 0, 0),
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
                "google_calendar_event_id": None,
                "collaborators": [],
            },
            {
                "_id": "id3",
                "owner_id": USER_ID,
                "title": "Physics quiz",
                "due_datetime": datetime(2026, 3, 26, 15, 0, 0),
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
                "google_calendar_event_id": None,
                "collaborators": [],
            },
        ]
        inserted_logs = []
        pending_state = {"context": None}

        async def fake_fetch(_user_id, _session_id):
            return _fetched(context=pending_state["context"])

        async def fake_set_context(_user_id, payload):
            pending_state["context"] = payload
            return True

        async def fake_delete_context(_user_id):
            pending_state["context"] = None
            return True

        async def fake_find_tasks_for_delete(_user_id, filters):
            priority = str(filters.get("priority") or "").lower()
            rows = []
            for task in tasks_store:
                if task.get("is_deleted"):
                    continue
                if priority and str(task.get("priority") or "").lower() != priority:
                    continue
                rows.append(
                    {
                        "_id": task["_id"],
                        "title": task["title"],
                        "due_datetime": task["due_datetime"],
                        "priority": task["priority"],
                    }
                )
            return rows

        async def fake_get_task_by_id(task_id, user_id):
            for task in tasks_store:
                if (
                    str(task.get("_id")) == str(task_id)
                    and str(task.get("owner_id")) == str(user_id)
                    and not task.get("is_deleted")
                ):
                    return dict(task)
            return None

        async def fake_soft_delete_task(task_id):
            for task in tasks_store:
                if str(task.get("_id")) == str(task_id) and not task.get("is_deleted"):
                    task["is_deleted"] = True
                    return True
            return False

        async def fake_insert_log(payload):
            inserted_logs.append(dict(payload))
            return f"log_{len(inserted_logs)}"

        def classifier1_predict(text):
            normalized = text.strip().lower()
            if normalized in {"yes", "no", "all", "1", "2", "3", "4", "5"}:
                return {"label": "confirmation"}
            return {"label": "command"}

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(side_effect=fake_fetch),
        ), patch.object(
            ai_main.classifier1, "loaded", True
        ), patch.object(
            ai_main.classifier1,
            "predict",
            side_effect=classifier1_predict,
        ), patch.object(
            ai_main.classifier2, "loaded", True
        ), patch.object(
            ai_main.classifier2,
            "predict",
            return_value={"label": "delete"},
        ), patch.object(
            ai_main.ner_extractor, "loaded", True
        ), patch.object(
            ai_main.ner_extractor,
            "extract",
            return_value={"priority": "high"},
        ), patch(
            "main.resolve_all",
            new=AsyncMock(return_value={"priority": "high"}),
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(side_effect=fake_set_context),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(side_effect=fake_delete_context),
        ), patch(
            "handlers.scheduling.delete.redis_client.set_context",
            new=AsyncMock(side_effect=fake_set_context),
        ), patch(
            "handlers.scheduling.delete.redis_client.delete_context",
            new=AsyncMock(side_effect=fake_delete_context),
        ), patch(
            "handlers.scheduling.delete.find_tasks_for_delete",
            new=AsyncMock(side_effect=fake_find_tasks_for_delete),
        ), patch(
            "handlers.scheduling.delete.get_task_by_id",
            new=AsyncMock(side_effect=fake_get_task_by_id),
        ), patch(
            "handlers.scheduling.delete.soft_delete_task",
            new=AsyncMock(side_effect=fake_soft_delete_task),
        ), patch(
            "handlers.scheduling.delete.insert_log",
            new=AsyncMock(side_effect=fake_insert_log),
        ), patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "main.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.delete._save_turn",
            new=AsyncMock(return_value=None),
        ):
            first = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="delete high priority tasks",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )
            second = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="all",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )
            third = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="yes",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertEqual(first["route"]["status"], "pending")
        self.assertEqual(first["route"]["pending"]["expected_response"], "number")
        self.assertEqual(second["parsed_value"], "all")
        self.assertEqual(second["next_expected_response"], "yes_no")
        self.assertEqual(third["route"]["status"], "success")
        self.assertEqual(third["route"]["deleted"]["count"], 3)
        self.assertTrue(all(task["is_deleted"] for task in tasks_store))
        self.assertEqual(len(inserted_logs), 3)


if __name__ == "__main__":
    unittest.main()
