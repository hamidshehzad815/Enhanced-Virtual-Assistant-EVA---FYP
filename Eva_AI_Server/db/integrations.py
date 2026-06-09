"""
Integration write helpers for the AI server.
"""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from config.database import get_db


def _to_object_id(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return value


async def update_integration_tokens(
    user_id: str,
    integration_id: str,
    access_token: str,
    token_expires: Optional[datetime] = None,
) -> bool:
    """Persist refreshed OAuth tokens for a user's integration."""
    db = get_db()
    now = datetime.now(timezone.utc)
    update_doc = {
        "$set": {
            "access_token": access_token,
            "token_expires": token_expires,
            "updated_at": now,
        }
    }

    query = {
        "_id": _to_object_id(integration_id),
        "user_id": _to_object_id(user_id),
    }
    result = await db.integrations.update_one(query, update_doc)
    if result.matched_count:
        return True

    if str(_to_object_id(user_id)) != str(user_id):
        query = {"_id": _to_object_id(integration_id), "user_id": user_id}
        result = await db.integrations.update_one(query, update_doc)
    return result.matched_count > 0
