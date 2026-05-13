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

    def test_unknown_to_general(self):
        self.assertEqual(lu.map_subtopic("xyz", "Python"), "general")

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


class AvailableSessionsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
