"""Phase 6 pipeline tests — spell correction."""

import unittest

from pipeline.spell_correction import apply_spell_corrections


class SpellCorrectionTests(unittest.TestCase):
    def test_fixes_common_typos(self):
        self.assertIn("physics", apply_spell_corrections("add physcis exam").lower())
        self.assertIn("beginner", apply_spell_corrections("learn py beginer").lower())

    def test_protects_canonical_topic(self):
        text = apply_spell_corrections("learn Python on Monday")
        self.assertIn("Python", text)
        self.assertIn("Monday", text)

    def test_preserves_punctuation(self):
        self.assertTrue(apply_spell_corrections("add physcis exam,").endswith(","))


if __name__ == "__main__":
    unittest.main()
