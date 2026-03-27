"""
Conversation history insert operations.
"""
from datetime import datetime, timezone
from typing import Any, Dict

from config.database import get_db


async def insert_message(message_data: Dict[str, Any]) -> str:
    """Insert one conversation message and return inserted id as string."""
    db = get_db()
    payload = dict(message_data)
    payload.setdefault("created_at", datetime.now(timezone.utc).replace(tzinfo=None))
    result = await db.conversation_history.insert_one(payload)
    return str(result.inserted_id)
