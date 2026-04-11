"""
Unit tests for Google Calendar event payload timezone handling.
"""
import unittest

from services.google_calendar import GoogleCalendarClient


class TestGoogleCalendarService(unittest.TestCase):
    def test_build_event_payload_converts_utc_naive_to_pkt_local_time(self):
        payload = GoogleCalendarClient._build_event_payload(
            {
                "title": "physics exam",
                "due_datetime": "2026-03-30T11:00:00",
                "duration_minutes": 60,
                "timezone": "PKT",
            }
        )

        self.assertEqual(payload["start"]["timeZone"], "Asia/Karachi")
        self.assertEqual(payload["end"]["timeZone"], "Asia/Karachi")
        self.assertEqual(payload["start"]["dateTime"], "2026-03-30T16:00:00+05:00")
        self.assertEqual(payload["end"]["dateTime"], "2026-03-30T17:00:00+05:00")

    def test_build_event_payload_supports_duration_and_reminder_override(self):
        payload = GoogleCalendarClient._build_event_payload(
            {
                "title": "chemistry lab",
                "due_datetime": "2026-03-30T11:00:00",
                "duration": 90,
                "timezone": "PKT",
                "reminder_minutes_before": 30,
            }
        )

        self.assertEqual(payload["start"]["dateTime"], "2026-03-30T16:00:00+05:00")
        self.assertEqual(payload["end"]["dateTime"], "2026-03-30T17:30:00+05:00")
        self.assertIn("reminders", payload)
        self.assertEqual(payload["reminders"]["useDefault"], False)
        self.assertEqual(payload["reminders"]["overrides"][0]["minutes"], 30)


if __name__ == "__main__":
    unittest.main()
