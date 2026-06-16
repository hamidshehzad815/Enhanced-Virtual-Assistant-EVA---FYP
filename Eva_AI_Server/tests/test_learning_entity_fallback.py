"""Phase 6 pipeline tests — learning entity fallback + postprocess."""

import unittest

from pipeline.entity_postprocess import postprocess_ner_entities
from pipeline.learning_entity_fallback import extract_learning_entities_fallback


class LearningEntityFallbackTests(unittest.TestCase):
    def test_extracts_topic_and_subtopic(self):
        entities = extract_learning_entities_fallback(
            "create python oop roadmap",
            "learning_create",
        )
        self.assertEqual(entities.get("topic", "").lower(), "python")
        self.assertEqual(entities.get("subtopic", "").lower(), "oop")

    def test_delete_my_roadmap_gets_topic_not_filler(self):
        entities = extract_learning_entities_fallback(
            "delete my Python roadmap",
            "learning_delete",
        )
        self.assertEqual(entities.get("topic"), "Python")

    def test_postprocess_drops_ma_subtopic(self):
        cleaned = postprocess_ner_entities(
            {"topic": "Python", "subtopic": "ma"},
            "learning_delete",
            "delete my Python roadmap",
        )
        self.assertNotEqual(cleaned.get("subtopic"), "ma")
        self.assertNotIn("subtopic", cleaned)

    def test_postprocess_recovers_oop_hint(self):
        cleaned = postprocess_ner_entities(
            {"topic": "python"},
            "learning_create",
            "create python oop roadmap",
        )
        self.assertEqual(cleaned.get("subtopic"), "oop")

    def test_postprocess_keeps_start_date_today(self):
        cleaned = postprocess_ner_entities(
            {
                "topic": "python",
                "subtopic": "basics",
                "start_date": "today",
                "duration": "60days",
            },
            "learning_create",
            "create python basics plan starting today for 60days",
        )
        self.assertEqual(cleaned.get("start_date"), "today")


if __name__ == "__main__":
    unittest.main()
