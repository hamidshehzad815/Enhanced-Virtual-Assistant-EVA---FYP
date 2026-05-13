"""
fetch_user_settings includes preferred_learning_schedule for self-fetch / learning.
"""

import unittest
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from db import readers


class FetchUserSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_preserves_preferred_learning_schedule_from_doc(self):
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

        self.assertEqual(
            out.get("preferred_learning_schedule"),
            [{"day": 1, "time": "15:30"}],
        )

    async def test_defaults_preferred_learning_schedule_when_absent(self):
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

        self.assertEqual(out.get("preferred_learning_schedule"), [])


if __name__ == "__main__":
    unittest.main()
