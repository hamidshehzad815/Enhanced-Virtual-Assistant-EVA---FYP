"""
Phase 3 tests for learning_update DB-layer helpers.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from bson import ObjectId
from pymongo import ReturnDocument

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
        if isinstance(expected, dict) and expected and all(k.startswith("$") for k in expected):
            for op, val in expected.items():
                if op == "$ne":
                    if actual == val:
                        return False
                elif op == "$in":
                    if actual not in val:
                        return False
                elif op == "$gt":
                    if not (actual is not None and actual > val):
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
            self._rows = sorted(self._rows, key=lambda r: r.get(key_or_list, 0), reverse=rev)
            return self

        if isinstance(key_or_list, list) and key_or_list:
            # Apply first sort only (sufficient for our tests)
            key, dirn = key_or_list[0]
            rev = dirn == -1
            self._rows = sorted(self._rows, key=lambda r: r.get(key, 0), reverse=rev)
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

    async def find_one(self, query, projection=None, sort=None):
        rows = [d for d in self.docs if _matches(d, query)]
        if sort:
            # sort=[(key, dir)]
            key, direction = sort[0]
            rows = sorted(rows, key=lambda r: r.get(key, 0), reverse=(direction == -1))
        doc = rows[0] if rows else None
        if doc is None:
            return None
        if projection:
            out = {}
            for k, include in projection.items():
                if include and k in doc:
                    out[k] = doc[k]
            return dict(out)
        return dict(doc)

    async def update_one(self, filt, update):
        matched = 0
        for doc in self.docs:
            if _matches(doc, filt):
                matched += 1
                for k, v in update.get("$set", {}).items():
                    doc[k] = v
                for k, v in update.get("$inc", {}).items():
                    doc[k] = int(doc.get(k) or 0) + int(v)
                break
        return FakeUpdateResult(matched)

    async def find_one_and_update(self, filt, update, return_document=None):
        assert return_document in (None, ReturnDocument.AFTER)
        for doc in self.docs:
            if _matches(doc, filt):
                for k, v in update.get("$set", {}).items():
                    doc[k] = v
                for k, v in update.get("$inc", {}).items():
                    doc[k] = int(doc.get(k) or 0) + int(v)
                return dict(doc)
        return None


class FakeDB:
    def __init__(self):
        self.learning_goals = FakeCollection()
        self.roadmap_topics = FakeCollection()


def _naive_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None)


class LearningUpdatePhase3DbLayerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.goal_id = ObjectId()
        self.other_goal_id = ObjectId()

    async def test_find_goals_for_update_filters_status_and_roadmap_key(self):
        fake = FakeDB()
        fake.learning_goals.docs = [
            {
                "_id": self.goal_id,
                "user_id": self.user_id,
                "subject": "python",
                "roadmap_key": "basics",
                "status": "active",
                "is_deleted": False,
                "created_at": _naive_utc(datetime(2025, 1, 1, tzinfo=timezone.utc)),
            },
            {
                "_id": self.other_goal_id,
                "user_id": self.user_id,
                "subject": "python",
                "roadmap_key": "basics",
                "status": "paused",
                "is_deleted": False,
                "created_at": _naive_utc(datetime(2025, 1, 2, tzinfo=timezone.utc)),
            },
        ]

        with patch("db.learning_goals.get_db", return_value=fake):
            active = await lg.find_goals_for_update(
                str(self.user_id),
                "Python",
                roadmap_key="basics",
                status_filter="active",
            )
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["status"], "active")

            any_status = await lg.find_goals_for_update(
                str(self.user_id),
                "Python",
                roadmap_key="basics",
            )
            self.assertEqual(len(any_status), 2)
            # newest first
            self.assertEqual(any_status[0]["status"], "paused")

    async def test_pause_and_resume_goal(self):
        fake = FakeDB()
        fake.learning_goals.docs = [
            {"_id": self.goal_id, "status": "active", "is_deleted": False},
        ]
        with patch("db.learning_goals.get_db", return_value=fake):
            paused = await lg.pause_goal(str(self.goal_id))
            self.assertTrue(paused)
            self.assertEqual(fake.learning_goals.docs[0]["status"], "paused")
            self.assertIsNotNone(fake.learning_goals.docs[0].get("paused_at"))

            resumed = await lg.resume_goal(str(self.goal_id))
            self.assertTrue(resumed)
            self.assertEqual(fake.learning_goals.docs[0]["status"], "active")

    async def test_increment_completed_topics_returns_new_count(self):
        fake = FakeDB()
        fake.learning_goals.docs = [
            {"_id": self.goal_id, "completed_topics": 2, "is_deleted": False},
        ]
        with patch("db.learning_goals.get_db", return_value=fake):
            new_count = await lg.increment_completed_topics(str(self.goal_id))
            self.assertEqual(new_count, 3)
            self.assertEqual(fake.learning_goals.docs[0]["completed_topics"], 3)

    async def test_set_started_at_sets_once(self):
        fake = FakeDB()
        fake.learning_goals.docs = [
            {"_id": self.goal_id, "started_at": None},
        ]
        with patch("db.learning_goals.get_db", return_value=fake):
            ok1 = await lg.set_started_at(str(self.goal_id))
            self.assertTrue(ok1)
            started_value = fake.learning_goals.docs[0]["started_at"]
            self.assertIsNotNone(started_value)

            ok2 = await lg.set_started_at(str(self.goal_id))
            self.assertFalse(ok2)
            self.assertEqual(fake.learning_goals.docs[0]["started_at"], started_value)

    async def test_update_end_date(self):
        fake = FakeDB()
        fake.learning_goals.docs = [
            {"_id": self.goal_id, "end_date": None},
        ]
        new_end = _naive_utc(datetime(2025, 2, 1, tzinfo=timezone.utc))
        with patch("db.learning_goals.get_db", return_value=fake):
            ok = await lg.update_end_date(str(self.goal_id), new_end)
            self.assertTrue(ok)
            self.assertEqual(fake.learning_goals.docs[0]["end_date"], new_end)

    async def test_get_current_session_and_pending_lists(self):
        fake = FakeDB()
        fake.roadmap_topics.docs = [
            {
                "_id": ObjectId(),
                "goal_id": self.goal_id,
                "order": 2,
                "status": "pending",
                "is_deleted": False,
            },
            {
                "_id": ObjectId(),
                "goal_id": self.goal_id,
                "order": 1,
                "status": "pending",
                "is_deleted": False,
            },
            {
                "_id": ObjectId(),
                "goal_id": self.goal_id,
                "order": 3,
                "status": "completed",
                "is_deleted": False,
            },
        ]

        with patch("db.roadmap_topics.get_db", return_value=fake):
            current = await rt.get_current_session(str(self.goal_id))
            self.assertIsNotNone(current)
            self.assertEqual(current["order"], 1)

            after = await rt.get_pending_sessions_after(str(self.goal_id), 1)
            self.assertEqual([row["order"] for row in after], [2])

            all_pending = await rt.get_all_pending_sessions(str(self.goal_id))
            self.assertEqual([row["order"] for row in all_pending], [1, 2])

    async def test_skip_and_reschedule_and_bulk_reschedule(self):
        fake = FakeDB()
        t1 = ObjectId()
        t2 = ObjectId()
        fake.roadmap_topics.docs = [
            {"_id": t1, "status": "pending", "is_deleted": False, "scheduled_date": None},
            {"_id": t2, "status": "pending", "is_deleted": False, "scheduled_date": None},
        ]

        new_dt1 = _naive_utc(datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc))
        new_dt2 = _naive_utc(datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc))

        with patch("db.roadmap_topics.get_db", return_value=fake):
            ok_skip = await rt.skip_topic(str(t1))
            self.assertTrue(ok_skip)
            self.assertEqual(fake.roadmap_topics.docs[0]["status"], "skipped")

            ok_res = await rt.reschedule_topic(str(t2), new_dt1, estimated_duration_minutes=45)
            self.assertTrue(ok_res)
            self.assertEqual(fake.roadmap_topics.docs[1]["scheduled_date"], new_dt1)
            self.assertEqual(fake.roadmap_topics.docs[1]["estimated_duration"], 45)

            updated = await rt.bulk_reschedule_topics(
                [
                    {"topic_id": str(t1), "new_datetime": new_dt2},
                    {"topic_id": str(t2), "new_datetime": new_dt2},
                ],
            )
            self.assertEqual(updated, 2)
            self.assertEqual(fake.roadmap_topics.docs[0]["scheduled_date"], new_dt2)
            self.assertEqual(fake.roadmap_topics.docs[1]["scheduled_date"], new_dt2)


if __name__ == "__main__":
    unittest.main()

