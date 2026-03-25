"""
Chat session update operations used by AI server.
"""
from datetime import datetime
from typing import Any

from bson import ObjectId

from config.database import get_db


def _to_object_id(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))
    except Exception:
        return value


async def update_last_message(session_id: str, preview: str, timestamp: datetime) -> bool:
    """
    Update chat session summary fields.
    Tries both snake_case and mongoose-pluralized collection names.
    """
    db = get_db()
    collections = [db.chat_sessions, db.chatsessions]

    session_object_id = _to_object_id(session_id)
    payload = {
        "last_message_preview": (preview or "")[:200],
        "last_message_at": timestamp,
        "updated_at": timestamp,
    }

    for collection in collections:
        result = await collection.update_one({"_id": session_object_id}, {"$set": payload})
        if result.matched_count:
            return True

        if session_object_id != session_id:
            result = await collection.update_one({"_id": session_id}, {"$set": payload})
            if result.matched_count:
                return True

    return False
