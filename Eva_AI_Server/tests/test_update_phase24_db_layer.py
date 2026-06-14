"""
Phase 24 tests for update DB-layer helpers.
"""
from datetime import datetime
import re
import unittest
from unittest.mock import patch

from bson import ObjectId

from db.activity_logs import increment_reschedule_count, insert_log
from db.tasks import (
    check_update_overlap,
    find_tasks_for_update,
    update_task,
)


class FakeResult:
    def __init__(self, matched_count: int = 0, modified_count: int = 0):
        self.matched_count = matched_count
        self.modified_count = modified_count


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, key, direction):
        reverse = direction == -1
        self.rows = sorted(self.rows, key=lambda row: row.get(key), reverse=reverse)
        return self

    def limit(self, amount):
        self.rows = self.rows[:amount]
        return self

    async def to_list(self, length=100):
        return [dict(row) for row in self.rows[:length]]


class FakeTasksCollection:
    def __init__(self, docs):
        self.docs = [dict(doc) for doc in docs]

    @staticmethod
    def _match_condition(actual, expected):
        if isinstance(expected, dict):
            if "$regex" in expected:
                pattern = expected["$regex"]
                flags = re.IGNORECASE if expected.get("$options") == "i" else 0
                return re.search(pattern, str(actual or ""), flags) is not None

            for op, value in expected.items():
                if op == "$ne" and actual == value:
                    return False
                if op == "$in" and actual not in value:
                    return False
                if op == "$gte" and actual < value:
                    return False
                if op == "$lte" and actual > value:
                    return False
                if op == "$lt" and actual >= value:
                    return False
            return True

        return actual == expected

    def _matches(self, doc, query):
        for key, expected in query.items():
            if not self._match_condition(doc.get(key), expected):
                return False
        return True

    def find(self, query):
        rows = [doc for doc in self.docs if self._matches(doc, query)]
        return FakeCursor(rows)

    async def update_one(self, query, update):
        for doc in self.docs:
            if self._matches(doc, query):
                before = dict(doc)
                for key, value in update.get("$set", {}).items():
                    doc[key] = value
                modified = 1 if doc != before else 0
                return FakeResult(matched_count=1, modified_count=modified)
        return FakeResult()


class FakeActivityLogsCollection:
    def __init__(self):
        self.rows = []

    async def insert_one(self, payload):
        row = dict(payload)
        row["_id"] = ObjectId()
        self.rows.append(row)
        return FakeInsertResult(row["_id"])

    @staticmethod
    def _normalize(value):
        return str(value)

    async def update_one(self, query, update):
        for row in self.rows:
            row_task = self._normalize(row.get("task_id"))
            query_task = self._normalize(query.get("task_id"))
            if (
                row_task == query_task
                and row.get("action_type") == query.get("action_type")
            ):
                if "$inc" in update:
                    for key, amount in update["$inc"].items():
                        row[key] = int(row.get(key) or 0) + int(amount)
                return FakeResult(matched_count=1, modified_count=1)
        return FakeResult(matched_count=0, modified_count=0)


class FakeDB:
    def __init__(self, tasks_collection=None, activity_logs_collection=None):
        self.tasks = tasks_collection
        self.activity_logs = activity_logs_collection


