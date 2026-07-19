"""
Gemini fallback wiring for scheduling_add's date/time resolution
(handlers/scheduling/add.py::_resolve_date_time).

_resolve_date_time is the single choke point both the original message's
extracted date/time AND a user's follow-up reply to "what date?"/"what time?"
flow through (the reply is blind-merged into entities["date"]/["time"] by
context_manager.handle_free_text_reply, then the handler re-runs from the
top). Testing it directly covers both paths in one place.
"""
from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from config import settings as settings_module
from handlers.scheduling import add as add_handler


class TestResolveDateTimeFallback(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_PENDING_REPLY
        settings_module.settings.USE_GEMINI_PENDING_REPLY = False

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_PENDING_REPLY = self._flag

    async def test_duckling_success_short_circuits_gemini(self):
        with patch.object(
            add_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value="2030-06-17"),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
        ) as mock_gemini:
            date_value, time_value = await add_handler._resolve_date_time(
                {"date": "next Monday"}, "UTC",
            )
        self.assertEqual(date_value, "2030-06-17")
        mock_gemini.assert_not_called()

    async def test_duckling_miss_falls_back_to_gemini_for_date(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            add_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"2030-06-17","confidence":0.95}',
        ):
            date_value, time_value = await add_handler._resolve_date_time(
                {"date": "from monday"}, "UTC",
            )
        self.assertEqual(date_value, "2030-06-17")

    async def test_gemini_flag_off_leaves_date_unresolved(self):
        with patch.object(
            add_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value=None),
        ):
            date_value, time_value = await add_handler._resolve_date_time(
                {"date": "from monday"}, "UTC",
            )
        self.assertIsNone(date_value)

    async def test_duckling_miss_falls_back_to_gemini_for_time(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            add_handler.duckling_client, "resolve_time",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"time":"17:00","confidence":0.9}',
        ):
            date_value, time_value = await add_handler._resolve_date_time(
                {"time": "5ish in the evening"}, "UTC",
            )
        self.assertEqual(time_value, "17:00:00")

    async def test_both_miss_returns_none_none(self):
        settings_module.settings.USE_GEMINI_PENDING_REPLY = True
        with patch.object(
            add_handler.duckling_client, "resolve_date",
            new=AsyncMock(return_value=None),
        ), patch(
            "pipeline.pending_reply_fallback.gemini_service.generate_constrained_text",
            return_value='{"date":"none","confidence":0.1}',
        ):
            date_value, time_value = await add_handler._resolve_date_time(
                {"date": "blah blah"}, "UTC",
            )
        self.assertIsNone(date_value)


if __name__ == "__main__":
    unittest.main()
