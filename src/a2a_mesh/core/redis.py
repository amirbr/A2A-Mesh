"""Redis client singleton."""

from redis.asyncio import Redis

from a2a_mesh.config import settings

_redis: Redis | None = None  # type: ignore[type-arg]


def get_redis() -> Redis:  # type: ignore[type-arg]
    """Return the shared async Redis client, creating it on first call."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Close the Redis connection. Call on app shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
