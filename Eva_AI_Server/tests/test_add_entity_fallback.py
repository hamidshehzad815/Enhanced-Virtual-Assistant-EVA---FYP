"""Phase 6 pipeline tests — scheduling add fallback."""

import unittest

from pipeline.add_entity_fallback import extract_add_entities_fallback


class AddEntityFallbackTests(unittest.TestCase):
    def test_extracts_task_date_time(self):
        entities = extract_add_entities_fallback(
            "add physics exam on Monday at 5pm"
        )
        self.assertEqual(entities.get("task_name"), "physics exam")
        self.assertEqual(entities.get("date", "").lower(), "monday")
        self.assertEqual(entities.get("time", "").lower(), "5pm")

    def test_without_leading_add_verb_still_gets_date_time(self):
        entities = extract_add_entities_fallback("physics exam Monday 5pm add")
        self.assertEqual(entities.get("date", "").lower(), "monday")
        self.assertEqual(entities.get("time", "").lower(), "5pm")

    def test_typo_spelling_after_correction_path(self):
        from pipeline.spell_correction import apply_spell_corrections

        text = apply_spell_corrections("add physcis exam on munday at 5pm")
        entities = extract_add_entities_fallback(text)
        self.assertEqual(entities.get("task_name"), "physics exam")
        self.assertEqual(entities.get("date", "").lower(), "monday")


if __name__ == "__main__":
    unittest.main()
