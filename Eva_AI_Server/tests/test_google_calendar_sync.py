"""
Unit tests for Google Calendar sync gating and token refresh helpers.
"""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from utils.google_calendar_sync import (
    is_google_calendar_sync_enabled,
    pick_active_google_integration,
    refresh_google_access_token,
    resolve_google_calendar_sync,
)


class TestGoogleCalendarSyncHelpers(unittest.TestCase):
    def test_is_google_calendar_sync_enabled_requires_explicit_true(self):
        self.assertFalse(is_google_calendar_sync_enabled({}))
        self.assertFalse(is_google_calendar_sync_enabled({"google_calendar_sync_enabled": False}))
        self.assertTrue(is_google_calendar_sync_enabled({"google_calendar_sync_enabled": True}))

    def test_pick_active_google_integration(self):
        integrations = [
            {"provider": "google_calendar", "is_active": False},
            {"provider": "google_calendar", "is_active": True, "access_token": "tok"},
        ]
        picked = pick_active_google_integration(integrations)
        self.assertEqual(picked["access_token"], "tok")


class TestGoogleCalendarSyncAsync(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_google_calendar_sync_returns_none_when_toggle_off(self):
        integrations = [
            {
                "provider": "google_calendar",
                "is_active": True,
                "access_token": "tok",
            }
        ]
        result = await resolve_google_calendar_sync(
            "user1",
            integrations,
            {"google_calendar_sync_enabled": False},
        )
        self.assertIsNone(result)

    async def test_resolve_google_calendar_sync_returns_integration_when_enabled(self):
        integrations = [
            {
                "_id": "int1",
                "provider": "google_calendar",
                "is_active": True,
                "access_token": "tok",
                "token_expires": datetime.now(timezone.utc) + timedelta(hours=1),
            }
        ]
        result = await resolve_google_calendar_sync(
            "user1",
            integrations,
            {"google_calendar_sync_enabled": True},
        )
        self.assertEqual(result["access_token"], "tok")

    async def test_resolve_google_calendar_sync_refreshes_expired_token(self):
        integrations = [
            {
                "_id": "int1",
                "provider": "google_calendar",
                "is_active": True,
                "access_token": "old",
                "refresh_token": "refresh",
                "token_expires": datetime.now(timezone.utc) - timedelta(minutes=1),
            }
        ]
        with patch(
            "utils.google_calendar_sync.refresh_google_access_token",
            new=AsyncMock(
                return_value={
                    "access_token": "new",
                    "token_expires": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            ),
        ) as mock_refresh, patch(
            "utils.google_calendar_sync.update_integration_tokens",
            new=AsyncMock(return_value=True),
        ):
            result = await resolve_google_calendar_sync(
                "user1",
                integrations,
                {"google_calendar_sync_enabled": True},
            )

        mock_refresh.assert_awaited_once_with("refresh")
        self.assertEqual(result["access_token"], "new")

    async def test_refresh_google_access_token_success(self):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"access_token": "fresh", "expires_in": 3600}

        fake_client = AsyncMock()
        fake_client.post = AsyncMock(return_value=FakeResponse())
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=None)

        with patch("utils.google_calendar_sync.settings") as mock_settings, patch(
            "utils.google_calendar_sync.httpx.AsyncClient",
            return_value=fake_client,
        ):
            mock_settings.GOOGLE_CLIENT_ID = "client"
            mock_settings.GOOGLE_CLIENT_SECRET = "secret"
            refreshed = await refresh_google_access_token("refresh-token")

        self.assertEqual(refreshed["access_token"], "fresh")
        self.assertIsNotNone(refreshed["token_expires"])


if __name__ == "__main__":
    unittest.main()
