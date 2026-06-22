"""Unit tests for services/youtube.py (HTTP mocked)."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from config.settings import settings
from services.youtube import (
    YouTubeSearchFailed,
    resolve_youtube_api_keys,
    search_topic,
)


def _mock_client(responses: list) -> MagicMock:
    """Build async client whose .get returns each response in order."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=responses)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class YoutubeServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_query_returns_empty(self):
        self.assertEqual(await search_topic(""), [])
        self.assertEqual(await search_topic("   "), [])

    async def test_missing_api_key_raises(self):
        with patch("services.youtube.resolve_youtube_api_keys", return_value=[]):
            with self.assertRaises(YouTubeSearchFailed) as ctx:
                await search_topic("python tutorial")
        self.assertIn("No YouTube API keys", str(ctx.exception))

    async def test_success_returns_top_by_views(self):
        search_payload = {
            "items": [
                {"id": {"videoId": "low"}},
                {"id": {"videoId": "high"}},
                {"id": {"videoId": "mid"}},
            ]
        }
        videos_payload = {
            "items": [
                {
                    "id": "low",
                    "snippet": {
                        "title": "Low views",
                        "channelTitle": "A",
                        "thumbnails": {"default": {"url": "https://a.jpg"}},
                    },
                    "statistics": {"viewCount": "100"},
                },
                {
                    "id": "high",
                    "snippet": {
                        "title": "High views",
                        "channelTitle": "B",
                        "thumbnails": {"high": {"url": "https://b.jpg"}},
                    },
                    "statistics": {"viewCount": "5000000"},
                },
                {
                    "id": "mid",
                    "snippet": {
                        "title": "Mid views",
                        "channelTitle": "C",
                        "thumbnails": {"medium": {"url": "https://c.jpg"}},
                    },
                    "statistics": {"viewCount": "50000"},
                },
            ]
        }

        def _resp(status: int, payload: dict) -> MagicMock:
            r = MagicMock()
            r.status_code = status
            r.text = ""
            r.json = MagicMock(return_value=payload)
            return r

        mock_client = _mock_client(
            [_resp(200, search_payload), _resp(200, videos_payload)],
        )

        with patch("services.youtube.httpx.AsyncClient", return_value=mock_client):
            out = await search_topic("python basics", max_results=3, api_keys=["test-key"])

        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["title"], "High views")
        self.assertEqual(out[0]["view_count"], "5000000")
        self.assertTrue(out[0]["url"].startswith("https://www.youtube.com/watch?v="))

    async def test_rotates_key_on_quota(self):
        quota_body = {
            "error": {
                "code": 403,
                "message": "quota exceeded",
                "errors": [{"reason": "quotaExceeded"}],
            }
        }

        search_ok = {
            "items": [{"id": {"videoId": "abc123"}}],
        }
        videos_ok = {
            "items": [
                {
                    "id": "abc123",
                    "snippet": {
                        "title": "Tutorial",
                        "channelTitle": "Ch",
                        "thumbnails": {},
                    },
                    "statistics": {"viewCount": "9999"},
                }
            ]
        }

        def _resp(status: int, payload: dict) -> MagicMock:
            r = MagicMock()
            r.status_code = status
            r.text = str(payload)
            r.json = MagicMock(return_value=payload)
            return r

        mock_client = _mock_client(
            [
                _resp(403, quota_body),
                _resp(200, search_ok),
                _resp(200, videos_ok),
            ],
        )

        with patch("services.youtube.httpx.AsyncClient", return_value=mock_client):
            out = await search_topic("python", api_keys=["key1", "key2"])

        self.assertEqual(len(out), 1)
        self.assertEqual(mock_client.get.await_count, 3)

    async def test_all_keys_quota_raises(self):
        quota_body = {
            "error": {
                "errors": [{"reason": "quotaExceeded"}],
            }
        }

        def _resp(status: int, payload: dict) -> MagicMock:
            r = MagicMock()
            r.status_code = status
            r.text = ""
            r.json = MagicMock(return_value=payload)
            return r

        mock_client = _mock_client([_resp(403, quota_body), _resp(403, quota_body)])

        with patch("services.youtube.httpx.AsyncClient", return_value=mock_client):
            with self.assertRaises(YouTubeSearchFailed) as ctx:
                await search_topic("anything", api_keys=["k1", "k2"])
        self.assertIn("All 2", str(ctx.exception))

    async def test_non_200_raises(self):
        resp = MagicMock()
        resp.status_code = 400
        resp.text = "bad request"
        resp.json = MagicMock(return_value={"error": {"errors": [{"reason": "badRequest"}]}})

        mock_client = _mock_client([resp])

        with patch("services.youtube.httpx.AsyncClient", return_value=mock_client):
            with self.assertRaises(YouTubeSearchFailed) as ctx:
                await search_topic("anything", api_keys=["k"])
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_http_exception_raises(self):
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("network down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.youtube.httpx.AsyncClient", return_value=mock_client):
            with self.assertRaises(YouTubeSearchFailed) as ctx:
                await search_topic("query", api_keys=["k"])
        self.assertIn("network", str(ctx.exception).lower())

    def test_resolve_keys_from_settings(self):
        with patch.object(settings, "YOUTUBE_API_KEY", "single-key"):
            with patch.dict("os.environ", {}, clear=False):
                import os

                env = os.environ.copy()
                env.pop("YOUTUBE_API_KEYS", None)
                with patch.dict(os.environ, env, clear=True):
                    self.assertEqual(resolve_youtube_api_keys(None), ["single-key"])


if __name__ == "__main__":
    unittest.main()
