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
        out = lu.build_schedule(start, topics, schedule_slots)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["title"], "A")
        self.assertEqual(out[1]["title"], "B")
        self.assertEqual(out[2]["title"], "C")
        self.assertEqual(out[0]["scheduled_date"], datetime(2025, 1, 6, 18, 0))
        self.assertEqual(out[1]["scheduled_date"], datetime(2025, 1, 8, 14, 0))
        self.assertEqual(out[2]["scheduled_date"], datetime(2025, 1, 10, 9, 0))
        self.assertEqual(out[1]["resources"], [{"url": "x"}])

    def test_empty_learning_schedule(self):
        self.assertEqual(
            lu.build_schedule(date(2025, 1, 1), [{"title": "T"}], []),
            [],
        )


class DetectLearningSubIntentTests(unittest.TestCase):
    def test_pause_keywords(self):
        self.assertEqual(lu.detect_learning_sub_intent("pause my Python"), "pause")
        self.assertEqual(lu.detect_learning_sub_intent("put my plan on hold"), "pause")

    def test_resume_keywords(self):
        self.assertEqual(lu.detect_learning_sub_intent("resume Python basics"), "resume")
        self.assertEqual(lu.detect_learning_sub_intent("continue my javascript plan"), "resume")

    def test_complete_keywords(self):
        self.assertEqual(
            lu.detect_learning_sub_intent("mark next session done"),
            "complete",
        )
        self.assertEqual(lu.detect_learning_sub_intent("I finished today's session"), "complete")

    def test_skip_keywords(self):
        self.assertEqual(lu.detect_learning_sub_intent("skip today's topic"), "skip")
        self.assertEqual(lu.detect_learning_sub_intent("bypass this session"), "skip")

    def test_reschedule_keywords(self):
        self.assertEqual(
            lu.detect_learning_sub_intent("reschedule to Monday"),
            "reschedule",
        )
        self.assertEqual(
            lu.detect_learning_sub_intent("move my session to Friday"),
            "reschedule",
        )

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

    def test_overdue_after_scheduled_time(self):
        scheduled = datetime(2025, 6, 10, 9, 0)
        now = datetime(2025, 6, 10, 12, 0)
        state = lu.compute_session_state(self._session(scheduled), now)
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


if __name__ == "__main__":
    unittest.main()
