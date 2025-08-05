import redis.asyncio as redis

from core.config import env_helper


pool: redis.ConnectionPool = redis.ConnectionPool.from_url(  # pyright: ignore[reportUnknownMemberType]
    url=env_helper.ASYNC_REDIS_URL, decode_responses=True
)

client = redis.Redis(connection_pool=pool)

__all__ = ["pool", "client"]
