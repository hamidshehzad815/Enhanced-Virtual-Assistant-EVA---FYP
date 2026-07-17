"""Tests for utils/learning_utils.py."""

import unittest
from datetime import date, datetime

from utils import learning_utils as lu


class NormalizeTopicTests(unittest.TestCase):
    def test_alias_py(self):
        self.assertEqual(lu.normalize_topic("py"), "Python")

    def test_alias_js(self):
        self.assertEqual(lu.normalize_topic("js"), "JavaScript")

    def test_alias_golang(self):
        self.assertEqual(lu.normalize_topic("golang"), "Go")

    def test_canonical_pass_through(self):
        self.assertEqual(lu.normalize_topic("Python"), "Python")

    def test_unsupported(self):
        self.assertIsNone(lu.normalize_topic("React"))


class MapSubtopicTests(unittest.TestCase):
    def test_beginner_to_basics_real_json(self):
        self.assertEqual(lu.map_subtopic("beginner", "Python"), "basics")

    def test_intermediate_alias_real_json(self):
        self.assertEqual(lu.map_subtopic("mid", "Python"), "intermediate")

    def test_unknown_phrase_to_general(self):
        self.assertEqual(lu.map_subtopic("xyz", "Python"), "general")

    def test_array_does_not_force_basics_with_default_tracks(self):
        # Legacy alias "array" → basics was wrong for granular roadmaps; without a matching
        # track key, fall back to general (not basics) on the small default Python JSON.
        self.assertEqual(lu.map_subtopic("array", "Python"), "general")
        self.assertEqual(lu.map_subtopic("arrays", "Python"), "general")

    def test_array_prefers_granular_track_when_key_contains_term(self):
        keys = (
            "basics",
            "intermediate",
            "arrays tuples and dictionaries",
        )
        self.assertEqual(
            lu.map_subtopic("array", "X", level_keys=keys),
            "arrays tuples and dictionaries",
        )
        self.assertEqual(
            lu.map_subtopic("arrays", "X", level_keys=keys),
            "arrays tuples and dictionaries",
        )

    def test_empty_to_general(self):
        self.assertEqual(lu.map_subtopic("", "Python"), "general")
        self.assertEqual(lu.map_subtopic(None, "Python"), "general")

    def test_oop_with_matching_level_key(self):
        keys = ("general", "basics", "object oriented programming")
        self.assertEqual(
            lu.map_subtopic("oop", "Python", level_keys=keys),
            "object oriented programming",
        )

    def test_oop_list_with_ma_noise_not_loops(self):
        keys = (
            "basics",
            "loops",
            "object oriented programming",
            "lists tuples dictionaries sets",
        )
        self.assertEqual(
            lu.map_subtopic(["oop", "ma"], "Python", level_keys=keys),
            "object oriented programming",
        )

    def test_oop_stringified_list_not_loops(self):
        keys = ("loops", "object oriented programming")
        self.assertEqual(
            lu.map_subtopic("['oop', 'ma']", "Python", level_keys=keys),
            "object oriented programming",
        )

    def test_list_and_oop_prefers_oop_alias(self):
        keys = ("lists tuples dictionaries sets", "object oriented programming")
        self.assertEqual(
            lu.map_subtopic(["list", "oop", "ma"], "Python", level_keys=keys),
            "object oriented programming",
        )

    def test_begginers_typo_maps_to_basics(self):
        self.assertEqual(lu.map_subtopic("begginers", "Python"), "basics")

    def test_begginers_resolution_confident(self):
        res = lu.resolve_subtopic_mapping("begginers", "Python")
        self.assertEqual(res.roadmap_key, "basics")
        self.assertTrue(res.confident)

    def test_vague_subtopic_not_confident(self):
        res = lu.resolve_subtopic_mapping("beg", "Python")
        self.assertEqual(res.roadmap_key, "general")
        self.assertFalse(res.confident)

    def test_no_subtopic_confident_general(self):
        res = lu.resolve_subtopic_mapping(None, "Python")
        self.assertEqual(res.roadmap_key, "general")
        self.assertTrue(res.confident)


