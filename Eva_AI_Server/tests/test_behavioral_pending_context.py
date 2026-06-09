"""
Behavioral pending-context tests through main.process_message.
"""
from datetime import datetime
from types import SimpleNamespace
import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


def _import_ai_main_with_stubs():
    """
    Import main.py while tolerating environments without torch.
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
        _shared_ner = _StubModel()
        fake_ner.ner_extractor = _shared_ner
        fake_ner.learning_ner_extractor = _shared_ner
        fake_ner.get_ner_extractor_for_intent = lambda _intent: _shared_ner

        sys.modules["pipeline.classifier1"] = fake_classifier1
        sys.modules["pipeline.classifier2"] = fake_classifier2
        sys.modules["pipeline.ner"] = fake_ner
        sys.modules.pop("main", None)
        return importlib.import_module("main")


ai_main = _import_ai_main_with_stubs()

USER_ID = "507f1f77bcf86cd799439011"
SESSION_ID = "69c0c6d79c98840a2697022f"


def _fetched(context):
    return SimpleNamespace(
        user={
            "name": "Hamid",
            "timezone": "Asia/Karachi",
        },
        settings={"behavioral_analytics_enabled": True},
        history=[],
        integrations=[],
        context=context,
    )


class TestBehavioralPendingContext(unittest.IsolatedAsyncioTestCase):
    async def test_free_text_weekday_reply_routes_behavioral_handler(self):
        pending_context = {
            "expected_response": "free_text",
            "missing_entity": "day",
            "pending_action": {
                "intent": "behavioral",
                "sub_intent": "best_time_for_day",
                "entities": {},
            },
        }
        payload = ai_main.ProcessRequest(
            message="Friday",
            user_id=USER_ID,
            session_id=SESSION_ID,
            input_type="text",
            timestamp=datetime(2026, 4, 13, 10, 0, 0),
        )

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "main.route_intent",
            new=AsyncMock(
                return_value={
                    "status": "success",
                    "intent": "behavioral",
                    "response_text": "done",
                    "notifications": [],
                }
            ),
        ) as mock_route:
            result = await ai_main.process_message(payload)

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["handler_status"], "success")
        self.assertEqual(result["route"]["intent"], "behavioral")
        self.assertEqual(str(result["merged_entities"]["day"]).lower(), "friday")
        mock_clear.assert_awaited_once_with(USER_ID)
        mock_route.assert_awaited_once()

    async def test_pending_behavioral_cancel_clears_context(self):
        pending_context = {
            "expected_response": "free_text",
            "pending_action": {
                "intent": "behavioral",
                "sub_intent": "best_time_for_day",
                "entities": {},
            },
        }
        payload = ai_main.ProcessRequest(
            message="cancel",
            user_id=USER_ID,
            session_id=SESSION_ID,
            input_type="text",
            timestamp=datetime(2026, 4, 13, 10, 5, 0),
        )

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "main._safe_reply",
            return_value="ACTION:pending_cancelled",
        ), patch(
            "main.route_intent",
            new=AsyncMock(return_value={}),
        ) as mock_route:
            result = await ai_main.process_message(payload)

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["response_text"], "ACTION:pending_cancelled")
        mock_clear.assert_awaited_once_with(USER_ID)
        mock_route.assert_not_awaited()

    async def test_pending_behavioral_invalid_day_asks_again_and_keeps_context(self):
        pending_context = {
            "expected_response": "free_text",
            "pending_action": {
                "intent": "behavioral",
                "sub_intent": "best_time_for_day",
                "entities": {},
            },
        }
        payload = ai_main.ProcessRequest(
            message="tomorrow at 5pm",
            user_id=USER_ID,
            session_id=SESSION_ID,
            input_type="text",
            timestamp=datetime(2026, 4, 13, 10, 10, 0),
        )

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch(
            "main.route_intent",
            new=AsyncMock(
                return_value={
                    "status": "pending",
                    "intent": "behavioral",
                    "response_text": "ACTION:behavioral_ask_day",
                    "notifications": [],
                    "pending": {
                        "expected_response": "free_text",
                        "missing_entity": "day",
                    },
                }
            ),
        ) as mock_route:
            result = await ai_main.process_message(payload)

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["expected_response"], "free_text")
        self.assertEqual(result["response_text"], "ACTION:behavioral_ask_day")
        mock_route.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
