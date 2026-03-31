"""
Phase 20 tests for show DB-layer and date utilities.
"""
from datetime import datetime, timedelta
import re
import unittest
from unittest.mock import patch

from bson import ObjectId

from db.tasks import find_tasks_for_show
from utils.date_utils import build_date_range, convert_tasks_to_local


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

    async def count_documents(self, query):
        return sum(1 for doc in self.docs if self._matches(doc, query))


class FakeDB:
    def __init__(self, tasks_collection):
        self.tasks = tasks_collection


class TestShowDbLayer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.owner_id = ObjectId()
        self.other_owner_id = ObjectId()

        self.docs = [
            {
                "_id": ObjectId(),
                "owner_id": self.owner_id,
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 9, 0, 0),
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
            },
            {
                "_id": ObjectId(),
                "owner_id": self.owner_id,
                "title": "Chemistry lab",
                "due_datetime": datetime(2026, 4, 1, 15, 0, 0),
                "priority": "medium",
                "status": "pending",
                "is_deleted": False,
            },
            {
                "_id": ObjectId(),
                "owner_id": self.owner_id,
                "title": "Physics assignment",
                "due_datetime": datetime(2026, 3, 20, 10, 0, 0),
                "priority": "high",
                "status": "complete",
                "is_deleted": False,
            },
            {
                "_id": ObjectId(),
                "owner_id": self.owner_id,
                "title": "Math quiz",
                "due_datetime": datetime(2026, 3, 15, 12, 0, 0),
                "priority": "low",
                "status": "pending",
                "is_deleted": False,
            },
            {
                "_id": ObjectId(),
                "owner_id": self.owner_id,
                "title": "Hidden deleted",
                "due_datetime": datetime(2026, 4, 1, 11, 0, 0),
                "priority": "high",
                "status": "pending",
                "is_deleted": True,
            },
            {
                "_id": ObjectId(),
                "owner_id": self.other_owner_id,
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 8, 0, 0),
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
            },
        ]

    async def test_find_tasks_for_show_with_date_filter(self):
        fake_db = FakeDB(FakeTasksCollection(self.docs))
        date_range = {
            "start_utc": datetime(2026, 4, 1, 0, 0, 0),
            "end_utc": datetime(2026, 4, 1, 23, 59, 59, 999999),
        }

        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {"date_range": date_range},
            )

        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["title"] for row in rows], ["Physics exam", "Chemistry lab"])

    async def test_find_tasks_for_show_with_priority_filter(self):
        fake_db = FakeDB(FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {
                    "priority": "high",
                    "now_utc": datetime(2026, 4, 1, 0, 0, 0),
                },
            )

        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Physics exam")

    async def test_find_tasks_for_show_with_pending_status(self):
        fake_db = FakeDB(FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {
                    "status": "pending",
                    "now_utc": datetime(2026, 4, 1, 0, 0, 0),
                },
            )

        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["status"] == "pending" for row in rows))

    async def test_find_tasks_for_show_complete_includes_past_desc(self):
        fake_docs = list(self.docs) + [
            {
                "_id": ObjectId(),
                "owner_id": self.owner_id,
                "title": "Physics project",
                "due_datetime": datetime(2026, 3, 25, 14, 0, 0),
                "priority": "medium",
                "status": "complete",
                "is_deleted": False,
            }
        ]
        fake_db = FakeDB(FakeTasksCollection(fake_docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {
                    "status": "complete",
                    "now_utc": datetime(2026, 4, 1, 0, 0, 0),
                },
            )

        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["title"] for row in rows], ["Physics project", "Physics assignment"])

    async def test_find_tasks_for_show_with_task_name_filter(self):
        fake_db = FakeDB(FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {
                    "task_name": "physics",
                    "now_utc": datetime(2026, 4, 1, 0, 0, 0),
                },
            )

        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Physics exam")

    async def test_find_tasks_for_show_with_no_filter_uses_upcoming(self):
        fake_db = FakeDB(FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {
                    "now_utc": datetime(2026, 4, 1, 0, 0, 0),
                },
            )

        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["title"] for row in rows], ["Physics exam", "Chemistry lab"])

    async def test_find_tasks_for_show_with_combined_filters(self):
        fake_db = FakeDB(FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {
                    "date_range": {
                        "start_utc": datetime(2026, 4, 1, 0, 0, 0),
                        "end_utc": datetime(2026, 4, 1, 23, 59, 59, 999999),
                    },
                    "task_name": "physics",
                    "priority": "high",
                    "status": "pending",
                },
            )

        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Physics exam")

    async def test_find_tasks_for_show_returns_empty_when_no_match(self):
        fake_db = FakeDB(FakeTasksCollection(self.docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {
                    "task_name": "biology",
                    "now_utc": datetime(2026, 4, 1, 0, 0, 0),
                },
            )

        self.assertEqual(rows, [])
        self.assertEqual(total, 0)

    async def test_find_tasks_for_show_returns_total_count_when_more_than_ten(self):
        now_utc = datetime(2026, 4, 1, 0, 0, 0)
        many_docs = []
        for index in range(12):
            many_docs.append(
                {
                    "_id": ObjectId(),
                    "owner_id": self.owner_id,
                    "title": f"Task {index + 1}",
                    "due_datetime": now_utc + timedelta(hours=index + 1),
                    "priority": "medium",
                    "status": "pending",
                    "is_deleted": False,
                }
            )

        fake_db = FakeDB(FakeTasksCollection(many_docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows, total = await find_tasks_for_show(
                str(self.owner_id),
                {"now_utc": now_utc},
            )

        self.assertEqual(total, 12)
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["title"], "Task 1")
        self.assertEqual(rows[-1]["title"], "Task 10")

    def test_build_date_range_day_grain(self):
        result = build_date_range(
            {
                "value": {
                    "value": "2026-03-30T00:00:00.000+05:00",
                    "grain": "day",
                }
            },
            "PKT",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["start_utc"], datetime(2026, 3, 29, 19, 0, 0))
        self.assertEqual(result["end_utc"], datetime(2026, 3, 30, 18, 59, 59, 999999))

    def test_build_date_range_week_grain(self):
        result = build_date_range(
            {
                "value": {
                    "value": "2026-03-23T00:00:00.000+05:00",
                    "grain": "week",
                }
            },
            "PKT",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["start_utc"], datetime(2026, 3, 22, 19, 0, 0))
        self.assertEqual(result["end_utc"], datetime(2026, 3, 29, 18, 59, 59, 999999))

    def test_build_date_range_month_grain(self):
        result = build_date_range(
            {
                "value": {
                    "value": "2026-03-01T00:00:00.000+05:00",
                    "grain": "month",
                }
            },
            "PKT",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["start_utc"], datetime(2026, 2, 28, 19, 0, 0))
        self.assertEqual(result["end_utc"], datetime(2026, 3, 31, 18, 59, 59, 999999))

    def test_convert_tasks_to_local_timezone(self):
        tasks = [
            {
                "title": "Physics exam",
                "due_datetime": datetime(2026, 3, 30, 12, 0, 0),
            }
        ]

        localized = convert_tasks_to_local(tasks, "PKT")
        self.assertEqual(len(localized), 1)
        self.assertEqual(localized[0]["local_datetime_str"], "Monday 5:00 PM")
        self.assertEqual(localized[0]["local_time_str"], "5:00 PM")


if __name__ == "__main__":
    unittest.main()
