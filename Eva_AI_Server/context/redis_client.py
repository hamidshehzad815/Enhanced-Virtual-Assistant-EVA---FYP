"""
Redis client module for context management
"""
import json
from typing import Optional
import redis.asyncio as redis
from config.settings import settings


class RedisClient:
    """Redis connection manager for context state"""

    client: redis.Redis = None

    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True
            )
            # Verify connection
            await self.client.ping()
            print(f"[Redis] Connected to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
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
