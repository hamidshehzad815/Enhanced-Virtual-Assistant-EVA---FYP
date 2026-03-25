"""
General/non-command handler logic.
Phase 8: uses Gemini service first with safe fallback generation.
"""
from typing import Any, Dict, List, Optional

from services.gemini import gemini_service


def _user_name(user: Optional[Dict[str, Any]]) -> Optional[str]:
    if not user:
        return None
    return user.get("name")


def handle_general(
    user: Optional[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    user_name = _user_name(user)
    response_text = gemini_service.generate_reply(
        action_context={
            "action": "general_greeting",
            "user_message": message,
        },
        user_name=user_name,
        conversation_history=history,
    )

    return {
        "route": "general",
        "response_text": response_text,
        "user_name": user_name,
    }


def handle_out_of_scope(
    user: Optional[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    user_name = _user_name(user)
    response_text = gemini_service.generate_reply(
        action_context={
            "action": "out_of_scope",
            "user_message": message,
        },
        user_name=user_name,
        conversation_history=history,
    )

    return {
        "route": "out_of_scope",
        "response_text": response_text,
        "user_name": user_name,
    }


def handle_multiple_command(
    user: Optional[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    user_name = _user_name(user)
    response_text = gemini_service.generate_reply(
        action_context={
            "action": "multiple_command",
            "user_message": message,
        },
        user_name=user_name,
        conversation_history=history,
    )

    return {
        "route": "multiple_command",
        "response_text": response_text,
        "user_name": user_name,
    }


def handle_confirmation_unexpected(
    user: Optional[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    user_name = _user_name(user)
    response_text = gemini_service.generate_reply(
        action_context={
            "action": "confirmation_unexpected",
            "user_message": message,
        },
        user_name=user_name,
        conversation_history=history,
    )

    return {
        "route": "confirmation_unexpected",
        "response_text": response_text,
        "user_name": user_name,
    }
