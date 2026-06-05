"""Phase 1 schema checks for learning_update — activity log task_completed."""
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


class LearningUpdatePhase1SchemaTests(unittest.IsolatedAsyncioTestCase):
    async def test_insert_log_accepts_task_completed_from_learning_module(self):
        fake_activity_logs = FakeActivityLogsCollection()
        fake_db = FakeDB(activity_logs_collection=fake_activity_logs)
        owner_id = ObjectId()
        task_id = ObjectId()

        with patch("db.activity_logs.get_db", return_value=fake_db):
            inserted_id = await insert_log(
                {
                    "user_id": owner_id,
                    "task_id": task_id,
                    "action_type": "task_completed",
                    "subject": "python",
                    "source": "learning_module",
                }
            )

        self.assertTrue(inserted_id)
        self.assertEqual(len(fake_activity_logs.rows), 1)
        row = fake_activity_logs.rows[0]
        self.assertEqual(row["action_type"], "task_completed")
        self.assertEqual(row["source"], "learning_module")
        self.assertEqual(row["task_id"], task_id)

    async def test_insert_log_accepts_task_completed_without_task_id(self):
        """Goal-level completion logs may omit task_id."""
        fake_activity_logs = FakeActivityLogsCollection()
        fake_db = FakeDB(activity_logs_collection=fake_activity_logs)
        owner_id = ObjectId()

        with patch("db.activity_logs.get_db", return_value=fake_db):
            inserted_id = await insert_log(
                {
                    "user_id": owner_id,
                    "task_id": None,
                    "action_type": "task_completed",
                    "subject": "python",
                    "source": "learning_module",
                }
            )

        self.assertTrue(inserted_id)
        self.assertEqual(fake_activity_logs.rows[0]["action_type"], "task_completed")


if __name__ == "__main__":
    unittest.main()
