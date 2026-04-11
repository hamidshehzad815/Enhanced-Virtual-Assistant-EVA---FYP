"""
Google Calendar client service for task sync operations.
Phase 11: non-blocking calendar sync for scheduling add flow.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from utils.timezone_utils import get_zoneinfo, resolve_timezone_name


class GoogleCalendarClient:
    """Minimal async Google Calendar REST client."""

    def __init__(self):
        self.base_url = "https://www.googleapis.com/calendar/v3"

    @staticmethod
    def _build_headers(access_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _build_event_payload(task_data: Dict[str, Any]) -> Dict[str, Any]:
        due_datetime = task_data.get("due_datetime")
        if isinstance(due_datetime, str):
            due_dt = datetime.fromisoformat(due_datetime)
        elif isinstance(due_datetime, datetime):
            due_dt = due_datetime
        else:
            raise ValueError("task_data.due_datetime must be datetime or ISO string")

        duration_minutes = int(task_data.get("duration_minutes", task_data.get("duration", 120)))
        timezone_name = resolve_timezone_name(task_data.get("timezone") or "UTC")
        zone = get_zoneinfo(timezone_name)
        if due_dt.tzinfo is None:
            due_dt_utc = due_dt.replace(tzinfo=timezone.utc)
        else:
            due_dt_utc = due_dt.astimezone(timezone.utc)

        start_local = due_dt_utc.astimezone(zone)
        end_local = start_local + timedelta(minutes=duration_minutes)

        title = task_data.get("title") or "EVA Task"
        description = task_data.get("description")

        payload: Dict[str, Any] = {
            "summary": title,
            "start": {
                "dateTime": start_local.isoformat(),
                "timeZone": timezone_name,
            },
            "end": {
                "dateTime": end_local.isoformat(),
                "timeZone": timezone_name,
            },
        }

        if description:
            payload["description"] = description

        reminder_minutes_raw = task_data.get("reminder_minutes_before")
        if reminder_minutes_raw is not None:
            try:
                reminder_minutes = max(0, int(reminder_minutes_raw))
                payload["reminders"] = {
                    "useDefault": False,
                    "overrides": [
                        {
                            "method": "popup",
                            "minutes": reminder_minutes,
                        }
                    ],
                }
            except (TypeError, ValueError):
                # Ignore malformed reminder value and keep default behavior.
                pass

        return payload

    async def create_event(
        self,
        token: str,
        calendar_id: str,
        task_data: Dict[str, Any],
    ) -> Optional[str]:
        """Create event and return Google event id, else None."""
        if not token or not calendar_id:
            return None

        try:
            payload = self._build_event_payload(task_data)
            url = f"{self.base_url}/calendars/{calendar_id}/events"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    headers=self._build_headers(token),
                    json=payload,
                )

            if response.status_code in {200, 201}:
                data = response.json()
                return data.get("id")

            print(
                f"[GoogleCalendar] create_event failed: "
                f"status={response.status_code}, body={response.text[:300]}"
            )
            return None
        except Exception as error:
            print(f"[GoogleCalendar] create_event exception: {error}")
            return None

    async def update_event(
        self,
        token: str,
        calendar_id: str,
        event_id: str,
        task_data: Dict[str, Any],
    ) -> bool:
        """Update existing event by id."""
        if not token or not calendar_id or not event_id:
            return False

        try:
            payload = dict(task_data or {})
            if any(key in payload for key in ("due_datetime", "title", "duration", "duration_minutes")):
                payload = self._build_event_payload(payload)

            url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.patch(
                    url,
                    headers=self._build_headers(token),
                    json=payload,
                )
            return response.status_code in {200, 204}
        except Exception as error:
            print(f"[GoogleCalendar] update_event exception: {error}")
            return False

    async def delete_event(
        self,
        token: str,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        """Delete existing event by id."""
        if not token or not calendar_id or not event_id:
            return False

        try:
            url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(
                    url,
                    headers=self._build_headers(token),
                )
            return response.status_code in {200, 204}
        except Exception as error:
            print(f"[GoogleCalendar] delete_event exception: {error}")
            return False


# Singleton instance
google_calendar_client = GoogleCalendarClient()
