from ast import match_case
import logging
from typing import Any
from dataclasses import dataclass

from agents import Model

from core.shared.components.agent import Agent
from core.shared.enums import TaskState, TaskAuditSource
from core.shared.components.session import RSession
from core.shared.database.session import (
    get_async_tx_session_direct,
)
from ..tasks.scheme import Tasks
from . import service
from .models import TaskInDispatchModel, TaskInDispatchUpdateModel

logger = logging.getLogger("Dispatch")


class TaskProxy(TaskInDispatchModel):
    @classmethod
    async def create(cls, task_id: int) -> "TaskProxy":
        db_obj = await service.get_task(task_id=task_id)
        return cls.model_validate(db_obj)

    def _sync(self, other: Tasks):
        for field_name in self.__class__.model_fields:
            if hasattr(other, field_name):
                setattr(self, field_name, getattr(other, field_name))

    async def update(self, update_model: TaskInDispatchUpdateModel):
        async with get_async_tx_session_direct() as session:
            from_state = self.state
            to_state = update_model.state

            # 1. 更新任务状态
            db_obj = await service.update_task_state(
                task_id=self.id, state=to_state, session=session
            )

            # 2. 写审计日志（状态变化 & 模型保证字段完整性）
            if from_state != to_state:
                # 模型层确保字段完整性，类型断言只是为了通过类型检查器
                assert update_model.source is not None
                assert update_model.source_context is not None
                assert update_model.comment is not None

                await service.create_task_audit(
                    task_id=self.id,
                    from_state=from_state,
                    to_state=to_state,
                    source=update_model.source,
                    source_context=update_model.source_context,
                    comment=update_model.comment,
                    session=session,
                )

            # 3. 写历史记录（无论状态是否变化）
            if update_model.process and update_model.thinking:
                await service.update_task_process(
                    task_id=self.id,
                    state=to_state,
                    process=update_model.process,
                    thinking=update_model.thinking,
                    session=session,
                )

            # 4. 同步自身字段
            self._sync(db_obj)


@dataclass
class TaskAgent:
    agent: Agent
    task: TaskProxy

    @classmethod
    def create(
        cls,
        *,
        name: str,
        bind_task: TaskProxy,
        instructions: str | None,
        model: Model | None = None,
        session: RSession | None = None,
        **kwargs: Any,
    ) -> "TaskAgent":
        agent_instance = Agent(
            name=name, instructions=instructions, session=session, model=model, **kwargs
        )
        return cls(agent=agent_instance, task=bind_task)

    async def before_execute(self):
        pass

    async def execute(self):
        logger.info(f"消费任务: {self.task.model_dump_json(indent=2)}")

        # 可能得情况:
        #  -. CANCELLED: 在等待消费过程中, 被用户取消了
        #  -. UPDATING: 在等待消费过程中, 用户修改了任务的某些信息.
        if self.task.state != TaskState.QUEUING:
            match self.task.state:
                case TaskState.CANCELLED:
                    logger.info("任务非正常出队, 已被用户取消. 放弃该任务")
                    return

                case _:
                    await self.task.update(
                        TaskInDispatchUpdateModel(
                            state=TaskState.SCHEDULING,
                            source=TaskAuditSource.SYSTEM,
                            source_context="任务非正常出队.",
                            comment="任务重新等待调度 ..",
                        )
                    )
                    return

        await self.task.update(
            TaskInDispatchUpdateModel(
                state=TaskState.ACTIVATING,
                source=TaskAuditSource.SYSTEM,
                source_context="任务已成功出队并被消费.",
                comment="开始执行任务中 ..",
            )
        )

        logger.info(self.task.model_dump_json(indent=2))
