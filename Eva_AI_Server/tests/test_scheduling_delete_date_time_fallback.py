"""
Gemini fallback wiring for scheduling_delete's date/time resolution
(handlers/scheduling/delete.py::_resolve_date_filter and the inline time
resolution in handle_scheduling_delete).
"""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from config import settings as settings_module
from handlers.scheduling import delete as delete_handler


class TestResolveDateFilterFallback(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = False

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    async def test_duckling_success_short_circuits_gemini(self):
        with patch.object(
            delete_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value="2026-06-15"),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
        ) as mock_gemini, patch.object(
            delete_handler, "local_day_bounds_to_utc_naive",
            return_value=(1, 2),
        ):
            candidate, day_range = await delete_handler._resolve_date_filter(
                "next Monday", "UTC",
            )
        self.assertEqual(candidate, "2026-06-15")
        mock_gemini.assert_not_called()

    async def test_duckling_miss_falls_back_to_gemini_allows_past_date(self):
        # Deleting past tasks is valid, unlike scheduling a new one.
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            delete_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"2020-01-01","confidence":0.95}',
        ), patch.object(
            delete_handler, "local_day_bounds_to_utc_naive",
            return_value=(1, 2),
        ):
            candidate, day_range = await delete_handler._resolve_date_filter(
                "from last monday", "UTC",
            )
        self.assertEqual(candidate, "2020-01-01")
        self.assertIsNotNone(day_range)

    async def test_both_miss_returns_none(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            delete_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"none","confidence":0.1}',
        ):
            candidate, day_range = await delete_handler._resolve_date_filter(
                "blah", "UTC",
            )
        self.assertIsNone(candidate)
        self.assertIsNone(day_range)


if __name__ == "__main__":
    unittest.main()