class NormalizeSubtopicEntityTests(unittest.TestCase):
    def test_drops_ma_from_list(self):
        self.assertEqual(lu.normalize_subtopic_entity(["oop", "ma"]), "oop")

    def test_drops_standalone_ma(self):
        self.assertIsNone(lu.normalize_subtopic_entity("ma"))
        self.assertIsNone(lu.normalize_subtopic_entity("MA"))

    def test_subtopic_hint_from_message(self):
        self.assertEqual(
            lu.subtopic_hint_from_message("create python oop roadmap"),
            "oop",
        )


class ParseDurationTests(unittest.TestCase):
    def test_weeks_months_days(self):
        self.assertEqual(lu.parse_duration("2 weeks"), 14)
        self.assertEqual(lu.parse_duration("1 month"), 30)
        self.assertEqual(lu.parse_duration("10 days"), 10)
        self.assertEqual(lu.parse_duration("3 months"), 90)
        self.assertEqual(lu.parse_duration("1 week"), 7)
        self.assertEqual(lu.parse_duration("6 months"), 180)

    def test_invalid(self):
        self.assertIsNone(lu.parse_duration("soon"))
        self.assertIsNone(lu.parse_duration(""))


class ExtractDurationDaysTests(unittest.TestCase):
    def test_embedded_for_one_month(self):
        self.assertEqual(lu.extract_duration_days("for 1 month"), 30)

    def test_sentence_with_weeks(self):
        self.assertEqual(lu.extract_duration_days("learn arrays from tomorrow for 3 weeks"), 21)


class DurationEntityToDaysTests(unittest.TestCase):
    def test_duckling_minutes_one_month(self):
        self.assertEqual(lu.duration_entity_to_days(30 * 24 * 60), 30)

    def test_plain_string_one_month(self):
        self.assertEqual(lu.duration_entity_to_days("1 month"), 30)

    def test_digit_string_minutes(self):
        self.assertEqual(lu.duration_entity_to_days(str(14 * 24 * 60)), 14)

    def test_short_int_not_treated_as_days(self):
        self.assertIsNone(lu.duration_entity_to_days(45))

    def test_list_wraps_first_value(self):
        self.assertEqual(lu.duration_entity_to_days(["30 days"]), 30)
    def test_mon_wed_fri_two_weeks(self):
        # 2025-01-06 is Monday
        start = date(2025, 1, 6)
        learning = {0, 2, 4}
        self.assertEqual(lu.calculate_available_sessions(start, 14, learning), 6)

    def test_mon_wed_fri_one_week(self):
        start = date(2025, 1, 6)
        learning = {0, 2, 4}
        self.assertEqual(lu.calculate_available_sessions(start, 7, learning), 3)

    def test_two_monday_slots_count_twice(self):
        start = date(2025, 1, 6)  # Monday
        slots = [
            {"day": 0, "time": "09:00", "duration_minutes": 60},
            {"day": 0, "time": "19:00", "duration_minutes": 60},
        ]
        self.assertEqual(lu.calculate_available_sessions(start, 7, slots), 2)
        self.assertEqual(lu.calculate_available_sessions(start, 14, slots), 4)

    def test_min_days_needed_with_multi_slot_monday(self):
        start = date(2025, 1, 6)
        slots = [
            {"day": 0, "time": "09:00", "duration_minutes": 60},
            {"day": 0, "time": "19:00", "duration_minutes": 60},
        ]
        self.assertEqual(lu.calculate_min_days_needed(start, 4, slots), 8)


class MinWeeksTests(unittest.TestCase):
    def test_ceil(self):
        self.assertEqual(lu.calculate_min_weeks_needed(12, 3), 4)


class RoadmapDensityTests(unittest.TestCase):
    def test_sessions_per_calendar_day(self):
        self.assertAlmostEqual(lu.roadmap_sessions_per_calendar_day(10, 5), 2.0)
        self.assertIsNone(lu.roadmap_sessions_per_calendar_day(10, None))
        self.assertIsNone(lu.roadmap_sessions_per_calendar_day(10, 0))


