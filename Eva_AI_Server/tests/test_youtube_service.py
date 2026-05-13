"""Unit tests for services/youtube.py (HTTP mocked)."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from config.settings import settings
from services.youtube import search_topic


class YoutubeServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_query_returns_empty(self):
        self.assertEqual(await search_topic(""), [])
        self.assertEqual(await search_topic("   "), [])

    async def test_missing_api_key_returns_empty(self):
        with patch.object(settings, "YOUTUBE_API_KEY", ""):
            out = await search_topic("python tutorial")
        self.assertEqual(out, [])

    async def test_success_returns_three_fields(self):
        payload = {
            "items": [
                {
                    "id": {"videoId": "abc123"},
                    "snippet": {
                        "title": "Hello World",
                        "channelTitle": "My Channel",
                        "thumbnails": {"high": {"url": "https://img.example/hq.jpg"}},
                    },
                },
                {
                    "id": {"videoId": "xyz"},
                    "snippet": {
                        "title": "Second",
                        "channelTitle": "C2",
                        "thumbnails": {"medium": {"url": "https://m.jpg"}},
                    },
                },
            ]
        }
        resp = MagicMock()
        resp.status_code = 200
        resp.text = ""
        resp.json = MagicMock(return_value=payload)

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(settings, "YOUTUBE_API_KEY", "test-key"):
            with patch("services.youtube.httpx.AsyncClient", return_value=mock_client):
                out = await search_topic("python basics", max_results=3)

        self.assertEqual(len(out), 2)
        for item in out:
            self.assertIn("title", item)
            self.assertIn("url", item)
            self.assertIn("thumbnail", item)
            self.assertIn("channel", item)
        self.assertTrue(out[0]["url"].startswith("https://www.youtube.com/watch?v="))

    async def test_non_200_returns_empty(self):
        resp = MagicMock()
        resp.status_code = 403
        resp.text = "quota exceeded"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(settings, "YOUTUBE_API_KEY", "k"):
            with patch("services.youtube.httpx.AsyncClient", return_value=mock_client):
                out = await search_topic("anything")
        self.assertEqual(out, [])

    async def test_http_exception_returns_empty(self):
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("network down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(settings, "YOUTUBE_API_KEY", "k"):
            with patch("services.youtube.httpx.AsyncClient", return_value=mock_client):
                out = await search_topic("query")
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
