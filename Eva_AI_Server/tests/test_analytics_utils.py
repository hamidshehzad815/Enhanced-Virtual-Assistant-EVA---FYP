"""
Phase 4/10 tests for analytics utility helpers.
"""
from datetime import datetime, timedelta, timezone
import unittest

from utils.analytics_utils import (
    aggregate_day_scores,
    build_hour_ranges,
    compute_slot_score,
    compute_time_decay,
    filter_reliable_days,
    get_best_day_overall,
    get_best_range_for_day,
    get_top_days,
    get_top_slots,
    normalize_scores,
)
from utils.date_utils import days_since


class TestAnalyticsUtils(unittest.TestCase):
    def test_days_since_today_is_near_zero(self):
        now = datetime.now(timezone.utc)
        value = days_since(now)
        self.assertGreaterEqual(value, 0.0)
        self.assertLess(value, 0.01)

    def test_days_since_30_days_ago(self):
        ts = datetime.now(timezone.utc) - timedelta(days=30)
        value = days_since(ts)
        self.assertGreaterEqual(value, 29.9)
        self.assertLessEqual(value, 30.1)

    def test_compute_time_decay_reference_points(self):
        self.assertAlmostEqual(compute_time_decay(0), 1.0, places=6)
        self.assertAlmostEqual(compute_time_decay(30), 0.7408, places=3)
        self.assertAlmostEqual(compute_time_decay(90), 0.4066, places=3)

    def test_normalize_scores_basic(self):
        raw = {(0, 10): 0.2, (1, 10): 0.4, (2, 10): 0.8}
        normalized = normalize_scores(raw)
        self.assertAlmostEqual(normalized[(0, 10)], 0.25, places=6)
        self.assertAlmostEqual(normalized[(1, 10)], 0.5, places=6)
        self.assertAlmostEqual(normalized[(2, 10)], 1.0, places=6)

    def test_normalize_scores_all_zeros(self):
        raw = {(0, 10): 0.0, (1, 10): 0.0}
        normalized = normalize_scores(raw)
        self.assertEqual(normalized, {(0, 10): 0.0, (1, 10): 0.0})

    def test_compute_slot_score_known_input(self):
        score = compute_slot_score(volume=0.8, reliability=0.75, efficiency=0.6, penalty=0.9)
        expected = (0.35 * 0.8 + 0.40 * 0.75 + 0.25 * 0.6) * 0.9
        self.assertAlmostEqual(score, expected, places=6)

    def test_build_hour_ranges_consecutive_merge(self):
        ranges = build_hour_ranges([(18, 0.8), (19, 0.7), (20, 0.3)], threshold=0.6, merge_threshold=0.6)
        self.assertEqual(ranges, ["6PM-8PM"])

    def test_build_hour_ranges_gap_separate(self):
        ranges = build_hour_ranges([(10, 0.7), (11, 0.7), (18, 0.8), (20, 0.9)], threshold=0.6, merge_threshold=0.6)
        self.assertEqual(ranges, ["10AM-12PM", "6PM", "8PM"])

    def test_build_hour_ranges_empty(self):
        ranges = build_hour_ranges([(10, 0.3), (11, 0.2)], threshold=0.6, merge_threshold=0.6)
        self.assertEqual(ranges, [])

    def test_build_hour_ranges_single_hour(self):
        ranges = build_hour_ranges([(18, 0.8)], threshold=0.6, merge_threshold=0.6)
        self.assertEqual(ranges, ["6PM"])

    def test_aggregate_day_scores(self):
        slot_scores = {
            (0, 10): 0.8,
            (0, 11): 0.6,
            (1, 14): 0.9,
        }
        day_scores = aggregate_day_scores(slot_scores)
        self.assertAlmostEqual(day_scores[0], 0.7, places=6)
        self.assertAlmostEqual(day_scores[1], 0.9, places=6)

    def test_filter_reliable_days(self):
        counts = {0: 5, 1: 4, 2: 0, 3: 9}
        reliable, unreliable = filter_reliable_days(counts, per_day_threshold=5)
        self.assertIn(0, reliable)
        self.assertIn(3, reliable)
        self.assertIn(1, unreliable)
        self.assertIn(2, unreliable)

    def test_get_top_slots(self):
        slot_scores = {
            (0, 10): 0.7,
            (1, 14): 0.9,
            (2, 18): 0.6,
            (3, 9): 0.85,
        }
        top = get_top_slots(slot_scores, n=3)
        self.assertEqual(top, [(1, 14), (3, 9), (0, 10)])

    def test_get_top_days(self):
        day_scores = {0: 0.7, 1: 0.9, 2: 0.6, 3: 0.85}
        top = get_top_days(day_scores, reliable_days={0, 1, 3}, n=2)
        self.assertEqual(top, [{"day": 1, "score": 0.9}, {"day": 3, "score": 0.85}])

    def test_get_best_range_for_day(self):
        slot_scores = {
            (0, 18): 0.8,
            (0, 19): 0.75,
            (1, 10): 0.9,
        }
        best = get_best_range_for_day(slot_scores, day=0)
        self.assertEqual(best, "6PM-8PM")

    def test_get_best_day_overall(self):
        day_scores = {0: 0.7, 1: 0.9, 2: 0.6}
        best = get_best_day_overall(day_scores, reliable_days={0, 1})
        self.assertEqual(best, 1)

    def test_get_best_day_overall_none_when_no_reliable(self):
        day_scores = {0: 0.7, 1: 0.9}
        best = get_best_day_overall(day_scores, reliable_days=set())
        self.assertIsNone(best)


if __name__ == "__main__":
    unittest.main()
