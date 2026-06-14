"""
Phase 3 tests for learning_delete DB-layer helpers.
"""

import unittest
from datetime import datetime
from unittest.mock import patch

from bson import ObjectId

from db import learning_goals as lg
from db import roadmap_topics as rt
from db.tasks import (
    get_pending_learning_tasks,
    get_task_for_learning_topic,
    soft_delete_learning_topic_task,
    soft_delete_pending_learning_tasks,
)


def _matches(doc, query):
    if not query:
        return True
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(doc, clause) for clause in expected):
                return False
            continue
        actual = doc.get(key)
        if isinstance(expected, dict) and expected and all(
            k.startswith("$") for k in expected
        ):
            for op, val in expected.items():
                if op == "$ne":
                    if actual == val:
                        return False
                elif op == "$in":
                    if actual not in val:
                        return False
            continue
        if actual != expected:
            return False
    return True


class FakeUpdateResult:
    def __init__(self, matched_count: int, modified_count: int = 0):
        self.matched_count = matched_count
        self.modified_count = modified_count


class FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, str):
            rev = direction == -1
            self._rows = sorted(
                self._rows,
                key=lambda r: r.get(key_or_list, 0),
                reverse=rev,
            )
        return self

    async def to_list(self, length=None):
        if length is None:
            return [dict(r) for r in self._rows]
        return [dict(r) for r in self._rows[:length]]


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def find(self, query, projection=None):
        rows = [d for d in self.docs if _matches(d, query)]
        if projection:
            projected = []
            for row in rows:
                item = {}
                for key, include in projection.items():
                    if include and key in row:
                        item[key] = row[key]
                projected.append(item)
            rows = projected
        return FakeCursor(rows)

    async def update_one(self, filt, update):
        matched = 0
        for doc in self.docs:
            if _matches(doc, filt):
                matched += 1
                for k, v in update.get("$set", {}).items():
                    doc[k] = v
        return FakeUpdateResult(matched)

    async def update_many(self, filt, update):
        matched = 0
        for doc in self.docs:
            if _matches(doc, filt):
                matched += 1
                for k, v in update.get("$set", {}).items():
                    doc[k] = v
        return FakeUpdateResult(matched)

    async def find_one(self, query, projection=None):
        rows = [d for d in self.docs if _matches(d, query)]
        if not rows:
            return None
        row = dict(rows[0])
        if projection:
            projected = {}
            for key, include in projection.items():
                if include and key in row:
                    projected[key] = row[key]
            return projected
        return row


class FakeDB:
    def __init__(self):
        self.learning_goals = FakeCollection()
        self.roadmap_topics = FakeCollection()
        self.tasks = FakeCollection()


