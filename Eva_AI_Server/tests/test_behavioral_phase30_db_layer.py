"""
Phase 30 tests for behavioral analytics DB-layer helpers.
"""
from datetime import datetime
import unittest
from unittest.mock import patch

from bson import ObjectId

from db.activity_logs import (
    count_completed,
    get_completed_logs_for_scoring,
    get_avg_time_taken,
    get_completion_rate,
    get_days_distribution,
    get_hours_distribution,
    get_log_count_per_day,
    get_logs_for_day,
    get_total_completed,
)
from db.tasks import get_tasks_for_day
from utils.date_utils import hour_to_12h_format, weekday_name_to_number


class FakeAggregateCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    async def to_list(self, length=100):
        return [dict(row) for row in self.rows[:length]]


class FakeTasksCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, key, direction):
        reverse = direction == -1
        self.rows = sorted(self.rows, key=lambda row: row.get(key), reverse=reverse)
        return self

    async def to_list(self, length=100):
        return [dict(row) for row in self.rows[:length]]


class FakeActivityLogsCollection:
    def __init__(self, docs):
        self.docs = [dict(doc) for doc in docs]

    @staticmethod
    def _match_condition(actual, expected):
        if isinstance(expected, dict):
            for op, value in expected.items():
                if op == "$in" and actual not in value:
                    return False
                if actual is None and op in {"$gte", "$lte"}:
                    return False
                if op == "$gte" and actual < value:
                    return False
                if op == "$lte" and actual > value:
                    return False
                if op == "$type":
                    if value == "number" and not isinstance(actual, (int, float)):
                        return False
            return True
        return actual == expected

    def _matches(self, doc, query):
        for key, expected in query.items():
            if not self._match_condition(doc.get(key), expected):
                return False
        return True

    async def count_documents(self, query):
        return sum(1 for doc in self.docs if self._matches(doc, query))

    def find(self, query, projection=None):
        rows = [dict(doc) for doc in self.docs if self._matches(doc, query)]
        if projection:
            include_keys = {
                key
                for key, include in projection.items()
                if include and key != "_id"
            }
            normalized = []
            for row in rows:
                filtered = {key: row.get(key) for key in include_keys}
                if projection.get("_id", 1):
                    filtered["_id"] = row.get("_id")
                normalized.append(filtered)
            rows = normalized
        return FakeTasksCursor(rows)

    def aggregate(self, pipeline):
        rows = [dict(doc) for doc in self.docs]

        for stage in pipeline:
            if "$match" in stage:
                query = stage["$match"]
                rows = [doc for doc in rows if self._matches(doc, query)]
                continue

            if "$group" in stage:
                group_spec = stage["$group"]
                key_expr = group_spec.get("_id")

                if "avg_time_taken" in group_spec:
                    values = [doc.get("time_taken_minutes") for doc in rows if isinstance(doc.get("time_taken_minutes"), (int, float))]
                    rows = [{"_id": None, "avg_time_taken": (sum(values) / len(values))}] if values else []
                    continue

                grouped = {}
                for doc in rows:
                    if key_expr is None:
                        group_key = None
                    elif isinstance(key_expr, str) and key_expr.startswith("$"):
                        group_key = doc.get(key_expr[1:])
                    else:
                        group_key = key_expr

                    bucket = grouped.setdefault(
                        group_key,
                        {
                            "_id": group_key,
                            "count": 0,
                            "on_time_count": 0,
                            "total_completed": 0,
                            "on_time": 0,
                        },
                    )
                    bucket["count"] += 1
                    bucket["total_completed"] += 1
                    if doc.get("was_on_time") is True:
                        bucket["on_time_count"] += 1
                        bucket["on_time"] += 1

                rows = list(grouped.values())
                # Remove unused keys based on requested output fields.
                cleaned = []
                for row in rows:
                    cleaned_row = {"_id": row.get("_id")}
                    for field in group_spec.keys():
                        if field == "_id":
                            continue
                        cleaned_row[field] = row.get(field, 0)
                    cleaned.append(cleaned_row)
                rows = cleaned
                continue

            if "$sort" in stage:
                sort_spec = stage["$sort"]
                for field, direction in reversed(list(sort_spec.items())):
                    rows = sorted(rows, key=lambda row: row.get(field, 0), reverse=(direction == -1))
                continue

            if "$limit" in stage:
                rows = rows[: int(stage["$limit"])]
                continue

        return FakeAggregateCursor(rows)


