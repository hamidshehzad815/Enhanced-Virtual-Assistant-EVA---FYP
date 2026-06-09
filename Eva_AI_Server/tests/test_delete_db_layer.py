"""
Phase 14 tests for delete DB-layer helpers.
"""
from datetime import datetime
import re
import unittest
from unittest.mock import patch

from bson import ObjectId

from db.activity_logs import insert_log
from db.tasks import (
    find_tasks_for_delete,
    get_task_by_id,
    soft_delete_many,
    soft_delete_task,
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

    async def to_list(self, length=10):
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

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if self._matches(doc, query):
                if projection:
                    projected = {}
                    for key, include in projection.items():
                        if include and key in doc:
                            projected[key] = doc[key]
                    return projected
                return dict(doc)
        return None

    async def update_one(self, query, update):
        for doc in self.docs:
            if self._matches(doc, query):
                before = dict(doc)
                for key, value in update.get("$set", {}).items():
                    doc[key] = value
                modified = 1 if doc != before else 0
                return FakeResult(matched_count=1, modified_count=modified)
        return FakeResult()

    async def update_many(self, query, update):
        matched = 0
        modified = 0
        for doc in self.docs:
            if self._matches(doc, query):
                matched += 1
                before = dict(doc)
                for key, value in update.get("$set", {}).items():
                    doc[key] = value
                if doc != before:
                    modified += 1
        return FakeResult(matched_count=matched, modified_count=modified)


class FakeActivityLogsCollection:
    def __init__(self):
        self.rows = []

    async def insert_one(self, payload):
        row = dict(payload)
        row["_id"] = ObjectId()
        self.rows.append(row)
        return FakeInsertResult(row["_id"])


class FakeDB:
    def __init__(self, tasks_collection=None, activity_logs_collection=None):
        self.tasks = tasks_collection
        self.activity_logs = activity_logs_collection


class TestDeleteDbLayer(unittest.IsolatedAsyncioTestCase):
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
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
                "collaborators": [{"user_id": ObjectId(), "status": "accepted"}],
                "google_calendar_event_id": "evt_123",
            },
            {
                "_id": self.task2_id,
                "owner_id": self.owner_id,
                "title": "Physics lab",
                "due_datetime": datetime(2026, 4, 1, 10, 0, 0),
                "priority": "medium",
                "status": "pending",
                "is_deleted": False,
                "collaborators": [],
                "google_calendar_event_id": None,
            },
            {
                "_id": self.task3_id,
                "owner_id": self.other_owner_id,
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 15, 0, 0),
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
                "collaborators": [],
                "google_calendar_event_id": None,
            },
        ]

    async def test_find_tasks_for_delete_with_combined_filters(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            rows = await find_tasks_for_delete(
                str(self.owner_id),
                {
                    "task_name": "physics",
                    "date": "2026-04-01",
                    "priority": "high",
                    "status": "pending",
                },
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_id"], str(self.task1_id))

    async def test_find_tasks_for_delete_with_task_name_filter(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            rows = await find_tasks_for_delete(
                str(self.owner_id),
                {
                    "task_name": "exam",
                },
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Physics exam")

    async def test_find_tasks_for_delete_with_priority_filter(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            rows = await find_tasks_for_delete(
                str(self.owner_id),
                {
                    "priority": "medium",
                },
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_id"], str(self.task2_id))
        self.assertEqual(rows[0]["priority"], "medium")

    async def test_find_tasks_for_delete_with_date_filter(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            rows = await find_tasks_for_delete(
                str(self.owner_id),
                {
                    "date": "2026-04-01",
                },
            )

        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["owner_id"] == str(self.owner_id) for row in rows))

    async def test_find_tasks_for_delete_returns_empty_when_no_match(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            rows = await find_tasks_for_delete(
                str(self.owner_id),
                {
                    "task_name": "biology",
                    "date": "2026-04-01",
                },
            )

        self.assertEqual(rows, [])

    async def test_soft_delete_task_marks_task_deleted(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            updated = await soft_delete_task(str(self.task1_id))

        self.assertTrue(updated)
        updated_doc = next(doc for doc in fake_tasks.docs if doc["_id"] == self.task1_id)
        self.assertTrue(updated_doc["is_deleted"])
        self.assertIsNotNone(updated_doc["deleted_at"])

    async def test_soft_delete_many_marks_multiple_tasks(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            matched_count = await soft_delete_many(
                [str(self.task1_id), str(self.task2_id)]
            )

        self.assertEqual(matched_count, 2)
        doc1 = next(doc for doc in fake_tasks.docs if doc["_id"] == self.task1_id)
        doc2 = next(doc for doc in fake_tasks.docs if doc["_id"] == self.task2_id)
        self.assertTrue(doc1["is_deleted"])
        self.assertTrue(doc2["is_deleted"])

    async def test_get_task_by_id_respects_owner(self):
        fake_tasks = FakeTasksCollection(self.docs)
        fake_db = FakeDB(tasks_collection=fake_tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            owned_task = await get_task_by_id(str(self.task1_id), str(self.owner_id))
            foreign_task = await get_task_by_id(str(self.task1_id), str(self.other_owner_id))

        self.assertIsNotNone(owned_task)
        self.assertEqual(owned_task.get("_id"), str(self.task1_id))
        self.assertIn("collaborators", owned_task)
        self.assertIn("google_calendar_event_id", owned_task)
        self.assertIsNone(foreign_task)

    async def test_insert_log_accepts_task_deleted_action(self):
        fake_activity_logs = FakeActivityLogsCollection()
        fake_db = FakeDB(activity_logs_collection=fake_activity_logs)

        with patch("db.activity_logs.get_db", return_value=fake_db):
            inserted_id = await insert_log(
                {
                    "user_id": self.owner_id,
                    "task_id": self.task1_id,
                    "action_type": "task_deleted",
                    "subject": "Physics exam",
                },
                force=True,
            )

        self.assertTrue(inserted_id)
        self.assertEqual(len(fake_activity_logs.rows), 1)
        self.assertEqual(fake_activity_logs.rows[0]["action_type"], "task_deleted")


if __name__ == "__main__":
    unittest.main()
