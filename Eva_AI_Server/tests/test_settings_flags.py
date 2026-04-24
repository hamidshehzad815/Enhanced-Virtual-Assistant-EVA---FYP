"""
Settings flag parsing tests.
"""
import unittest

from config.settings import _as_bool


class TestSettingsFlags(unittest.TestCase):
    def test_as_bool_truthy_values(self):
        self.assertTrue(_as_bool("true", False))
        self.assertTrue(_as_bool("1", False))
        self.assertTrue(_as_bool("yes", False))
        self.assertTrue(_as_bool("on", False))
        self.assertTrue(_as_bool('"true"', False))
        self.assertTrue(_as_bool("'true'", False))

    def test_as_bool_falsey_values(self):
        self.assertFalse(_as_bool("false", True))
        self.assertFalse(_as_bool("0", True))
        self.assertFalse(_as_bool("no", True))
        self.assertFalse(_as_bool("off", True))
        self.assertFalse(_as_bool('"false"', True))
        self.assertFalse(_as_bool("'false'", True))

    def test_as_bool_unknown_uses_default(self):
        self.assertTrue(_as_bool("maybe", True))
        self.assertFalse(_as_bool("maybe", False))


if __name__ == "__main__":
    unittest.main()

