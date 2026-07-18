"""
Unit tests for Gemini pending-reply fallback (issue #73).

Mocks GeminiService — no real API calls.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from config import settings as settings_module
from pipeline import pending_reply_fallback as fallback


class TestPendingReplyFallback(unittest.TestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        self._min = settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE
        self._min_dest = (
            settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE_DESTRUCTIVE
        )
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE = 0.7
        settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE_DESTRUCTIVE = 0.85

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag
        settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE = self._min
        settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE_DESTRUCTIVE = (
            self._min_dest
        )

    def test_flag_off_skips_gemini(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = False
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"yes","confidence":0.99}',
        ) as mock_call:
            self.assertIsNone(fallback.resolve_yes_no_fallback("go for it"))
            mock_call.assert_not_called()

    def test_yes_no_go_for_it(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"yes","confidence":0.96}',
        ):
            self.assertEqual(
                fallback.resolve_yes_no_fallback("go for it"),
                "yes",
            )

    def test_yes_no_nah_im_good(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"no","confidence":0.91}',
        ):
            self.assertEqual(
                fallback.resolve_yes_no_fallback("nah I'm good"),
                "no",
            )

    def test_yes_no_none_reasks(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"none","confidence":0.4}',
        ):
            self.assertIsNone(fallback.resolve_yes_no_fallback("asdfgh"))

    def test_yes_no_empty_skips_gemini(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"yes","confidence":0.99}',
        ) as mock_call:
            self.assertIsNone(fallback.resolve_yes_no_fallback("   "))
            mock_call.assert_not_called()

    def test_destructive_low_confidence_yes_rejected(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"yes","confidence":0.72}',
        ):
            self.assertIsNone(
                fallback.resolve_yes_no_fallback(
                    "I guess so",
                    destructive=True,
                )
            )

    def test_destructive_high_confidence_yes_accepted(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"yes","confidence":0.9}',
        ):
            self.assertEqual(
                fallback.resolve_yes_no_fallback(
                    "go for it",
                    destructive=True,
                ),
                "yes",
            )

    def test_list_python_one(self):
        options = [
            {"id": "gid_1", "index": 1, "label": "Python basics"},
            {"id": "gid_2", "index": 2, "label": "JavaScript"},
        ]
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"gid_1","confidence":0.96}',
        ):
            self.assertEqual(
                fallback.resolve_list_choice_fallback(
                    "the python one",
                    options,
                    allow_all=True,
                ),
                "gid_1",
            )

    def test_list_first_and_last_via_id(self):
        options = [
            {"id": "a", "index": 1, "label": "Alpha"},
            {"id": "b", "index": 2, "label": "Beta"},
            {"id": "c", "index": 3, "label": "Gamma"},
        ]
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"c","confidence":0.93}',
        ):
            self.assertEqual(
                fallback.resolve_list_choice_fallback("the last one", options),
                "c",
            )

    def test_list_rejects_spoofed_id(self):
        options = [
            {"id": "gid_1", "index": 1, "label": "Python"},
            {"id": "gid_2", "index": 2, "label": "Java"},
        ]
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"gid_hacker","confidence":0.99}',
        ):
            self.assertIsNone(
                fallback.resolve_list_choice_fallback("whatever", options)
            )

    def test_list_all_only_when_allowed(self):
        options = [
            {"id": "gid_1", "index": 1, "label": "Python"},
            {"id": "gid_2", "index": 2, "label": "Java"},
        ]
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"all","confidence":0.95}',
        ):
            self.assertIsNone(
                fallback.resolve_list_choice_fallback(
                    "delete both",
                    options,
                    allow_all=False,
                )
            )
            self.assertEqual(
                fallback.resolve_list_choice_fallback(
                    "delete both",
                    options,
                    allow_all=True,
                ),
                "all",
            )

    def test_list_malformed_json_is_none(self):
        options = [{"id": "gid_1", "index": 1, "label": "Python"}]
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value="not json at all",
        ):
            self.assertIsNone(
                fallback.resolve_list_choice_fallback("python", options)
            )

    def test_list_low_confidence_rejected(self):
        options = [{"id": "gid_1", "index": 1, "label": "Python"}]
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"choice":"gid_1","confidence":0.4}',
        ):
            self.assertIsNone(
                fallback.resolve_list_choice_fallback("python?", options)
            )

    def test_breaker_open_returns_none(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value=None,
        ):
            self.assertIsNone(fallback.resolve_yes_no_fallback("go for it"))

    def test_build_options_from_tasks_and_goals(self):
        task_opts = fallback.build_options_from_tasks(
            ["t1", "t2"],
            [{"title": "Physics"}, {"title": "Chem"}],
        )
        self.assertEqual(task_opts[0]["id"], "t1")
        self.assertEqual(task_opts[0]["label"], "Physics")
        goal_opts = fallback.build_options_from_goals(
            ["g1"],
            [{"title": "", "subject": "python", "roadmap_key": "basics"}],
        )
        self.assertEqual(goal_opts[0]["label"], "python basics")

    def test_is_destructive_intent(self):
        self.assertTrue(fallback.is_destructive_yes_no_intent("learning_delete"))
        self.assertTrue(fallback.is_destructive_yes_no_intent("delete"))
        self.assertFalse(fallback.is_destructive_yes_no_intent("learning_create"))


class TestDeterministicStillFirst(unittest.TestCase):
    """Gemini must not be called when deterministic resolvers already hit."""

    def test_yes_no_keywords_do_not_need_fallback(self):
        from context.context_manager import handle_yes_no_reply

        self.assertEqual(handle_yes_no_reply("yes"), "yes")
        self.assertEqual(handle_yes_no_reply("go ahead"), "yes")
        self.assertEqual(handle_yes_no_reply("nope"), "no")
        # Natural phrases still miss deterministically — that is the fallback's job.
        self.assertEqual(handle_yes_no_reply("go for it"), "invalid")
        self.assertEqual(handle_yes_no_reply("sounds good"), "invalid")

    def test_number_choice_still_digit_first(self):
        from context.context_manager import handle_number_delete

        context = {
            "pending_action": {
                "task_ids": ["a", "b", "c"],
                "tasks": [
                    {"title": "Alpha"},
                    {"title": "Beta"},
                    {"title": "Gamma"},
                ],
            }
        }
        self.assertEqual(handle_number_delete("2", context), "b")
        self.assertEqual(handle_number_delete("all", context), "all")
        self.assertEqual(handle_number_delete("the python one", context), "invalid")


if __name__ == "__main__":
    unittest.main()
