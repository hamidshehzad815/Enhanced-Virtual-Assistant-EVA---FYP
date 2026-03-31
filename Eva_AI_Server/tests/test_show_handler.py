"""
Phase 22 tests for scheduling show handler and related flow guardrails.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace
import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from handlers.router import route_intent
from handlers.scheduling.show import handle_scheduling_show


def _import_ai_main_with_stubs():
    """
    Import main.py while tolerating environments without torch.
    """
    try:
        return importlib.import_module("main")
    except ModuleNotFoundError as error:
        if getattr(error, "name", "") != "torch":
            raise

        class _StubModel:
            def __init__(self):
                self.loaded = True

            def load(self):
                self.loaded = True
                return True

            def predict(self, _text):
                return {"label": "general"}

            def extract(self, _text, intent_hint=""):
                _ = intent_hint
                return {}

        fake_classifier1 = types.ModuleType("pipeline.classifier1")
        fake_classifier1.classifier1 = _StubModel()

        fake_classifier2 = types.ModuleType("pipeline.classifier2")
        fake_classifier2.classifier2 = _StubModel()

        fake_ner = types.ModuleType("pipeline.ner")
        fake_ner.ner_extractor = _StubModel()

        sys.modules["pipeline.classifier1"] = fake_classifier1
        sys.modules["pipeline.classifier2"] = fake_classifier2
        sys.modules["pipeline.ner"] = fake_ner
        sys.modules.pop("main", None)
        return importlib.import_module("main")


ai_main = _import_ai_main_with_stubs()


def _base_context(message: str = "show tasks"):
    return {
        "user_id": "507f1f77bcf86cd799439011",
        "session_id": "69c0c6d79c98840a2697022f",
        "message": message,
        "input_type": "text",
        "user": {
            "name": "Hamid",
            "timezone": "Asia/Karachi",
        },
        "history": [],
    }


def _fetched(context=None):
    return SimpleNamespace(
        user={
            "name": "Hamid",
            "timezone": "Asia/Karachi",
        },
        settings={},
        history=[],
        integrations=[],
        context=context,
    )


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


class TestShowHandler(unittest.IsolatedAsyncioTestCase):
    async def test_show_success_with_date_and_task_name_filters(self):
        task_rows = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 3, 30, 11, 0, 0),
                "priority": "high",
                "status": "pending",
                "is_deleted": False,
            }
        ]

        with patch(
            "handlers.scheduling.show.duckling_client.parse",
            new=AsyncMock(return_value=[
                {
                    "dim": "time",
                    "value": {
                        "value": "2026-03-30T00:00:00.000+05:00",
                        "grain": "day",
                    },
                }
            ]),
        ), patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=(task_rows, 1)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={"date": "monday", "task_name": "physics"},
                context=_base_context("show physics tasks on monday"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["intent"], "scheduling_show")
        self.assertEqual(result["notifications"], [])
        self.assertEqual(result["total_count"], 1)
        self.assertFalse(result["has_more"])
        self.assertEqual(len(result["tasks"]), 1)
        self.assertIn("ACTION:show_results", result["response_text"])
        self.assertIn("Physics exam", result["response_text"])

        query_filters = mock_find.await_args.args[1]
        self.assertEqual(query_filters.get("task_name"), "physics")
        self.assertIn("date_range", query_filters)
        self.assertIn("start_utc", query_filters["date_range"])
        self.assertIn("end_utc", query_filters["date_range"])

    async def test_show_priority_filter_applied(self):
        rows = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 3, 30, 11, 0, 0),
                "priority": "high",
                "status": "pending",
            }
        ]
        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=(rows, 1)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={"priority": "high"},
                context=_base_context("show high priority tasks"),
            )

        self.assertEqual(result["status"], "success")
        query_filters = mock_find.await_args.args[1]
        self.assertEqual(query_filters.get("priority"), "high")

    async def test_show_pending_status_filter_applied(self):
        rows = [
            {
                "_id": "task1",
                "title": "Chemistry",
                "due_datetime": datetime(2026, 3, 30, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
            }
        ]
        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=(rows, 1)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={"status": "pending"},
                context=_base_context("show pending tasks"),
            )

        self.assertEqual(result["status"], "success")
        query_filters = mock_find.await_args.args[1]
        self.assertEqual(query_filters.get("status"), "pending")

    async def test_show_complete_status_filter_applied(self):
        rows = [
            {
                "_id": "task1",
                "title": "Past completed task",
                "due_datetime": datetime(2026, 3, 20, 12, 0, 0),
                "priority": "low",
                "status": "complete",
            }
        ]
        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=(rows, 1)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={"status": "complete"},
                context=_base_context("show completed tasks"),
            )

        self.assertEqual(result["status"], "success")
        query_filters = mock_find.await_args.args[1]
        self.assertEqual(query_filters.get("status"), "complete")

    async def test_show_combined_date_and_priority_filters(self):
        with patch(
            "handlers.scheduling.show.duckling_client.parse",
            new=AsyncMock(return_value=[
                {
                    "dim": "time",
                    "value": {
                        "value": "2026-03-30T00:00:00.000+05:00",
                        "grain": "day",
                    },
                }
            ]),
        ), patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            await handle_scheduling_show(
                entities={"date": "monday", "priority": "high"},
                context=_base_context("show high priority tasks on monday"),
            )

        query_filters = mock_find.await_args.args[1]
        self.assertEqual(query_filters.get("priority"), "high")
        self.assertIn("date_range", query_filters)

    async def test_show_no_filters_uses_upcoming_now(self):
        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            await handle_scheduling_show(
                entities={},
                context=_base_context("show all tasks"),
            )

        query_filters = mock_find.await_args.args[1]
        self.assertIn("now_utc", query_filters)
        self.assertNotIn("date_range", query_filters)
        self.assertNotIn("priority", query_filters)
        self.assertNotIn("status", query_filters)
        self.assertNotIn("task_name", query_filters)

    async def test_show_date_parse_failure_falls_back_without_date_filter(self):
        with patch(
            "handlers.scheduling.show.duckling_client.parse",
            new=AsyncMock(return_value=None),
        ), patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={"date": "unknown day"},
                context=_base_context("show tasks for unknown day"),
            )

        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["intent"], "scheduling_show")
        self.assertEqual(result["total_count"], 0)
        self.assertEqual(result["tasks"], [])
        self.assertIn("ACTION:show_not_found", result["response_text"])

        query_filters = mock_find.await_args.args[1]
        self.assertNotIn("date_range", query_filters)
        self.assertIn("now_utc", query_filters)

    async def test_show_single_result_uses_singular_text(self):
        row = {
            "_id": "task1",
            "title": "Physics exam",
            "due_datetime": datetime(2026, 3, 30, 12, 0, 0),
            "priority": "high",
            "status": "pending",
        }
        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=([row], 1)),
        ), patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={"task_name": "physics"},
                context=_base_context("show my physics tasks"),
            )

        self.assertEqual(result["status"], "success")
        self.assertIn("is scheduled for", result["response_text"])

    async def test_show_relaxes_task_name_when_exact_phrase_has_no_match(self):
        row = {
            "_id": "task1",
            "title": "physics exam",
            "due_datetime": datetime(2026, 3, 30, 12, 0, 0),
            "priority": "medium",
            "status": "pending",
        }
        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(side_effect=[([], 0), ([row], 1)]),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={"task_name": "physics task", "date": "monday"},
                context=_base_context("show physics task on monday"),
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(len(result["tasks"]), 1)
        self.assertIn('exact match for "physics task"', result["response_text"])
        self.assertEqual(mock_find.await_count, 2)

        first_filters = mock_find.await_args_list[0].args[1]
        second_filters = mock_find.await_args_list[1].args[1]
        self.assertEqual(first_filters.get("task_name"), "physics task")
        self.assertEqual(second_filters.get("task_name"), "physics")

    async def test_show_exact_ten_results_has_no_more(self):
        base_due = datetime(2026, 3, 30, 11, 0, 0)
        rows = [
            {
                "_id": f"task{idx}",
                "title": f"Task {idx}",
                "due_datetime": base_due + timedelta(hours=idx),
                "priority": "medium",
                "status": "pending",
                "is_deleted": False,
            }
            for idx in range(1, 11)
        ]

        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=(rows, 10)),
        ), patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={},
                context=_base_context("show all tasks"),
            )

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["has_more"])
        self.assertEqual(result["total_count"], 10)
        self.assertEqual(len(result["tasks"]), 10)

    async def test_show_has_more_mentions_total_count(self):
        base_due = datetime(2026, 3, 30, 11, 0, 0)
        rows = [
            {
                "_id": f"task{idx}",
                "title": f"Task {idx}",
                "due_datetime": base_due + timedelta(hours=idx),
                "priority": "medium",
                "status": "pending",
                "is_deleted": False,
            }
            for idx in range(1, 11)
        ]

        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=(rows, 12)),
        ), patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={},
                context=_base_context("show all tasks"),
            )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["has_more"])
        self.assertEqual(result["total_count"], 12)
        self.assertEqual(len(result["tasks"]), 10)
        self.assertIn("12 tasks in total", result["response_text"])

    async def test_show_timezone_conversion_used_in_response(self):
        row = {
            "_id": "task1",
            "title": "Physics exam",
            "due_datetime": datetime(2026, 3, 30, 12, 0, 0),
            "priority": "high",
            "status": "pending",
        }
        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=([row], 1)),
        ), patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={},
                context=_base_context("show tasks"),
            )

        self.assertEqual(result["tasks"][0]["local_datetime_str"], "Monday 5:00 PM")
        self.assertIn("Monday, 30 Mar 2026 at 5:00 PM", result["response_text"])

    async def test_show_week_grain_uses_monday_to_sunday_range(self):
        with patch(
            "handlers.scheduling.show.duckling_client.parse",
            new=AsyncMock(return_value=[
                {
                    "dim": "time",
                    "value": {
                        "value": "2026-03-23T00:00:00.000+05:00",
                        "grain": "week",
                    },
                }
            ]),
        ), patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            await handle_scheduling_show(
                entities={"date": "this week"},
                context=_base_context("show tasks this week"),
            )

        date_range = mock_find.await_args.args[1]["date_range"]
        self.assertEqual(date_range["start_utc"], datetime(2026, 3, 22, 19, 0, 0))
        self.assertEqual(date_range["end_utc"], datetime(2026, 3, 29, 18, 59, 59, 999999))

    async def test_show_month_grain_uses_full_month_range(self):
        with patch(
            "handlers.scheduling.show.duckling_client.parse",
            new=AsyncMock(return_value=[
                {
                    "dim": "time",
                    "value": {
                        "value": "2026-03-01T00:00:00.000+05:00",
                        "grain": "month",
                    },
                }
            ]),
        ), patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            await handle_scheduling_show(
                entities={"date": "this month"},
                context=_base_context("show tasks this month"),
            )

        date_range = mock_find.await_args.args[1]["date_range"]
        self.assertEqual(date_range["start_utc"], datetime(2026, 2, 28, 19, 0, 0))
        self.assertEqual(date_range["end_utc"], datetime(2026, 3, 31, 18, 59, 59, 999999))

    async def test_show_overdue_builds_pending_past_query(self):
        with patch(
            "handlers.scheduling.show.find_tasks_for_show",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_find, patch(
            "handlers.scheduling.show.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.show._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_show(
                entities={},
                context=_base_context("show overdue tasks"),
            )

        self.assertEqual(result["status"], "not_found")
        query_filters = mock_find.await_args.args[1]
        self.assertTrue(query_filters.get("overdue_only"))
        self.assertEqual(query_filters.get("status"), "pending")

    async def test_router_maps_show_intent_to_show_handler(self):
        with patch(
            "handlers.router.handle_scheduling_show",
            new=AsyncMock(
                return_value={
                    "status": "success",
                    "intent": "scheduling_show",
                    "response_text": "ok",
                    "notifications": [],
                }
            ),
        ) as mock_show:
            result = await route_intent(
                "show",
                entities={"date": "2026-03-30"},
                context={"user_id": "u1", "session_id": "s1"},
            )

        self.assertEqual(result["intent"], "scheduling_show")
        mock_show.assert_awaited_once()


class TestShowPhase22MainFlow(unittest.IsolatedAsyncioTestCase):
    async def test_show_command_is_blocked_when_another_pending_flow_exists(self):
        pending_context = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "add",
                "entities": {"task_name": "physics quiz"},
            },
        }
        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(context=pending_context)),
        ), patch(
            "main._safe_reply",
            side_effect=lambda action, *_a, **_k: f"ACTION:{action}",
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "command", "confidence": 0.99},
        ), patch(
            "main.route_intent",
            new=AsyncMock(
                return_value={
                    "status": "success",
                    "intent": "scheduling_show",
                    "response_text": "should-not-route",
                    "notifications": [],
                }
            ),
        ) as mock_route, patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="show tasks on monday",
                    user_id="u1",
                    session_id="s1",
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["response_text"], "ACTION:pending_waiting_reply")
        mock_route.assert_not_awaited()
        mock_set.assert_not_awaited()

    async def test_show_command_does_not_write_redis_context(self):
        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(context=None)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier2,
            "loaded",
            True,
        ), patch.object(
            ai_main.ner_extractor,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "command", "confidence": 0.99},
        ), patch.object(
            ai_main.classifier2,
            "predict",
            return_value={"label": "show", "confidence": 0.99},
        ), patch.object(
            ai_main.ner_extractor,
            "extract",
            return_value={"date": "monday"},
        ), patch(
            "main.resolve_all",
            new=AsyncMock(return_value={"date": "2026-03-30"}),
        ), patch(
            "main.route_intent",
            new=AsyncMock(
                return_value={
                    "status": "success",
                    "intent": "scheduling_show",
                    "response_text": "Here are your tasks",
                    "notifications": [],
                }
            ),
        ) as mock_route, patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ) as mock_set, patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_delete:
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="show tasks on monday",
                    user_id="u1",
                    session_id="s1",
                    input_type="text",
                )
            )

        self.assertFalse(result.get("context_handled", False))
        self.assertEqual(result["route"]["intent"], "scheduling_show")
        mock_route.assert_awaited_once()
        mock_set.assert_not_awaited()
        mock_delete.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
