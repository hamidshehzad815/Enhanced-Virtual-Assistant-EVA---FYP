"""
Chat intents EVA does not implement.

Learning plan progress is available only via the mobile/web Roadmap UI
(GET /api/roadmaps/* on the backend), not through chat commands.
"""
from typing import Any, Dict, Optional

# Legacy Classifier 2 label — removed from training; old model weights may still emit it.
_LEGACY_UNSUPPORTED_LABELS = frozenset({"learning_show"})


def _display_name(user: Dict[str, Any]) -> str:
    name = str(user.get("name") or "").strip()
    if name:
        return name.split()[0]
    username = str(user.get("username") or "").strip()
    if username:
        return username
    return "there"


def is_legacy_unsupported_intent(intent: str) -> bool:
    label = str(intent or "").strip().lower()
    return label in _LEGACY_UNSUPPORTED_LABELS


def build_unsupported_intent_response(
    intent: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a routed response for legacy unsupported chat intents."""
    ctx = context or {}
    user = ctx.get("user") or {}
    who = _display_name(user)
    canonical = str(intent or "").strip().lower()

    response_text = (
        f"{who}, showing learning progress in chat isn't supported. "
        "Open the Roadmap tab in the app to view your plans and sessions."
    )

    return {
        "routed": False,
        "intent": canonical,
        "status": "unsupported",
        "response_text": response_text,
        "notifications": [],
    }
