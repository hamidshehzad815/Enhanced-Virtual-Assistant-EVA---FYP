"""
Ensure MongoDB indexes for learning / roadmap collections (idempotent).
"""

from typing import Any


async def ensure_learning_indexes(db: Any) -> None:
    if db is None:
        return

    rr = db.roadmap_resources
    await rr.create_index(
        [("language", 1), ("level", 1), ("order", 1)],
        name="language_level_order",
    )
    await rr.create_index(
        [("language", 1), ("level", 1)],
        name="language_level",
    )
    await rr.create_index([("fetched_at", 1)], name="fetched_at")

    lg = db.learning_goals
    await lg.create_index(
        [("user_id", 1), ("status", 1)],
        name="user_id_status",
    )

    rt = db.roadmap_topics
    await rt.create_index(
        [("goal_id", 1), ("order", 1)],
        name="goal_id_order",
    )
