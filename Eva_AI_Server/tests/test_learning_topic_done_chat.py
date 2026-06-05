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

    async def test_returns_none_for_reschedule_typo_with_session_to_date(self):
        """reschdule + session to june4 must not hit completion shortcut."""
        out = await tdc.maybe_handle_learning_topic_done_chat(
            user_id=str(ObjectId()),
            message_lower="reschdule python session to june4",
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
        current = {
            "_id": tid,
            "title": "Variables",
            "order": 1,
            "status": "pending",
            "scheduled_date": __import__("datetime").datetime(2020, 1, 1, 9, 0),
        }
        goal_after = {
            "_id": gid,
            "title": "Learn Python",
            "completed_topics": 1,
            "total_topics": 3,
            "status": "active",
        }
        mock_complete = AsyncMock(return_value=True)
        with (
            patch.object(
                tdc,
                "pick_pending_topic_for_chat_completion",
                new=AsyncMock(return_value=picked),
            ),
            patch.object(tdc, "fetch_user", new=AsyncMock(return_value={"timezone": "UTC"})),
            patch.object(
                tdc,
                "get_current_session",
                new=AsyncMock(return_value=current),
            ),
            patch.object(
                tdc,
                "_session_state_for_topic",
                new=AsyncMock(return_value="overdue"),
            ),
            patch.object(tdc, "complete_topic", mock_complete),
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
        mock_complete.assert_awaited_once_with(tid)

    async def test_blocks_complete_when_unlocked_future(self):
        uid = str(ObjectId())
        gid = str(ObjectId())
        tid = str(ObjectId())
        picked = {
            "goal": {"_id": gid, "title": "Learn Python", "total_topics": 12},
            "topic": {"_id": tid, "title": "Intro"},
        }
        current = {
            "_id": tid,
            "title": "Intro",
            "order": 1,
            "status": "pending",
            "scheduled_date": __import__("datetime").datetime(2099, 6, 10, 19, 0),
        }
        with (
            patch.object(
                tdc,
                "pick_pending_topic_for_chat_completion",
                new=AsyncMock(return_value=picked),
            ),
            patch.object(tdc, "fetch_user", new=AsyncMock(return_value={"timezone": "UTC"})),
            patch.object(
                tdc,
                "get_current_session",
                new=AsyncMock(return_value=current),
            ),
            patch.object(
                tdc,
                "_session_state_for_topic",
                new=AsyncMock(return_value="unlocked_future"),
            ),
            patch.object(tdc, "complete_topic", AsyncMock()) as mock_complete,
        ):
            out = await tdc.maybe_handle_learning_topic_done_chat(
                user_id=uid,
                message_lower="mark python session as completed",
                user_name="Alex",
                history=[],
                settings_data={},
                preprocessed={"processed": "mark python session as completed"},
            )
        self.assertIsNotNone(out)
        self.assertFalse(out.get("learning_topic_completed"))
        self.assertIn("hasn't started yet", out.get("response_text", "").lower())
        mock_complete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
