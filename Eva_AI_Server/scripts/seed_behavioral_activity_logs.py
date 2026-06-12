#!/usr/bin/env python3
"""
Seed Activity_Logs for behavioral analytics testing.

Usage:
  cd Eva_AI_Server
  PYTHONPATH=. python scripts/seed_behavioral_activity_logs.py --user-id <mongo_user_id>
  PYTHONPATH=. python scripts/seed_behavioral_activity_logs.py --user-id <id> --profile sparse
  PYTHONPATH=. python scripts/seed_behavioral_activity_logs.py --user-id <id> --conflict-task

Profiles:
  full  — 29+ completed logs (passes global threshold 20); Mon/Tue/Thu strong, Wed/Fri weak
  sparse — 12 completed logs (below threshold 20) for "not enough data" tests

Clears prior seed rows where source=behavioral_seed for that user before insert.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta, time, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bson import ObjectId  # noqa: E402

from config.database import database, get_db  # noqa: E402
from db.activity_logs import get_log_count_per_day, get_total_completed, insert_log  # noqa: E402
from db.tasks import insert_task  # noqa: E402


SOURCE = "behavioral_seed"


def _to_object_id(value: str) -> Any:
    try:
        return ObjectId(str(value))
    except Exception:
        return value


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _completed_log(
    user_id: Any,
    day: int,
    hour: int,
    *,
    days_ago: int,
    on_time: bool = True,
    reschedule_count: int = 0,
    time_taken_minutes: int = 55,
    task_duration_minutes: int = 60,
    priority: str = "medium",
    subject: str = "",
) -> Dict[str, Any]:
    ts = _utc_naive_now() - timedelta(days=days_ago, hours=(hour % 6))
    return {
        "user_id": user_id,
        "task_id": ObjectId(),
        "action_type": "task_completed",
        "action_timestamp": ts,
        "day_of_week": day,
        "hour_of_day": hour,
        "scheduled_day": day,
        "scheduled_hour": hour,
        "week_number": ts.isocalendar().week,
        "task_priority": priority,
        "subject": subject or f"Seed {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day]} {hour}:00",
        "source": SOURCE,
        "time_taken_minutes": time_taken_minutes,
        "task_duration_minutes": task_duration_minutes,
        "was_on_time": on_time,
        "reschedule_count": reschedule_count,
    }


def build_full_logs(user_id: Any) -> List[Dict[str, Any]]:
    """Curated dataset for productive_hours/days/best_time/completion_rate/report."""
    logs: List[Dict[str, Any]] = []
    idx = 0

    def add(day: int, hour: int, count: int, **kwargs) -> None:
        nonlocal idx
        for i in range(count):
            logs.append(
                _completed_log(
                    user_id,
                    day,
                    hour,
                    days_ago=3 + (idx % 40),
                    **kwargs,
                )
            )
            idx += 1

    # Monday — strong evening window 6–8 PM; weak/rescheduled morning
    add(0, 18, 4, on_time=True, reschedule_count=0, time_taken_minutes=50)
    add(0, 19, 3, on_time=True, reschedule_count=0, time_taken_minutes=52)
    add(0, 20, 2, on_time=True, reschedule_count=0, time_taken_minutes=48)
    add(0, 10, 2, on_time=False, reschedule_count=3, time_taken_minutes=90)
    add(0, 14, 1, on_time=False, reschedule_count=1, time_taken_minutes=80)

    # Tuesday — evening focus
    add(1, 19, 4, on_time=True, reschedule_count=0, time_taken_minutes=54)
    add(1, 20, 3, on_time=True, reschedule_count=0, time_taken_minutes=56)
    add(1, 9, 2, on_time=True, reschedule_count=0, time_taken_minutes=58)

    # Wednesday — only 3 (below per-day threshold 5) for B11
    add(2, 15, 2, on_time=True, reschedule_count=0)
    add(2, 16, 1, on_time=False, reschedule_count=2)

    # Thursday — strong late morning
    add(3, 10, 3, on_time=True, reschedule_count=0, time_taken_minutes=50)
    add(3, 11, 3, on_time=True, reschedule_count=0, time_taken_minutes=52)

    # Friday — only 2 (unreliable day)
    add(4, 13, 1, on_time=True, reschedule_count=0)
    add(4, 14, 1, on_time=False, reschedule_count=1)

    return logs


def build_sparse_logs(user_id: Any) -> List[Dict[str, Any]]:
    """Below global threshold (20) for not_enough_data tests."""
    logs: List[Dict[str, Any]] = []
    for i, (day, hour) in enumerate(
        [
            (0, 18),
            (0, 19),
            (1, 19),
            (1, 20),
            (3, 10),
            (3, 11),
            (0, 18),
            (1, 19),
            (3, 10),
            (0, 20),
            (1, 20),
            (3, 11),
        ]
    ):
        logs.append(
            _completed_log(
                user_id,
                day,
                hour,
                days_ago=5 + i,
                on_time=i % 3 != 0,
                reschedule_count=0 if i % 3 else 1,
            )
        )
    return logs


async def clear_seed_data(user_id: str) -> int:
    db = get_db()
    owner = _to_object_id(user_id)
    variants = [owner]
    if owner != user_id:
        variants.append(user_id)

    result = await db.activity_logs.delete_many(
        {
            "user_id": {"$in": variants},
            "source": SOURCE,
        }
    )
    task_result = await db.tasks.delete_many(
        {
            "owner_id": {"$in": variants},
            "source": SOURCE,
        }
    )
    return int(result.deleted_count) + int(task_result.deleted_count)


async def seed_conflict_task(user_id: str) -> str:
    """Block Monday 6 PM for best_time conflict test (B12)."""
    owner = _to_object_id(user_id)
    today = date.today()
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_monday = today + timedelta(days=days_ahead)
    due = datetime.combine(next_monday, time(18, 0))

    task_id = await insert_task(
        {
            "owner_id": owner,
            "title": "Seed blocker — Monday 6PM (behavioral B12)",
            "due_datetime": due,
            "duration": 60,
            "priority": "medium",
            "status": "pending",
            "source": SOURCE,
            "scheduled_by": "manual",
            "collaborators": [],
            "is_deleted": False,
            "created_at": _utc_naive_now(),
            "updated_at": _utc_naive_now(),
        }
    )
    return task_id


async def main_async(
    user_id: str,
    profile: str,
    conflict_task: bool,
    skip_clear: bool,
) -> None:
    if not user_id.strip():
        raise SystemExit("--user-id is required")

    ok = await database.connect()
    if not ok:
        raise SystemExit("MongoDB connection failed")

    try:
        if not skip_clear:
            removed = await clear_seed_data(user_id)
            print(f"Cleared {removed} prior seed document(s).")

        owner = _to_object_id(user_id)
        logs = build_sparse_logs(owner) if profile == "sparse" else build_full_logs(owner)

        for payload in logs:
            await insert_log(payload, force=True)

        total = await get_total_completed(user_id)
        counts = await get_log_count_per_day(user_id)

        print(f"Inserted {len(logs)} task_completed logs (profile={profile}).")
        print(f"Total completed for user: {total}")
        print("Per weekday counts (Mon=0 … Sun=6):")
        for day in range(7):
            label = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day]
            print(f"  {label} ({day}): {counts.get(day, 0)}")

        if conflict_task and profile == "full":
            task_id = await seed_conflict_task(user_id)
            print(f"Conflict task inserted for next Monday 18:00 — task_id={task_id}")
        elif conflict_task:
            print("Skipped --conflict-task (use with --profile full).")

        print("\nReady for behavioral chat tests. See behavioral_seed_test_cases.txt")
    finally:
        await database.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed behavioral analytics activity logs")
    parser.add_argument("--user-id", required=True, help="MongoDB user _id")
    parser.add_argument(
        "--profile",
        choices=("full", "sparse"),
        default="full",
        help="full=29+ logs (default), sparse=12 logs (below threshold)",
    )
    parser.add_argument(
        "--conflict-task",
        action="store_true",
        help="Insert a pending task next Monday 6PM for B12 conflict test",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not remove previous behavioral_seed rows",
    )
    args = parser.parse_args()
    asyncio.run(
        main_async(
            user_id=args.user_id.strip(),
            profile=args.profile,
            conflict_task=args.conflict_task,
            skip_clear=args.no_clear,
        )
    )


if __name__ == "__main__":
    main()
