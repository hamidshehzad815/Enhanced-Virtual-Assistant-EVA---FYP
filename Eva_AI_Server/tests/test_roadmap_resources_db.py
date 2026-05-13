"""
Tests for db/roadmap_resources.py (faked Mongo collection).
"""

import json
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from bson import ObjectId

from db import roadmap_resources as rr


def _matches(doc, query):
    if not query:
        return True
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(doc, clause) for clause in expected):
                return False
            continue
        actual = doc.get(key)
        if isinstance(expected, dict):
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
    def __init__(self, matched_count: int, modified_count: int):
        self.matched_count = matched_count
        self.modified_count = modified_count


class FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, str):
            rev = direction == -1
            self._rows = sorted(self._rows, key=lambda r: r.get(key_or_list, 0), reverse=rev)
        else:
            rows = list(self._rows)
            for key, direc in reversed(key_or_list):
                rev = direc == -1
                rows = sorted(rows, key=lambda r: r.get(key, 0), reverse=rev)
            self._rows = rows
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    async def to_list(self, length=None):
        if length is None:
            return [dict(r) for r in self._rows]
        return [dict(r) for r in self._rows[:length]]


class FakeRoadmapResources:
    def __init__(self):
        self.docs = []

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if _matches(doc, query):
                if projection == {"_id": 1}:
                    return {"_id": doc["_id"]}
                return dict(doc)
        return None

    async def insert_one(self, payload):
        row = dict(payload)
        row["_id"] = ObjectId()
        self.docs.append(row)
        return type("R", (), {"inserted_id": row["_id"]})()

    def find(self, query):
        rows = [d for d in self.docs if _matches(d, query)]
        return FakeCursor(rows)

    async def count_documents(self, query):
        return sum(1 for d in self.docs if _matches(d, query))

    async def update_one(self, filt, update):
        matched = 0
        modified = 0
        for d in self.docs:
            if _matches(d, filt):
                matched += 1
                for k, v in update.get("$set", {}).items():
                    if d.get(k) != v:
                        modified += 1
                    d[k] = v
        return FakeUpdateResult(matched, modified)


class FakeDB:
    def __init__(self):
        self.roadmap_resources = FakeRoadmapResources()


class RoadmapResourcesDbTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_inserts_and_skips(self):
        data = {
            "topics": ["Python"],
            "Python": {
                "topics": ["basics"],
                "basics": {
                    "days": 2,
                    "topics": ["T1", "T2"],
                },
            },
        }
        fake = FakeDB()
        with patch.object(rr, "get_db", return_value=fake):
            ins, skip, exp = await rr.seed_from_roadmaps_json(data)
        self.assertEqual(exp, 2)
        self.assertEqual(ins, 2)
        self.assertEqual(skip, 0)
        self.assertEqual(len(fake.roadmap_resources.docs), 2)

        with patch.object(rr, "get_db", return_value=fake):
            ins2, skip2, exp2 = await rr.seed_from_roadmaps_json(data)
        self.assertEqual(exp2, 2)
        self.assertEqual(ins2, 0)
        self.assertEqual(skip2, 2)

    async def test_seed_days_mismatch_raises(self):
        data = {
            "topics": ["Python"],
            "Python": {
                "topics": ["basics"],
                "basics": {"days": 9, "topics": ["a", "b"]},
            },
        }
        fake = FakeDB()
        with patch.object(rr, "get_db", return_value=fake):
            with self.assertRaises(ValueError):
                await rr.seed_from_roadmaps_json(data)

    async def test_get_roadmap_sorted_by_order(self):
        fake = FakeDB()
        fake.roadmap_resources.docs = [
            {
                "_id": ObjectId(),
                "language": "Python",
                "level": "basics",
                "order": 2,
                "title": "B",
            },
            {
                "_id": ObjectId(),
                "language": "Python",
                "level": "basics",
                "order": 1,
                "title": "A",
            },
        ]
        with patch.object(rr, "get_db", return_value=fake):
            rows = await rr.get_roadmap("Python", "basics")
        self.assertEqual([r["title"] for r in rows], ["A", "B"])
        self.assertIsInstance(rows[0]["_id"], str)

    async def test_get_sessions_required(self):
        fake = FakeDB()
        fake.roadmap_resources.docs = [
            {"language": "Python", "level": "basics", "order": 1},
            {"language": "Python", "level": "basics", "order": 2},
        ]
        with patch.object(rr, "get_db", return_value=fake):
            n = await rr.get_sessions_required("Python", "basics")
        self.assertEqual(n, 2)

    async def test_get_unfetched_only_null_fetched_at(self):
        fake = FakeDB()
        fake.roadmap_resources.docs = [
            {
                "language": "A",
                "level": "basics",
                "order": 1,
                "fetched_at": None,
            },
            {
                "language": "B",
                "level": "basics",
                "order": 1,
                "fetched_at": datetime(2020, 1, 1),
            },
        ]
        with patch.object(rr, "get_db", return_value=fake):
            rows = await rr.get_unfetched_topics(limit=50)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["language"], "A")

    async def test_count_unfetched(self):
        fake = FakeDB()
        fake.roadmap_resources.docs = [
            {"fetched_at": None},
            {"fetched_at": datetime(2020, 1, 1)},
        ]
        with patch.object(rr, "get_db", return_value=fake):
            c = await rr.count_unfetched()
        self.assertEqual(c, 1)

    async def test_update_resources_sets_fields(self):
        oid = ObjectId()
        fake = FakeDB()
        fake.roadmap_resources.docs = [
            {
                "_id": oid,
                "language": "Python",
                "level": "basics",
                "order": 1,
                "resources": [],
                "fetched_at": None,
            }
        ]
        resources = [{"title": "V", "url": "https://youtu.be/x", "thumbnail": "", "channel": "C"}]
        with patch.object(rr, "get_db", return_value=fake):
            ok = await rr.update_resources(str(oid), resources)
        self.assertTrue(ok)
        self.assertEqual(fake.roadmap_resources.docs[0]["resources"], resources)
        self.assertIsNotNone(fake.roadmap_resources.docs[0]["fetched_at"])

    async def test_get_stale_topics(self):
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        old = now_naive - timedelta(days=60)
        recent = now_naive - timedelta(days=1)
        fake = FakeDB()
        fake.roadmap_resources.docs = [
            {"language": "A", "level": "basics", "order": 1, "fetched_at": old},
            {"language": "B", "level": "basics", "order": 1, "fetched_at": recent},
            {"language": "C", "level": "basics", "order": 1, "fetched_at": None},
        ]
        with patch.object(rr, "get_db", return_value=fake):
            rows = await rr.get_stale_topics(days=30, limit=50)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["language"], "A")


class RoadmapsJsonFileTests(unittest.TestCase):
    """data/roadmaps.json structure (no DB)."""

    def test_days_match_topic_counts_and_expected_total(self):
        path = Path(__file__).resolve().parent.parent / "data" / "roadmaps.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        topics = data["topics"]
        self.assertEqual(len(topics), 20)
        total = 0
        for lang in topics:
            block = data[lang]
            for level in block["topics"]:
                level_data = block[level]
                titles = level_data["topics"]
                self.assertEqual(
                    level_data["days"],
                    len(titles),
                    f"{lang}/{level}",
                )
                total += len(titles)
        self.assertEqual(total, 760)


if __name__ == "__main__":
    unittest.main()
