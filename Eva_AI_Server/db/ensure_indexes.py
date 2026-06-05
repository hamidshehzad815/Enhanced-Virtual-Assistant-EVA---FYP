"""
Ensure MongoDB indexes for learning / roadmap collections (idempotent).
"""

from typing import Any

from pymongo.errors import OperationFailure

# Mongoose (Eva_Backend_Server) uses default index names for the same key patterns.
_MONGOOSE_INDEX_NAMES = {
    frozenset([("user_id", 1), ("status", 1)]): "user_id_1_status_1",
    frozenset([("goal_id", 1), ("order", 1)]): "goal_id_1_order_1",
}


async def _create_index_idempotent(collection: Any, keys: list, name: str) -> None:
    """Create index; skip if an equivalent index already exists under another name."""
    key_set = frozenset(keys)
    preferred = _MONGOOSE_INDEX_NAMES.get(key_set, name)
    try:
        await collection.create_index(keys, name=preferred)
    except OperationFailure as exc:
        if exc.code != 85:  # IndexOptionsConflict
            raise
        async for existing in collection.list_indexes():
            if existing.get("key") == dict(keys):
                return
        raise


async def ensure_learning_indexes(db: Any) -> None:
    if db is None:
        return

    rr = db.roadmap_resources
    await _create_index_idempotent(
        rr,
        [("language", 1), ("level", 1), ("order", 1)],
        "language_level_order",
    )
    await _create_index_idempotent(
        rr,
        [("language", 1), ("level", 1)],
        "language_level",
    )
    await _create_index_idempotent(rr, [("fetched_at", 1)], "fetched_at")

    lg = db.learning_goals
    await _create_index_idempotent(
        lg,
        [("user_id", 1), ("status", 1)],
        "user_id_status",
    )

    rt = db.roadmap_topics
    await _create_index_idempotent(
        rt,
        [("goal_id", 1), ("order", 1)],
        "goal_id_order",
    )
