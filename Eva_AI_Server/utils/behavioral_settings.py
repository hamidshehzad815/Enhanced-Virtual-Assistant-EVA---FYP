"""User-facing behavioral analytics toggle helpers."""

from typing import Any, Dict, Optional


def is_behavioral_analytics_enabled(settings: Optional[Dict[str, Any]]) -> bool:
    """Return True unless the user explicitly disabled behavioral analytics."""
    if not settings:
        return True
    value = settings.get("behavioral_analytics_enabled")
    if value is None:
        return True
    return bool(value)