class BuildScheduleTests(unittest.TestCase):
    def test_skips_non_learning_days(self):
        start = date(2025, 1, 6)  # Monday
        schedule_slots = [
            {"day": 0, "time": "18:00"},
            {"day": 2, "time": "14:00"},
            {"day": 4, "time": "09:00"},
        ]
        topics = [
            {"order": 1, "title": "A", "resources": []},
            {"order": 2, "title": "B", "resources": [{"url": "x"}]},
            {"order": 3, "title": "C", "resources": []},
        ]
        out = lu.build_schedule(start, topics, schedule_slots, timezone_name="UTC")
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["title"], "A")
        self.assertEqual(out[1]["title"], "B")
        self.assertEqual(out[2]["title"], "C")
        self.assertEqual(out[0]["scheduled_date"], datetime(2025, 1, 6, 18, 0))
        self.assertEqual(out[1]["scheduled_date"], datetime(2025, 1, 8, 14, 0))
        self.assertEqual(out[2]["scheduled_date"], datetime(2025, 1, 10, 9, 0))
        self.assertEqual(out[1]["resources"], [{"url": "x"}])

    def test_two_slots_same_monday(self):
        start = date(2025, 1, 6)  # Monday
        schedule_slots = [
            {"day": 0, "time": "09:00", "duration_minutes": 60},
            {"day": 0, "time": "19:00", "duration_minutes": 45},
        ]
        topics = [
            {"order": 1, "title": "Morning", "resources": []},
            {"order": 2, "title": "Evening", "resources": []},
            {"order": 3, "title": "NextMonAM", "resources": []},
        ]
        out = lu.build_schedule(start, topics, schedule_slots, timezone_name="UTC")
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["scheduled_date"], datetime(2025, 1, 6, 9, 0))
        self.assertEqual(out[0]["duration_minutes"], 60)
        self.assertEqual(out[1]["scheduled_date"], datetime(2025, 1, 6, 19, 0))
        self.assertEqual(out[1]["duration_minutes"], 45)
        self.assertEqual(out[2]["scheduled_date"], datetime(2025, 1, 13, 9, 0))
        self.assertEqual(out[0]["title"], "Morning")
        self.assertEqual(out[1]["title"], "Evening")

    def test_converts_user_local_slot_to_utc_naive(self):
        """09:40 Asia/Karachi on Friday → 04:40 UTC stored."""
        start = date(2026, 6, 5)  # Friday
        schedule_slots = [{"day": 4, "time": "09:40", "duration_minutes": 60}]
        topics = [{"order": 1, "title": "Intro", "resources": []}]
        out = lu.build_schedule(
            start,
            topics,
            schedule_slots,
            timezone_name="Asia/Karachi",
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["scheduled_date"], datetime(2026, 6, 5, 4, 40))

    def test_monday_6pm_karachi_stored_as_utc(self):
        start = date(2026, 6, 8)  # Monday
        schedule_slots = [{"day": 0, "time": "18:00", "duration_minutes": 60}]
        topics = [{"order": 1, "title": "S1", "resources": []}]
        out = lu.build_schedule(
            start,
            topics,
            schedule_slots,
            timezone_name="Asia/Karachi",
        )
        self.assertEqual(out[0]["scheduled_date"], datetime(2026, 6, 8, 13, 0))

    def test_empty_learning_schedule(self):
        self.assertEqual(
            lu.build_schedule(date(2025, 1, 1), [{"title": "T"}], []),
            [],
        )


