"""
Phase 4 tests for learning_delete context manager helpers.
"""

import sys
import types
import unittest
from unittest.mock import patch

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

from context import context_manager as cm


def _delete_ctx(expected: str, **pending_kwargs):
    pending_action = {
        "intent": "learning_delete",
        "goal_ids": pending_kwargs.pop("goal_ids", []),
        "goals": pending_kwargs.pop("goals", []),
        "bulk": pending_kwargs.pop("bulk", False),
        "entities": pending_kwargs.pop("entities", {}),
    }
    pending_action.update(pending_kwargs)
    return {
        "expected_response": expected,
        "pending_action": pending_action,
    }


class LearningDeleteContextManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_free_text_valid_topic_merges(self):
        ctx = _delete_ctx("free_text")
        with patch.object(
            cm.learning_ner_extractor,
            "extract",
            return_value={"topic": "Python", "subtopic": "basics"},
        ), patch.object(cm.learning_ner_extractor, "loaded", True), patch.object(
            cm,
            "map_subtopic",
            return_value="basics",
        ):
            out = await cm.process_learning_delete_free_text_reply(
                ctx,
                "Python basics",
                user_name="Ali",
            )
        self.assertEqual(out["outcome"], "merged")
        self.assertEqual(out["merged_entities"]["topic"], "Python")
        self.assertEqual(out["merged_entities"]["subtopic"], "basics")
        self.assertEqual(out["merged_entities"]["roadmap_key"], "basics")

    async def test_free_text_missing_topic_retries(self):
        ctx = _delete_ctx("free_text")
        with patch.object(
            cm.learning_ner_extractor,
            "extract",
            return_value={},
        ), patch.object(cm.learning_ner_extractor, "loaded", True):
            out = await cm.process_learning_delete_free_text_reply(
                ctx,
                "maybe later",
                user_name="Ali",
            )
        self.assertEqual(out["outcome"], "retry")
        self.assertIn("didn't catch", out["message"])

    async def test_free_text_unsupported_topic(self):
        ctx = _delete_ctx("free_text")
        with patch.object(
            cm.learning_ner_extractor,
            "extract",
            return_value={"topic": "Klingon"},
        ), patch.object(cm.learning_ner_extractor, "loaded", True), patch.object(
            cm,
            "normalize_topic",
            return_value=None,
        ):
            out = await cm.process_learning_delete_free_text_reply(
                ctx,
                "Klingon",
                user_name="Ali",
            )
        self.assertEqual(out["outcome"], "unsupported_topic")

    def test_cancel_message(self):
        self.assertIn("nothing was deleted", cm.learning_delete_cancel_message("Ali"))

    def test_number_selection_moves_to_single_confirm(self):
        ctx = _delete_ctx(
            "number",
            goal_ids=["g1", "g2"],
            goals=[
                {
                    "title": "Python basics",
                    "status": "active",
                    "completed_topics": 3,
                    "total_topics": 8,
                },
                {
                    "title": "Python functions",
                    "status": "active",
                    "completed_topics": 0,
                    "total_topics": 5,
                },
            ],
        )
        choice = cm.handle_number_learning_delete("1", ctx)
        self.assertEqual(choice, "g1")
        msg = cm.learning_delete_single_confirm_message(ctx["pending_action"]["goals"][0], "Ali")
        self.assertIn("Python basics", msg)
        self.assertIn("delete", msg.lower())

    def test_number_all_keyword(self):
        ctx = _delete_ctx(
            "number",
            goal_ids=["g1", "g2"],
            goals=[{"title": "Python basics"}, {"title": "Python functions"}],
            entities={"topic": "Python"},
        )
        self.assertEqual(cm.handle_number_learning_delete("all", ctx), "all")
        msg = cm.learning_delete_bulk_confirm_message(
            ctx["pending_action"]["goals"],
            ctx["pending_action"]["entities"],
            "Ali",
        )
        self.assertIn("delete all 2", msg)
        self.assertIn("Completed sessions", msg)

    def test_number_invalid_range(self):
        ctx = _delete_ctx("number", goal_ids=["g1", "g2"])
        self.assertEqual(cm.handle_number_learning_delete("9", ctx), "invalid_range")

    def test_blocked_command_messages(self):
        yes_ctx = _delete_ctx(
            "yes_no",
            goals=[{"title": "Python basics"}],
        )
        self.assertIn("Python basics", cm.learning_delete_blocked_command_message(yes_ctx, "Ali"))

        num_ctx = _delete_ctx("number", goal_ids=["g1", "g2"])
        self.assertIn("Say cancel", cm.learning_delete_blocked_command_message(num_ctx, "Ali"))

    def test_yes_no_and_cancel_helpers(self):
        self.assertTrue(cm.is_cancel("never mind"))
        self.assertEqual(cm.handle_yes_no_reply("yes"), "yes")
        self.assertEqual(cm.handle_yes_no_reply("keep it"), "no")
        self.assertTrue(cm.is_all_keyword("all goals"))


if __name__ == "__main__":
    unittest.main()
