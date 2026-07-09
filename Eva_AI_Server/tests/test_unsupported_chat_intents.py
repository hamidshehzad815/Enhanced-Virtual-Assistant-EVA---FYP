import unittest

from handlers.unsupported_chat_intents import (
    build_unsupported_intent_response,
    is_legacy_unsupported_intent,
)


class UnsupportedChatIntentsTests(unittest.TestCase):
    def test_legacy_learning_show_label_is_unsupported(self):
        self.assertTrue(is_legacy_unsupported_intent("learning_show"))
        self.assertFalse(is_legacy_unsupported_intent("learning_create"))

    def test_response_directs_user_to_roadmap(self):
        result = build_unsupported_intent_response(
            "learning_show",
            {"user": {"name": "Ali"}},
        )
        self.assertEqual(result["status"], "unsupported")
        self.assertIn("Roadmap", result["response_text"])
        self.assertIn("isn't supported", result["response_text"])


if __name__ == "__main__":
    unittest.main()
