"""Tests for delete time-of-day matching without a date."""
from datetime import datetime
import unittest

from db.tasks import _filter_rows_by_time_of_day


class TestDeleteTimeOfDay(unittest.TestCase):
    def test_matches_local_time_within_window(self):
        # Asia/Karachi is UTC+5, so 12:00 UTC == 17:00 local
        rows = [
            {"_id": "a", "due_datetime": datetime(2026, 7, 20, 12, 0, 0)},
            {"_id": "b", "due_datetime": datetime(2026, 7, 20, 10, 0, 0)},
        ]
        matched = _filter_rows_by_time_of_day(rows, "17:00:00", "Asia/Karachi")
        self.assertEqual([r["_id"] for r in matched], ["a"])

    def test_rejects_outside_window(self):
        rows = [{"_id": "a", "due_datetime": datetime(2026, 7, 20, 12, 0, 0)}]
        matched = _filter_rows_by_time_of_day(rows, "10:00:00", "Asia/Karachi")
        self.assertEqual(matched, [])


if __name__ == "__main__":
    unittest.main()
