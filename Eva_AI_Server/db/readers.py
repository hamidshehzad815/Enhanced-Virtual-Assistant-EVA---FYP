"""
Read-only database helpers used by the AI server self-fetch step.
"""
from typing import Any, Dict, List, Optional

from bson import ObjectId

from config.database import get_db


def _to_object_id(value: str):
	"""Convert string ids to ObjectId when possible; keep original on failure."""
	try:
		return ObjectId(value)
	except Exception:
		return value


def _normalize_value(value: Any) -> Any:
	"""Recursively convert BSON-specific values into JSON-friendly values."""
	if isinstance(value, ObjectId):
		return str(value)
	if isinstance(value, dict):
		return {k: _normalize_value(v) for k, v in value.items()}
	if isinstance(value, list):
		return [_normalize_value(item) for item in value]
	return value


def _normalize_doc_id(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
	"""Return a fully JSON-friendly copy of a Mongo document."""
	if not document:
		return document
	return _normalize_value(dict(document))


async def fetch_user(user_id: str) -> Optional[Dict[str, Any]]:
	"""Fetch user basics needed by the AI pipeline."""
	db = get_db()
	query = {"_id": _to_object_id(user_id)}
	projection = {
		"name": 1,
		"username": 1,
		"timezone": 1,
		"is_active": 1,
	}
	doc = await db.users.find_one(query, projection)
	return _normalize_doc_id(doc)


async def fetch_user_settings(user_id: str) -> Dict[str, Any]:
	"""
	Fetch settings for the user.
	Returns an empty dict when no document exists yet.
	"""
	db = get_db()
	user_id_query = _to_object_id(user_id)

	# Try both common collection naming styles used across this project.
	collections = [db.user_settings, db.usersettings]
	doc = None
	for collection in collections:
		doc = await collection.find_one({"user_id": user_id_query})
		if doc:
			break

	# Fallback for projects where user_id may be stored as plain string.
	if not doc and user_id_query != user_id:
		for collection in collections:
			doc = await collection.find_one({"user_id": user_id})
			if doc:
				break

	return _normalize_doc_id(doc) or {}


async def fetch_conversation_history(
	session_id: str,
	limit: int = 10,
) -> List[Dict[str, Any]]:
	"""Fetch most recent chat messages for model context."""
	db = get_db()
	cursor = (
		db.conversation_history.find({"session_id": session_id})
		.sort("created_at", -1)
		.limit(limit)
	)

	rows = await cursor.to_list(length=limit)
	return [_normalize_doc_id(row) for row in rows]


async def fetch_integrations(user_id: str) -> List[Dict[str, Any]]:
	"""Fetch active integrations for the current user."""
	db = get_db()
	user_id_query = _to_object_id(user_id)
	cursor = db.integrations.find({"user_id": user_id_query, "is_active": True})
	rows = await cursor.to_list(length=20)

	# Fallback when user_id is stored as plain string.
	if not rows and user_id_query != user_id:
		cursor = db.integrations.find({"user_id": user_id, "is_active": True})
		rows = await cursor.to_list(length=20)

	return [_normalize_doc_id(row) for row in rows]

