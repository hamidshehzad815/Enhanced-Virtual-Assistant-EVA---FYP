"""
Phase 13 tests for scheduling_delete entity extraction/scoping.
"""
import unittest

from pipeline.delete_entity_fallback import extract_delete_entities_fallback
from pipeline.entity_scoper import scope_entities


class TestDeletePhase13(unittest.TestCase):
    def test_delete_fallback_does_not_invent_task_name(self):
        entities = extract_delete_entities_fallback("delete physics exam")
        self.assertNotIn("task_name", entities)

    def test_delete_fallback_does_not_invent_task_name_from_date_time_noise(self):
        entities = extract_delete_entities_fallback("delete tasks scheduled today 2pm")
        self.assertNotIn("task_name", entities)
        self.assertEqual((entities.get("date") or "").lower(), "today")

    def test_delete_fallback_extracts_priority_and_date(self):
        entities = extract_delete_entities_fallback(
            "remove high priority tasks on Monday"
        )
        self.assertEqual(entities.get("priority"), "high")
        self.assertEqual((entities.get("date") or "").lower(), "monday")
        self.assertNotIn("task_name", entities)

    def test_delete_fallback_extracts_status(self):
        entities = extract_delete_entities_fallback("delete all pending tasks")
        self.assertEqual(entities.get("status"), "pending")
        self.assertNotIn("task_name", entities)

    def test_delete_fallback_maps_priority_alias_to_canonical(self):
        entities = extract_delete_entities_fallback("delete all urgent priority tasks")
        self.assertEqual(entities.get("priority"), "high")
        self.assertNotIn("task_name", entities)

    def test_delete_fallback_maps_status_alias_to_canonical(self):
        entities = extract_delete_entities_fallback("delete all done tasks")
        self.assertEqual(entities.get("status"), "complete")
        self.assertNotIn("task_name", entities)

    def test_delete_fallback_extracts_date_without_task_name(self):
        entities = extract_delete_entities_fallback("delete the exam on Monday")
        self.assertEqual((entities.get("date") or "").lower(), "monday")
        self.assertNotIn("task_name", entities)

    def test_delete_scoper_keeps_only_allowed_fields(self):
        raw_entities = {
            "task_name": "physics exam",
            "date": "Monday",
            "priority": "high",
            "status": "pending",
            "time": "5PM",
            "duration": "2 hours",
            "collaborator": "Ahmed",
            "topic": "python",
        }

        scoped = scope_entities(raw_entities, "scheduling_delete")

        self.assertEqual(
            set(scoped.keys()),
            {"task_name", "date", "time", "priority", "status"},
        )


if __name__ == "__main__":
    unittest.main()
