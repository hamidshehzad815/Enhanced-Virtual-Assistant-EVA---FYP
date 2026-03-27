"""
Delete flow timezone display regression tests.
"""
import unittest
from datetime import datetime
from unittest.mock import patch

from handlers.scheduling.delete import _format_due_display, multi_list_prompt


class TestDeleteTimezoneDisplay(unittest.TestCase):
    def test_format_due_display_uses_user_timezone(self):
        due_utc = datetime(2026, 3, 30, 11, 0, 0)
        display = _format_due_display(due_utc, "Asia/Karachi")
        self.assertEqual(display, "Monday, 30 Mar 2026 at 4:00 PM")

    def test_multi_list_prompt_displays_local_times(self):
        tasks = [
            {
                "title": "physics exam",
                "due_datetime": datetime(2026, 3, 30, 11, 0, 0),
                "priority": "medium",
            },
            {
                "title": "physics exam",
                "due_datetime": datetime(2026, 3, 30, 12, 0, 0),
                "priority": "medium",
            },
        ]
        with patch(
            "handlers.scheduling.delete.gemini_service.generate_reply",
            return_value="There are 2 tasks matching that request.",
        ):
            text = multi_list_prompt("Hamid", tasks, "Asia/Karachi", [])

        self.assertIn("4:00 PM", text)
        self.assertIn("5:00 PM", text)


if __name__ == "__main__":
    unittest.main()
