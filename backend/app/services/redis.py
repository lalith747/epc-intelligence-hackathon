"""
Redis service for caching and session management
"""
import json
from typing import Optional, Any, List
import redis.asyncio as redis
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RedisService:
    """Redis service for caching and session management"""
    
    def __init__(self):
        self.redis_client = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            self.redis_client = None
            logger.warning(f"Redis unavailable, continuing in local mode: {e}")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            if not self.redis_client:
                return None
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        try:
            if not self.redis_client:
                return False
            serialized_value = json.dumps(value)
            if ttl:
                await self.redis_client.setex(key, ttl, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            if not self.redis_client:
                return False
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        try:
            if not self.redis_client:
                return []
            return await self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            keys = await self.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
            return 0
    
    async def get_hash(self, key: str, field: str) -> Optional[str]:
        """Get hash field value"""
        try:
            if not self.redis_client:
                return None
            return await self.redis_client.hget(key, field)
        except Exception as e:
            logger.error(f"Redis hget error: {e}")
            return None
    
    async def set_hash(self, key: str, field: str, value: str) -> bool:
        """Set hash field value"""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.hset(key, field, value)
            return True
        except Exception as e:
            logger.error(f"Redis hset error: {e}")
            return False
    
    async def get_all_hash(self, key: str) -> dict:
        """Get all hash fields"""
        try:
            if not self.redis_client:
                return {}
            return await self.redis_client.hgetall(key)
        except Exception as e:
            logger.error(f"Redis hgetall error: {e}")
            return {}
    
    async def delete_hash(self, key: str) -> bool:
        """Delete hash"""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete hash error: {e}")
            return False
    
    async def push_list(self, key: str, value: str) -> bool:
        """Push value to list"""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.lpush(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis lpush error: {e}")
            return False
    
    async def pop_list(self, key: str) -> Optional[str]:
        """Pop value from list"""
        try:
            if not self.redis_client:
                return None
            return await self.redis_client.rpop(key)
        except Exception as e:
            logger.error(f"Redis rpop error: {e}")
            return None
    
    async def get_list_range(self, key: str, start: int, end: int) -> List[str]:
        """Get list range"""
        try:
            if not self.redis_client:
                return []
            return await self.redis_client.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis lrange error: {e}")
            return []
    
    async def get_list_length(self, key: str) -> int:
        """Get list length"""
        try:
            if not self.redis_client:
                return 0
            return await self.redis_client.llen(key)
        except Exception as e:
            logger.error(f"Redis llen error: {e}")
            return 0


# Global Redis service instance
redis_service = RedisService()


async def get_redis() -> RedisService:
    """Dependency for getting Redis service"""
    return redis_service
