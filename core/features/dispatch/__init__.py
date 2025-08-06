import uuid
import asyncio
from typing import ClassVar

from core.shared.globals import broker, cacher, g
from core.shared.components.session import RSession
from . import service
from .agent import TaskAgent, TaskProxy


class Dispatch:
    topic: ClassVar[str] = "ready-tasks"

    @classmethod
    async def producer(cls):
        while True:
            tasks_id = await service.get_dispatch_tasks_id()
            for task_id in tasks_id:
                await broker.send(topic=cls.topic, message={"task_id": task_id})

            await asyncio.sleep(60)

    @classmethod
    async def consumer(cls, message: dict[str, int]):
        g.trace_id = str(uuid.uuid4())
        task_id: int = message["task_id"]

        task = await TaskProxy.create(task_id=task_id)
        agent = TaskAgent.create(
            name="Task-Schedule-Agent",
            instructions="任务执行调度器",
            bind_task=task,
            session=RSession(session_id=g.trace_id, cacher=cacher),
        )
        await agent.execute()

    @classmethod
    async def start(cls):
        asyncio.create_task(cls.producer())
        await broker.consumer(topic=cls.topic, callback=cls.consumer, count=5)

    @classmethod
    async def shutdown(cls):
        await broker.shutdown()