class FakeTasksCollection:
    def __init__(self, docs):
        self.docs = [dict(doc) for doc in docs]

    @staticmethod
    def _matches(doc, query):
        for key, expected in query.items():
            if key == "$expr":
                # Handles:
                # {"$eq": [{"$subtract": [{"$isoDayOfWeek": "$due_datetime"}, 1]}, day]}
                eq_expr = expected.get("$eq", [])
                if len(eq_expr) != 2:
                    return False
                day_target = int(eq_expr[1])
                due = doc.get("due_datetime")
                if not isinstance(due, datetime):
                    return False
                if due.weekday() != day_target:
                    return False
                continue

            actual = doc.get(key)
            if isinstance(expected, dict):
                for op, value in expected.items():
                    if op == "$ne" and actual == value:
                        return False
                    if op == "$type":
                        if value == "date" and not isinstance(actual, datetime):
                            return False
            else:
                if actual != expected:
                    return False
        return True

    def find(self, query, projection=None):
        rows = [doc for doc in self.docs if self._matches(doc, query)]
        if projection:
            normalized_rows = []
            include_keys = {k for k, v in projection.items() if v}
            include_keys.add("_id")
            for row in rows:
                normalized_rows.append({k: row.get(k) for k in include_keys if k in row})
            rows = normalized_rows
        return FakeTasksCursor(rows)


class FakeDB:
    def __init__(self, activity_logs_collection=None, tasks_collection=None):
        self.activity_logs = activity_logs_collection
        self.tasks = tasks_collection


