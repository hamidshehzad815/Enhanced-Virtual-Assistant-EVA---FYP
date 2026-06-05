"""
Phase 2 tests for learning_delete entity scoping.
"""
import unittest

from pipeline.entity_scoper import scope_entities


class TestLearningDeletePhase2EntityScoper(unittest.TestCase):
    def test_keeps_topic_and_subtopic_only(self):
        raw_entities = {
            "topic": "Python",
            "subtopic": "basics",
            "task_name": "physics exam",
            "date": "Monday",
            "time": "5pm",
            "priority": "high",
            "status": "pending",
            "duration": "2 weeks",
            "start_date": "next Monday",
            "person": "Ahmed",
            "collaborator": "Ahmed",
            "new_title": "something",
            "day": "Monday",
        }

        scoped = scope_entities(raw_entities, "learning_delete")

        self.assertEqual(set(scoped.keys()), {"topic", "subtopic"})
        self.assertEqual(scoped["topic"], "Python")
        self.assertEqual(scoped["subtopic"], "basics")

    def test_topic_only_when_subtopic_missing(self):
        raw_entities = {
            "topic": "Python",
            "duration": "2 weeks",
            "person": "Ahmed",
        }

        scoped = scope_entities(raw_entities, "learning_delete")

        self.assertEqual(scoped, {"topic": "Python"})
        self.assertNotIn("subtopic", scoped)

    def test_maps_subject_to_topic(self):
        raw_entities = {
            "subject": "MySQL",
            "subtopic": "basics",
            "task_name": "exam prep",
        }

        scoped = scope_entities(raw_entities, "learning_delete")

        self.assertEqual(scoped.get("topic"), "MySQL")
        self.assertEqual(scoped.get("subtopic"), "basics")
        self.assertNotIn("task_name", scoped)

    def test_drops_duration_and_person(self):
        raw_entities = {
            "topic": "Python",
            "duration": "2 weeks",
            "person": "Ahmed",
        }

        scoped = scope_entities(raw_entities, "learning_delete")

        self.assertEqual(scoped, {"topic": "Python"})


if __name__ == "__main__":
    unittest.main()