class LearningDeletePhase3DbLayerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.goal_id = ObjectId()
        self.other_goal_id = ObjectId()

    async def test_find_goals_for_delete_topic_only(self):
        fake = FakeDB()
        fake.learning_goals.docs = [
            {
                "_id": self.goal_id,
                "user_id": self.user_id,
                "subject": "python",
                "roadmap_key": "basics",
                "title": "Python basics",
                "status": "active",
                "completed_topics": 1,
                "total_topics": 5,
                "collaborators": [],
                "is_deleted": False,
                "created_at": datetime(2026, 2, 1),
            },
            {
                "_id": self.other_goal_id,
                "user_id": self.user_id,
                "subject": "python",
                "roadmap_key": "functions",
                "title": "Python functions",
                "status": "paused",
                "completed_topics": 0,
                "total_topics": 4,
                "collaborators": [],
                "is_deleted": False,
                "created_at": datetime(2026, 1, 1),
            },
        ]
        with patch.object(lg, "get_db", return_value=fake):
            rows = await lg.find_goals_for_delete(str(self.user_id), "Python")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["roadmap_key"], "basics")

    async def test_find_goals_for_delete_with_roadmap_key(self):
        fake = FakeDB()
        fake.learning_goals.docs = [
            {
                "_id": self.goal_id,
                "user_id": self.user_id,
                "subject": "python",
                "roadmap_key": "basics",
                "title": "Python basics",
                "status": "active",
                "is_deleted": False,
                "created_at": datetime(2026, 2, 1),
            },
            {
                "_id": self.other_goal_id,
                "user_id": self.user_id,
                "subject": "python",
                "roadmap_key": "functions",
                "title": "Python functions",
                "status": "active",
                "is_deleted": False,
                "created_at": datetime(2026, 1, 1),
            },
        ]
        with patch.object(lg, "get_db", return_value=fake):
            rows = await lg.find_goals_for_delete(
                str(self.user_id), "python", roadmap_key="basics"
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_id"], str(self.goal_id))

    async def test_find_goals_for_delete_excludes_deleted_and_includes_completed(self):
        fake = FakeDB()
        deleted_id = ObjectId()
        completed_id = ObjectId()
        fake.learning_goals.docs = [
            {
                "_id": deleted_id,
                "user_id": self.user_id,
                "subject": "mysql",
                "roadmap_key": "basics",
                "status": "active",
                "is_deleted": True,
                "created_at": datetime(2026, 3, 1),
            },
            {
                "_id": completed_id,
                "user_id": self.user_id,
                "subject": "mysql",
                "roadmap_key": "general",
                "status": "completed",
                "is_deleted": False,
                "created_at": datetime(2026, 2, 1),
            },
        ]
        with patch.object(lg, "get_db", return_value=fake):
            rows = await lg.find_goals_for_delete(str(self.user_id), "mysql")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_id"], str(completed_id))
        self.assertEqual(rows[0]["status"], "completed")

    async def test_find_goals_for_delete_no_matches(self):
        fake = FakeDB()
        with patch.object(lg, "get_db", return_value=fake):
            rows = await lg.find_goals_for_delete(str(self.user_id), "rust")
        self.assertEqual(rows, [])

    async def test_soft_delete_goal(self):
        fake = FakeDB()
        fake.learning_goals.docs = [
            {
                "_id": self.goal_id,
                "user_id": self.user_id,
                "is_deleted": False,
            }
        ]
        with patch.object(lg, "get_db", return_value=fake):
            ok = await lg.soft_delete_goal(str(self.goal_id))
        self.assertTrue(ok)
        doc = fake.learning_goals.docs[0]
        self.assertTrue(doc["is_deleted"])
        self.assertIsNotNone(doc.get("deleted_at"))
        self.assertIsNotNone(doc.get("updated_at"))

    async def test_soft_delete_goal_invalid_id_returns_false(self):
        fake = FakeDB()
        with patch.object(lg, "get_db", return_value=fake):
            ok = await lg.soft_delete_goal("not-a-valid-object-id")
        self.assertFalse(ok)

    async def test_soft_delete_goals_bulk(self):
        fake = FakeDB()
        gid2 = ObjectId()
        fake.learning_goals.docs = [
            {"_id": self.goal_id, "is_deleted": False},
            {"_id": gid2, "is_deleted": False},
        ]
        with patch.object(lg, "get_db", return_value=fake):
            count = await lg.soft_delete_goals_bulk(
                [str(self.goal_id), str(gid2)]
            )
        self.assertEqual(count, 2)
        self.assertTrue(all(d["is_deleted"] for d in fake.learning_goals.docs))

    async def test_soft_delete_pending_topics_keeps_completed(self):
        fake = FakeDB()
        pending_ids = [ObjectId() for _ in range(5)]
        completed_ids = [ObjectId() for _ in range(3)]
        fake.roadmap_topics.docs = [
            *[
                {
                    "_id": tid,
                    "goal_id": self.goal_id,
                    "status": "pending",
                    "is_deleted": False,
                }
                for tid in pending_ids[:4]
            ],
            {
                "_id": pending_ids[4],
                "goal_id": self.goal_id,
                "status": "ongoing",
                "is_deleted": False,
            },
            *[
                {
                    "_id": tid,
                    "goal_id": self.goal_id,
                    "status": "completed",
                    "is_deleted": False,
                }
                for tid in completed_ids
            ],
        ]
        with patch.object(rt, "get_db", return_value=fake):
            deleted_count = await rt.soft_delete_pending_topics(str(self.goal_id))
        self.assertEqual(deleted_count, 5)
        for doc in fake.roadmap_topics.docs:
            if doc["status"] in {"pending", "ongoing"}:
                self.assertTrue(doc["is_deleted"])
            else:
                self.assertFalse(doc["is_deleted"])

    async def test_soft_delete_pending_learning_tasks_keeps_complete(self):
        fake = FakeDB()
        plan_oid = self.goal_id
        pending = [ObjectId() for _ in range(5)]
        completed = [ObjectId() for _ in range(2)]
        fake.tasks.docs = [
            *[
                {
                    "_id": tid,
                    "learning_plan_id": plan_oid,
                    "status": "pending",
                    "is_deleted": False,
                }
                for tid in pending[:4]
            ],
            {
                "_id": pending[4],
                "learning_plan_id": plan_oid,
                "status": "ongoing",
                "is_deleted": False,
            },
            *[
                {
                    "_id": tid,
                    "learning_plan_id": plan_oid,
                    "status": "complete",
                    "is_deleted": False,
                }
                for tid in completed
            ],
        ]
        with patch("db.tasks.get_db", return_value=fake):
            deleted_count = await soft_delete_pending_learning_tasks(str(self.goal_id))
        self.assertEqual(deleted_count, 5)
        for doc in fake.tasks.docs:
            if doc["status"] in {"pending", "ongoing"}:
                self.assertTrue(doc["is_deleted"])
            else:
                self.assertFalse(doc["is_deleted"])

    async def test_get_pending_learning_tasks(self):
        fake = FakeDB()
        cal_id = "gcal-event-123"
        fake.tasks.docs = [
            {
                "_id": ObjectId(),
                "learning_plan_id": self.goal_id,
                "status": "pending",
                "is_deleted": False,
                "google_calendar_event_id": cal_id,
            },
            {
                "_id": ObjectId(),
                "learning_plan_id": self.goal_id,
                "status": "complete",
                "is_deleted": False,
                "google_calendar_event_id": "should-not-return",
            },
        ]
        with patch("db.tasks.get_db", return_value=fake):
            rows = await get_pending_learning_tasks(str(self.goal_id))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["google_calendar_event_id"], cal_id)

    async def test_get_task_for_learning_topic_falls_back_to_learning_topic_id(self):
        fake = FakeDB()
        topic_id = ObjectId()
        task_id = ObjectId()
        fake.tasks.docs = [
            {
                "_id": task_id,
                "owner_id": self.user_id,
                "learning_plan_id": self.goal_id,
                "learning_topic_id": topic_id,
                "status": "pending",
                "is_deleted": False,
            }
        ]
        with patch("db.tasks.get_db", return_value=fake):
            row = await get_task_for_learning_topic(
                str(topic_id),
                str(self.goal_id),
                str(self.user_id),
            )
        self.assertEqual(row["_id"], str(task_id))

    async def test_soft_delete_learning_topic_task_uses_learning_topic_id_fallback(self):
        fake = FakeDB()
        topic_id = ObjectId()
        task_id = ObjectId()
        fake.tasks.docs = [
            {
                "_id": task_id,
                "owner_id": self.user_id,
                "learning_plan_id": self.goal_id,
                "learning_topic_id": topic_id,
                "status": "pending",
                "is_deleted": False,
            }
        ]
        with patch("db.tasks.get_db", return_value=fake):
            deleted, task_doc = await soft_delete_learning_topic_task(
                topic_id=str(topic_id),
                goal_id=str(self.goal_id),
                user_id=str(self.user_id),
            )
        self.assertTrue(deleted)
        self.assertEqual(task_doc["_id"], str(task_id))
        self.assertTrue(fake.tasks.docs[0]["is_deleted"])


if __name__ == "__main__":
    unittest.main()
