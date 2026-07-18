"""
Gemini fallback wiring for scheduling_update's date/time/duration/priority/
status resolution (handlers/scheduling/update.py).
"""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from config import settings as settings_module
from handlers.scheduling import update as update_handler


class TestUpdateResolverFallbacks(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = False

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    async def test_resolve_update_date_duckling_success_short_circuits_gemini(self):
        with patch.object(
            update_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value="2030-06-17"),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
        ) as mock_gemini:
            result = await update_handler._resolve_update_date("next Monday", "UTC")
        self.assertEqual(result, "2030-06-17")
        mock_gemini.assert_not_called()

    async def test_resolve_update_date_gemini_rescues_and_allows_past(self):
        # Past-date rejection happens downstream against the combined
        # datetime, so this function itself should allow a past date.
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            update_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"2020-01-01","confidence":0.95}',
        ):
            result = await update_handler._resolve_update_date("from monday", "UTC")
        self.assertEqual(result, "2020-01-01")

    async def test_resolve_update_time_gemini_rescues(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            update_handler.duckling_client, "resolve_time",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"time":"17:00","confidence":0.9}',
        ):
            result = await update_handler._resolve_update_time("5ish", "UTC")
        self.assertEqual(result, "17:00:00")

    async def test_parse_duration_minutes_gemini_rescues(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            update_handler.duckling_client, "resolve_duration",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"amount":90,"confidence":0.9}',
        ):
            result = await update_handler._parse_duration_minutes(
                "an hour and a half",
            )
        self.assertEqual(result, 90)

    async def test_resolve_identifier_date_gemini_rescues_and_allows_past(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            update_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"2020-01-01","confidence":0.9}',
        ), patch.object(
            update_handler, "local_day_bounds_to_utc_naive",
            return_value=(1, 2),
        ):
            candidate, day_range = await update_handler._resolve_identifier_date(
                "last monday", "UTC",
            )
        self.assertEqual(candidate, "2020-01-01")
        self.assertIsNotNone(day_range)

    async def test_flag_off_leaves_date_unresolved(self):
        with patch.object(
            update_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value=None),
        ):
            result = await update_handler._resolve_update_date("from monday", "UTC")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
