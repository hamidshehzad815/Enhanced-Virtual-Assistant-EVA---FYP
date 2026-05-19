"""Tests for services.roadmap_youtube_worker (locked YouTube query builder)."""

import unittest
from unittest.mock import AsyncMock, patch

from services.youtube import YouTubeSearchFailed

from services.roadmap_youtube_worker import build_youtube_search_query, fetch_and_store_for_documents


class BuildYouTubeSearchQueryTests(unittest.TestCase):
    def test_language_plus_title_when_title_has_no_language_prefix(self):
        q = build_youtube_search_query(
            {
                "language": "Python",
                "title": "basics session 4: loops and iteration",
            },
        )
        self.assertEqual(q, "Python basics session 4: loops and iteration")

    def test_title_only_when_title_already_starts_with_language(self):
        q = build_youtube_search_query(
            {
                "language": "C++",
                "title": "C++ basics session 4: structured topic and hands-on practice",
            },
        )
        self.assertEqual(q, "C++ basics session 4: structured topic and hands-on practice")

    def test_case_insensitive_prefix_match(self):
        q = build_youtube_search_query(
            {"language": "Python", "title": "python hello world tutorial"},
        )
        self.assertEqual(q, "python hello world tutorial")

    def test_title_only_when_language_missing(self):
        self.assertEqual(
            build_youtube_search_query({"title": "installation steps"}),
            "installation steps",
        )

    def test_language_only_when_title_missing(self):
        self.assertEqual(
            build_youtube_search_query({"language": "Go"}),
            "Go",
        )


class FetchAndStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_stops_on_youtube_failure_returns_reason(self):
        docs = [
            {"_id": "a", "language": "Python", "title": "loops"},
            {"_id": "b", "language": "Python", "title": "decorators"},
        ]

        async def fake_search(_q: str):
            raise YouTubeSearchFailed("HTTP 403 simulated")

        with patch("services.roadmap_youtube_worker.search_topic", side_effect=fake_search):
            updated, calls, fatal = await fetch_and_store_for_documents(
                docs,
                delay_seconds=0,
                progress_every=99,
            )

        self.assertEqual(updated, 0)
        self.assertEqual(calls, 1)
        self.assertEqual(fatal, "HTTP 403 simulated")

    async def test_processes_all_when_search_returns_empty(self):
        docs = [{"_id": "x", "language": "X", "title": "y"}]

        with patch(
            "services.roadmap_youtube_worker.search_topic",
            new_callable=AsyncMock,
            return_value=[],
        ):
            updated, calls, fatal = await fetch_and_store_for_documents(
                docs,
                delay_seconds=0,
                progress_every=99,
            )

        self.assertIsNone(fatal)
        self.assertEqual(calls, 1)
        self.assertEqual(updated, 0)


if __name__ == "__main__":
    unittest.main()
