"""Unit tests for adversarial_eval helpers (no models)."""

import unittest

from adversarial_eval import (
    compare_entities,
    evaluate_case,
    forbidden_present,
    summarize_results,
)


class AdversarialEvalTests(unittest.TestCase):
    def test_compare_entities_pass(self):
        ok, errs = compare_entities(
            {"topic": "python", "subtopic": "oop"},
            {"topic": "Python", "subtopic": "OOP"},
        )
        self.assertTrue(ok)
        self.assertEqual(errs, [])

    def test_forbidden_ma_detected(self):
        banned = forbidden_present({"subtopic": "ma"}, ["ma", "my"])
        self.assertIn("ma", banned)

    def test_evaluate_case_must_not_extract(self):
        result = evaluate_case(
            {
                "id": "x",
                "text": "delete my Python roadmap",
                "intent": "learning_delete",
                "expected": {"topic": "python"},
                "must_not_extract": ["my", "ma", "roadmap"],
            },
            {"topic": "Python", "subtopic": "ma"},
        )
        self.assertFalse(result["passed"])

    def test_summarize_results(self):
        summary = summarize_results(
            [{"passed": True, "intent": "a", "tags": []}, {"passed": False, "intent": "b", "tags": ["typo"], "errors": ["missing topic: expected 'x'"]}]
        )
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["passed"], 1)


if __name__ == "__main__":
    unittest.main()
