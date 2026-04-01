"""
Phase 28 consolidated tests for scheduling update flow.
"""
from datetime import datetime
from types import SimpleNamespace
import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from db.tasks import update_task
from handlers.scheduling.update import handle_scheduling_update


USER_ID = "507f1f77bcf86cd799439011"
SESSION_ID = "69c0c6d79c98840a2697022f"


def _base_context(message: str) -> dict:
    return {
        "user_id": USER_ID,
        "session_id": SESSION_ID,
        "message": message,
        "input_type": "text",
        "user": {
            "name": "Hamid",
            "timezone": "Asia/Karachi",
        },
        "history": [],
        "integrations": [],
    }


def _gemini_stub(action_context, _user_name, _history):
    return f"ACTION:{action_context.get('action', 'unknown')}"


def _import_ai_main_with_stubs():
    """
    Import main.py while tolerating local environments without torch.
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


class _FakeResult:
    def __init__(self, matched_count: int):
        self.matched_count = matched_count


class _FakeTasksCollection:
    def __init__(self, docs):
        self.docs = [dict(doc) for doc in docs]

    async def update_one(self, query, update):
        for doc in self.docs:
            if doc.get("_id") == query.get("_id"):
                for key, value in update.get("$set", {}).items():
                    doc[key] = value
                return _FakeResult(1)
        return _FakeResult(0)


class _FakeDB:
    def __init__(self, tasks_collection):
        self.tasks = tasks_collection


class TestUpdateHandlerPhase28(unittest.IsolatedAsyncioTestCase):
    async def test_no_identifier_asks_then_reentered_free_text_routes_again(self):
        with patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            first = await handle_scheduling_update(
                entities={"new_priority": "high"},
                context=_base_context("change priority to high"),
            )

        self.assertEqual(first["status"], "pending")
        self.assertEqual(first["pending"]["stage"], "identify")
        self.assertEqual(first["pending"]["expected_response"], "free_text")

        pending_context = {
            "expected_response": "free_text",
            "pending_action": {
                "intent": "update",
                "stage": "identify",
                "entities": {"new_priority": "high"},
            },
        }
        route_result = {
            "status": "pending",
            "intent": "scheduling_update",
            "response_text": "Update flow resumed",
            "notifications": [],
        }
        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch(
            "main.handle_free_text_reply",
            new=AsyncMock(return_value={"task_name": "physics exam", "new_priority": "high"}),
        ), patch(
            "main.route_intent",
            new=AsyncMock(return_value=route_result),
        ) as mock_route:
            second = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="physics exam",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(second["context_handled"])
        self.assertEqual(second["merged_entities"]["task_name"], "physics exam")
        self.assertEqual(second["route"]["intent"], "scheduling_update")
        mock_route.assert_awaited_once()

    async def test_one_match_with_update_field_confirm_then_yes_updates(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
            }
        ]

        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            pending = await handle_scheduling_update(
                entities={"task_name": "physics exam", "new_priority": "high"},
                context=_base_context("change physics exam priority to high"),
            )

        self.assertEqual(pending["status"], "pending")
        self.assertEqual(pending["pending"]["stage"], "confirm")
        self.assertEqual(pending["updates"]["priority"], "high")

        current_task = dict(one_match[0])
        updated_task = dict(one_match[0])
        updated_task["priority"] = "high"
        yes_context = _base_context("yes")
        yes_context["pending_context"] = {
            "pending_action": {
                "intent": "update",
                "task_id": "task1",
                "entities": {"task_id": "task1", "task_name": "Physics exam", "new_priority": "high"},
                "updates": pending["updates"],
                "change_summary": "priority from medium to high",
            }
        }
        yes_context["pending_reply_type"] = "yes_no"
        yes_context["pending_reply_value"] = "yes"

        with patch(
            "handlers.scheduling.update.get_task_by_id",
            new=AsyncMock(side_effect=[current_task, updated_task]),
        ), patch(
            "handlers.scheduling.update.update_task",
            new=AsyncMock(return_value=True),
        ) as mock_update, patch(
            "handlers.scheduling.update.insert_log",
            new=AsyncMock(return_value="log1"),
        ) as mock_log, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            completed = await handle_scheduling_update(
                entities={"task_id": "task1"},
                context=yes_context,
            )

        self.assertEqual(completed["status"], "success")
        self.assertEqual(completed["task"]["priority"], "high")
        mock_update.assert_awaited_once_with("task1", {"priority": "high"})
        mock_log.assert_awaited_once()

    async def test_one_match_without_update_field_then_asks_what_to_update(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
            }
        ]

        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics exam"},
                context=_base_context("update physics exam"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["stage"], "what_to_update")
        self.assertEqual(result["pending"]["expected_response"], "free_text")

    async def test_two_to_five_matches_pick_number_with_update_fields_moves_confirm(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "update",
                "stage": "identify",
                "task_ids": ["id1", "id2", "id3"],
                "tasks": [
                    {"title": "Physics exam", "due_datetime": "2026-03-26T10:00:00", "priority": "high"},
                    {"title": "Physics lab", "due_datetime": "2026-03-26T12:00:00", "priority": "medium"},
                    {"title": "Physics quiz", "due_datetime": "2026-03-26T15:00:00", "priority": "low"},
                ],
                "entities": {"new_priority": "high"},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ):
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="2",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["parsed_value"], "id2")
        self.assertEqual(result["next_expected_response"], "yes_no")

    async def test_two_to_five_matches_pick_number_without_update_fields_moves_what_to_update(self):
        pending_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "update",
                "stage": "identify",
                "task_ids": ["id1", "id2"],
                "tasks": [
                    {"title": "Physics exam", "due_datetime": "2026-03-26T10:00:00", "priority": "high"},
                    {"title": "Physics lab", "due_datetime": "2026-03-26T12:00:00", "priority": "medium"},
                ],
                "entities": {},
            },
        }

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(pending_context)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "confirmation"},
        ), patch(
            "main.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ):
            result = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="1",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(result["context_handled"])
        self.assertEqual(result["parsed_value"], "id1")
        self.assertEqual(result["next_expected_response"], "free_text")

    async def test_six_plus_matches_returns_too_broad(self):
        matches = [
            {
                "_id": f"task{index}",
                "title": f"Task {index}",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
            }
            for index in range(1, 8)
        ]
        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=matches),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics"},
                context=_base_context("update physics"),
            )

        self.assertEqual(result["status"], "too_broad")
        self.assertEqual(result["match_count"], 7)

    async def test_zero_matches_returns_not_found(self):
        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=[]),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "calculus exam"},
                context=_base_context("update calculus exam"),
            )

        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["match_count"], 0)

    async def test_date_time_reschedule_utc_correct_calendar_and_log_called(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Chemistry lab",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
                "google_calendar_event_id": "evt_1",
            }
        ]

        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.check_update_overlap",
            new=AsyncMock(return_value=False),
        ), patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            pending = await handle_scheduling_update(
                entities={
                    "task_name": "chemistry lab",
                    "new_date": "2026-04-02",
                    "new_time": "6pm",
                    "new_duration": "90 minutes",
                    "new_title": "Chemistry lab prep",
                },
                context=_base_context("reschedule chemistry lab to 2 april 6pm for 90 min"),
            )

        self.assertEqual(pending["status"], "pending")
        self.assertEqual(pending["pending"]["stage"], "confirm")
        # 6:00 PM Asia/Karachi == 1:00 PM UTC
        self.assertEqual(pending["updates"]["due_datetime"], "2026-04-02T13:00:00")
        self.assertEqual(pending["updates"]["duration"], 90)
        self.assertEqual(pending["updates"]["title"], "Chemistry lab prep")

        current_task = dict(one_match[0])
        updated_task = dict(one_match[0])
        updated_task.update(
            {
                "title": "Chemistry lab prep",
                "duration": 90,
                "due_datetime": datetime(2026, 4, 2, 13, 0, 0),
            }
        )

        yes_context = _base_context("yes")
        yes_context["integrations"] = [
            {
                "provider": "google_calendar",
                "is_active": True,
                "access_token": "token_1",
                "calendar_id": "primary",
            }
        ]
        yes_context["pending_context"] = {
            "pending_action": {
                "intent": "update",
                "task_id": "task1",
                "entities": {"task_id": "task1", "task_name": "Chemistry lab"},
                "updates": pending["updates"],
                "change_summary": "schedule, duration and title updated",
            }
        }
        yes_context["pending_reply_type"] = "yes_no"
        yes_context["pending_reply_value"] = "yes"

        with patch(
            "handlers.scheduling.update.get_task_by_id",
            new=AsyncMock(side_effect=[current_task, updated_task]),
        ), patch(
            "handlers.scheduling.update.update_task",
            new=AsyncMock(return_value=True),
        ) as mock_update, patch(
            "handlers.scheduling.update.insert_log",
            new=AsyncMock(return_value="log1"),
        ) as mock_log, patch(
            "handlers.scheduling.update.google_calendar_client.update_event",
            new=AsyncMock(return_value=True),
        ) as mock_calendar, patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            done = await handle_scheduling_update(
                entities={"task_id": "task1"},
                context=yes_context,
            )

        self.assertEqual(done["status"], "success")
        update_payload = mock_update.await_args.args[1]
        self.assertEqual(update_payload["due_datetime"], datetime(2026, 4, 2, 13, 0, 0))
        mock_log.assert_awaited_once()
        mock_calendar.assert_awaited_once()

    async def test_status_backwards_complete_to_pending_is_blocked(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Biology assignment",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "complete",
                "duration": 60,
            }
        ]
        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "biology assignment", "new_status": "pending"},
                context=_base_context("mark biology assignment pending"),
            )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["response_text"], "ACTION:update_status_locked")

    async def test_overlap_conflict_warns_and_pauses(self):
        one_match = [
            {
                "_id": "task1",
                "title": "Physics exam",
                "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                "priority": "medium",
                "status": "pending",
                "duration": 120,
            }
        ]

        with patch(
            "handlers.scheduling.update.find_tasks_for_update",
            new=AsyncMock(return_value=one_match),
        ), patch(
            "handlers.scheduling.update.check_update_overlap",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.update.redis_client.set_context",
            new=AsyncMock(return_value=True),
        ), patch(
            "handlers.scheduling.update.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ), patch(
            "handlers.scheduling.update._save_turn",
            new=AsyncMock(return_value=None),
        ):
            result = await handle_scheduling_update(
                entities={"task_name": "physics exam", "new_time": "6pm"},
                context=_base_context("change physics exam to 6pm"),
            )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["pending"]["stage"], "what_to_update")
        self.assertEqual(result["response_text"], "ACTION:update_overlap_conflict")

    async def test_cancel_identify_and_confirm_and_new_command_block(self):
        identify_context = {
            "expected_response": "number",
            "pending_action": {
                "intent": "update",
                "stage": "identify",
                "task_ids": ["id1", "id2"],
                "tasks": [{"title": "A"}, {"title": "B"}],
                "entities": {},
            },
        }
        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(identify_context)),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear, patch(
            "main.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ):
            cancelled_identify = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="cancel",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )
        self.assertTrue(cancelled_identify["context_handled"])
        self.assertEqual(cancelled_identify["response_text"], "ACTION:pending_cancelled")
        mock_clear.assert_awaited_once_with(USER_ID)

        confirm_context = {
            "expected_response": "yes_no",
            "pending_action": {
                "intent": "update",
                "stage": "confirm",
                "task_id": "id1",
                "task": {"title": "Physics exam"},
                "entities": {"task_name": "physics exam", "new_priority": "high"},
            },
        }
        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(confirm_context)),
        ), patch(
            "main.redis_client.delete_context",
            new=AsyncMock(return_value=True),
        ) as mock_clear_confirm, patch(
            "main.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ):
            cancelled_confirm = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="cancel",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )
        self.assertTrue(cancelled_confirm["context_handled"])
        self.assertEqual(cancelled_confirm["response_text"], "ACTION:pending_cancelled")
        mock_clear_confirm.assert_awaited_once_with(USER_ID)

        with patch(
            "main.self_fetch_all",
            new=AsyncMock(return_value=_fetched(confirm_context)),
        ), patch.object(
            ai_main.classifier1,
            "loaded",
            True,
        ), patch.object(
            ai_main.classifier1,
            "predict",
            return_value={"label": "command"},
        ), patch(
            "main.gemini_service.generate_reply",
            side_effect=_gemini_stub,
        ):
            blocked = await ai_main.process_message(
                ai_main.ProcessRequest(
                    message="update another task",
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    input_type="text",
                )
            )

        self.assertTrue(blocked["context_handled"])
        self.assertEqual(blocked["response_text"], "ACTION:pending_waiting_reply")

    async def test_db_updates_priority_duration_title_and_complete_sets_completed_at(self):
        task_id = ObjectId()
        tasks = _FakeTasksCollection(
            [
                {
                    "_id": task_id,
                    "title": "Physics exam",
                    "priority": "medium",
                    "status": "pending",
                    "duration": 120,
                    "due_datetime": datetime(2026, 4, 1, 12, 0, 0),
                }
            ]
        )
        fake_db = _FakeDB(tasks_collection=tasks)

        with patch("db.tasks.get_db", return_value=fake_db):
            ok_priority = await update_task(str(task_id), {"priority": "high"})
            ok_duration = await update_task(str(task_id), {"duration": 90})
            ok_title = await update_task(str(task_id), {"title": "Physics final"})
            ok_complete = await update_task(str(task_id), {"status": "complete"})

        self.assertTrue(ok_priority)
        self.assertTrue(ok_duration)
        self.assertTrue(ok_title)
        self.assertTrue(ok_complete)

        row = tasks.docs[0]
        self.assertEqual(row["priority"], "high")
        self.assertEqual(row["duration"], 90)
        self.assertEqual(row["title"], "Physics final")
        self.assertEqual(row["status"], "complete")
        self.assertIsNotNone(row.get("completed_at"))


if __name__ == "__main__":
    unittest.main()
