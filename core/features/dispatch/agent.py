import uuid
import logging
import asyncio
import typing
from typing import Any
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from agents import Model

from core.shared.base.model import LLMOutputModel
from core.shared.components.agent import Agent
from core.shared.enums import TaskState, TaskAuditSource, MessageRole, TaskExecuteSource
from core.shared.components.session import RSession
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
)
from ..tasks.scheme import Tasks
from ..tasks.models import TaskUpdateModel
from ..tasks import service as tasks_service
from ..tasks_unit.models import TaskUnitCreateModel, TaskUnitUpdateModel
from ..tasks_unit import service as tasks_unit_service
from ..tasks_unit.scheme import TasksUnit
from ..tasks_workspace.service import update as update_workspace, get as get_workspace
from ..tasks_workspace.models import TaskWorkspaceUpdateModel
from .prompt import (
    task_planning_prompt,
    task_analyst_prompt,
    task_get_unit_prompt,
    task_unit_run_prompt,
)
from . import action
from .models import (
    TaskInDispatchModel,
    TaskDispatchUpdateStateModel,
    TaskDispatchCreateModel,
    TaskDispatchGeneratorInfoModel,
    TaskDispatchGeneratorPlanningModel,
    TaskDispatchGeneratorExecuteUnitModel,
    TaskDispatchExecuteUnitModel,
    TaskDispatchExecuteUnitOutputModel,
)

logger = logging.getLogger("Dispatch")


