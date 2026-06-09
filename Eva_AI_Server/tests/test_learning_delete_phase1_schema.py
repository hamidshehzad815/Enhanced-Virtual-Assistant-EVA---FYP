"""Phase 1 schema checks for learning_delete — activity log action_type."""
import unittest
from unittest.mock import patch

from bson import ObjectId

from db.activity_logs import insert_log


class FakeActivityLogsCollection:
    def __init__(self):
        self.rows = []

    async def insert_one(self, document):
        self.rows.append(dict(document))
        return type("Result", (), {"inserted_id": ObjectId()})()


class FakeDB:
    def __init__(self, activity_logs_collection):
        self.activity_logs = activity_logs_collection


class LearningDeletePhase1SchemaTests(unittest.IsolatedAsyncioTestCase):
    async def test_insert_log_accepts_goal_deleted_action(self):
        fake_activity_logs = FakeActivityLogsCollection()
        fake_db = FakeDB(activity_logs_collection=fake_activity_logs)
        owner_id = ObjectId()

        with patch("db.activity_logs.get_db", return_value=fake_db):
            inserted_id = await insert_log(
                {
                    "user_id": owner_id,
                    "task_id": None,
                    "action_type": "goal_deleted",
                    "subject": "python",
                    "source": "learning_module",
                },
                force=True,
            )

        self.assertTrue(inserted_id)
        self.assertEqual(len(fake_activity_logs.rows), 1)
        self.assertEqual(fake_activity_logs.rows[0]["action_type"], "goal_deleted")
        self.assertEqual(fake_activity_logs.rows[0]["source"], "learning_module")


if __name__ == "__main__":
    unittest.main()
