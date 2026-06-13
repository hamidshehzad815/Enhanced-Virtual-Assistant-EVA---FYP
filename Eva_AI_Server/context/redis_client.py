"""
Redis client module for context management
"""
import json
from typing import Any, Optional
from urllib.parse import urlparse

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover - runtime dependency guard
    redis = None
from config.settings import settings


def _normalize_redis_host(host: str) -> str:
    value = (host or "").strip()
    for prefix in ("rediss://", "redis://", "https://", "http://"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    if "@" in value:
        value = value.split("@", 1)[1]
    if ":" in value:
        value = value.split(":", 1)[0]
    return value.strip("/")


class RedisClient:
    """Redis connection manager for context state"""

    client: Any = None

    def _build_client(self):
        redis_url = settings.REDIS_URL.strip()
        if redis_url:
            return redis.from_url(redis_url, decode_responses=True)

        host = _normalize_redis_host(settings.REDIS_HOST)
        username = (settings.REDIS_USERNAME or "").strip() or None
        if settings.REDIS_SSL and not username:
            username = "default"

        kwargs = {
            "host": host,
            "port": settings.REDIS_PORT,
            "username": username,
            "password": settings.REDIS_PASSWORD or None,
            "decode_responses": True,
        }
        if settings.REDIS_SSL:
            kwargs["ssl"] = True

        return redis.Redis(**kwargs)

    async def connect(self):
        """Connect to Redis"""
        if redis is None:
            print("[Redis] redis-py dependency not installed")
            return False

        try:
            self.client = self._build_client()
            await self.client.ping()
            if settings.REDIS_URL:
                parsed = urlparse(settings.REDIS_URL)
                target = parsed.hostname or "redis"
            else:
                target = _normalize_redis_host(settings.REDIS_HOST)
            print(f"[Redis] Connected to {target}:{settings.REDIS_PORT}")
            return True
        except Exception as e:
            print(f"[Redis] Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            print("[Redis] Disconnected")

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            await self.client.ping()
            return True
        except Exception:
            return False

    async def get_context(self, user_id: str) -> Optional[dict]:
        """
        Get pending context for a user
        Key: context:{user_id}
        """
        try:
            key = f"context:{user_id}"
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"[Redis] Error getting context: {e}")
            return None

    async def set_context(self, user_id: str, data: dict, ttl: int = None) -> bool:
        """
        Set pending context for a user
        Key: context:{user_id}
        TTL: defaults to CONTEXT_TTL from settings (300 seconds)
        """
        try:
            key = f"context:{user_id}"
            ttl = ttl or settings.CONTEXT_TTL
            await self.client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            print(f"[Redis] Error setting context: {e}")
            return False

    async def delete_context(self, user_id: str) -> bool:
        """
        Delete pending context for a user
        Key: context:{user_id}
        """
        try:
            key = f"context:{user_id}"
            await self.client.delete(key)
            return True
        except Exception as e:
            print(f"[Redis] Error deleting context: {e}")
            return False


# Singleton instance
redis_client = RedisClient()
