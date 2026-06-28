"""
Intent router for Phase 6.
Routes Model 2 intents to handler stubs.
"""
from typing import Any, Dict, Optional

from handlers.behavioral import handle_behavioral
from handlers.learning.create import handle_learning_create
from handlers.learning.delete import handle_learning_delete
from handlers.learning.update import handle_learning_update
from handlers.unsupported_chat_intents import (
    build_unsupported_intent_response,
    is_legacy_unsupported_intent,
)
from handlers.scheduling.add import handle_scheduling_add
from handlers.scheduling.delete import handle_scheduling_delete
from handlers.scheduling.show import handle_scheduling_show
from handlers.scheduling.update import handle_scheduling_update
from services.gemini import gemini_service
from utils.api_datetime import with_api_timezone
from utils.timezone_utils import resolve_timezone_name


def _localize_handler_response(
    result: Dict[str, Any],
    context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    user = (context or {}).get("user") or {}
    tz = resolve_timezone_name(user.get("timezone"))
    return with_api_timezone(result, tz)


# Map historical/custom labels to canonical phase-6 intents.
_INTENT_ALIASES = {
    "add": "scheduling_add",
    "delete": "scheduling_delete",
    "update": "scheduling_update",
    "show": "scheduling_show",
    "add_roadmap": "learning_create",
    "update_roadmap": "learning_update",
    "delete_roadmap": "learning_delete",
    "behavioral": "behavioral",
}


def normalize_intent(intent: str) -> str:
    if not intent:
        return "unknown"
    return _INTENT_ALIASES.get(intent, _INTENT_ALIASES.get(intent.lower(), intent))


async def route_intent(
    intent: str,
    entities: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Route an intent to a handler.
    Phase 6 returns placeholder handler responses until full handlers are implemented.
    """
    canonical_intent = normalize_intent(intent)
    entities = entities or {}
    context = context or {}

    if is_legacy_unsupported_intent(canonical_intent):
        return build_unsupported_intent_response(canonical_intent, context)

    if canonical_intent == "scheduling_add":
        return _localize_handler_response(
            await handle_scheduling_add(entities=entities, context=context),
            context,
        )

    if canonical_intent == "scheduling_delete":
        return _localize_handler_response(
            await handle_scheduling_delete(entities=entities, context=context),
            context,
        )

    if canonical_intent == "scheduling_show":
        return _localize_handler_response(
            await handle_scheduling_show(entities=entities, context=context),
            context,
        )

    if canonical_intent == "scheduling_update":
        return _localize_handler_response(
            await handle_scheduling_update(entities=entities, context=context),
            context,
        )

    if canonical_intent == "behavioral":
        return _localize_handler_response(
            await handle_behavioral(entities=entities, context=context),
            context,
        )

    if canonical_intent == "learning_create":
        return _localize_handler_response(
            await handle_learning_create(entities=entities, context=context),
            context,
        )

    if canonical_intent == "learning_delete":
        return _localize_handler_response(
            await handle_learning_delete(entities=entities, context=context),
            context,
        )

    if canonical_intent == "learning_update":
        return _localize_handler_response(
            await handle_learning_update(entities=entities, context=context),
            context,
        )

    response_map = {
        "scheduling_add": "scheduling_add",
        "scheduling_delete": "scheduling_delete",
        "scheduling_show": "scheduling_show",
        "scheduling_update": "scheduling_update",
    }

    user = context.get("user") or {}
    user_name = user.get("name")
    history = context.get("history") or []

    if canonical_intent in response_map:
        response_text = gemini_service.generate_reply(
            {
                "action": "intent_not_implemented",
                "intent_name": canonical_intent,
            },
            user_name,
            history,
        )
    else:
        response_text = gemini_service.generate_reply(
            {
                "action": "unknown_input_type",
            },
            user_name,
            history,
        )

    return {
        "routed": canonical_intent in response_map,
        "intent": canonical_intent,
        "entities": entities,
        "context": {
            "session_id": context.get("session_id"),
            "user_id": context.get("user_id"),
        },
        "response_text": response_text,
    }
