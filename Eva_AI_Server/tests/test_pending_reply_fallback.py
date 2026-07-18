"""
Unit tests for Gemini pending-reply fallback (issue #73).

Mocks GeminiService — no real API calls.
"""
from __future__ import annotations

import unittest
from datetime import date
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


class TestDateFallback(unittest.TestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    def test_from_monday_resolves_relative_to_reference_date(self):
        # Wed 2026-07-15 -> "from monday" means the upcoming Monday, 2026-07-20.
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"date":"2026-07-20","confidence":0.95}',
        ):
            result = fallback.resolve_date_fallback(
                "from monday",
                eva_prompt="When would you like to start?",
                reference_date=date(2026, 7, 15),
            )
            self.assertEqual(result, "2026-07-20")

    def test_none_reasks(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"date":"none","confidence":0.2}',
        ):
            self.assertIsNone(fallback.resolve_date_fallback("whenever"))

    def test_past_date_rejected_unless_allowed(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"date":"2020-01-01","confidence":0.9}',
        ):
            self.assertIsNone(
                fallback.resolve_date_fallback(
                    "January 1 2020", reference_date=date(2026, 7, 15),
                )
            )

    def test_past_date_allowed_when_flagged(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"date":"2020-01-01","confidence":0.9}',
        ):
            self.assertEqual(
                fallback.resolve_date_fallback(
                    "January 1 2020",
                    reference_date=date(2026, 7, 15),
                    allow_past=True,
                ),
                "2020-01-01",
            )

    def test_unparseable_date_rejected(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"date":"not-a-date","confidence":0.9}',
        ):
            self.assertIsNone(fallback.resolve_date_fallback("blah"))

    def test_low_confidence_rejected(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"date":"2026-07-20","confidence":0.3}',
        ):
            self.assertIsNone(
                fallback.resolve_date_fallback(
                    "from monday", reference_date=date(2026, 7, 15),
                )
            )

    def test_flag_off_skips_gemini(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = False
        with patch.object(
            fallback.gemini_service, "generate_constrained_text",
        ) as mock_call:
            self.assertIsNone(fallback.resolve_date_fallback("from monday"))
            mock_call.assert_not_called()


class TestTimeFallback(unittest.TestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    def test_five_pm_resolves(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"time":"17:00","confidence":0.95}',
        ):
            self.assertEqual(fallback.resolve_time_fallback("5pm"), "17:00:00")

    def test_none_reasks(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"time":"none","confidence":0.2}',
        ):
            self.assertIsNone(fallback.resolve_time_fallback("later"))

    def test_malformed_time_rejected(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"time":"25:99","confidence":0.9}',
        ):
            self.assertIsNone(fallback.resolve_time_fallback("blah"))


class TestDurationFallback(unittest.TestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    def test_two_weeks_in_days(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"amount":14,"confidence":0.95}',
        ):
            self.assertEqual(
                fallback.resolve_duration_fallback("2 weeks", unit="days"),
                14,
            )

    def test_hour_and_half_in_minutes(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"amount":90,"confidence":0.95}',
        ):
            self.assertEqual(
                fallback.resolve_duration_fallback(
                    "an hour and a half", unit="minutes", min_value=5, max_value=1440,
                ),
                90,
            )

    def test_out_of_range_rejected(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"amount":5000,"confidence":0.95}',
        ):
            self.assertIsNone(
                fallback.resolve_duration_fallback(
                    "way too long", unit="minutes", min_value=5, max_value=1440,
                )
            )

    def test_none_reasks(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"amount":"none","confidence":0.2}',
        ):
            self.assertIsNone(
                fallback.resolve_duration_fallback("dunno", unit="days")
            )


class TestEnumFallback(unittest.TestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    def test_topic_resolves_from_free_text(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"value":"Python","confidence":0.97}',
        ):
            self.assertEqual(
                fallback.resolve_enum_fallback(
                    "py please", ["Python", "JavaScript", "SQL"], kind="topic",
                ),
                "Python",
            )

    def test_value_not_in_set_rejected(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"value":"Haskell","confidence":0.97}',
        ):
            self.assertIsNone(
                fallback.resolve_enum_fallback(
                    "haskell", ["Python", "JavaScript", "SQL"], kind="topic",
                )
            )

    def test_case_mismatch_tolerated(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"value":"python","confidence":0.97}',
        ):
            self.assertEqual(
                fallback.resolve_enum_fallback(
                    "py", ["Python", "JavaScript", "SQL"], kind="topic",
                ),
                "Python",
            )

    def test_priority_enum(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"value":"high","confidence":0.9}',
        ):
            self.assertEqual(
                fallback.resolve_enum_fallback(
                    "urgent please", ["low", "medium", "high"], kind="priority",
                ),
                "high",
            )

    def test_none_reasks(self):
        with patch.object(
            fallback.gemini_service,
            "generate_constrained_text",
            return_value='{"value":"none","confidence":0.2}',
        ):
            self.assertIsNone(
                fallback.resolve_enum_fallback(
                    "whatever", ["low", "medium", "high"], kind="priority",
                )
            )

    def test_empty_allowed_values_returns_none(self):
        self.assertIsNone(
            fallback.resolve_enum_fallback("anything", [], kind="topic")
        )


if __name__ == "__main__":
    unittest.main()
