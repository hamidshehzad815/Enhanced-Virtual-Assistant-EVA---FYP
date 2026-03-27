"""
Unit tests for timezone conversion helpers.
"""
import unittest
from datetime import datetime

from utils.timezone_utils import (
    local_datetime_to_utc_naive,
    local_day_bounds_to_utc_naive,
    resolve_timezone_name,
    utc_naive_to_local,
)


class TestTimezoneUtils(unittest.TestCase):
    def test_pkt_alias_resolves_to_karachi(self):
        self.assertEqual(resolve_timezone_name("PKT"), "Asia/Karachi")

    def test_ist_alias_resolves_to_kolkata(self):
        self.assertEqual(resolve_timezone_name("IST"), "Asia/Kolkata")

    def test_local_datetime_pkt_converts_to_utc_naive(self):
        utc_dt = local_datetime_to_utc_naive(
            "2026-03-30",
            "16:00:00",
            "PKT",
        )
        self.assertEqual(utc_dt, datetime(2026, 3, 30, 11, 0, 0))

    def test_local_datetime_ist_converts_to_utc_naive(self):
        utc_dt = local_datetime_to_utc_naive(
            "2026-03-30",
            "16:00:00",
            "IST",
        )
        self.assertEqual(utc_dt, datetime(2026, 3, 30, 10, 30, 0))

    def test_local_day_bounds_pkt_convert_to_utc_window(self):
        start_utc, end_utc = local_day_bounds_to_utc_naive(
            "2026-03-30",
            "PKT",
        )
        self.assertEqual(start_utc, datetime(2026, 3, 29, 19, 0, 0))
        self.assertEqual(end_utc, datetime(2026, 3, 30, 18, 59, 59, 999999))

    def test_utc_naive_to_local_pkt(self):
        local_dt = utc_naive_to_local("2026-03-30T11:00:00", "PKT")
        self.assertIsNotNone(local_dt)
        self.assertEqual(local_dt.strftime("%Y-%m-%d %H:%M:%S"), "2026-03-30 16:00:00")


if __name__ == "__main__":
    unittest.main()
