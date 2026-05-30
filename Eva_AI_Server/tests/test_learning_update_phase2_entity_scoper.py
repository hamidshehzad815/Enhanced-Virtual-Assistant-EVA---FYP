"""
Phase 2 tests for learning_update entity scoping.
"""
import unittest

from pipeline.entity_scoper import scope_entities


class TestLearningUpdatePhase2EntityScoper(unittest.TestCase):
    def test_keeps_topic_subtopic_and_date_only(self):
        raw_entities = {
            "topic": "Python",
            "subtopic": "basics",
            "date": "next Monday",
            "task_name": "physics exam",
            "time": "5pm",
            "priority": "high",
            "status": "pending",
            "duration": "2 weeks",
            "start_date": "next Monday",
            "person": "Ahmed",
            "new_date": "Friday",
            "new_time": "3pm",
            "new_priority": "high",
            "new_status": "done",
            "new_duration": "2 hours",
            "new_taskname": "other",
            "day": "Monday",
            "subject": "ignored if topic present",
        }

        scoped = scope_entities(raw_entities, "learning_update")

        self.assertEqual(set(scoped.keys()), {"topic", "subtopic", "date"})
        self.assertEqual(scoped["topic"], "Python")
        self.assertEqual(scoped["subtopic"], "basics")
        self.assertEqual(scoped["date"], "next Monday")

    def test_maps_subject_to_topic(self):
        raw_entities = {
            "subject": "MySQL",
            "subtopic": "basics",
            "date": "tomorrow",
            "task_name": "exam",
        }

        scoped = scope_entities(raw_entities, "learning_update")

        self.assertEqual(scoped.get("topic"), "MySQL")
        self.assertEqual(scoped.get("subtopic"), "basics")
        self.assertEqual(scoped.get("date"), "tomorrow")
        self.assertNotIn("task_name", scoped)

    def test_topic_only_when_subtopic_and_date_missing(self):
        raw_entities = {
            "topic": "Python",
            "duration": "2 weeks",
            "person": "Ahmed",
        }

        scoped = scope_entities(raw_entities, "learning_update")

        self.assertEqual(scoped, {"topic": "Python"})


if __name__ == "__main__":
    unittest.main()
