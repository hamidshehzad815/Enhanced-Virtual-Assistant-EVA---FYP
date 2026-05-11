"""
Phase 5 tests for core productivity scoring engine.
"""
from datetime import datetime, timedelta, timezone
import unittest

from services.productivity_scorer import (
    get_best_time_for_day,
    get_productive_days,
    get_productive_hours,
    get_scheduling_suggestion,
    score_all_slots,
)


def _log(
    day: int,
    hour: int,
    *,
    on_time: bool = True,
    reschedule_count: int = 0,
    time_taken: int = 60,
    duration: int = 60,
    ts: datetime | None = None,
):
    return {
        "day_of_week": day,
        "hour_of_day": hour,
        "scheduled_day": day,
        "scheduled_hour": hour,
        "was_on_time": on_time,
        "reschedule_count": reschedule_count,
        "time_taken_minutes": time_taken,
        "duration": duration,
        "action_timestamp": ts or datetime.now(timezone.utc),
    }


class TestProductivityScorer(unittest.TestCase):
    def test_score_all_slots_empty_returns_empty(self):
        self.assertEqual(score_all_slots([]), {})

    def test_score_all_slots_monday_18_highest(self):
        logs = []
        for _ in range(5):
            logs.append(_log(0, 18, on_time=True, reschedule_count=0, time_taken=50))
        for _ in range(2):
            logs.append(_log(0, 10, on_time=True, reschedule_count=0, time_taken=60))

        scores = score_all_slots(logs)
        self.assertGreater(scores[(0, 18)], scores[(0, 10)])

    def test_score_all_slots_time_decay_recent_beats_old(self):
        now = datetime.now(timezone.utc)
        logs = [
            _log(0, 10, ts=now - timedelta(days=90)),
            _log(0, 11, ts=now - timedelta(days=1)),
        ]

        scores = score_all_slots(logs)
        self.assertGreater(scores[(0, 11)], scores[(0, 10)])

    def test_score_all_slots_reschedule_penalty_lowers_score(self):
        now = datetime.now(timezone.utc)
        logs = [
            _log(0, 10, ts=now, reschedule_count=0),
            _log(0, 11, ts=now, reschedule_count=3),
        ]

        scores = score_all_slots(logs)
        self.assertGreater(scores[(0, 10)], scores[(0, 11)])

    def test_score_all_slots_missing_time_taken_defaults_efficiency(self):
        logs = [
            _log(0, 10, time_taken=60, duration=60),
            {
                "day_of_week": 0,
                "hour_of_day": 11,
                "scheduled_day": 0,
                "scheduled_hour": 11,
                "was_on_time": True,
                "reschedule_count": 0,
                "action_timestamp": datetime.now(timezone.utc),
            },
        ]
        scores = score_all_slots(logs)
        self.assertIn((0, 10), scores)
        self.assertIn((0, 11), scores)

    def test_get_productive_hours_returns_sorted_metadata(self):
        logs = [
            _log(0, 18),
            _log(0, 18),
            _log(0, 10),
        ]
        rows = get_productive_hours(logs)
        self.assertGreaterEqual(rows[0]["score"], rows[1]["score"])
        self.assertIn("hour_display", rows[0])
        self.assertIn("on_time_rate", rows[0])
        self.assertIn("log_count", rows[0])

    def test_get_productive_hours_day_filter(self):
        logs = [
            _log(0, 18),
            _log(1, 12),
        ]
        rows = get_productive_hours(logs, day=0)
        self.assertTrue(rows)
        self.assertTrue(all(row["day_num"] == 0 for row in rows))

    def test_get_productive_days_reliable_and_unreliable(self):
        logs = []
        for _ in range(6):
            logs.append(_log(0, 18, on_time=True))
        for _ in range(4):
            logs.append(_log(1, 18, on_time=True))

        counts = {0: 6, 1: 4, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        result = get_productive_days(logs, counts, per_day_threshold=5)
        reliable_days = {row["day_num"] for row in result["reliable"]}
        unreliable_days = {row["day_num"] for row in result["unreliable"]}

        self.assertIn(0, reliable_days)
        self.assertIn(1, unreliable_days)

    def test_get_best_time_for_day_uses_next_best_when_first_conflicts(self):
        logs = []
        for _ in range(5):
            logs.append(_log(0, 18))
        for _ in range(4):
            logs.append(_log(0, 20))

        existing_tasks = [
            {
                "due_datetime": datetime(2026, 4, 20, 18, 30, 0),
                "duration": 90,
            }
        ]
        best = get_best_time_for_day(logs, day=0, existing_tasks=existing_tasks)
        self.assertEqual(best["start_hour"], 20)
        self.assertTrue(best["conflict_free"])

    def test_get_best_time_for_day_returns_none_when_all_conflict(self):
        logs = []
        for _ in range(5):
            logs.append(_log(0, 18))
        for _ in range(4):
            logs.append(_log(0, 20))

        existing_tasks = [
            {"due_datetime": datetime(2026, 4, 20, 18, 0, 0), "duration": 120},
            {"due_datetime": datetime(2026, 4, 20, 20, 0, 0), "duration": 120},
        ]
        best = get_best_time_for_day(logs, day=0, existing_tasks=existing_tasks)
        self.assertIsNone(best["best_range"])
        self.assertFalse(best["conflict_free"])

    def test_get_scheduling_suggestion_has_data_false_when_no_reliable_days(self):
        logs = [_log(0, 18), _log(1, 10)]
        counts = {day: 0 for day in range(7)}
        counts[0] = 1
        counts[1] = 1
        suggestion = get_scheduling_suggestion(logs, counts, existing_tasks={})
        self.assertFalse(suggestion["has_data"])

    def test_get_scheduling_suggestion_returns_day_and_range(self):
        logs = []
        for _ in range(6):
            logs.append(_log(0, 18))
        counts = {day: 0 for day in range(7)}
        counts[0] = 6
        suggestion = get_scheduling_suggestion(logs, counts, existing_tasks={0: []}, day=0)
        self.assertEqual(suggestion["day_num"], 0)
        self.assertTrue(suggestion["has_data"])


if __name__ == "__main__":
    unittest.main()
