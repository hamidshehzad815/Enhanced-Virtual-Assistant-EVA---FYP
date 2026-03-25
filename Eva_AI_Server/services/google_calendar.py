"""
Google Calendar client service for task sync operations.
Phase 11: non-blocking calendar sync for scheduling add flow.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx


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

        duration_minutes = int(task_data.get("duration_minutes", 120))
        end_dt = due_dt + timedelta(minutes=duration_minutes)

        timezone = task_data.get("timezone") or "UTC"
        title = task_data.get("title") or "EVA Task"
        description = task_data.get("description")

        payload: Dict[str, Any] = {
            "summary": title,
            "start": {
                "dateTime": due_dt.isoformat(),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": timezone,
            },
        }

        if description:
            payload["description"] = description

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
        data: Dict[str, Any],
    ) -> bool:
        """Update existing event by id."""
        if not token or not calendar_id or not event_id:
            return False

        try:
            url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.patch(
                    url,
                    headers=self._build_headers(token),
                    json=data,
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
