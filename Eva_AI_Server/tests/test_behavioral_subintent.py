"""
Unit tests for the Gemini behavioral sub-intent classifier.

Mocks GeminiService — no real API calls.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from config import settings as settings_module
from pipeline import behavioral_subintent as subintent


class TestBehavioralSubIntent(unittest.TestCase):
    def setUp(self) -> None:
        self._flag = settings_module.settings.USE_GEMINI_BEHAVIORAL_SUBINTENT
        self._min = settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE
        settings_module.settings.USE_GEMINI_BEHAVIORAL_SUBINTENT = True
        settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE = 0.7

    def tearDown(self) -> None:
        settings_module.settings.USE_GEMINI_BEHAVIORAL_SUBINTENT = self._flag
        settings_module.settings.GEMINI_PENDING_REPLY_MIN_CONFIDENCE = self._min

    def test_flag_off_skips_gemini(self):
        settings_module.settings.USE_GEMINI_BEHAVIORAL_SUBINTENT = False
        with patch.object(
            subintent.gemini_service,
            "generate_constrained_text",
            return_value='{"sub_intent":"completion_rate","confidence":0.9}',
        ) as mock_call:
            self.assertIsNone(subintent.resolve_behavioral_sub_intent("how am i doing"))
            mock_call.assert_not_called()

    def test_empty_message_skips_gemini(self):
        with patch.object(
            subintent.gemini_service,
            "generate_constrained_text",
            return_value='{"sub_intent":"completion_rate","confidence":0.9}',
        ) as mock_call:
            self.assertIsNone(subintent.resolve_behavioral_sub_intent("   "))
            mock_call.assert_not_called()

    def test_maps_colloquial_phrasing_to_completion_rate(self):
        with patch.object(
            subintent.gemini_service,
            "generate_constrained_text",
            return_value='{"sub_intent":"completion_rate","confidence":0.88}',
        ):
            self.assertEqual(
                subintent.resolve_behavioral_sub_intent("am i staying on track lately"),
                "completion_rate",
            )

    def test_low_confidence_rejected(self):
        with patch.object(
            subintent.gemini_service,
            "generate_constrained_text",
            return_value='{"sub_intent":"productive_days","confidence":0.3}',
        ):
            self.assertIsNone(subintent.resolve_behavioral_sub_intent("hmm not sure what i want"))

    def test_invalid_label_rejected(self):
        with patch.object(
            subintent.gemini_service,
            "generate_constrained_text",
            return_value='{"sub_intent":"something_else","confidence":0.95}',
        ):
            self.assertIsNone(subintent.resolve_behavioral_sub_intent("random text"))

    def test_gemini_unavailable_returns_none(self):
        with patch.object(
            subintent.gemini_service,
            "generate_constrained_text",
            return_value=None,
        ):
            self.assertIsNone(subintent.resolve_behavioral_sub_intent("when am i most productive"))

    def test_unparseable_json_returns_none(self):
        with patch.object(
            subintent.gemini_service,
            "generate_constrained_text",
            return_value="not json",
        ):
            self.assertIsNone(subintent.resolve_behavioral_sub_intent("when am i most productive"))


if __name__ == "__main__":
    unittest.main()
