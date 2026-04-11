"""
Phase 25 tests for update-context pending state handling.
"""
from types import SimpleNamespace
import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


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


class TestUpdatePhase25ContextManager(unittest.IsolatedAsyncioTestCase):
    async def test_state1_identify_free_text_reenters_with_task_name(self):
        pending_context = {
            "expected_response": "free_text",
            "pending_action": {
                "intent": "update",
                "stage": "identify",
                "entities": {"new_priority": "high"},
            },
        }
        route_result = {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": "Update flow resumed",
            "notifications": [],
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch(
            "main.route_intent",
            new=AsyncMock(return_value=route_result),
        ) as mock_route, patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="physics exam",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["merged_entities"]["task_name"], "physics exam")
        self.assertEqual(result["route"]["intent"], "scheduling_update")
        mock_route.assert_awaited_once()
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_state2_number_selects_task_and_moves_to_confirm_when_updates_exist(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "update",
                "stage": "identify",
                "task_ids": ["id1", "id2", "id3"],
                "tasks": [
                    {"title": "Physics exam", "due_datetime": "2026-03-26T10:00:00", "priority": "high"},
                    {"title": "Physics lab", "due_datetime": "2026-03-26T12:00:00", "priority": "medium"},
                    {"title": "Physics quiz", "due_datetime": "2026-03-26T15:00:00", "priority": "low"},
                ],
                "entities": {"new_priority": "high"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="2",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        updated_context = mock_set.await_args.args[1]
        updated_pending = updated_context["pending_action"]
        self.assertEqual(updated_pending["task_id"], "id2")
        self.assertEqual(updated_pending["stage"], "confirm")
        self.assertEqual(updated_context["expected_response"], "yes_no")
        self.assertEqual(result["next_expected_response"], "yes_no")
        self.assertEqual(result["parsed_value"], "id2")

    async def test_state2_number_selects_task_and_moves_to_what_to_update_when_no_updates(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "update",
                "stage": "identify",
                "task_ids": ["id1", "id2"],
                "tasks": [
                    {"title": "Physics exam", "due_datetime": "2026-03-26T10:00:00", "priority": "high"},
                    {"title": "Physics lab", "due_datetime": "2026-03-26T12:00:00", "priority": "medium"},
                ],
                "entities": {},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="1",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        updated_context = mock_set.await_args.args[1]
        updated_pending = updated_context["pending_action"]
        self.assertEqual(updated_pending["task_id"], "id1")
        self.assertEqual(updated_pending["stage"], "what_to_update")
        self.assertEqual(updated_context["expected_response"], "free_text")
        self.assertEqual(result["next_expected_response"], "free_text")
        self.assertEqual(result["parsed_value"], "id1")

    async def test_state3_what_to_update_free_text_extracts_fields_and_reroutes(self):
        pending_context = {
            "expected_response": "free_text",
            "pending_action": {
                "intent": "update",
                "stage": "what_to_update",
                "task_id": "id1",
                "task": {"title": "Physics exam"},
                "entities": {"task_name": "physics exam"},
            },
        }
        route_result = {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": "Update step 5 resumed",
            "notifications": [],
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.ner_extractor,
            "loaded",
            True,
        ), patch.object(
            ai_main.ner_extractor,
            "extract",
            return_value={"new_priority": "high"},
        ), patch(
            "main.scope_entities",
            return_value={"new_priority": "high"},
        ), patch(
            "main.resolve_all",
            new=AsyncMock(return_value={"new_priority": "high"}),
        ), patch(
            "main.route_intent",
            new=AsyncMock(return_value=route_result),
        ) as mock_route, patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="priority to high",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["extracted_update_fields"], {"new_priority": "high"})
        self.assertEqual(result["merged_entities"]["new_priority"], "high")
        self.assertEqual(result["route"]["intent"], "scheduling_update")
        mock_route.assert_awaited_once()
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_state3_what_to_update_free_text_with_no_fields_asks_again(self):
        pending_context = {
            "expected_response": "free_text",
            "pending_action": {
                "intent": "update",
                "stage": "what_to_update",
                "task_id": "id1",
                "task": {"title": "Physics exam"},
                "entities": {"task_name": "physics exam"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.ner_extractor,
            "loaded",
            True,
        ), patch.object(
            ai_main.ner_extractor,
            "extract",
            return_value={},
        ), patch(
            "main.scope_entities",
            return_value={},
        ), patch(
            "main.resolve_all",
            new=AsyncMock(return_value={}),
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="whatever",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["expected_response"], "free_text")
        self.assertEqual(result["stage"], "what_to_update")
        self.assertIn("didn't catch what to update", result["response_text"])
        mock_set.assert_awaited_once()

    async def test_state4_confirm_yes_routes_update(self):
        pending_context = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "update",
                "stage": "confirm",
                "task_id": "id1",
                "task": {"title": "Physics exam"},
                "entities": {"task_name": "physics exam", "new_priority": "high"},
            },
        }
        route_result = {
            "status": "success",
            "intent": "scheduling_update",
            "response_text": "Updated",
            "notifications": [],
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ), patch(
            "main.route_intent",
            new=AsyncMock(return_value=route_result),
        ) as mock_route, patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="yes",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["parsed_value"], "yes")
        self.assertEqual(result["route"]["intent"], "scheduling_update")
        mock_route.assert_awaited_once()
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_state4_confirm_no_cancels(self):
        pending_context = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "update",
                "stage": "confirm",
                "task_id": "id1",
                "task": {"title": "Physics exam"},
                "entities": {"task_name": "physics exam", "new_priority": "high"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="no",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["parsed_value"], "no")
        self.assertIn("kept Physics exam unchanged", result["response_text"])
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_cancel_clears_update_pending_state(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "update",
                "stage": "identify",
                "task_ids": ["id1", "id2"],
                "tasks": [{"title": "A"}, {"title": "B"}],
                "entities": {},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
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
        mock_clear.assert_awaited_once_with(USER_ID)

    async def test_new_command_while_update_confirm_pending_is_blocked(self):
        pending_context = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "update",
                "stage": "confirm",
                "task_id": "id1",
                "task": {"title": "Physics exam"},
                "entities": {"new_priority": "high"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
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
                    message="update another task",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["response_text"], "ACTION:pending_waiting_reply")

    async def test_ttl_expiry_starts_fresh_update_flow(self):
        route_result = {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": "Update flow started fresh",
            "notifications": [],
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(context=None)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "command"},
        ), patch.object(
            ai_main.classifier2,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier2,
            "predict",
            return_value={"label": "update"},
        ), patch.object(
            ai_main.ner_extractor,
            "loaded",
            True,
        ), patch.object(
            ai_main.ner_extractor,
            "extract",
            return_value={"task_name": "physics exam", "new_priority": "high"},
        ), patch(
            "main.scope_entities",
            return_value={"task_name": "physics exam", "new_priority": "high"},
        ), patch(
            "main.resolve_all",
            new=AsyncMock(return_value={"task_name": "physics exam", "new_priority": "high"}),
        ), patch(
            "main.route_intent",
            new=AsyncMock(return_value=route_result),
        ) as mock_route:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="change physics exam priority to high",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertFalse(result.get("context_handled", False))
        self.assertEqual(result["route"]["intent"], "scheduling_update")
        self.assertEqual(result["response_text"], "Update flow started fresh")
        mock_route.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
