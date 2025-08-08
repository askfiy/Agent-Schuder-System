import logging
from collections.abc import Sequence

from core.shared.enums import TaskExecuteSource
from core.shared.globals import g, cacher
from core.shared.components.session import RSession
from core.shared.database.session import (
    get_async_tx_session_direct,
)

from ..tasks.scheme import Tasks
from ..tasks import service as tasks_service
from .agent import TaskAgent, TaskProxy
from .models import TaskDispatchCreateModel

logger = logging.getLogger("Dispatch-Task")


async def get_dispatch_tasks_id() -> Sequence[int]:
    """
    获取调度任务
    """
    async with get_async_tx_session_direct() as session:
        return await tasks_service.get_dispatch_tasks_id(session=session)


async def create_task(create_model: TaskDispatchCreateModel) -> Tasks | str:
    """
    Coding 引导创建任务.
    """
    trace_id = g.trace_id

    agent = TaskAgent.create(
        name="Task-Analyst-Agent",
        instructions="任务分析器",
    )

    return await agent.create_task(trace_id=trace_id, create_model=create_model)


async def execute_task(task_id: int, execute_source: TaskExecuteSource):
    """
    Coding 引导执行任务
    """
    task = await TaskProxy.create(task_id=task_id)
    g.trace_id = task.trace_id

    agent = TaskAgent.create(
        name="Task-Schedule-Agent",
        instructions="任务执行器",
        bind_task=task,
    )

    await agent.execute(execute_source)
