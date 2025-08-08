import asyncio
from typing import ClassVar

from core.shared.globals import broker
from . import service


class Dispatch:
    topic: ClassVar[str] = "ready-tasks"

    @classmethod
    async def producer_forver(cls):
        while True:
            tasks_id = await service.get_dispatch_tasks_id()
            for task_id in tasks_id:
                await cls.producer_once(task_id=task_id)

            await asyncio.sleep(60)

    @classmethod
    async def producer_once(cls, task_id: int):
        await broker.send(topic=cls.topic, message={"task_id": task_id})

    @classmethod
    async def consumer(cls, message: dict[str, int]):
        await service.execute_task(task_id=message["task_id"])

    @classmethod
    async def start(cls):
        asyncio.create_task(cls.producer_forver())
        await broker.consumer(topic=cls.topic, callback=cls.consumer, count=5)

    @classmethod
    async def shutdown(cls):
        await broker.shutdown()
