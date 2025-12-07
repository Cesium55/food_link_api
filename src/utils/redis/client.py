import redis.asyncio as aioredis
from typing import Optional
from config import settings
from logger import get_sync_logger

logger = get_sync_logger(__name__)

_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """Get or create Redis client"""
    global _redis_client
    
    if _redis_client is None:
        redis_url = settings.redis_url or f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        _redis_client = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Redis client initialized", extra={"redis_url": redis_url})
    
    return _redis_client


async def close_redis_client():
    """Close Redis client"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")