class TestUpdatePhase24DbLayer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.owner_id = ObjectId()
        self.other_owner_id = ObjectId()
        self.task1_id = ObjectId()
        self.task2_id = ObjectId()
        self.task3_id = ObjectId()

        self.docs = [
            {
                "_id": self.task1_id,
                "owner_id": self.owner_id,
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 17, 0, 0),
                "duration": 120,
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
            },
            {
                "_id": self.task2_id,
                "owner_id": self.owner_id,
                "title": "Physics lab",
                "due_datetime": datetime(2026, 4, 1, 20, 30, 0),
                "duration": 60,
                "priority": "medium",
                "status": "pending",
                "is_deleted": False,
            },
            {
                "_id": self.task3_id,
                "owner_id": self.other_owner_id,
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 19, 0, 0),
                "duration": 60,
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
            },
        ]

    async def test_find_tasks_for_update_with_combined_filters(self):
        fake_db = FakeDB(tasks_collection=FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows = await find_tasks_for_update(
                str(self.owner_id),
                {
                    "task_name": "physics exam",
                    "date_range": {
                        "start": datetime(2026, 4, 1, 0, 0, 0),
                        "end": datetime(2026, 4, 1, 23, 59, 59, 999999),
                    },
                    "priority": "high",
                    "status": "pending",
                },
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_id"], str(self.task1_id))

    async def test_update_task_updates_priority_and_updated_at(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)
        with patch("db.tasks.get_db", return_value=fake_db):
            ok = await update_task(
                str(self.task1_id),
                {"priority": "low"},
            )

        self.assertTrue(ok)
        updated = next(doc for doc in fake_tasks.docs if doc["_id"] == self.task1_id)
        self.assertEqual(updated["priority"], "low")
        self.assertIsNotNone(updated.get("updated_at"))

    async def test_update_task_status_complete_sets_completed_at(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)
        with patch("db.tasks.get_db", return_value=fake_db):
            ok = await update_task(
                str(self.task1_id),
                {"status": "complete"},
            )

        self.assertTrue(ok)
        updated = next(doc for doc in fake_tasks.docs if doc["_id"] == self.task1_id)
        self.assertEqual(updated["status"], "complete")
        self.assertIsNotNone(updated.get("completed_at"))

    async def test_update_task_multiple_fields_applied(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)
        with patch("db.tasks.get_db", return_value=fake_db):
            ok = await update_task(
                str(self.task1_id),
                {
                    "title": "Physics final",
                    "priority": "medium",
                    "duration": 180,
                    "due_datetime": datetime(2026, 4, 2, 11, 0, 0),
                },
            )

        self.assertTrue(ok)
        updated = next(doc for doc in fake_tasks.docs if doc["_id"] == self.task1_id)
        self.assertEqual(updated["title"], "Physics final")
        self.assertEqual(updated["priority"], "medium")
        self.assertEqual(updated["duration"], 180)
        self.assertEqual(updated["due_datetime"], datetime(2026, 4, 2, 11, 0, 0))

    async def test_check_update_overlap_returns_true_when_conflict_exists(self):
        fake_db = FakeDB(tasks_collection=FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            has_conflict = await check_update_overlap(
                str(self.owner_id),
                str(self.task1_id),
                datetime(2026, 4, 1, 19, 45, 0),
                120,
            )

        self.assertTrue(has_conflict)

    async def test_check_update_overlap_returns_false_when_no_conflict(self):
        fake_db = FakeDB(tasks_collection=FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            has_conflict = await check_update_overlap(
                str(self.owner_id),
                str(self.task1_id),
                datetime(2026, 4, 1, 23, 0, 0),
                60,
            )

        self.assertFalse(has_conflict)

    async def test_check_update_overlap_excludes_same_task(self):
        fake_db = FakeDB(tasks_collection=FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            has_conflict = await check_update_overlap(
                str(self.owner_id),
                str(self.task1_id),
                datetime(2026, 4, 1, 17, 0, 0),
                120,
            )

        self.assertFalse(has_conflict)

    async def test_check_update_overlap_honors_exclude_task_ids(self):
        fake_db = FakeDB(tasks_collection=FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            has_conflict = await check_update_overlap(
                str(self.owner_id),
                str(self.task1_id),
                datetime(2026, 4, 1, 19, 45, 0),
                120,
                exclude_task_ids={str(self.task2_id)},
            )

        self.assertFalse(has_conflict)

    async def test_insert_log_accepts_task_updated_action(self):
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection())
        with patch("db.activity_logs.get_db", return_value=fake_db):
            inserted_id = await insert_log(
                {
                    "user_id": self.owner_id,
                    "task_id": self.task1_id,
                    "action_type": "task_updated",
                    "subject": "Physics exam",
                },
                force=True,
            )

        self.assertTrue(inserted_id)
        self.assertEqual(len(fake_db.activity_logs.rows), 1)
        self.assertEqual(fake_db.activity_logs.rows[0]["action_type"], "task_updated")

    async def test_increment_reschedule_count_increments_task_created_log(self):
        fake_logs = FakeActivityLogsCollection()
        fake_db = FakeDB(activity_logs_collection=fake_logs)
        with patch("db.activity_logs.get_db", return_value=fake_db):
            task_id = ObjectId()
            await insert_log(
                {
                    "user_id": self.owner_id,
                    "task_id": task_id,
                    "action_type": "task_created",
                    "subject": "Physics exam",
                    "reschedule_count": 0,
                },
                force=True,
            )

            ok_first = await increment_reschedule_count(str(task_id))
            ok_second = await increment_reschedule_count(str(task_id))
            missing = await increment_reschedule_count(str(ObjectId()))

        self.assertTrue(ok_first)
        self.assertTrue(ok_second)
        self.assertFalse(missing)
        self.assertEqual(fake_logs.rows[0]["reschedule_count"], 2)


if __name__ == "__main__":
    unittest.main()
