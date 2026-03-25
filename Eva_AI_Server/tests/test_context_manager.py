"""
Unit tests for Phase 5 context manager helpers.
"""
import unittest
from unittest.mock import AsyncMock, patch

from context.context_manager import (
    handle_free_text_reply,
    handle_number_reply,
    handle_yes_no_reply,
    is_cancel,
    should_block_new_command,
)


class TestContextManager(unittest.IsolatedAsyncioTestCase):
    def test_cancel_detection(self):
        self.assertTrue(is_cancel("cancel"))
        self.assertTrue(is_cancel("never mind"))
        self.assertTrue(is_cancel("please stop this"))
        self.assertFalse(is_cancel("schedule physics exam"))

    async def test_free_text_handling(self):
        context = {
            "missing_entity": "task_name",
            "pending_action": {
                "intent": "add",
                "entities": {
                    "date": "monday",
                },
            },
        }

        with patch(
            "context.context_manager.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_delete:
            merged = await handle_free_text_reply(
                "507f1f77bcf86cd799439011",
                context,
                "Physics Exam",
            )

        self.assertEqual(merged["task_name"], "Physics Exam")
        self.assertEqual(merged["date"], "monday")
        mock_delete.assert_awaited_once()

    def test_yes_no_handling(self):
        self.assertEqual(handle_yes_no_reply("yes"), "yes")
        self.assertEqual(handle_yes_no_reply("go ahead"), "yes")
        self.assertEqual(handle_yes_no_reply("nope"), "no")
        self.assertEqual(handle_yes_no_reply("maybe"), "invalid")

    def test_number_handling(self):
        self.assertEqual(handle_number_reply("1"), 1)
        self.assertEqual(handle_number_reply("2"), 2)
        self.assertIsNone(handle_number_reply("3"))
        self.assertIsNone(handle_number_reply("one"))

    def test_new_command_blocking(self):
        self.assertTrue(should_block_new_command("command"))
        self.assertTrue(should_block_new_command("multiple_command"))
        self.assertFalse(should_block_new_command("confirmation"))
        self.assertFalse(should_block_new_command("general"))


if __name__ == "__main__":
    unittest.main()