class DetectLearningSubIntentTests(unittest.TestCase):
    def test_pause_keywords(self):
        self.assertEqual(lu.detect_learning_sub_intent("pause my Python"), "pause")
        self.assertEqual(lu.detect_learning_sub_intent("put my plan on hold"), "pause")
        self.assertEqual(lu.detect_learning_sub_intent("hold my python roadmap"), "pause")
        self.assertEqual(lu.detect_learning_sub_intent("freeze my javascript plan"), "pause")
        self.assertEqual(lu.detect_learning_sub_intent("halt kotlin for now"), "pause")
        self.assertEqual(lu.detect_learning_sub_intent("take a break from python"), "pause")
        self.assertEqual(lu.detect_learning_sub_intent("stop my python learning for now"), "pause")

    def test_resume_keywords(self):
        self.assertEqual(lu.detect_learning_sub_intent("resume Python basics"), "resume")
        self.assertEqual(lu.detect_learning_sub_intent("continue my javascript plan"), "resume")
        self.assertEqual(lu.detect_learning_sub_intent("unpause my go roadmap"), "resume")
        self.assertEqual(lu.detect_learning_sub_intent("pick up python again"), "resume")
        self.assertEqual(lu.detect_learning_sub_intent("get back to javascript"), "resume")
        self.assertEqual(lu.detect_learning_sub_intent("restart my rust plan"), "resume")

    def test_complete_keywords(self):
        self.assertEqual(
            lu.detect_learning_sub_intent("mark next session done"),
            "complete",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("mark next python session as done"),
            "complete",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("mark next Python basics session done"),
            "complete",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("mark python next session as done"),
            "complete",
        )
        self.assertEqual(lu.detect_learning_sub_intent("I finished today's session"), "complete")
        self.assertEqual(lu.detect_learning_sub_intent("complete my python session"), "complete")
        self.assertEqual(lu.detect_learning_sub_intent("i did today's session"), "complete")
        self.assertEqual(lu.detect_learning_sub_intent("session done"), "complete")
        self.assertEqual(
            lu.detect_learning_sub_intent("mark today's python session as done"),
            "complete",
        )

    def test_skip_next_session_with_topic(self):
        self.assertEqual(
            lu.detect_learning_sub_intent("skip next python session"),
            "skip",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("skip python next session"),
            "skip",
        )

    def test_skip_keywords(self):
        self.assertEqual(lu.detect_learning_sub_intent("skip today's topic"), "skip")
        self.assertEqual(lu.detect_learning_sub_intent("bypass this session"), "skip")
        self.assertEqual(lu.detect_learning_sub_intent("pass on next topic"), "skip")
        self.assertEqual(lu.detect_learning_sub_intent("jump past this lesson"), "skip")
        self.assertEqual(lu.detect_learning_sub_intent("move past this topic"), "skip")
        self.assertEqual(lu.detect_learning_sub_intent("already know this module"), "skip")

    def test_reschedule_keywords(self):
        self.assertEqual(
            lu.detect_learning_sub_intent("reschedule to Monday"),
            "reschedule",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("move my session to Friday"),
            "reschedule",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("postpone python to next week"),
            "reschedule",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("push my session to Tuesday"),
            "reschedule",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("shift python to next monday"),
            "reschedule",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("change my session date to friday"),
            "reschedule",
        )

    def test_reschedule_wins_over_finished_in_same_message(self):
        self.assertEqual(
            lu.detect_learning_sub_intent(
                "i finished, reschedule my python session to next monday",
            ),
            "reschedule",
        )

    def test_reschedule_typo_and_session_to_date(self):
        msg = "reschdule python session to june4"
        self.assertTrue(lu.message_implies_reschedule(msg))
        self.assertEqual(lu.detect_learning_sub_intent(msg), "reschedule")

    def test_ambiguous_returns_none(self):
        self.assertIsNone(lu.detect_learning_sub_intent("update my learning plan"))
        self.assertIsNone(lu.detect_learning_sub_intent(""))
        self.assertIsNone(lu.detect_learning_sub_intent(None))


