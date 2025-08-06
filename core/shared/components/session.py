from typing import override

from agents import Session
from agents.items import TResponseInputItem

from . import RCacher


class RSession(Session):
    """
    基于 RCacher 实现的、并发安全的 openai.agents session 管理。
    所有列表操作都基于 Redis 的原子命令，避免了竞态条件。
    """

    def __init__(self, session_id: str, cacher: RCacher, ttl: int = 3600):
        self.session_id = session_id
        self.cacher = cacher
        self.ttl = ttl

    @override
    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        items: list[TResponseInputItem] = await self.cacher.list_get_all(
            self.session_id
        )
        if limit is not None and limit > 0:
            return items[-limit:]
        return items

    @override
    async def add_items(self, items: list[TResponseInputItem]) -> None:
        if not items:
            return
        await self.cacher.list_push_left_many(self.session_id, items)
        await self.cacher.expire(self.session_id, self.ttl)

    @override
    async def pop_item(self) -> TResponseInputItem | None:
        return await self.cacher.list_pop_right(self.session_id)

    @override
    async def clear_session(self) -> None:
        await self.cacher.delete(self.session_id)
