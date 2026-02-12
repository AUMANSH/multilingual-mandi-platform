"""
Redis client configuration and management.

This module provides Redis connection management for caching and session storage.
"""

import json
from typing import Any, Optional, Union
import redis.asyncio as redis
from redis.asyncio import Redis

from .config import get_redis_url, settings


class RedisManager:
    """Manages Redis connections and operations."""
    
    def __init__(self, redis_url: str):
        """Initialize Redis manager with connection URL."""
        self.redis_url = redis_url
        self.client: Optional[Redis] = None
    
    async def connect(self) -> Redis:
        """Connect to Redis and return client."""
        if self.client is None:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,
            )
        return self.client
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        client = await self.connect()
        return await client.get(key)
    
    async def set(
        self,
        key: str,
        value: Union[str, dict, list],
        ttl: Optional[int] = None,
    ) -> bool:
        """Set a value in Redis with optional TTL."""
        client = await self.connect()
        
        # Serialize complex objects to JSON
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        if ttl is None:
            ttl = settings.redis_cache_ttl
        
        return await client.set(key, value, ex=ttl)
    
    async def get_json(self, key: str) -> Optional[Union[dict, list]]:
        """Get and deserialize JSON value from Redis."""
        value = await self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    
    async def delete(self, key: str) -> int:
        """Delete a key from Redis."""
        client = await self.connect()
        return await client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        client = await self.connect()
        return bool(await client.exists(key))
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for an existing key."""
        client = await self.connect()
        return await client.expire(key, ttl)
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value in Redis."""
        client = await self.connect()
        return await client.incr(key, amount)
    
    async def hash_get(self, key: str, field: str) -> Optional[str]:
        """Get a field from a Redis hash."""
        client = await self.connect()
        return await client.hget(key, field)
    
    async def hash_set(self, key: str, field: str, value: str) -> int:
        """Set a field in a Redis hash."""
        client = await self.connect()
        return await client.hset(key, field, value)
    
    async def hash_get_all(self, key: str) -> dict:
        """Get all fields from a Redis hash."""
        client = await self.connect()
        return await client.hgetall(key)
    
    async def list_push(self, key: str, *values: str) -> int:
        """Push values to a Redis list."""
        client = await self.connect()
        return await client.lpush(key, *values)
    
    async def list_pop(self, key: str) -> Optional[str]:
        """Pop a value from a Redis list."""
        client = await self.connect()
        return await client.rpop(key)
    
    async def list_range(self, key: str, start: int = 0, end: int = -1) -> list:
        """Get a range of values from a Redis list."""
        client = await self.connect()
        return await client.lrange(key, start, end)
    
    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a Redis channel."""
        client = await self.connect()
        return await client.publish(channel, message)
    
    async def ping(self) -> bool:
        """Ping Redis to check connection."""
        try:
            client = await self.connect()
            await client.ping()
            return True
        except Exception:
            return False


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def get_redis_manager(test_mode: bool = False) -> RedisManager:
    """Get or create the global Redis manager."""
    global _redis_manager
    
    if _redis_manager is None or test_mode:
        redis_url = get_redis_url(test=test_mode)
        _redis_manager = RedisManager(redis_url)
    
    return _redis_manager


async def get_redis_client() -> Redis:
    """Dependency for getting Redis client in FastAPI."""
    redis_manager = get_redis_manager()
    return await redis_manager.connect()


async def close_redis():
    """Close Redis connections."""
    global _redis_manager
    if _redis_manager:
        await _redis_manager.disconnect()
        _redis_manager = None