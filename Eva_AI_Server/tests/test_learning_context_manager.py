"""
Phase 7 — learning_create pending free-text (topic / start_date / duration).
"""

import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

# Allow collecting this module when `torch` / real `pipeline.ner` are not importable yet.
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


def _ctx(stage: str, entities=None):
    return {
        "expected_response": "free_text",
        "pending_action": {
            "intent": "learning_create",
            "stage": stage,
            "entities": dict(entities or {}),
        },
    }


class LearningCreatePendingTests(unittest.IsolatedAsyncioTestCase):
    # These tests exercise the deterministic-parse retry path, not the Gemini
    # fallback (that has its own dedicated tests in
    # test_pending_reply_fallback.py). Force the flag off so a real .env with
    # USE_GEMINI_PENDING_REPLY=true can't make these hit the live network.
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = False

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    async def test_topic_valid_merges(self):
        ctx = _ctx("topic", {})
        with patch.object(
            cm.learning_ner_extractor,
            "extract",
            return_value={"topic": "Python", "subtopic": "basics"},
        ), patch.object(cm.learning_ner_extractor, "loaded", True):
            out = await cm.process_learning_create_free_text_reply(
                ctx,
                "I want to learn Python basics",
                user_timezone="UTC",
                preferred_learning_schedule=[{"day": 0, "time": "09:00"}],
            )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["topic"], "Python")
        self.assertEqual(out["merged_entities"]["subtopic"], "basics")

    async def test_topic_missing_retries(self):
        ctx = _ctx("topic", {})
        with patch.object(
            cm.learning_ner_extractor,
            "extract",
            return_value={},
        ), patch.object(cm.learning_ner_extractor, "loaded", True):
            out = await cm.process_learning_create_free_text_reply(
                ctx,
                "maybe later",
                user_timezone="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "retry")

    async def test_topic_unsupported_clears(self):
        ctx = _ctx("topic", {})
        with patch.object(
            cm.learning_ner_extractor,
            "extract",
            return_value={"topic": "Klingon"},
        ), patch.object(cm.learning_ner_extractor, "loaded", True):
            out = await cm.process_learning_create_free_text_reply(
                ctx,
                "Klingon",
                user_timezone="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "unsupported_topic")

    async def test_start_date_valid_merges(self):
        ctx = _ctx("start_date", {"topic": "Python"})
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value="2026-06-15"),
        ), patch.object(cm, "_today_in_user_tz", return_value=__import__("datetime").date(2026, 6, 1)):
            out = await cm.process_learning_create_free_text_reply(
                ctx,
                "June 15",
                user_timezone="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["start_date"], "2026-06-15")

    async def test_start_date_past_retries(self):
        ctx = _ctx("start_date", {"topic": "Python"})
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value="2026-01-01"),
        ), patch.object(cm, "_today_in_user_tz", return_value=__import__("datetime").date(2026, 6, 1)):
            out = await cm.process_learning_create_free_text_reply(
                ctx,
                "Jan 1 2026",
                user_timezone="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "retry")

    async def test_start_date_unparsed_retries(self):
        ctx = _ctx("start_date", {"topic": "Python"})
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value=None),
        ):
            out = await cm.process_learning_create_free_text_reply(
                ctx,
                "blah",
                user_timezone="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "retry")

    async def test_start_date_gemini_rescues_when_duckling_down(self):
        # Reproduces the reported bug: Duckling unreachable/fails to parse
        # "from monday" -> Gemini fallback resolves it against today's date.
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        ctx = _ctx("start_date", {"topic": "Python"})
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch.object(cm, "_today_in_user_tz", return_value=__import__("datetime").date(2026, 7, 15)), \
        patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"2026-07-20","confidence":0.95}',
        ):
            out = await cm.process_learning_create_free_text_reply(
                ctx,
                "from monday",
                user_timezone="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["start_date"], "2026-07-20")

    async def test_start_date_still_retries_when_gemini_also_unsure(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        ctx = _ctx("start_date", {"topic": "Python"})
        with patch.object(
            cm.duckling_client,
            "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"none","confidence":0.2}',
        ):
            out = await cm.process_learning_create_free_text_reply(
                ctx,
                "blah",
                user_timezone="UTC",
                preferred_learning_schedule=[],
            )
        self.assertEqual(out["outcome"], "retry")

    async def test_duration_short_merges_for_handler_counteroffer(self):
        # Duration stage only parses; feasibility / counter-offer is in learning_create.
        ctx = _ctx(
            "duration",
            {"topic": "Python", "start_date": "2026-06-01"},
        )
        out = await cm.process_learning_create_free_text_reply(
            ctx,
            "3 days",
            user_timezone="UTC",
            preferred_learning_schedule=[{"day": 0, "time": "09:00"}],
        )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["duration_days"], 3)

    async def test_duration_merges_without_schedule_check(self):
        ctx = _ctx(
            "duration",
            {"topic": "Python", "start_date": "2026-06-01"},
        )
        out = await cm.process_learning_create_free_text_reply(
            ctx,
            "2 weeks",
            user_timezone="UTC",
            preferred_learning_schedule=[],
        )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["duration_days"], 14)

    async def test_duration_feasible_merges(self):
        ctx = _ctx(
            "duration",
            {"topic": "Python", "start_date": "2026-06-01"},
        )
        out = await cm.process_learning_create_free_text_reply(
            ctx,
            "2 weeks",
            user_timezone="UTC",
            preferred_learning_schedule=[{"day": 0, "time": "09:00"}],
        )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["duration_days"], 14)


if __name__ == "__main__":
    unittest.main()
