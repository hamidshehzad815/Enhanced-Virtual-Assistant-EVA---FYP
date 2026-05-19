"""
Tests for db/learning_goals.py and db/roadmap_topics.py (faked Mongo collections).
"""

import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from db import learning_goals as lg
from db import roadmap_topics as rt


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
                elif op == "$lt":
                    if not (actual is not None and actual < val):
                        return False
                elif op == "$exists":
                    has = key in doc
                    if val and not has:
                        return False
                    if not val and has:
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
        else:
            rows = list(self._rows)
            for key, direc in reversed(key_or_list):
                rev = direc == -1
                rows = sorted(rows, key=lambda r: r.get(key, 0), reverse=rev)
            self._rows = rows
        return self

    async def to_list(self, length=None):
        if length is None:
            return [dict(r) for r in self._rows]
        return [dict(r) for r in self._rows[:length]]


def _apply_update(doc, update):
    if "$set" in update:
        for k, v in update["$set"].items():
            doc[k] = v
    if "$inc" in update:
        for k, v in update["$inc"].items():
            doc[k] = int(doc.get(k, 0)) + int(v)


class FakeLearningGoals:
    def __init__(self):
        self.docs = []

    async def insert_one(self, payload):
        row = dict(payload)
        row["_id"] = ObjectId()
        self.docs.append(row)
        return type("R", (), {"inserted_id": row["_id"]})()

    def find(self, query):
        rows = [d for d in self.docs if _matches(d, query)]
        return FakeCursor(rows)

    async def find_one(self, query, projection=None, sort=None):
        rows = [d for d in self.docs if _matches(d, query)]
        if sort:
            for key, direc in reversed(sort):
                rev = direc == -1
                rows = sorted(rows, key=lambda x: x.get(key, 0), reverse=rev)
        if not rows:
            return None
        doc = dict(rows[0])
        if projection == {"_id": 1}:
            return {"_id": doc["_id"]}
        return doc

    async def update_one(self, filt, update):
        matched = 0
        modified = 0
        for d in self.docs:
            if _matches(d, filt):
                matched += 1
                before = dict(d)
                _apply_update(d, update)
                if d != before:
                    modified += 1
        return FakeUpdateResult(matched, modified)

    async def find_one_and_update(self, filt, update, return_document=None):
        for d in self.docs:
            if _matches(d, filt):
                _apply_update(d, update)
                return dict(d)
        return None


class FakeRoadmapTopics:
    def __init__(self):
        self.docs = []

    async def insert_one(self, payload):
        row = dict(payload)
        row["_id"] = ObjectId()
        self.docs.append(row)
        return type("R", (), {"inserted_id": row["_id"]})()

    async def insert_many(self, payloads):
        ids = []
        for payload in payloads:
            row = dict(payload)
            row["_id"] = ObjectId()
            self.docs.append(row)
            ids.append(row["_id"])
        return type("R", (), {"inserted_ids": ids})()

    def find(self, query):
        rows = [d for d in self.docs if _matches(d, query)]
        return FakeCursor(rows)

    async def find_one(self, query, projection=None, sort=None):
        rows = [d for d in self.docs if _matches(d, query)]
        if sort:
            for key, direc in reversed(sort):
                rev = direc == -1
                rows = sorted(rows, key=lambda x: x.get(key, 0), reverse=rev)
        if not rows:
            return None
        return dict(rows[0])

    async def update_one(self, filt, update):
        matched = 0
        modified = 0
        for d in self.docs:
            if _matches(d, filt):
                matched += 1
                before = dict(d)
                _apply_update(d, update)
                if d != before:
                    modified += 1
        return FakeUpdateResult(matched, modified)


class FakeDB:
    def __init__(self):
        self.learning_goals = FakeLearningGoals()
        self.roadmap_topics = FakeRoadmapTopics()


@contextmanager
def patch_learning_db(fake: FakeDB):
    with patch.object(lg, "get_db", return_value=fake), patch.object(
        rt, "get_db", return_value=fake
    ):
        yield


