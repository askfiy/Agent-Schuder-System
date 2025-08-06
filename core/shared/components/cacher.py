import json
import typing
from typing import Any

import redis.asyncio as redis


class RCacher:
    """
    基于 Redis 实现的 Simple 缓存系统
    在创建客户端时设置 decode_responses=True.
    """

    def __init__(self, redis_client: redis.Redis):
        self._client = redis_client

    async def has(self, key: str) -> bool:
        return await self._client.exists(key) > 0

    async def get(self, key: str, default: Any = None) -> Any:
        value = await self._client.get(key)
        if value is None:
            return default

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not ttl and await self._client.exists(key):
            current_ttl = await self._client.ttl(key)
            if current_ttl == -1:
                raise ValueError(
                    f"Key '{key}' exists without TTL. Refusing to set without TTL."
                )

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        await self._client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> bool:
        return await self._client.delete(key) > 0

    async def ttl(self, key: str) -> int:
        return await self._client.ttl(key)

    async def expire(self, key: str, ttl: int) -> bool:
        return await self._client.expire(key, ttl)

    async def list_length(self, key: str) -> int:
        return typing.cast("int", await self._client.llen(key))  # pyright: ignore[reportGeneralTypeIssues]

    async def list_get_all(self, key: str) -> list[Any]:
        items_str: list[Any] = typing.cast(
            "list[Any]",
            await self._client.lrange(key, 0, -1),  # pyright: ignore[reportUnknownMemberType, reportGeneralTypeIssues]
        )

        if not items_str:
            return []

        items: list[Any] = []
        for item_str in items_str:
            try:
                items.append(json.loads(item_str))
            except (json.JSONDecodeError, TypeError):
                items.append(item_str)
        return items

    async def list_push_left_many(self, key: str, values: list[Any]) -> int:
        if not values:
            return await self.list_length(key)

        values_str = [json.dumps(v) for v in values]
        return typing.cast("int", await self._client.lpush(key, *values_str))  # pyright: ignore[reportGeneralTypeIssues]

    async def list_pop_right(self, key: str) -> Any | None:
        item_str: str | None = typing.cast("str | None", await self._client.rpop(key))  # pyright: ignore[reportUnknownMemberType, reportGeneralTypeIssues]
        if item_str is None:
            return None

        try:
            return json.loads(item_str)
        except (json.JSONDecodeError, TypeError):
            return item_str
