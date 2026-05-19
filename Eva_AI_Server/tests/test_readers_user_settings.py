"""
fetch_user_settings includes preferred_learning_schedules for self-fetch / learning.
"""

import unittest
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from db import readers


class FetchUserSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_normalizes_preferred_learning_schedules_from_doc(self):
        uid = str(ObjectId())
        doc = {
            "_id": ObjectId(),
            "user_id": ObjectId(uid),
            "preferred_learning_schedules": [
                {
                    "id": "s1",
                    "label": "Evening",
                    "slots": [{"day": 1, "time": "15:30", "duration_minutes": 45}],
                },
            ],
        }

        fake_coll = AsyncMock()
        fake_coll.find_one = AsyncMock(return_value=doc)
        fake_db = type(
            "DB",
            (),
            {"user_settings": fake_coll, "usersettings": AsyncMock()},
        )()

        with patch.object(readers, "get_db", return_value=fake_db):
            out = await readers.fetch_user_settings(uid)

        self.assertEqual(len(out.get("preferred_learning_schedules") or []), 1)
        self.assertEqual(out["preferred_learning_schedules"][0]["label"], "Evening")

    async def test_migrates_orphan_flat_slots_into_schedules(self):
        uid = str(ObjectId())
        doc = {
            "_id": ObjectId(),
            "user_id": ObjectId(uid),
            "preferred_learning_schedule": [{"day": 1, "time": "15:30"}],
        }

        fake_coll = AsyncMock()
        fake_coll.find_one = AsyncMock(return_value=doc)
        fake_db = type(
            "DB",
            (),
            {"user_settings": fake_coll, "usersettings": AsyncMock()},
        )()

        with patch.object(readers, "get_db", return_value=fake_db):
            out = await readers.fetch_user_settings(uid)

        schedules = out.get("preferred_learning_schedules") or []
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0]["label"], "Default")

    async def test_defaults_preferred_learning_schedules_when_absent(self):
        uid = str(ObjectId())
        doc = {"_id": ObjectId(), "user_id": ObjectId(uid)}

        fake_coll = AsyncMock()
        fake_coll.find_one = AsyncMock(return_value=doc)
        fake_db = type(
            "DB",
            (),
            {"user_settings": fake_coll, "usersettings": AsyncMock()},
        )()

        with patch.object(readers, "get_db", return_value=fake_db):
            out = await readers.fetch_user_settings(uid)

        self.assertEqual(out.get("preferred_learning_schedules"), [])


if __name__ == "__main__":
    unittest.main()
