"""
Intent router for Phase 6.
Routes Model 2 intents to handler stubs.
"""
from typing import Any, Dict, Optional

from handlers.behavioral import handle_behavioral
from handlers.scheduling.add import handle_scheduling_add
from handlers.scheduling.delete import handle_scheduling_delete
from handlers.scheduling.show import handle_scheduling_show
from handlers.scheduling.update import handle_scheduling_update
from services.gemini import gemini_service


# Map historical/custom labels to canonical phase-6 intents.
_INTENT_ALIASES = {
    "add": "scheduling_add",
    "delete": "scheduling_delete",
    "update": "scheduling_update",
    "show": "scheduling_show",
    "add_roadmap": "learning_create",
    "update_roadmap": "learning_update",
    "delete_roadmap": "learning_delete",
    "show_roadmap": "learning_show",
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

    if canonical_intent == "scheduling_add":
        return await handle_scheduling_add(entities=entities, context=context)

    if canonical_intent == "scheduling_delete":
        return await handle_scheduling_delete(entities=entities, context=context)

    if canonical_intent == "scheduling_show":
        return await handle_scheduling_show(entities=entities, context=context)

    if canonical_intent == "scheduling_update":
        return await handle_scheduling_update(entities=entities, context=context)

    if canonical_intent == "behavioral":
        return await handle_behavioral(entities=entities, context=context)

    disabled_intents = {
        "learning_create",
        "learning_update",
        "learning_delete",
        "learning_show",
        "add_roadmap",
        "update_roadmap",
        "delete_roadmap",
        "show_roadmap",
    }
    if canonical_intent in disabled_intents:
        user = context.get("user") or {}
        user_name = user.get("name")
        history = context.get("history") or []
        response_text = gemini_service.generate_reply(
            {
                "action": "out_of_scope",
                "user_message": context.get("message", ""),
            },
            user_name,
            history,
        )
        return {
            "routed": False,
            "intent": canonical_intent,
            "status": "disabled",
            "response_text": response_text,
            "notifications": [],
        }

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