class TaskProxy(TaskInDispatchModel):
    @classmethod
    async def create(cls, task_id: int) -> "TaskProxy":
        db_obj = await action.get_task(task_id=task_id)
        return cls.model_validate(db_obj)

    def reload(self, other: Tasks):
        validated_data = self.__class__.model_validate(other)

        for field_name in self.__class__.model_fields:
            if hasattr(other, field_name):
                setattr(self, field_name, getattr(validated_data, field_name))

    async def update_state(self, update_model: TaskDispatchUpdateStateModel):
        async with get_async_tx_session_direct() as session:
            from_state = self.state
            to_state = update_model.state

            # 1. 更新任务状态
            db_obj = await action.update_task_state(
                task_id=self.id, state=to_state, session=session
            )

            # 2. 写审计日志（状态变化 & 模型保证字段完整性）
            if from_state != to_state:
                # 模型层确保字段完整性，类型断言只是为了通过类型检查器
                assert update_model.source is not None
                assert update_model.source_context is not None
                assert update_model.comment is not None

                await action.create_task_audit(
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
                await action.update_task_process(
                    task_id=self.id,
                    state=to_state,
                    process=update_model.process,
                    thinking=update_model.thinking,
                    session=session,
                )

        self.reload(db_obj)


@dataclass
class TaskAgent:
    agent: Agent
    task: TaskProxy | None

    @classmethod
    def create(
        cls,
        *,
        name: str,
        bind_task: TaskProxy | None = None,
        instructions: str | None | Callable[..., str],
        model: Model | None | str = None,
        session: RSession | None = None,
        **kwargs: Any,
    ) -> "TaskAgent":
        agent_instance = Agent(
            name=name, instructions=instructions, session=session, model=model, **kwargs
        )
        return cls(agent=agent_instance, task=bind_task)

    async def run_struct_output(
        self, input: str | list[Any], output_cls: type[LLMOutputModel]
    ):
        response = await self.agent.run(input=input, output_type=output_cls)
        response_model = response.final_output_as(output_cls)

        print(input)

        logger.info(response_model.pretty_json())
        return response_model

    async def call_soon_task(
        self,
        task: TaskProxy,
    ):
        """
        将任务加入调度中 ..
        """
        from . import Dispatch

        if task.expect_execute_time <= datetime.now(timezone.utc):
            await task.update_state(
                update_model=TaskDispatchUpdateStateModel(
                    state=TaskState.QUEUING,
                    source=TaskAuditSource.SYSTEM,
                    source_context="立即执行任务调度",
                    comment="任务属于立即执行任务. 改变状态并加入调度队列",
                )
            )
            logger.info(f"任务: {task.id} 加入调度 ..")
            await Dispatch.producer_once(task_id=task.id)

    async def create_task(
        self, trace_id: uuid.UUID, create_model: TaskDispatchCreateModel
    ) -> Tasks | str:
        """
        创建一个调度任务 ..

        """

        response_model: TaskDispatchGeneratorInfoModel = await self.run_struct_output(
            input=[
                {
                    "role": MessageRole.SYSTEM,
                    "content": task_analyst_prompt(TaskDispatchGeneratorInfoModel),
                },
                {
                    "role": MessageRole.USER,
                    "content": create_model.model_dump_markdown(),
                },
            ],
            output_cls=TaskDispatchGeneratorInfoModel,
        )

        if not response_model.is_splittable:
            return response_model.thinking

        db_obj = await action.create_dispatch_task(
            trace_id=trace_id,
            owner=create_model.owner,
            owner_timezone=create_model.owner_timezone,
            original_user_input=create_model.original_user_input,
            name=response_model.name,
            prd=response_model.prd,
            keywords=response_model.keywords,
            expect_execute_time=response_model.expect_execute_time.get_utc_datetime(),
        )

        task = TaskProxy.model_validate(db_obj)
        await self.call_soon_task(task)

        return db_obj

    async def run_unit(self, unit_orm: TasksUnit):
        """
        运行执行单元
        """
        assert self.task, "TaskAgent 未绑定任务. 因此无法运行执行单元."

        # 运行执行单元
        response_model: TaskDispatchExecuteUnitOutputModel = (
            await self.run_struct_output(
                input=[
                    {
                        "role": MessageRole.SYSTEM,
                        "content": task_unit_run_prompt(
                            output_cls=TaskDispatchExecuteUnitOutputModel
                        ),
                    },
                    {"role": MessageRole.USER, "content": ...},
                ],
                output_cls=TaskDispatchExecuteUnitOutputModel,
            )
        )

    async def get_unit(self):
        """
        拆解执行单元
        """

        assert self.task, "TaskAgent 未绑定任务. 因此无法运行执行计划."

        unit_orm_list: list[TasksUnit] = []
        async with get_async_tx_session_direct() as session:
            workspace = await get_workspace(
                workspace_id=self.task.workspace_id, session=session
            )

            process = workspace.process

            # 拆解执行单元
            response_model: TaskDispatchGeneratorExecuteUnitModel = (
                await self.run_struct_output(
                    input=[
                        {
                            "role": MessageRole.SYSTEM,
                            "content": task_get_unit_prompt(
                                output_cls=TaskDispatchGeneratorExecuteUnitModel
                            ),
                        },
                        {"role": MessageRole.USER, "content": process},
                    ],
                    output_cls=TaskDispatchGeneratorExecuteUnitModel,
                )
            )
            # 创建执行单元
            for unit in response_model.unit_list:
                unit: TaskDispatchExecuteUnitModel

                unit_orm = await tasks_unit_service.create(
                    create_model=TaskUnitCreateModel(
                        name=unit.name,
                        objective=unit.objective,
                        task_id=self.task.id,
                        invocation_id=typing.cast("uuid.UUID", self.task.invocation_id),
                    ),
                    session=session,
                )

                unit_orm_list.append(unit_orm)

        for unit_orm in unit_orm_list:
            asyncio.create_task(self.run_unit(unit_orm))

    async def planning(self):
        """
        拆解执行计划
        """
        assert self.task, "TaskAgent 未绑定任务. 因此无法计划任务."

        if not self.task.invocation_id:
            async with get_async_session_direct() as session:
                workspace = await get_workspace(
                    workspace_id=self.task.workspace_id, session=session
                )
                prd = workspace.prd

            # 拆解执行计划
            response_model: TaskDispatchGeneratorPlanningModel = (
                await self.run_struct_output(
                    input=[
                        {
                            "role": MessageRole.SYSTEM,
                            "content": task_planning_prompt(
                                output_cls=TaskDispatchGeneratorPlanningModel
                            ),
                        },
                        {"role": MessageRole.USER, "content": prd},
                    ],
                    output_cls=TaskDispatchGeneratorPlanningModel,
                )
            )

            # TODO: 代码优化
            async with get_async_tx_session_direct() as session:
                await update_workspace(
                    workspace_id=self.task.workspace_id,
                    update_model=TaskWorkspaceUpdateModel(
                        process=response_model.process,
                    ),
                    session=session,
                )

                self.task.reload(
                    await tasks_service.update(
                        task_id=self.task.id,
                        update_model=TaskUpdateModel(invocation_id=uuid.uuid4()),
                        session=session,
                    )
                )

    async def execute(self, execute_source: TaskExecuteSource):
        """
        执行调度任务 ...

        任务执行有 4 个步骤:
            1. 步骤规划
            2. 单元调度
            3. 状态推进
            4. 结果反思
        """
        assert self.task, "TaskAgent 未绑定任务. 因此无法执行."

        if execute_source == TaskExecuteSource.DISPATCH:
            logger.info(f"调度开始消费任务: {self.task.pretty_json()}")

            if self.task.state != TaskState.QUEUING:
                match self.task.state:
                    case state if state in [TaskState.CANCELLED]:
                        logger.info("任务非正常出队, 已被用户取消. 放弃该任务")
                        return
                    case state if state in [TaskState.FAILED, TaskState.FINISHED]:
                        logger.info("任务非正常出队, 已进入结束态. 放弃该任务")
                        return
                    case _:
                        logger.info("任务非正常出队, 状态可恢复. 尝试恢复中...")
                        await self.task.update_state(
                            TaskDispatchUpdateStateModel(
                                state=TaskState.SCHEDULING,
                                source=TaskAuditSource.SYSTEM,
                                source_context="任务非正常出队.",
                                comment="任务重新等待调度 ..",
                            )
                        )
                        await self.call_soon_task(task=self.task)
                        return

            await self.task.update_state(
                TaskDispatchUpdateStateModel(
                    state=TaskState.ACTIVATING,
                    source=TaskAuditSource.SYSTEM,
                    source_context="任务已成功出队并被消费.",
                    comment="开始执行任务中 ..",
                )
            )

            await self.planning()

        else:
            await self.get_unit()
