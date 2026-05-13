"""
Track YouTube Data API search calls per UTC day (persisted under data/).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class DailySearchQuota:
    """Limit search calls per calendar day (UTC)."""

    state_path: Path
    limit: int

    def __post_init__(self) -> None:
        self._count: int = 0
        self._date: str = ""
        self._load()

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load(self) -> None:
        self._date = self._today_utc()
        self._count = 0
        path = self.state_path
        try:
            if path.is_file():
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    stored_date = str(raw.get("date") or "")
                    if stored_date == self._date:
                        self._count = int(raw.get("count") or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not read quota state %s: %s", path, exc)
            self._count = 0

    def _save(self) -> None:
        path = self.state_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload: Dict[str, Any] = {"date": self._date, "count": self._count}
            path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not write quota state %s: %s", path, exc)

    def remaining(self) -> int:
        if self._date != self._today_utc():
            self._load()
        return max(0, int(self.limit) - self._count)

    def consume(self, n: int = 1) -> bool:
        if self._date != self._today_utc():
            self._load()
        if self._count + n > self.limit:
            return False
        self._count += n
        self._save()
        return True


def default_quota_path() -> Path:
    return settings.BASE_DIR / "data" / ".youtube_search_quota.json"


def build_default_quota() -> DailySearchQuota:
    return DailySearchQuota(
        state_path=default_quota_path(),
        limit=settings.YOUTUBE_DAILY_SEARCH_LIMIT,
    )
