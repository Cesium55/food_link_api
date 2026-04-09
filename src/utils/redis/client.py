import redis.asyncio as aioredis
from typing import Optional
from urllib.parse import urlparse
from config import settings
from logger import get_logger

logger = get_logger(__name__)

_redis_client: Optional[aioredis.Redis] = None


def _build_redis_url() -> str:
    """
    Build and normalize Redis URL.

    If redis_url is provided without a scheme (e.g. "localhost:6379/0"),
    prepend "redis://".
    """
    configured_url = (settings.redis_url or "").strip()
    if configured_url:
        if "://" not in configured_url:
            configured_url = f"redis://{configured_url}"
        return configured_url

    return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


async def get_redis_client() -> aioredis.Redis:
    """Get or create Redis client"""
    global _redis_client
    
    if _redis_client is None:
        redis_url = _build_redis_url()
        _redis_client = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        parsed = urlparse(redis_url)
        logger.info(
            "Redis client initialized",
            extra={
                "redis_scheme": parsed.scheme,
                "redis_host": parsed.hostname,
                "redis_port": parsed.port,
                "redis_db_path": parsed.path,
            },
        )
    
    return _redis_client


async def close_redis_client():
    """Close Redis client"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")
