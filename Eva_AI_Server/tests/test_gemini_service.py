"""
Unit tests for Gemini service fallback behavior.
"""
import time
import unittest

from services.gemini import GeminiService


class TestGeminiService(unittest.TestCase):
    def test_general_fallback_variation(self):
        service = GeminiService()
        service.enabled = False
        service.model = None

        replies = []
        for _ in range(5):
            replies.append(
                service.generate_reply(
                    action_context={"action": "general_greeting"},
                    user_name="Hamid",
                    conversation_history=[],
                )
            )

        self.assertEqual(len(set(replies)), 5)

    def test_out_of_scope_fallback_uses_name(self):
        service = GeminiService()
        service.enabled = False
        service.model = None

        reply = service.generate_reply(
            action_context={"action": "out_of_scope"},
            user_name="Hamid",
            conversation_history=[],
        )
        self.assertIn("Hamid", reply)

    def test_duplicate_fallback_mentions_existing_schedule_and_yes_no(self):
        service = GeminiService()
        service.enabled = False
        service.model = None

        reply = service.generate_reply(
            action_context={
                "action": "duplicate_found",
                "task_name": "Physics exam",
                "existing_date": "Monday, 23 Mar 2026",
                "existing_time": "5:00 PM",
            },
            user_name="Hamid",
            conversation_history=[],
        )

        self.assertIn("Physics exam", reply)
        self.assertIn("Monday, 23 Mar 2026", reply)
        self.assertIn("5:00 PM", reply)
        self.assertIn("yes or no", reply.lower())

    def test_intent_not_implemented_fallback_mentions_intent(self):
        service = GeminiService()
        service.enabled = False
        service.model = None

        reply = service.generate_reply(
            action_context={
                "action": "intent_not_implemented",
                "intent_name": "learning_update",
            },
            user_name="Hamid",
            conversation_history=[],
        )
        self.assertIn("learning_update", reply)

    def test_system_error_fallback_still_returns_safe_text(self):
        service = GeminiService()
        service.enabled = False
        service.model = None

        reply = service.generate_reply(
            action_context={"action": "system_error"},
            user_name="Hamid",
            conversation_history=[],
        )
        self.assertIn("Hamid", reply)

    def test_model_failure_disables_gemini_and_uses_fallback(self):
        class BrokenModel:
            def generate_content(self, *_args, **_kwargs):
                raise RuntimeError("forced model failure")

        service = GeminiService()
        service.enabled = True
        service.model = BrokenModel()
        service.disable_after_failure = True

        reply = service.generate_reply(
            action_context={"action": "task_added", "task_name": "Physics quiz"},
            user_name="Hamid",
            conversation_history=[],
        )

        self.assertTrue(reply)
        self.assertFalse(service.enabled)
        self.assertIsNone(service.model)

    def test_model_timeout_disables_gemini_and_uses_fallback(self):
        class SlowModel:
            def generate_content(self, *_args, **_kwargs):
                time.sleep(0.5)
                return type("Resp", (), {"text": "late"})()

        service = GeminiService()
        service.enabled = True
        service.model = SlowModel()
        service.disable_after_failure = True
        service.timeout_seconds = 0.05

        reply = service.generate_reply(
            action_context={"action": "task_added", "task_name": "Physics quiz"},
            user_name="Hamid",
            conversation_history=[],
        )

        self.assertTrue(reply)
        self.assertFalse(service.enabled)
        self.assertIsNone(service.model)


if __name__ == "__main__":
    unittest.main()
