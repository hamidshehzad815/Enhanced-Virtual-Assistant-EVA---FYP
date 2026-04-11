"""
Phase 23 tests for update-entity extraction fallback rules.
"""
import unittest

from pipeline.update_entity_fallback import extract_update_entities_fallback


class TestUpdatePhase23Entities(unittest.TestCase):
    def test_change_priority_to_high(self):
        entities = extract_update_entities_fallback("change physics exam priority to high")
        self.assertEqual(entities.get("task_name"), "physics exam")
        self.assertEqual(entities.get("new_priority"), "high")

    def test_reschedule_to_next_friday_at_2pm(self):
        entities = extract_update_entities_fallback(
            "reschedule chemistry lab to next Friday at 2PM"
        )
        self.assertEqual(entities.get("task_name"), "chemistry lab")
        self.assertEqual(entities.get("new_date"), "next Friday")
        self.assertEqual(entities.get("new_time"), "2PM")

    def test_mark_as_complete(self):
        entities = extract_update_entities_fallback(
            "mark my biology assignment as complete"
        )
        self.assertEqual(entities.get("task_name"), "biology assignment")
        self.assertEqual(entities.get("new_status"), "complete")

    def test_move_on_monday_to_tuesday(self):
        entities = extract_update_entities_fallback(
            "move physics exam on Monday to Tuesday"
        )
        self.assertEqual(entities.get("task_name"), "physics exam")
        self.assertEqual(entities.get("date"), "Monday")
        self.assertEqual(entities.get("new_date"), "Tuesday")

    def test_change_time_on_tuesday_to_5pm(self):
        entities = extract_update_entities_fallback(
            "change the time of my exam on Tuesday to 5PM"
        )
        self.assertEqual(entities.get("date"), "Tuesday")
        self.assertEqual(entities.get("new_time"), "5PM")
        self.assertEqual(entities.get("task_name"), "exam")

    def test_update_duration_to_three_hours(self):
        entities = extract_update_entities_fallback(
            "update physics exam duration to 3 hours"
        )
        self.assertEqual(entities.get("task_name"), "physics exam")
        self.assertEqual(entities.get("new_duration"), "3 hours")

    def test_rename_task(self):
        entities = extract_update_entities_fallback(
            "rename physics exam to physics final"
        )
        self.assertEqual(entities.get("task_name"), "physics exam")
        self.assertEqual(entities.get("new_title"), "physics final")


if __name__ == "__main__":
    unittest.main()

