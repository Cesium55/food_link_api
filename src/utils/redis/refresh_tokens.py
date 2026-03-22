import asyncio
import json
from typing import Optional

from app.auth import schemas
from config import settings
from utils.redis.client import get_redis_client


REFRESH_ROTATION_KEY_PREFIX = "refresh_rotation"
REFRESH_LOCK_KEY_PREFIX = "refresh_lock"


def _rotation_key(refresh_token: str) -> str:
    return f"{REFRESH_ROTATION_KEY_PREFIX}:{refresh_token}"


def _lock_key(refresh_token: str) -> str:
    return f"{REFRESH_LOCK_KEY_PREFIX}:{refresh_token}"


async def get_rotated_tokens(refresh_token: str) -> Optional[schemas.TokenResponse]:
    """Return cached rotation result for a recently rotated refresh token."""
    redis = await get_redis_client()
    payload = await redis.get(_rotation_key(refresh_token))
    if not payload:
        return None

    data = json.loads(payload)
    return schemas.TokenResponse(**data)


async def store_rotated_tokens(
    refresh_token: str,
    tokens: schemas.TokenResponse,
    expire_seconds: int | None = None,
) -> None:
    """Keep refresh rotation result for a short grace period."""
    redis = await get_redis_client()
    ttl = expire_seconds or settings.refresh_token_grace_period_seconds
    await redis.setex(
        _rotation_key(refresh_token),
        ttl,
        json.dumps(tokens.model_dump()),
    )


async def acquire_refresh_lock(
    refresh_token: str,
    timeout_seconds: int | None = None,
) -> bool:
    """Acquire a short-lived lock for a specific refresh token."""
    redis = await get_redis_client()
    ttl = timeout_seconds or settings.refresh_token_lock_timeout_seconds
    result = await redis.set(_lock_key(refresh_token), "1", ex=ttl, nx=True)
    return bool(result)


async def release_refresh_lock(refresh_token: str) -> None:
    """Release refresh token lock."""
    redis = await get_redis_client()
    await redis.delete(_lock_key(refresh_token))


async def wait_for_rotated_tokens(
    refresh_token: str,
    timeout_seconds: int | None = None,
    poll_interval_seconds: float = 0.05,
) -> Optional[schemas.TokenResponse]:
    """Wait until another request finishes rotating the same refresh token."""
    timeout = timeout_seconds or settings.refresh_token_lock_timeout_seconds
    deadline = asyncio.get_running_loop().time() + timeout

    while asyncio.get_running_loop().time() < deadline:
        tokens = await get_rotated_tokens(refresh_token)
        if tokens:
            return tokens
        await asyncio.sleep(poll_interval_seconds)

    return await get_rotated_tokens(refresh_token)