class ComputeSessionStateTests(unittest.TestCase):
    def _session(self, scheduled: datetime, status: str = "pending") -> dict:
        return {"status": status, "scheduled_date": scheduled}

    def test_completed_and_skipped_passthrough(self):
        now = datetime(2025, 6, 10, 12, 0)
        self.assertEqual(
            lu.compute_session_state(
                self._session(now, status="completed"),
                now,
            ),
            "completed",
        )
        self.assertEqual(
            lu.compute_session_state(
                self._session(now, status="skipped"),
                now,
            ),
            "skipped",
        )

    def test_locked_when_more_than_24h_before_schedule(self):
        scheduled = datetime(2025, 6, 15, 18, 0)
        now = datetime(2025, 6, 10, 12, 0)
        state = lu.compute_session_state(self._session(scheduled), now)
        self.assertEqual(state, "locked")

    def test_unlocked_future_within_24h_before_schedule(self):
        scheduled = datetime(2025, 6, 10, 18, 0)
        now = datetime(2025, 6, 10, 10, 0)
        state = lu.compute_session_state(self._session(scheduled), now)
        self.assertEqual(state, "unlocked_future")

    def test_ongoing_during_scheduled_session_window(self):
        scheduled = datetime(2025, 6, 10, 9, 0)
        now = datetime(2025, 6, 10, 10, 0)
        state = lu.compute_session_state(
            {
                "status": "pending",
                "scheduled_date": scheduled,
                "estimated_duration": 90,
            },
            now,
        )
        self.assertEqual(state, "ongoing")

    def test_ongoing_at_scheduled_start(self):
        scheduled = datetime(2025, 6, 10, 13, 45)
        state = lu.compute_session_state(
            {
                "status": "pending",
                "scheduled_date": scheduled,
                "estimated_duration": 90,
            },
            scheduled,
        )
        self.assertEqual(state, "ongoing")

    def test_overdue_after_session_window_ends(self):
        scheduled = datetime(2025, 6, 10, 9, 0)
        now = datetime(2025, 6, 10, 10, 31)
        state = lu.compute_session_state(
            {
                "status": "pending",
                "scheduled_date": scheduled,
                "estimated_duration": 90,
            },
            now,
        )
        self.assertEqual(state, "overdue")

    def test_short_gap_unlocks_after_previous_resolved(self):
        prev_scheduled = datetime(2025, 6, 10, 9, 0)
        scheduled = datetime(2025, 6, 10, 15, 0)
        prev_resolved = datetime(2025, 6, 10, 10, 0)
        now = datetime(2025, 6, 10, 11, 0)
        state = lu.compute_session_state(
            self._session(scheduled),
            now,
            previous_scheduled_date=prev_scheduled,
            previous_resolved_at=prev_resolved,
        )
        self.assertEqual(state, "unlocked_future")

    def test_short_gap_stays_locked_until_previous_resolved(self):
        prev_scheduled = datetime(2025, 6, 10, 9, 0)
        scheduled = datetime(2025, 6, 10, 15, 0)
        now = datetime(2025, 6, 10, 11, 0)
        state = lu.compute_session_state(
            self._session(scheduled),
            now,
            previous_scheduled_date=prev_scheduled,
            previous_resolved_at=None,
        )
        self.assertEqual(state, "locked")

    def test_mixed_naive_and_aware_datetimes_do_not_raise(self):
        """Mongo often returns naive UTC; now may be timezone-aware from get_zoneinfo."""
        from zoneinfo import ZoneInfo

        prev_scheduled = datetime(2026, 6, 4, 18, 0)  # naive, session 1 done
        scheduled = datetime(2026, 6, 5, 8, 0)  # naive, session 2
        now = datetime(2026, 6, 5, 6, 0, tzinfo=ZoneInfo("Asia/Karachi"))
        state = lu.compute_session_state(
            self._session(scheduled),
            now,
            previous_scheduled_date=prev_scheduled,
            previous_resolved_at=datetime(2026, 6, 4, 19, 0),
        )
        self.assertEqual(state, "unlocked_future")


class NextRebaseStartDateTests(unittest.TestCase):
    def test_uses_same_day_when_slot_still_upcoming(self):
        # Saturday 01:27, slot Saturday 01:50
        now = datetime(2026, 6, 27, 1, 27, 0)
        schedule = [
            {"day": 5, "time": "01:50", "duration_minutes": 15},
            {"day": 0, "time": "08:00", "duration_minutes": 60},
        ]
        self.assertEqual(lu.next_rebase_start_date(now, schedule), date(2026, 6, 27))

    def test_skips_same_day_when_slot_already_passed(self):
        # Saturday 01:55, slot Saturday 01:50 -> next Monday
        now = datetime(2026, 6, 27, 1, 55, 0)
        schedule = [
            {"day": 5, "time": "01:50", "duration_minutes": 15},
            {"day": 0, "time": "08:00", "duration_minutes": 60},
        ]
        self.assertEqual(lu.next_rebase_start_date(now, schedule), date(2026, 6, 29))

    def test_uses_today_when_slot_is_later_same_day(self):
        now = datetime(2026, 6, 27, 1, 10, 0)
        schedule = [{"day": 5, "time": "01:15", "duration_minutes": 60}]
        self.assertEqual(lu.next_rebase_start_date(now, schedule), date(2026, 6, 27))


class ResolveLearningReminderMinutesTests(unittest.TestCase):
    def test_uses_learning_setting(self):
        self.assertEqual(
            lu.resolve_learning_reminder_minutes({"default_learning_reminder_minutes": 20}),
            20,
        )

    def test_default_when_missing(self):
        self.assertEqual(lu.resolve_learning_reminder_minutes({}), 15)

    def test_ignores_task_reminder_setting(self):
        self.assertEqual(
            lu.resolve_learning_reminder_minutes({"default_reminder_minutes": 30}),
            15,
        )


if __name__ == "__main__":
    unittest.main()
