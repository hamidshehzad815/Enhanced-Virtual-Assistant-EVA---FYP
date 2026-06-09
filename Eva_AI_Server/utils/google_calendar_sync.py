"""
Google Calendar sync gating, integration selection, and token refresh.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from db.integrations import update_integration_tokens

REFRESH_BUFFER = timedelta(minutes=5)


def is_google_calendar_sync_enabled(user_settings: Optional[Dict[str, Any]]) -> bool:
    return (user_settings or {}).get("google_calendar_sync_enabled") is True


def pick_active_google_integration(
    integrations: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    for integration in integrations:
        if not isinstance(integration, dict):
            continue

        provider = str(integration.get("provider") or "").lower()
        is_active = integration.get("is_active") is True
        if provider == "google_calendar" and is_active:
            return integration

    return None


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _parse_token_expires(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _token_needs_refresh(integration: Dict[str, Any]) -> bool:
    access_token = _coerce_text(integration.get("access_token"))
    if not access_token:
        return bool(_coerce_text(integration.get("refresh_token")))

    expires = _parse_token_expires(integration.get("token_expires"))
    if expires is None:
        # Unknown expiry: use the stored access token until it fails or expires_at is set.
        return False
    return expires <= datetime.now(timezone.utc) + REFRESH_BUFFER


async def refresh_google_access_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    if not client_id or not client_secret or not refresh_token:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

        if response.status_code != 200:
            print(
                "[GoogleCalendarSync] token refresh failed: "
                f"status={response.status_code}, body={response.text[:200]}"
            )
            return None

        data = response.json()
        access_token = _coerce_text(data.get("access_token"))
        if not access_token:
            return None

        token_expires = None
        expires_in = data.get("expires_in")
        if expires_in is not None:
            try:
                token_expires = datetime.now(timezone.utc) + timedelta(
                    seconds=int(expires_in),
                )
            except (TypeError, ValueError):
                pass

        return {
            "access_token": access_token,
            "token_expires": token_expires,
        }
    except Exception as error:
        print(f"[GoogleCalendarSync] token refresh exception: {error}")
        return None


async def ensure_fresh_access_token(
    user_id: str,
    integration: Dict[str, Any],
) -> Dict[str, Any]:
    integration = dict(integration or {})
    if not _token_needs_refresh(integration):
        return integration

    refresh_token = _coerce_text(integration.get("refresh_token"))
    refreshed = await refresh_google_access_token(refresh_token)
    if not refreshed:
        return integration

    new_token = refreshed["access_token"]
    token_expires = refreshed.get("token_expires")
    integration_id = _coerce_text(integration.get("_id") or integration.get("id"))
    if integration_id:
        await update_integration_tokens(user_id, integration_id, new_token, token_expires)

    integration["access_token"] = new_token
    if token_expires is not None:
        integration["token_expires"] = token_expires
    return integration


async def resolve_google_calendar_sync(
    user_id: str,
    integrations: List[Dict[str, Any]],
    user_settings: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Return an active Google integration with a usable access token when sync is enabled.
    """
    if not is_google_calendar_sync_enabled(user_settings):
        return None

    integration = pick_active_google_integration(integrations)
    if not integration:
        return None

    integration = await ensure_fresh_access_token(user_id, integration)
    if not _coerce_text(integration.get("access_token")):
        return None

    return integration
