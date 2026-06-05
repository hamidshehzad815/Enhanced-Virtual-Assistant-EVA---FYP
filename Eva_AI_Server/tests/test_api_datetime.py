"""Tests for API datetime localization helpers."""
import unittest
from datetime import datetime

from utils.api_datetime import (
    localize_api_payload,
    serialize_stored_datetime,
    with_api_timezone,
)


class TestApiDatetime(unittest.TestCase):
    def test_serialize_stored_datetime_karachi(self):
        stored = datetime(2026, 6, 5, 4, 40, 0)
        result = serialize_stored_datetime(stored, "Asia/Karachi")
        self.assertEqual(result, "2026-06-05T09:40:00+05:00")

    def test_localize_task_payload(self):
        payload = {
            "task_id": "abc",
            "due_datetime": datetime(2026, 6, 5, 7, 0, 0),
        }
        localized = localize_api_payload(payload, "Asia/Karachi")
        self.assertEqual(localized["due_datetime"], "2026-06-05T12:00:00+05:00")

    def test_with_api_timezone_adds_field(self):
        out = with_api_timezone({"due_datetime": datetime(2026, 6, 5, 7, 0, 0)}, "Asia/Karachi")
        self.assertEqual(out["timezone"], "Asia/Karachi")
        self.assertEqual(out["due_datetime"], "2026-06-05T12:00:00+05:00")


if __name__ == "__main__":
    unittest.main()