class TestBehavioralPhase30DbLayer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.owner_id = ObjectId()
        self.other_owner_id = ObjectId()

        self.activity_docs = [
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "hour_of_day": 18, "day_of_week": 1, "scheduled_hour": 10, "scheduled_day": 0, "was_on_time": True, "week_number": 12, "time_taken_minutes": 60},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "hour_of_day": 18, "day_of_week": 1, "scheduled_hour": 10, "scheduled_day": 0, "was_on_time": True, "week_number": 12, "time_taken_minutes": 90},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "hour_of_day": 10, "day_of_week": 1, "scheduled_hour": 14, "scheduled_day": 0, "was_on_time": False, "week_number": 13, "time_taken_minutes": 120},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "hour_of_day": 15, "day_of_week": 0, "scheduled_hour": 16, "scheduled_day": 2, "was_on_time": True, "week_number": 14, "time_taken_minutes": 75},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "hour_of_day": 15, "day_of_week": 0, "scheduled_hour": 16, "scheduled_day": 2, "was_on_time": False, "week_number": 15, "time_taken_minutes": 105},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_created", "hour_of_day": 15, "day_of_week": 0, "scheduled_hour": 15, "scheduled_day": 0, "was_on_time": True, "week_number": 15, "time_taken_minutes": 30},
            {"_id": ObjectId(), "user_id": self.other_owner_id, "action_type": "task_completed", "hour_of_day": 22, "day_of_week": 4, "scheduled_hour": 22, "scheduled_day": 4, "was_on_time": True, "week_number": 15, "time_taken_minutes": 50},
        ]

        self.task_docs = [
            {"_id": ObjectId(), "owner_id": self.owner_id, "due_datetime": datetime(2026, 4, 13, 17, 0, 0), "duration": 60, "is_deleted": False},  # Monday
            {"_id": ObjectId(), "owner_id": self.owner_id, "due_datetime": datetime(2026, 4, 13, 19, 30, 0), "duration": 90, "is_deleted": False},  # Monday
            {"_id": ObjectId(), "owner_id": self.owner_id, "due_datetime": datetime(2026, 4, 14, 10, 0, 0), "duration": 45, "is_deleted": False},  # Tuesday
            {"_id": ObjectId(), "owner_id": self.owner_id, "due_datetime": datetime(2026, 4, 13, 21, 0, 0), "duration": 30, "is_deleted": True},   # Monday deleted
        ]

    async def test_count_completed_returns_correct_count(self):
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(self.activity_docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            count = await count_completed(str(self.owner_id))

        self.assertEqual(count, 5)

    async def test_get_hours_distribution_returns_ranked_hours(self):
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(self.activity_docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            rows = await get_hours_distribution(str(self.owner_id))

        self.assertEqual(rows[0]["hour"], 10)
        self.assertEqual(rows[0]["count"], 2)
        self.assertEqual(rows[1]["hour"], 16)
        self.assertEqual(rows[1]["count"], 2)
        self.assertEqual(rows[2]["hour"], 14)
        self.assertEqual(rows[2]["count"], 1)

    async def test_get_hours_distribution_with_day_filter(self):
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(self.activity_docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            rows = await get_hours_distribution(str(self.owner_id), day_of_week=0)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["hour"], 10)
        self.assertEqual(rows[0]["count"], 2)
        self.assertEqual(rows[1]["hour"], 14)
        self.assertEqual(rows[1]["count"], 1)

    async def test_get_days_distribution_returns_all_days_ranked(self):
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(self.activity_docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            rows = await get_days_distribution(str(self.owner_id))

        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["day_name"], "Monday")
        self.assertEqual(rows[0]["count"], 3)
        self.assertEqual(rows[1]["day_name"], "Wednesday")
        self.assertEqual(rows[1]["count"], 2)
        # Ranking is count desc.
        self.assertGreaterEqual(rows[0]["count"], rows[1]["count"])

    async def test_get_hours_distribution_ignores_missing_scheduled_hour(self):
        docs_with_missing = list(self.activity_docs) + [
            {
                "_id": ObjectId(),
                "user_id": self.owner_id,
                "action_type": "task_completed",
                "hour_of_day": 22,
                "day_of_week": 4,
                "was_on_time": True,
                "week_number": 16,
                "time_taken_minutes": 30,
            }
        ]
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(docs_with_missing))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            rows = await get_hours_distribution(str(self.owner_id))

        self.assertEqual(sum(int(row["count"]) for row in rows), 5)
        self.assertNotIn(22, [int(row["hour"]) for row in rows])

    async def test_get_completion_rate_returns_summary_and_trend(self):
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(self.activity_docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            result = await get_completion_rate(str(self.owner_id))

        self.assertEqual(result["total_completed"], 5)
        self.assertEqual(result["on_time"], 3)
        self.assertEqual(result["late"], 2)
        self.assertEqual(result["on_time_rate"], 60.0)
        self.assertTrue(len(result["weekly_trend"]) >= 1)

    async def test_get_avg_time_taken_returns_average(self):
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(self.activity_docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            avg = await get_avg_time_taken(str(self.owner_id))

        # (60 + 90 + 120 + 75 + 105) / 5 = 90
        self.assertEqual(avg, 90.0)

    async def test_get_completed_logs_for_scoring_returns_only_completed_sorted(self):
        docs = [
            {
                "_id": ObjectId(),
                "user_id": self.owner_id,
                "action_type": "task_completed",
                "day_of_week": 0,
                "hour_of_day": 18,
                "was_on_time": True,
                "time_taken_minutes": 50,
                "action_timestamp": datetime(2026, 4, 20, 10, 0, 0),
                "reschedule_count": 2,
                "scheduled_hour": 18,
                "task_priority": "high",
            },
            {
                "_id": ObjectId(),
                "user_id": self.owner_id,
                "action_type": "task_created",
                "day_of_week": 0,
                "hour_of_day": 17,
                "action_timestamp": datetime(2026, 4, 20, 9, 0, 0),
            },
            {
                "_id": ObjectId(),
                "user_id": self.owner_id,
                "action_type": "task_completed",
                "day_of_week": 1,
                "hour_of_day": 10,
                "was_on_time": False,
                "time_taken_minutes": 80,
                "action_timestamp": datetime(2026, 4, 21, 8, 0, 0),
                "scheduled_hour": 10,
                "task_priority": "medium",
            },
            {
                "_id": ObjectId(),
                "user_id": self.other_owner_id,
                "action_type": "task_completed",
                "day_of_week": 1,
                "hour_of_day": 14,
                "action_timestamp": datetime(2026, 4, 21, 7, 0, 0),
            },
        ]
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            rows = await get_completed_logs_for_scoring(str(self.owner_id))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["action_timestamp"], datetime(2026, 4, 21, 8, 0, 0))
        self.assertEqual(rows[1]["action_timestamp"], datetime(2026, 4, 20, 10, 0, 0))
        self.assertIn("reschedule_count", rows[0])

    async def test_get_logs_for_day_filters_requested_day_only(self):
        docs = [
            {
                "_id": ObjectId(),
                "user_id": self.owner_id,
                "action_type": "task_completed",
                "day_of_week": 0,
                "hour_of_day": 18,
                "action_timestamp": datetime(2026, 4, 20, 10, 0, 0),
            },
            {
                "_id": ObjectId(),
                "user_id": self.owner_id,
                "action_type": "task_completed",
                "day_of_week": 1,
                "hour_of_day": 19,
                "action_timestamp": datetime(2026, 4, 21, 10, 0, 0),
            },
            {
                "_id": ObjectId(),
                "user_id": self.owner_id,
                "action_type": "task_completed",
                "day_of_week": 0,
                "hour_of_day": 20,
                "action_timestamp": datetime(2026, 4, 22, 10, 0, 0),
            },
        ]
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            monday = await get_logs_for_day(str(self.owner_id), 0)
            invalid = await get_logs_for_day(str(self.owner_id), 99)

        self.assertEqual(len(monday), 2)
        self.assertTrue(all(row["day_of_week"] == 0 for row in monday))
        self.assertEqual(invalid, [])

    async def test_get_log_count_per_day_returns_full_day_map(self):
        docs = [
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "day_of_week": 0},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "day_of_week": 0},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "day_of_week": 0},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "day_of_week": 1},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "day_of_week": 1},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "day_of_week": 1},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "day_of_week": 1},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed", "day_of_week": 1},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_created", "day_of_week": 1},
        ]
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            counts = await get_log_count_per_day(str(self.owner_id))

        self.assertEqual(counts[0], 3)
        self.assertEqual(counts[1], 5)
        self.assertEqual(counts[2], 0)
        self.assertEqual(set(counts.keys()), set(range(7)))

    async def test_get_total_completed_counts_only_completed(self):
        docs = [
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed"},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed"},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed"},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed"},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_completed"},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_created"},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_created"},
            {"_id": ObjectId(), "user_id": self.owner_id, "action_type": "task_created"},
        ]
        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            total = await get_total_completed(str(self.owner_id))

        self.assertEqual(total, 5)

    async def test_phase3_scenario_15_completed_logs_across_4_days(self):
        docs = []
        day_sequence = [0] * 4 + [1] * 5 + [2] * 3 + [3] * 3  # total 15
        for index, day in enumerate(day_sequence):
            docs.append(
                {
                    "_id": ObjectId(),
                    "user_id": self.owner_id,
                    "action_type": "task_completed",
                    "day_of_week": day,
                    "hour_of_day": 9 + (index % 8),
                    "action_timestamp": datetime(2026, 4, 1, 10, 0, 0),
                }
            )
        docs.append(
            {
                "_id": ObjectId(),
                "user_id": self.owner_id,
                "action_type": "task_created",
                "day_of_week": 0,
            }
        )

        fake_db = FakeDB(activity_logs_collection=FakeActivityLogsCollection(docs))
        with patch("db.activity_logs.get_db", return_value=fake_db):
            all_logs = await get_completed_logs_for_scoring(str(self.owner_id))
            monday_logs = await get_logs_for_day(str(self.owner_id), 0)
            counts = await get_log_count_per_day(str(self.owner_id))
            total = await get_total_completed(str(self.owner_id))

        self.assertEqual(len(all_logs), 15)
        self.assertEqual(len(monday_logs), 4)
        self.assertEqual(counts[0], 4)
        self.assertEqual(counts[1], 5)
        self.assertEqual(counts[2], 3)
        self.assertEqual(counts[3], 3)
        self.assertEqual(total, 15)

    async def test_get_tasks_for_day_returns_monday_tasks_only(self):
        fake_db = FakeDB(tasks_collection=FakeTasksCollection(self.task_docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows = await get_tasks_for_day(str(self.owner_id), 0)  # Monday

        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["due_datetime"].weekday(), 0)

    async def test_get_tasks_for_day_invalid_day_returns_empty(self):
        fake_db = FakeDB(tasks_collection=FakeTasksCollection(self.task_docs))
        with patch("db.tasks.get_db", return_value=fake_db):
            rows = await get_tasks_for_day(str(self.owner_id), 9)
        self.assertEqual(rows, [])

    def test_weekday_name_to_number_all_days_case_insensitive(self):
        self.assertEqual(weekday_name_to_number("monday"), 0)
        self.assertEqual(weekday_name_to_number("TUESDAY"), 1)
        self.assertEqual(weekday_name_to_number("Wednesday"), 2)
        self.assertEqual(weekday_name_to_number("thursday"), 3)
        self.assertEqual(weekday_name_to_number("FRIDAY"), 4)
        self.assertEqual(weekday_name_to_number("saturday"), 5)
        self.assertEqual(weekday_name_to_number("Sunday"), 6)
        self.assertIsNone(weekday_name_to_number("xyz"))

    def test_hour_to_12h_format_edge_cases(self):
        self.assertEqual(hour_to_12h_format(0), "12AM")
        self.assertEqual(hour_to_12h_format(10), "10AM")
        self.assertEqual(hour_to_12h_format(12), "12PM")
        self.assertEqual(hour_to_12h_format(18), "6PM")
        self.assertEqual(hour_to_12h_format(23), "11PM")
        self.assertIsNone(hour_to_12h_format(24))
        self.assertIsNone(hour_to_12h_format("invalid"))


if __name__ == "__main__":
    unittest.main()
