"""Tests for jobs/resource_refresh.py (no real scheduler sleep)."""

import unittest
from unittest.mock import AsyncMock, patch

from config.settings import settings
from jobs import resource_refresh as rr


class ResourceRefreshJobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await rr.shutdown_refresh_scheduler()

    async def asyncTearDown(self):
        await rr.shutdown_refresh_scheduler()

    async def test_start_skips_when_disabled(self):
        with patch.object(settings, "RESOURCE_REFRESH_ENABLED", False):
            await rr.start_refresh_scheduler()
        self.assertIsNone(rr._refresh_task)

    async def test_start_then_shutdown(self):
        with patch.object(settings, "RESOURCE_REFRESH_ENABLED", True):
            with patch.object(settings, "RESOURCE_REFRESH_INTERVAL_DAYS", 50000):
                await rr.start_refresh_scheduler()
                self.assertIsNotNone(rr._refresh_task)
                await rr.shutdown_refresh_scheduler()
        self.assertIsNone(rr._refresh_task)

    async def test_run_stale_once_no_docs(self):
        with patch(
            "jobs.resource_refresh.get_stale_topics",
            new=AsyncMock(return_value=[]),
        ):
            await rr.run_stale_refresh_once(limit=10)


if __name__ == "__main__":
    unittest.main()
