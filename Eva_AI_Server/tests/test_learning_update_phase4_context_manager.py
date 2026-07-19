"""
Phase 4 tests for learning_update context manager helpers.
"""

import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


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


from config import settings as settings_module
from context import context_manager as cm


def _update_ctx(stage: str, sub_intent: str, **pending_kwargs):
    pending_action = {
        "intent": "learning_update",
        "sub_intent": sub_intent,
        "stage": stage,
        "goal_ids": pending_kwargs.pop("goal_ids", []),
        "goals": pending_kwargs.pop("goals", []),
        "entities": pending_kwargs.pop("entities", {}),
    }
    pending_action.update(pending_kwargs)
    return {
        "expected_response": "free_text",
        "pending_action": pending_action,
    }


class LearningUpdateContextManagerTests(unittest.IsolatedAsyncioTestCase):
    # Deterministic-parse retry path, not the Gemini fallback (dedicated tests
    # in test_pending_reply_fallback.py) — keep hermetic regardless of a real
    # .env's USE_GEMINI_PENDING_REPLY value.
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = False

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    async def test_state1_free_text_valid_topic_merges(self):
        ctx = _update_ctx("identify", "pause")
        with patch.object(
            cm.learning_ner_extractor,
            "extract",
            return_value={"topic": "Python", "subtopic": "basics"},
        ), patch.object(cm.learning_ner_extractor, "loaded", True), patch.object(
            cm,
            "normalize_topic",
            return_value="Python",
        ), patch.object(cm, "map_subtopic", return_value="basics"):
            out = await cm.process_learning_update_free_text_reply(
                ctx,
                "Python basics",
                user_name="Ali",
                timezone_name="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["topic"], "Python")
        self.assertEqual(out["merged_entities"]["subtopic"], "basics")
        self.assertEqual(out["merged_entities"]["roadmap_key"], "basics")

    async def test_state1_free_text_missing_topic_retries(self):
        ctx = _update_ctx("identify", "pause")
        with patch.object(
            cm.learning_ner_extractor,
            "extract",
            return_value={},
        ), patch.object(cm.learning_ner_extractor, "loaded", True):
            out = await cm.process_learning_update_free_text_reply(
                ctx,
                "maybe later",
                user_name="Ali",
                timezone_name="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "retry")
        self.assertIn("Python", out["message"])

    async def test_state5_new_date_valid_learning_day_merges(self):
        ctx = _update_ctx("new_date", "reschedule", entities={"topic": "Python"})
        # Use a stable future Monday so the handler doesn't reject it as past.
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value="2030-06-17"),
        ):
            out = await cm.process_learning_update_free_text_reply(
                ctx,
                "next Monday",
                user_name="Ali",
                timezone_name="UTC",
                preferred_learning_schedule=[{"day": 0, "time": "18:00"}],
            )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["date"], "2030-06-17")

    async def test_state5_new_date_not_learning_day_retries(self):
        ctx = _update_ctx("new_date", "reschedule")
        # Use a stable future Tuesday so the handler reaches the learning-day validation.
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value="2030-06-18"),
        ):
            out = await cm.process_learning_update_free_text_reply(
                ctx,
                "next Tuesday",
                user_name="Ali",
                timezone_name="UTC",
                preferred_learning_schedule=[{"day": 0, "time": "18:00"}],
            )
        self.assertEqual(out["outcome"], "retry")
        self.assertIn("learning days", out["message"])

    async def test_state5_new_date_unparseable_retries(self):
        ctx = _update_ctx("new_date", "reschedule")
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value=None),
        ):
            out = await cm.process_learning_update_free_text_reply(
                ctx,
                "someday",
                user_name="Ali",
                timezone_name="UTC",
                preferred_learning_schedule=[{"day": 0, "time": "18:00"}],
            )
        self.assertEqual(out["outcome"], "retry")
        self.assertIn("date", out["message"].lower())

    async def test_state5_new_date_gemini_rescues_when_duckling_down(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        ctx = _update_ctx("new_date", "reschedule", entities={"topic": "Python"})
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"2030-06-17","confidence":0.95}',
        ):
            out = await cm.process_learning_update_free_text_reply(
                ctx,
                "from monday",
                user_name="Ali",
                timezone_name="UTC",
                preferred_learning_schedule=[{"day": 0, "time": "18:00"}],
            )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["date"], "2030-06-17")

    def test_confirm_messages(self):
        goal = {"title": "Python basics"}
        self.assertIn("Pause", cm.learning_update_confirm_message(goal, sub_intent="pause", user_name="Ali"))
        self.assertIn("Resume", cm.learning_update_confirm_message(goal, sub_intent="resume", user_name="Ali"))


if __name__ == "__main__":
    unittest.main()

