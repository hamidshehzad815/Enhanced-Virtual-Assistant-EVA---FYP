"""
Self-fetch service to gather all required context at request start.
"""
import asyncio
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from context.redis_client import redis_client
from db.readers import (
	fetch_conversation_history,
	fetch_integrations,
	fetch_user,
	fetch_user_settings,
)


@dataclass
class SelfFetchResult:
	user: Optional[Dict[str, Any]]
	settings: Dict[str, Any]
	history: List[Dict[str, Any]]
	integrations: List[Dict[str, Any]]
	context: Optional[Dict[str, Any]]

	def to_dict(self) -> Dict[str, Any]:
		return asdict(self)


async def self_fetch_all(user_id: str, session_id: str) -> SelfFetchResult:
	"""
	Fetch all request-time context in parallel.
	"""
	user_task = fetch_user(user_id)
	settings_task = fetch_user_settings(user_id)
	history_task = fetch_conversation_history(session_id, limit=10)
	integrations_task = fetch_integrations(user_id)
	redis_context_task = redis_client.get_context(user_id)

	user, settings, history, integrations, context = await asyncio.gather(
		user_task,
		settings_task,
		history_task,
		integrations_task,
		redis_context_task,
	)

	return SelfFetchResult(
		user=user,
		settings=settings,
		history=history,
		integrations=integrations,
		context=context,
	)