class LearningDbLayerTests(unittest.IsolatedAsyncioTestCase):
    async def test_insert_goal_returns_objectid_string_and_normalizes(self):
        fake = FakeDB()
        uid = str(ObjectId())
        with patch_learning_db(fake):
            gid = await lg.insert_goal(
                {
                    "user_id": uid,
                    "subject": " Python ",
                    "roadmap_key": "Basics",
                    "total_topics": 3,
                }
            )
        self.assertEqual(len(gid), 24)
        self.assertEqual(fake.learning_goals.docs[0]["subject"], "python")
        self.assertEqual(fake.learning_goals.docs[0]["roadmap_key"], "basics")

    async def test_get_active_goals_excludes_completed(self):
        fake = FakeDB()
        uid = ObjectId()
        fake.learning_goals.docs = [
            {
                "_id": ObjectId(),
                "user_id": uid,
                "status": "active",
                "is_deleted": False,
                "created_at": datetime(2026, 1, 3),
            },
            {
                "_id": ObjectId(),
                "user_id": uid,
                "status": "active",
                "is_deleted": False,
                "created_at": datetime(2026, 1, 2),
            },
            {
                "_id": ObjectId(),
                "user_id": uid,
                "status": "completed",
                "is_deleted": False,
                "created_at": datetime(2026, 1, 1),
            },
        ]
        with patch_learning_db(fake):
            rows = await lg.get_active_goals_for_user(str(uid))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["created_at"].isoformat()[:10], "2026-01-03")

    async def test_check_duplicate_exact_match_and_different_level_allowed(self):
        fake = FakeDB()
        uid = ObjectId()
        fake.learning_goals.docs = [
            {
                "_id": ObjectId(),
                "user_id": uid,
                "subject": "python",
                "roadmap_key": "basics",
                "status": "active",
                "is_deleted": False,
            },
        ]
        with patch_learning_db(fake):
            dup_basics = await lg.check_duplicate_goal(str(uid), "python", "basics")
            dup_intermediate = await lg.check_duplicate_goal(
                str(uid), "python", "intermediate"
            )
            dup_rust = await lg.check_duplicate_goal(str(uid), "rust", "basics")
        self.assertTrue(dup_basics)
        self.assertFalse(dup_intermediate)
        self.assertFalse(dup_rust)

    async def test_check_duplicate_new_general_blocks_existing_track(self):
        fake = FakeDB()
        uid = ObjectId()
        fake.learning_goals.docs = [
            {
                "_id": ObjectId(),
                "user_id": uid,
                "subject": "python",
                "roadmap_key": "functions",
                "status": "active",
                "is_deleted": False,
            },
        ]
        with patch_learning_db(fake):
            dup = await lg.check_duplicate_goal(str(uid), "python", "general")
        self.assertTrue(dup)

    async def test_check_duplicate_general_blocks_any_roadmap_key(self):
        fake = FakeDB()
        uid = ObjectId()
        fake.learning_goals.docs = [
            {
                "_id": ObjectId(),
                "user_id": uid,
                "subject": "python",
                "roadmap_key": "general",
                "status": "active",
                "is_deleted": False,
            },
        ]
        with patch_learning_db(fake):
            dup_basics = await lg.check_duplicate_goal(str(uid), "python", "basics")
            dup_general = await lg.check_duplicate_goal(str(uid), "python", "general")
        self.assertTrue(dup_basics)
        self.assertTrue(dup_general)

    async def test_update_goal_status_completed_sets_time_taken(self):
        fake = FakeDB()
        gid = ObjectId()
        started = datetime(2026, 1, 1, tzinfo=timezone.utc).replace(tzinfo=None)
        fake.learning_goals.docs = [
            {
                "_id": gid,
                "user_id": ObjectId(),
                "started_at": started,
                "status": "active",
            }
        ]
        with patch_learning_db(fake), patch.object(
            lg,
            "_now_naive_utc",
            return_value=datetime(2026, 1, 13),
        ):
            ok = await lg.update_goal_status(str(gid), "completed")
        self.assertTrue(ok)
        doc = fake.learning_goals.docs[0]
        self.assertEqual(doc["status"], "completed")
        self.assertIsNotNone(doc.get("completed_at"))
        self.assertEqual(doc.get("time_taken_days"), 12)

    async def test_update_completed_topics_increments_and_completes_goal(self):
        fake = FakeDB()
        gid = ObjectId()
        fake.learning_goals.docs = [
            {
                "_id": gid,
                "user_id": ObjectId(),
                "total_topics": 2,
                "completed_topics": 0,
                "status": "active",
                "started_at": datetime(2026, 1, 1),
            }
        ]
        with patch_learning_db(fake):
            await lg.update_completed_topics(str(gid))
            await lg.update_completed_topics(str(gid))
        doc = fake.learning_goals.docs[0]
        self.assertEqual(doc["completed_topics"], 2)
        self.assertEqual(doc["status"], "completed")

    async def test_insert_topic_single(self):
        fake = FakeDB()
        gid = ObjectId()
        with patch_learning_db(fake):
            tid = await rt.insert_topic(
                {"goal_id": str(gid), "order": 1, "title": "One"},
            )
        self.assertEqual(len(tid), 24)
        self.assertEqual(len(fake.roadmap_topics.docs), 1)
        self.assertEqual(fake.roadmap_topics.docs[0]["title"], "One")

    async def test_insert_topics_bulk_and_get_topics_ordered(self):
        fake = FakeDB()
        gid = ObjectId()
        with patch_learning_db(fake):
            ids = await rt.insert_topics_bulk(
                [
                    {"goal_id": str(gid), "order": 2, "title": "B"},
                    {"goal_id": str(gid), "order": 1, "title": "A"},
                    {"goal_id": str(gid), "order": 3, "title": "C"},
                ]
            )
        self.assertEqual(len(ids), 3)
        with patch_learning_db(fake):
            topics = await rt.get_topics_for_goal(str(gid))
        titles = [t["title"] for t in topics]
        self.assertEqual(titles, ["A", "B", "C"])

    async def test_update_topic_task_id(self):
        fake = FakeDB()
        tid = ObjectId()
        task = ObjectId()
        fake.roadmap_topics.docs = [
            {"_id": tid, "goal_id": ObjectId(), "order": 1, "status": "pending"}
        ]
        with patch_learning_db(fake):
            ok = await rt.update_topic_task_id(str(tid), str(task))
        self.assertTrue(ok)
        self.assertEqual(fake.roadmap_topics.docs[0]["task_id"], task)

    async def test_get_pending_topic_lowest_order(self):
        fake = FakeDB()
        gid = ObjectId()
        fake.roadmap_topics.docs = [
            {
                "_id": ObjectId(),
                "goal_id": gid,
                "order": 2,
                "status": "pending",
                "is_deleted": False,
            },
            {
                "_id": ObjectId(),
                "goal_id": gid,
                "order": 1,
                "status": "pending",
                "is_deleted": False,
            },
        ]
        with patch_learning_db(fake):
            nxt = await rt.get_pending_topic(str(gid))
        self.assertEqual(nxt["order"], 1)

    async def test_update_topic_status_ongoing_sets_goal_started_at(self):
        fake = FakeDB()
        gid = ObjectId()
        tid = ObjectId()
        fake.learning_goals.docs = [
            {"_id": gid, "user_id": ObjectId(), "started_at": None},
        ]
        fake.roadmap_topics.docs = [
            {
                "_id": tid,
                "goal_id": gid,
                "order": 1,
                "status": "pending",
            }
        ]
        with patch_learning_db(fake):
            ok = await rt.update_topic_status(str(tid), "ongoing")
        self.assertTrue(ok)
        self.assertIsNotNone(fake.learning_goals.docs[0].get("started_at"))

    async def test_update_topic_completed_sets_started_at_and_updates_task(self):
        fake = FakeDB()
        gid = ObjectId()
        tid = ObjectId()
        task_oid = ObjectId()
        fake.learning_goals.docs = [
            {
                "_id": gid,
                "user_id": ObjectId(),
                "total_topics": 2,
                "completed_topics": 0,
                "status": "active",
                "started_at": None,
            }
        ]
        fake.roadmap_topics.docs = [
            {
                "_id": tid,
                "goal_id": gid,
                "order": 1,
                "status": "pending",
                "task_id": task_oid,
                "is_deleted": False,
            }
        ]
        mock_task_update = AsyncMock(return_value=True)
        with patch_learning_db(fake), patch("db.roadmap_topics.update_task", mock_task_update):
            ok = await rt.update_topic_status(str(tid), "completed")
        self.assertTrue(ok)
        self.assertEqual(fake.roadmap_topics.docs[0]["status"], "completed")
        self.assertIsNotNone(fake.learning_goals.docs[0].get("started_at"))
        mock_task_update.assert_awaited_once()

    async def test_pick_pending_topic_prefers_today_when_today_only(self):
        fake = FakeDB()
        uid = ObjectId()
        gid = ObjectId()
        today = datetime(2026, 5, 13, 10, 0, 0)
        other_day = datetime(2026, 5, 20, 10, 0, 0)
        fake.learning_goals.docs = [
            {
                "_id": gid,
                "user_id": uid,
                "status": "active",
                "is_deleted": False,
                "subject": "python",
                "created_at": datetime(2026, 5, 1),
            }
        ]
        t_today = ObjectId()
        t_later = ObjectId()
        fake.roadmap_topics.docs = [
            {
                "_id": t_later,
                "goal_id": gid,
                "order": 2,
                "status": "pending",
                "scheduled_date": other_day,
                "is_deleted": False,
            },
            {
                "_id": t_today,
                "goal_id": gid,
                "order": 1,
                "status": "pending",
                "scheduled_date": today,
                "is_deleted": False,
            },
        ]
        with patch.object(rt, "_now_naive_utc", return_value=today):
            with patch_learning_db(fake):
                picked = await rt.pick_pending_topic_for_chat_completion(
                    str(uid),
                    subject_hint="python",
                    today_only=True,
                )
        self.assertIsNotNone(picked)
        self.assertEqual(picked["topic"]["_id"], str(t_today))

    async def test_mark_topic_complete_increments_last_completes_goal(self):
        fake = FakeDB()
        gid = ObjectId()
        t1 = ObjectId()
        t2 = ObjectId()
        fake.learning_goals.docs = [
            {
                "_id": gid,
                "user_id": ObjectId(),
                "total_topics": 2,
                "completed_topics": 0,
                "status": "active",
                "started_at": datetime(2026, 1, 1),
            }
        ]
        fake.roadmap_topics.docs = [
            {"_id": t1, "goal_id": gid, "order": 1, "status": "ongoing"},
            {"_id": t2, "goal_id": gid, "order": 2, "status": "pending"},
        ]
        with patch_learning_db(fake):
            await rt.update_topic_status(str(t1), "completed")
            self.assertEqual(fake.learning_goals.docs[0]["completed_topics"], 1)
            self.assertEqual(fake.learning_goals.docs[0]["status"], "active")
            await rt.update_topic_status(str(t2), "completed")
        self.assertEqual(fake.learning_goals.docs[0]["completed_topics"], 2)
        self.assertEqual(fake.learning_goals.docs[0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
