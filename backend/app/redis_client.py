from redis.asyncio import Redis
from app.config import get_config

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        config = get_config()
        _redis = Redis.from_url(config.redis.url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
