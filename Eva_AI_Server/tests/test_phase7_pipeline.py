"""
Unit tests for Phase 7 pipeline helpers.
"""
import unittest
from unittest.mock import AsyncMock, patch

from pipeline.entity_scoper import scope_entities
from pipeline.date_resolver import resolve_all


class TestPhase7Pipeline(unittest.IsolatedAsyncioTestCase):
    def test_scope_entities_for_scheduling_add(self):
        raw_entities = {
            "task_name": "Physics exam",
            "date": "Monday",
            "time": "5PM",
            "priority": "high",
            "duration": "2 hours",
            "collaborator": "Ahmed",
            "topic": "python",  # should be removed for scheduling_add
            "new_taskname": "Chemistry exam",  # alias exists but not in add scope
        }

        scoped = scope_entities(raw_entities, "scheduling_add")

        self.assertEqual(scoped.get("task_name"), "Physics exam")
        self.assertEqual(scoped.get("date"), "Monday")
        self.assertEqual(scoped.get("time"), "5PM")
        self.assertEqual(scoped.get("priority"), "high")
        self.assertEqual(scoped.get("duration"), "2 hours")
        self.assertEqual(scoped.get("collaborator"), "Ahmed")
        self.assertNotIn("topic", scoped)
        self.assertNotIn("new_task_name", scoped)

    def test_scope_entities_for_scheduling_show_keeps_task_filters(self):
        raw_entities = {
            "task_name": "physics exam",
            "date": "monday",
            "priority": "high",
            "status": "pending",
            "duration": "2 hours",
            "collaborator": "hamid",
            "topic": "physics",
            "subtopic": "waves",
        }

        scoped = scope_entities(raw_entities, "scheduling_show")

        self.assertEqual(scoped, {
            "task_name": "physics exam",
            "date": "monday",
            "priority": "high",
            "status": "pending",
        })

    def test_scope_entities_for_scheduling_show_maps_subject_to_task_name(self):
        raw_entities = {
            "subject": "chemistry quiz",
            "date": "today",
            "time": "5pm",
        }

        scoped = scope_entities(raw_entities, "scheduling_show")

        self.assertEqual(scoped.get("task_name"), "chemistry quiz")
        self.assertEqual(scoped.get("date"), "today")
        self.assertNotIn("subject", scoped)
        self.assertNotIn("time", scoped)

    async def test_resolve_all_calls_duckling(self):
        entities = {
            "date": "Monday",
            "time": "5PM",
            "duration": "2 hours",
        }

        with patch(
            "pipeline.date_resolver.duckling_client.resolve_date",
            new=AsyncMock(return_value="2026-03-23"),
        ) as mock_date, patch(
            "pipeline.date_resolver.duckling_client.resolve_time",
            new=AsyncMock(return_value="17:00:00"),
        ) as mock_time, patch(
            "pipeline.date_resolver.duckling_client.resolve_duration",
            new=AsyncMock(return_value=120),
        ) as mock_duration:
            resolved = await resolve_all(entities, timezone="UTC")

        self.assertEqual(resolved.get("date"), "2026-03-23")
        self.assertEqual(resolved.get("time"), "17:00:00")
        self.assertEqual(resolved.get("duration"), 120)
        mock_date.assert_awaited()
        mock_time.assert_awaited()
        mock_duration.assert_awaited()


if __name__ == "__main__":
    unittest.main()
