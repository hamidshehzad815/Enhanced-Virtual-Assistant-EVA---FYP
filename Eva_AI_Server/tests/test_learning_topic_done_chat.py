"""Phase 10 — natural language learning topic completion."""

import unittest
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from handlers.learning import topic_done_chat as tdc


class LearningTopicDoneChatTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_none_when_message_not_completion(self):
        out = await tdc.maybe_handle_learning_topic_done_chat(
            user_id=str(ObjectId()),
            message_lower="schedule a meeting tomorrow",
            user_name=None,
            history=[],
            settings_data={},
            preprocessed={},
        )
        self.assertIsNone(out)

    async def test_marks_topic_and_replies(self):
        uid = str(ObjectId())
        gid = str(ObjectId())
        tid = str(ObjectId())
        picked = {
            "goal": {"_id": gid, "title": "Learn Python", "total_topics": 3},
            "topic": {"_id": tid, "title": "Variables"},
        }
        goal_after = {
            "_id": gid,
            "title": "Learn Python",
            "completed_topics": 1,
            "total_topics": 3,
            "status": "active",
        }
        mock_update = AsyncMock(return_value=True)
        with (
            patch.object(
                tdc,
                "pick_pending_topic_for_chat_completion",
                new=AsyncMock(return_value=picked),
            ),
            patch.object(tdc, "update_topic_status", mock_update),
            patch.object(
                tdc,
                "get_goal_by_id",
                new=AsyncMock(return_value=goal_after),
            ),
        ):
            out = await tdc.maybe_handle_learning_topic_done_chat(
                user_id=uid,
                message_lower="i completed today's session",
                user_name="Alex",
                history=[],
                settings_data={"x": 1},
                preprocessed={"processed": "i completed today's session"},
            )
        self.assertIsNotNone(out)
        self.assertTrue(out.get("learning_topic_completed"))
        self.assertIn("Variables", out.get("response_text", ""))
        mock_update.assert_awaited_once_with(tid, "completed")


if __name__ == "__main__":
    unittest.main()
