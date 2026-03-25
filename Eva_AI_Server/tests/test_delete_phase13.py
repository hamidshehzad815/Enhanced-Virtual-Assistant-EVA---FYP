"""
Phase 13 tests for scheduling_delete entity extraction/scoping.
"""
import unittest

from pipeline.delete_entity_fallback import extract_delete_entities_fallback
from pipeline.entity_scoper import scope_entities


class TestDeletePhase13(unittest.TestCase):
    def test_delete_fallback_extracts_task_name(self):
        entities = extract_delete_entities_fallback("delete physics exam")
        self.assertEqual(entities.get("task_name"), "physics exam")

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

    def test_delete_fallback_extracts_partial_task_name_and_date(self):
        entities = extract_delete_entities_fallback("delete the exam on Monday")
        self.assertEqual((entities.get("date") or "").lower(), "monday")
        self.assertEqual((entities.get("task_name") or "").lower(), "exam")

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
            {"task_name", "date", "priority", "status"},
        )


if __name__ == "__main__":
    unittest.main()

