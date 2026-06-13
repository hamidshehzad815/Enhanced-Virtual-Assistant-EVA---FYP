"""
Duckling HTTP client for date/time resolution
"""
from typing import Optional
import httpx
from config.settings import settings


class DucklingClient:
    """Duckling HTTP client for date/time parsing"""

    def __init__(self):
        self.base_url = settings.DUCKLING_URL
        self.connected = False

    async def connect(self) -> bool:
        """Check if Duckling service is available"""
        import asyncio

        for attempt in range(1, 6):
            try:
                async with httpx.AsyncClient() as client:
                    if attempt == 1:
                        print(f"[Duckling] Checking {self.base_url}")
                    response = await client.post(
                        f"{self.base_url}/parse",
                        data={
                            "locale": "en_US",
                            "text": "tomorrow",
                            "dims": '["time"]',
                        },
                        timeout=5.0,
                    )
                    if response.status_code == 200:
                        self.connected = True
                        print(f"[Duckling] Connected to {self.base_url}")
                        return True
                    print(f"[Duckling] Unexpected response: {response.status_code}")
            except Exception as e:
                print(f"[Duckling] Connection attempt {attempt}/5 failed: {e}")
            if attempt < 5:
                await asyncio.sleep(2)
        return False

    async def health_check(self) -> bool:
        """Check if Duckling service is healthy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/parse",
                    data={
                        "locale": "en_US",
                        "text": "now",
                        "dims": '["time"]'
                    },
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def parse(
        self,
        text: str,
        dims: list = None,
        locale: str = "en_US",
        timezone: str = "UTC"
    ) -> Optional[list]:
        """
        Parse text for date/time entities using Duckling

        Args:
            text: The text to parse
            dims: Dimensions to extract (e.g., ["time", "duration"])
            locale: Locale for parsing (default: en_US)
            timezone: Timezone for reference (default: UTC)

        Returns:
            List of parsed entities or None on error
        """
        dims = dims or ["time"]
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/parse",
                    data={
                        "locale": locale,
                        "text": text,
                        "dims": str(dims).replace("'", '"'),
                        "tz": timezone
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            print(f"[Duckling] Parse error: {e}")
            return None

    async def resolve_date(self, text: str, timezone: str = "UTC") -> Optional[str]:
        """
        Resolve a date expression to ISO format

        Args:
            text: Date expression (e.g., "Monday", "25th March")
            timezone: Timezone for reference

        Returns:
            ISO date string (YYYY-MM-DD) or None
        """
        results = await self.parse(text, dims=["time"], timezone=timezone)
        if results:
            for result in results:
                if result.get("dim") == "time":
                    value = result.get("value", {})
                    if "value" in value:
                        # Extract date part from ISO datetime
                        iso_value = value["value"]
                        return iso_value.split("T")[0]
        return None

    async def resolve_time(self, text: str, timezone: str = "UTC") -> Optional[str]:
        """
        Resolve a time expression to ISO format

        Args:
            text: Time expression (e.g., "5PM", "18:00")
            timezone: Timezone for reference

        Returns:
            ISO time string (HH:MM:SS) or None
        """
        results = await self.parse(text, dims=["time"], timezone=timezone)
        if results:
            for result in results:
                if result.get("dim") == "time":
                    value = result.get("value", {})
                    if "value" in value:
                        iso_value = value["value"]
                        if "T" in iso_value:
                            # Extract time part from ISO datetime
                            return iso_value.split("T")[1].split("+")[0].split("-")[0]
        return None

    async def resolve_duration(self, text: str) -> Optional[int]:
        """
        Resolve a duration expression to minutes

        Args:
            text: Duration expression (e.g., "2 hours", "30 minutes")

        Returns:
            Duration in minutes or None
        """
        results = await self.parse(text, dims=["duration"])
        if results:
            for result in results:
                if result.get("dim") == "duration":
                    value = result.get("value", {})
                    normalized = value.get("normalized", {})
                    if "value" in normalized:
                        # Duckling returns duration in seconds
                        seconds = normalized["value"]
                        return int(seconds / 60)
        return None


# Singleton instance
duckling_client = DucklingClient()
