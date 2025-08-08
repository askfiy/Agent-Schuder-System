
## `/Users/askfiy/project/coding/agent-scheduler-system/core/config.py`

```python
import os
from typing import Any

from pydantic import Field, MySQLDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


env = os.getenv("ENV")
assert env, "Invalid env."
configure_path = os.path.join(".", ".env", f".{env}.env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=configure_path)

    SYNC_DB_URL: str = Field(examples=["mysql+pymysql://root:123@127.0.0.1:3306/db1"])
    ASYNC_DB_URL: str = Field(examples=["mysql+asyncmy://root:123@127.0.0.1:3306/db1"])
    OPENAI_API_KEY: str = Field(examples=["sk-proj-..."])
    ASYNC_REDIS_URL: str = Field(examples=["redis://127.0.0.1:6379"])

    @field_validator("SYNC_DB_URL", "ASYNC_DB_URL", mode="before")
    @classmethod
    def _validate_db_url(cls, db_url: Any) -> str:
        if not isinstance(db_url, str):
            raise TypeError("Database URL must be a string")
        try:
            # 验证是否符合 MySQLDsn 类型.
            MySQLDsn(db_url)
        except Exception as e:
            raise ValueError(f"Invalid MySQL DSN: {e}") from e

        return str(db_url)

    @field_validator("ASYNC_REDIS_URL", mode="before")
    @classmethod
    def _validate_redis_url(cls, redis_url: Any) -> str:
        if not isinstance(redis_url, str):
            raise TypeError("Redis URL must be a string")
        try:
            # 验证是否符合 RedisDsn 类型.
            RedisDsn(redis_url)
        except Exception as e:
            raise ValueError(f"Invalid redis_url DSN: {e}") from e

        return str(redis_url)


env_helper = Settings()  # pyright: ignore[reportCallIssue]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/__init__.py`

```python

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/dispatch/__init__.py`

```python
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

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/dispatch/action.py`

```python
import uuid
import datetime
from collections.abc import Sequence

from core.shared.enums import TaskState, TaskAuditSource
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
    AsyncSession,
    AsyncTxSession,
)
from ..tasks.scheme import Tasks
from ..tasks_chat.scheme import TasksChat
from ..tasks_unit.scheme import TasksUnit
from ..tasks_audit.scheme import TasksAudit
from ..tasks_history.scheme import TasksHistory
from ..tasks_workspace.scheme import TasksWorkspace
from ..tasks import service as tasks_service
from ..tasks_chat import service as tasks_chat_service
from ..tasks_unit import service as tasks_unit_service
from ..tasks_audit import service as tasks_audit_service
from ..tasks_history import service as tasks_history_service
from ..tasks_workspace import service as tasks_workspace_service
from ..tasks.models import TaskCreateModel, TaskUpdateModel
from ..tasks_audit.models import TaskAuditCreateModel
from ..tasks_history.models import TaskHistoryCreateModel
from ..tasks_workspace.models import TaskWorkspaceCreateModel


async def get_task(task_id: int) -> Tasks:
    """
    获取任务
    """
    async with get_async_session_direct() as session:
        return await tasks_service.get(task_id, session=session)


async def create_dispatch_task(
    prd: str,
    name: str,
    expect_execute_time: datetime.datetime,
    owner: str,
    owner_timezone: str,
    keywords: list[str],
    original_user_input: str,
    trace_id: uuid.UUID,
) -> Tasks:
    """
    创建任务
    """

    async with get_async_tx_session_direct() as session:
        # 1. 先创建工作空间, 生成需求 PRD 等.
        workspace = await tasks_workspace_service.create(
            create_model=TaskWorkspaceCreateModel(prd=prd),
            session=session,
        )

        # 2. 再创建任务
        task = await tasks_service.create(
            create_model=TaskCreateModel(
                name=name,
                workspace_id=workspace.id,
                expect_execute_time=expect_execute_time,
                owner=owner,
                owner_timezone=owner_timezone,
                keywords=keywords,
                original_user_input=original_user_input,
                trace_id=trace_id,
            ),
            session=session,
        )
        return task

    # 3. 判断任务的执行时间是否小于等于当前时间. 若满足条件则进行入队


async def call_sonn_task(
    task_id: int, expect_execute_time: datetime.datetime
):
    if expect_execute_time <= datetime.datetime.now(datetime.timezone.utc):
        pass



async def update_task_state(
    task_id: int, state: TaskState, session: AsyncTxSession
) -> Tasks:
    # 更新任务本身状态
    task = await tasks_service.update(
        task_id=task_id,
        update_model=TaskUpdateModel(state=state),
        session=session,
    )

    return task


async def create_task_audit(
    task_id: int,
    from_state: TaskState,
    to_state: TaskState,
    source: TaskAuditSource,
    source_context: str,
    comment: str,
    session: AsyncTxSession,
) -> TasksAudit:
    # 创建审计日志
    return await tasks_audit_service.create(
        create_model=TaskAuditCreateModel(
            task_id=task_id,
            from_state=from_state,
            to_state=to_state,
            source=source,
            source_context=source_context,
            comment=comment,
        ),
        session=session,
    )


async def update_task_process(
    task_id: int, state: TaskState, process: str, thinking: str, session: AsyncSession
) -> TasksHistory:
    return await tasks_history_service.create(
        create_model=TaskHistoryCreateModel(
            task_id=task_id, state=state, process=process, thinking=thinking
        ),
        session=session,
    )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/dispatch/agent.py`

```python
import uuid
import logging
from typing import Any
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from agents import Model

from core.shared.base.model import LLMOutputModel
from core.shared.components.agent import Agent
from core.shared.enums import TaskState, TaskAuditSource
from core.shared.components.session import RSession
from core.shared.database.session import (
    get_async_tx_session_direct,
)
from ..tasks.scheme import Tasks
from . import action
from .models import (
    TaskInDispatchModel,
    TaskDispatchUpdateModel,
    TaskDispatchCreateModel,
    TaskDispatchGeneratorInfoModel,
)

logger = logging.getLogger("Dispatch")


class TaskProxy(TaskInDispatchModel):
    @classmethod
    async def create(cls, task_id: int) -> "TaskProxy":
        db_obj = await action.get_task(task_id=task_id)
        return cls.model_validate(db_obj)

    def _sync(self, other: Tasks):
        for field_name in self.__class__.model_fields:
            if hasattr(other, field_name):
                setattr(self, field_name, getattr(other, field_name))

    async def update(self, update_model: TaskDispatchUpdateModel):
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

            # 4. 同步自身字段
            self._sync(db_obj)


@dataclass
class TaskAgent:
    agent: Agent
    task: TaskProxy | None

    async def call_sonn_task(
        self,
        task: TaskProxy,
    ):
        from . import Dispatch

        if task.expect_execute_time <= datetime.now(timezone.utc):
            await task.update(
                update_model=TaskDispatchUpdateModel(
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
        response_model: TaskDispatchGeneratorInfoModel = await self.run_struct_output(
            input=create_model.model_dump_markdown(),
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
        await self.call_sonn_task(task)

        return db_obj

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

    async def run_struct_output(self, input: str, output_cls: type[LLMOutputModel]):
        response = await self.agent.run(input=input, output_type=output_cls)
        response_model = response.final_output_as(output_cls)

        logger.info(response_model.pretty_json())
        return response_model

    async def execute(self):
        assert self.task, "TaskAgent 未绑定任务. 因此无法执行."

        logger.info(f"消费任务: {self.task.pretty_json()}")

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
                    await self.task.update(
                        TaskDispatchUpdateModel(
                            state=TaskState.SCHEDULING,
                            source=TaskAuditSource.SYSTEM,
                            source_context="任务非正常出队.",
                            comment="任务重新等待调度 ..",
                        )
                    )
                    return

        await self.task.update(
            TaskDispatchUpdateModel(
                state=TaskState.ACTIVATING,
                source=TaskAuditSource.SYSTEM,
                source_context="任务已成功出队并被消费.",
                comment="开始执行任务中 ..",
            )
        )

        logger.info(self.task.pretty_json())

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/dispatch/models.py`

```python
import uuid
import datetime

from pydantic import Field, model_validator

from core.shared.enums import TaskState, TaskAuditSource
from core.shared.base.model import (
    BaseModel,
    LLMInputModel,
    LLMOutputModel,
    LLMTimeField,
)

from ..tasks_chat.models import TaskChatInCrudModel
from ..tasks_history.models import TaskHistoryInCrudModel
from . import prompt


class TaskDispatchUpdateModel(BaseModel):
    state: TaskState

    source: TaskAuditSource | None = None
    source_context: str | None = None
    comment: str | None = None

    process: str | None = None
    thinking: str | None = None

    @model_validator(mode="after")
    def validate_audit_dependency(self) -> "TaskDispatchUpdateModel":
        """
        验证规则 (二选一即可通过):
            - 所有审计字段必须“同生共死”。
            - 所有历史字段必须“同生共死”
        """

        validation_audit = all(
            {
                bool(self.source),
                bool(self.source_context),
                bool(self.comment),
            }
        )

        validation_histories = all(
            {
                bool(self.process),
                bool(self.thinking),
            }
        )

        if not any([validation_audit, validation_histories]):
            raise ValueError(
                "When updating state, 'state' and all audit fields ('source', 'source_context', 'comment') or all histories fields ('process', 'thinking') must be provided together."
            )

        return self


# 内部调度字段
class TaskInDispatchModel(LLMInputModel):
    id: int = Field(description="任务主键")
    name: str = Field(description="任务名称")
    state: TaskState = Field(description="当前任务状态")
    priority: int = Field(description="任务优先级")
    workspace_id: int = Field(description="任务关联工作区")
    trace_id: uuid.UUID = Field(description="任务来自的会话 ID")

    expect_execute_time: datetime.datetime = Field(description="任务预期执行时间")
    lasted_execute_time: datetime.datetime | None = Field(
        description="任务最后执行时间"
    )

    original_user_input: str = Field(description="原始用户输入")
    chats: list[TaskChatInCrudModel] = Field(description="任务和用户的交互历史")
    histories: list[TaskHistoryInCrudModel] = Field(description="LLM 执行历史")


# ----- 输入字段
class TaskDispatchCreateModel(LLMInputModel):
    owner: str
    original_user_input: str
    owner_timezone: str = Field(default="UTC", exclude=True)


# ---- 输出字段
class TaskDispatchGeneratorInfoModel(LLMOutputModel):
    is_splittable: bool = Field(description="是否需拆分任务", examples=[True])

    name: str = Field(
        description="任务名称, 若不需要拆分任务, 则不必生成名称",
        examples=["定时参加会议"],
    )

    expect_execute_time: LLMTimeField = Field(
        description="任务预期执行时间. 若是**立即执行**的任务, 则时间为当前时间. 若不需要拆分任务. 则不必计算时间.",
    )

    keywords: list[str] = Field(
        description="任务关键字, 必须是纯英文. 若不需要拆分任务. 则不必拆分关键字.",
        examples=["timed", "feature", "meeting", "ZhangSan"],
    )

    prd: str = Field(
        description="需求 PRD. 必须包含背景, 目标, 描述信息, 执行计划等等. 若不需要拆分任务. 则不必创建 PRD.",
        examples=[prompt.get_prd_example()],
    )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/dispatch/prompt.py`

```python
import datetime
from typing import Any


from core.shared.base.model import LLMOutputModel



def task_analyst_instructions(output_cls: type[LLMOutputModel]):
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    formatted = utc_now.strftime("%Y-%m-%d %H:%M:%S")

    return f"""
# 任务创建指南

## 角色与定义

作为一名需求分析专家，您的目标是分析用户的对话，并根据用户对话中蕴含的需求的复杂程度来决定是否要创建一个 **自动化调度任务** 来帮助用户更快更好的完成需求.

## 可调用的工具列表

**无**

## 步骤

1. 预检以下绝对不创建任务的场景, **若满足任意一条则不创建任务**.

    1.1: 过滤日常对话:
        - 日常互动且没有明确的时间要求 (例如：问候、感谢). 
        - 询问主观意见 (例如："你觉得……怎么样?").
        - 可以通过内部知识库直接回答的查询（例如："你是谁?").

    1.2: 过滤特殊场景:
        - 用户明确表示 **不需要** 创建任务.
        - 用户的需求核心意图依赖于 **单一、不可分割** 的原子能力（如：图像理解、文档解析等).

    1.3: 评估工具调用与内部功能调用的可行性:
        - 用户的需求无法通过现有工具或内部功能解决.
        - 用户的需求可以通过一个**已存在且可被调用**的工具 **单次调用** 解决.
        - 用户的需求可以通过一个**专门的内部模块或功能**来处理. 如更新 Agent 的自我意识. 即便其可能需要有多个步骤来完成这件事情.

    1.4: 自我思考的反省:
        - 思考过程中包含了很多的不确定性, 不知道是否应该创建任务.
        - 判断过程过于模糊, 包含 "可能", "大概", "也许" 等想法.

2. 当预检完成之后, 我们需要考虑以下原则. 若有 **任意** 条原则满足则可创建任务:

    - 用户明确指定 **需要** 创建任务. **优先级 100**
    - 用户的需求含有 **多个步骤**: 需求有 N 个可供拆解的小步骤. **优先级 97**
    - 用户的需求含有 **工具依赖**: 需求需要**多次调用工具**，或需要将**工具调用与其他步骤组合**才能解决. **优先级 95**
    - 用户的需求含有 **复杂性**: 需求明确需要多个步骤，或需要多个功能之间的协作才能解决. **优先级 90**
    - 用户的需求含有 **时间/周期性**: 用户指定了未来的执行时间点，或任务需要长期存在、按规律重复执行. **优先级 90**

3. 当原则考虑完成后, 若还是不能确定是否需要创建. 则最终决策依然是 **不创建**.

## 思考过程示例

---
用户输入:
    创建一个任务，帮我监控"AI Agent"这个关键词的最新新闻，每天下午5点汇总一下。

THINKING
    预检 (Step 1): 开始预检。用户请求明确，非日常对话，且无法通过单次调用解决，需要定时和持续性的执行。预检通过。
    原则评估 (Step 2): 开始评估创建原则。用户在输入中明确使用了 “创建一个任务” 的字眼，这直接命中了最高优先级（100）的创建规则。同时，“每天下午5点”也命中了“时间/周期性”规则（优先级 90）。
    最终决策 (Step 4): 决策是 创建任务，调用 create_dispatch_task_tool。

---
用户输入:
    我希望你以后叫我“李总”，记住这个偏好。

THINKING
    预检 (Step 1): 开始预检。检查到规则 1.3：“用户的需求可以通过一个已存在的专门的内部模块或功能来处理. 如更新 Agent 的自我意识”。
    用户的这个请求属于更新个人偏好或档案，这应该由一个专门的内部“用户画像管理” 或 “记忆更新” 功能来处理，而不是创建一个任务。
    因此，决策为不创建任务。

---
用户输入:
    帮我把我企业日历里今天下午的会议，和我的个人待办事项清单（Trello）合并，然后识别出时间上的冲突，并用中文高亮显示出来。

THINKING
    预检 (Step 1): 开始预检。该需求非常具体，但显然无法通过单次工具调用完成，它需要从至少两个不同来源（日历工具、Trello工具）获取数据并进行后续处理。预检通过。
    原则评估 (Step 2): 开始评估创建原则。这个需求命中了多个创建原则：
        - 多个步骤 (优先级 97): 1. 获取日历数据, 2. 获取Trello数据, 3. 合并数据, 4. 分析冲突, 5. 格式化输出。
        - 工具依赖 (优先级 95): 需要调用 日历工具 和 Trello工具，并将它们的结果组合起来。
        - 复杂性 (优先级 90): 需要在不同数据源之间进行逻辑判断（冲突识别），体现了协作和复杂性。
    最终决策 (Step 4): 决策是 创建任务，调用 create_dispatch_task_tool。

## 输出格式要求

你的输出格式必须是 JSON 格式. 且包含以下字段:

{output_cls.model_description()}

## 输出示例

{output_cls.output_example()}

## 常用信息区

**当前时间: {formatted}**
"""


def get_prd_example():
    return """
# 定时参加会议任务 PRD

## 1. 背景 (Background)

在 **2025年8月7日下午2点30分**，用户“张三”通过对话向我下达指令，要求为他设置一个会议提醒。该会议对他至关重要，是关于 **Q3 产品发布会** 的最终决策会议。为确保任务被准确无误地执行，我（作为AI助理）创建此PRD作为唯一的执行依据。

## 2. 任务目标 (Objective)

在指定时间 **准时、准确** 地提醒用户“张三”参加会议，并提供必要的会议信息，确保他不会错过会议或因信息不足而准备仓促。

## 3. 任务范围与具体描述 (Scope & Description)

- **任务类型:** 一次性定时提醒任务。
- **提醒时间:** **2025年8月8日，星期五，上午 9:45** (会议开始前15分钟)。
- **提醒方式:** 通过系统桌面通知。
- **提醒内容:** 通知的标题和内容必须严格如下：
    - **标题:** ‼️ 重要会议提醒：Q3产品发布会
    - **内容:** “您好，张三。提醒您，关于‘Q3产品发布会’的最终决策会议将在15分钟后（上午10:00）开始。请提前做好准备。会议链接：https://meet.google.com/xyz-abc-pqr”

## 4. 执行计划 (Execution Plan)

1.  **解析指令:** 从本文档中解析出关键信息：执行时间 (`2025-08-08 09:45:00`) 和提醒内容（标题和正文）。
2.  **设置定时器:** 创建一个定时调度任务（Scheduler/Timer），设置在上述“提醒时间”触发。
3.  **执行提醒:** 定时器触发时，调用系统通知服务，并传入预设的“标题”和“内容”参数。
4.  **记录日志:** 任务执行后，记录一条执行日志，内容包括“任务成功触发”以及执行时间。

## 5. 验收标准 (Acceptance Criteria)

满足以下所有条件，则视为任务成功完成：

-   ✅ 通知必须在 **2025年8月8日上午9:45:00至9:45:05** 之间弹出。
-   ✅ 通知的标题必须与“提醒内容”中定义的标题 **完全一致**。
-   ✅ 通知的内容必须与“提醒内容”中定义的内容 **完全一致**。
-   ✅ 通知中的会议链接必须是可点击的，并能正确跳转。
            """

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/dispatch/router.py`

```python
import fastapi

from core.shared.models.http import ResponseModel

from ..tasks.models import TaskInCrudModel
from ..tasks.scheme import Tasks
from .models import TaskDispatchCreateModel
from . import service


controller = fastapi.APIRouter(prefix="/dispatch", tags=["Dispatch"])


@controller.post(
    path="/create-task",
    name="创建任务并使其加入调度",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskInCrudModel | str],
)
async def create_task(create_model: TaskDispatchCreateModel):
    task_or_str = await service.create_task(create_model=create_model)

    if isinstance(task_or_str, Tasks):
        return ResponseModel(result=TaskInCrudModel.model_validate(task_or_str))

    return ResponseModel(result=task_or_str)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/dispatch/service.py`

```python
import logging
from collections.abc import Sequence

from core.shared.globals import g, cacher
from core.shared.components.session import RSession
from core.shared.database.session import (
    get_async_tx_session_direct,
)

from ..tasks.scheme import Tasks
from ..tasks import service as tasks_service
from .prompt import task_analyst_instructions
from .agent import TaskAgent, TaskProxy
from .models import TaskDispatchCreateModel, TaskDispatchGeneratorInfoModel

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
        instructions=lambda *_: task_analyst_instructions(
            TaskDispatchGeneratorInfoModel
        ),
        model="gpt-4.1",
    )

    return await agent.create_task(trace_id=trace_id, create_model=create_model)


async def execute_task(task_id: int):
    """
    Coding 引导执行任务
    """
    task = await TaskProxy.create(task_id=task_id)
    g.trace_id = task.trace_id

    agent = TaskAgent.create(
        name="Task-Schedule-Agent",
        instructions="任务执行器",
        bind_task=task,
        session=RSession(session_id=str(g.trace_id), cacher=cacher),
    )

    await agent.execute()

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/dispatch/tools.py`

```python
import uuid
from typing import Any

from agents import function_tool, FunctionTool, RunContextWrapper

from core.shared.base.model import LLMTimeField, BaseModel

from . import action
from . import models


class CreateDispatchTaskFuncToolArgs(BaseModel):
    prd: str
    name: str
    expect_execute_time: LLMTimeField
    owner: str
    owner_timezone: str
    keywords: list[str]
    original_user_input: str
    trace_id: uuid.UUID


async def create_dispatch_task_tool(
    ctx: RunContextWrapper[Any], args: str
) -> dict[str, Any]:
    try:
        parsed = CreateDispatchTaskFuncToolArgs.model_validate_json(args)
        call_tool_args = {
            "expect_execute_time": parsed.expect_execute_time.get_utc_datetime(),
        }
        call_tool_args.update(parsed.model_dump(exclude={"expect_execute_time"}))

        task = await action.create_dispatch_task(**call_tool_args)  # pyright: ignore[reportArgumentType]

        return models.TaskInDispatchModel.model_validate(task).model_dump()
    except Exception as exc:
        print(exc)
        return {"error_message": str(exc)}


create_dispatch_task_tool = FunctionTool(
    name="create_dispatch_task_tool",
    description=(
        "为用户创建一个后台调度任务，用于编排和执行一个复杂的工作流。这是处理多步骤、高复杂度用户请求的首选工具。"
        "在以下情况下必须调用此工具："
        "1. 当请求需要被分解成多个顺序或并行的步骤时 (例如：先搜索，再分析，最后总结)。"
        "2. 当需要调用多个不同的工具，并将它们的结果组合起来才能满足最终需求时 (例如：查询天气，然后根据天气搜索餐厅)。"
        "3. 当用户指定了未来的执行时间或要求周期性执行时 (例如：'明晚8点提醒我' 或 '每天早上报告新闻')。"
        "4. 当请求的本质是一个需要规划和执行的长期任务时 (例如：'帮我规划一次旅行' 或 '帮我写一份市场分析报告')。"
        "注意：如果一个简单的、单一功能的工具就能直接回答用户，请不要使用此工具。"
    ),
    params_json_schema=CreateDispatchTaskFuncToolArgs.model_json_schema(),
    on_invoke_tool=create_dispatch_task_tool,
)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks/models.py`

```python
import uuid
import datetime

from pydantic import field_serializer

from core.shared.enums import TaskState
from core.shared.base.model import BaseModel

from ..tasks_chat.models import TaskChatInCrudModel
from ..tasks_history.models import TaskHistoryInCrudModel


class TaskInCrudModel(BaseModel):
    id: int
    name: str
    trace_id: uuid.UUID
    state: TaskState
    priority: int
    workspace_id: int

    expect_execute_time: datetime.datetime
    owner: str
    keywords: str
    original_user_input: str

    chats: list[TaskChatInCrudModel]
    histories: list[TaskHistoryInCrudModel]

    invocation_id: uuid.UUID | None = None
    lasted_execute_time: datetime.datetime | None = None

    @field_serializer("keywords")
    def _validator_keywords(self, keywords: str) -> list[str]:
        return keywords.split(",")


class TaskCreateModel(BaseModel):
    name: str
    workspace_id: int
    expect_execute_time: datetime.datetime
    owner: str
    owner_timezone: str
    keywords: list[str]
    original_user_input: str
    trace_id: uuid.UUID

    @field_serializer("keywords")
    def _validator_keywords(self, keywords: list[str]) -> str:
        return ",".join(keywords)


class TaskUpdateModel(BaseModel):
    name: str | None = None
    state: TaskState | None = None
    priority: int | None = None
    invocation_id: uuid.UUID | None = None

    expect_execute_time: datetime.datetime | None = None
    lasted_execute_time: datetime.datetime | None = None

    keywords: list[str] | None = None
    original_user_input: str | None = None

    @field_serializer("keywords")
    def _validator_keywords(self, keywords: list[str] | None) -> str | None:
        if keywords:
            return ",".join(keywords)
        return None

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks/repository.py`

```python
import asyncio
from typing import override, Any
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.orm import aliased, subqueryload, with_loader_criteria, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.strategy_options import _AbstractLoad  # pyright: ignore[reportPrivateUsage]
from sqlalchemy.orm.util import LoaderCriteriaOption

from core.shared.enums import TaskState
from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .models import TaskCreateModel
from .scheme import Tasks
from ..tasks_chat.scheme import TasksChat
from ..tasks_unit.scheme import TasksUnit
from ..tasks_audit.scheme import TasksAudit
from ..tasks_history.scheme import TasksHistory
from ..tasks_workspace.service import delete as workspace_delete


class TasksCrudRepository(BaseCRUDRepository[Tasks]):
    def __init__(self, session: AsyncSession):
        super().__init__(session=session)

        self.default_limit_count = 10
        self.default_joined_loads = [Tasks.chats, Tasks.histories]

    def _get_history_loader_options(
        self, limit_count: int
    ) -> list[_AbstractLoad | LoaderCriteriaOption]:
        history_alias_for_ranking = aliased(TasksHistory)
        ranked_histories_cte = (
            sa.select(
                history_alias_for_ranking.id,
                sa.func.row_number()
                .over(
                    partition_by=history_alias_for_ranking.task_id,
                    order_by=history_alias_for_ranking.created_at.desc(),
                )
                .label("rn"),
            )
            .where(history_alias_for_ranking.task_id == Tasks.id)
            .cte("ranked_histories_cte")
        )

        return [
            subqueryload(Tasks.histories),
            with_loader_criteria(
                TasksHistory,
                TasksHistory.id.in_(
                    sa.select(ranked_histories_cte.c.id).where(
                        ranked_histories_cte.c.rn <= limit_count
                    )
                ),
            ),
        ]

    def _get_chat_loader_options(
        self, limit_count: int
    ) -> list[_AbstractLoad | LoaderCriteriaOption]:
        chat_alias_for_ranking = aliased(TasksChat)
        ranked_chats_cte = (
            sa.select(
                chat_alias_for_ranking.id,
                sa.func.row_number()
                .over(
                    partition_by=chat_alias_for_ranking.task_id,
                    order_by=chat_alias_for_ranking.created_at.desc(),
                )
                .label("rn"),
            )
            .where(chat_alias_for_ranking.task_id == Tasks.id)
            .cte("ranked_chats_cte")
        )

        return [
            subqueryload(Tasks.chats),
            with_loader_criteria(
                TasksChat,
                TasksChat.id.in_(
                    sa.select(ranked_chats_cte.c.id).where(
                        ranked_chats_cte.c.rn <= limit_count
                    )
                ),
            ),
        ]

    @override
    async def create(self, create_model: TaskCreateModel) -> Tasks:
        task = await super().create(create_model=create_model)

        # 创建 task 后需要手动 load 一下 chats 和 histories.
        await self.session.refresh(task, [Tasks.chats.key, Tasks.histories.key])
        return task

    @override
    async def get(
        self, pk: int, joined_loads: list[InstrumentedAttribute[Any]] | None = None
    ) -> Tasks | None:
        extend_joined_loads = self.default_joined_loads.copy()
        extend_joined_loads.extend(joined_loads or [])

        stmt = sa.select(self.model).where(
            self.model.id == pk, sa.not_(self.model.is_deleted)
        )

        if extend_joined_loads:
            for join_field in extend_joined_loads:
                if Tasks.chats is join_field:
                    stmt = stmt.options(
                        *self._get_chat_loader_options(self.default_limit_count)
                    )
                elif Tasks.histories is join_field:
                    stmt = stmt.options(
                        *self._get_history_loader_options(self.default_limit_count)
                    )
                else:
                    stmt = stmt.options(joinedload(join_field))

        result = await self.session.execute(stmt)

        return result.unique().scalar_one_or_none()

    @override
    async def delete(self, db_obj: Tasks) -> Tasks:
        task = db_obj

        # 软删除 tasks
        task = await super().delete(db_obj)

        # 软删除其他依赖关系 ....
        workspace_delete_coroutine = workspace_delete(
            workspace_id=task.workspace_id, session=self.session
        )

        soft_delete_coroutines = [
            self.session.execute(
                sa.update(table)
                .where(
                    # 注意：这里需要检查表是否有 task_id 属性，这些表都有
                    table.task_id == task.id,
                    sa.not_(table.is_deleted),
                )
                .values(is_deleted=True, deleted_at=sa.func.now())
            )
            for table in [
                TasksChat,
                TasksUnit,
                TasksAudit,
                TasksHistory,
            ]
        ]

        await asyncio.gather(workspace_delete_coroutine, *soft_delete_coroutines)

        # 因为有事务装饰器的存在， 故这里所有的操作均为原子操作.
        await self.session.refresh(task)

        return task

    async def upget_paginator(
        self,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(sa.not_(self.model.is_deleted))
        query_stmt = query_stmt.options(
            *self._get_chat_loader_options(self.default_limit_count)
        )
        query_stmt = query_stmt.options(
            *self._get_history_loader_options(self.default_limit_count)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

    async def get_dispatch_tasks_id(self) -> Sequence[int]:
        stmt = (
            sa.select(self.model.id)
            .where(
                sa.not_(self.model.is_deleted),
                self.model.state.in_([TaskState.INITIAL, TaskState.SCHEDULING]),
                self.model.expect_execute_time < sa.func.now(),
            )
            .order_by(
                self.model.expect_execute_time.asc(),
                self.model.priority.desc(),
                self.model.created_at.asc(),
            )
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(stmt)

        tasks_id = result.scalars().unique().all()

        await self.session.execute(
            sa.update(self.model)
            .where(self.model.id.in_(tasks_id))
            .values(state=TaskState.QUEUING)
        )

        return tasks_id

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks/router.py`

```python
import fastapi
from fastapi import Depends

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)
from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service
from .models import (
    TaskInCrudModel,
    TaskCreateModel,
    TaskUpdateModel,
)


controller = fastapi.APIRouter(prefix="/tasks", tags=["tasks"], deprecated=True)


@controller.get(
    path="",
    name="获取所有 task",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_all(
    request: PaginationRequest = Depends(PaginationRequest),
    session: AsyncSession = Depends(get_async_session),
) -> PaginationResponse:
    paginator = Paginator(request=request, serializer_cls=TaskInCrudModel)
    paginator = await service.upget_paginator(paginator=paginator, session=session)
    return paginator.response


@controller.get(
    path="/{task_id}",
    name="根据 pk 获取某个 task",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskInCrudModel],
)
async def get(
    task_id: int = fastapi.Path(description="任务 ID"),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel[TaskInCrudModel]:
    db_obj = await service.get(task_id=task_id, session=session)
    return ResponseModel(result=TaskInCrudModel.model_validate(db_obj))


@controller.post(
    path="",
    name="创建 Task",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskInCrudModel],
)
async def create(
    create_model: TaskCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskInCrudModel.model_validate(db_obj))


@controller.put(
    path="/{task_id}",
    name="更新 Task",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskInCrudModel],
)
async def update(
    update_model: TaskUpdateModel,
    task_id: int = fastapi.Path(description="任务 ID"),
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskInCrudModel]:
    db_obj = await service.update(
        task_id=task_id, update_model=update_model, session=session
    )
    return ResponseModel(result=TaskInCrudModel.model_validate(db_obj))


@controller.delete(
    path="/{task_id}",
    name="删除 Task",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[bool],
)
async def delete(
    task_id: int = fastapi.Path(description="任务 ID"),
    session: AsyncTxSession = Depends(get_async_tx_session),
):
    result = await service.delete(task_id=task_id, session=session)
    return ResponseModel(result=result)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks/scheme.py`

```python
import uuid
import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.enums import TaskState
from core.shared.util.func import to_enum_values
from core.shared.base.scheme import BaseTableScheme

from ..tasks_unit.scheme import TasksUnit
from ..tasks_chat.scheme import TasksChat
from ..tasks_history.scheme import TasksHistory
from ..tasks_workspace.scheme import TasksWorkspace


class Tasks(BaseTableScheme):
    __tablename__ = "tasks"
    __table_args__ = (
        sa.Index(
            "idx_tasks_state_priority_time", "state", "priority", "expect_execute_time"
        ),
        sa.Index("idx_keywords_fulltext", "keywords", mysql_prefix="FULLTEXT"),
        {"comment": "任务表"},
    )

    name: Mapped[str] = mapped_column(
        sa.String(255), index=True, nullable=False, comment="任务的名称"
    )

    state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        default=TaskState.INITIAL,
        index=True,
        comment="任务当前状态",
        server_default=TaskState.INITIAL.value,
    )

    priority: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        index=True,
        comment="任务优先级",
        server_default=sa.text("0"),
    )

    trace_id: Mapped[uuid.UUID] = mapped_column(
        sa.CHAR(36),
        nullable=False,
        index=True,
        comment="任务建立时流转的事务 Id.",
    )

    invocation_id: Mapped[uuid.UUID] = mapped_column(
        sa.CHAR(36), nullable=True, index=True, comment="任务的调用批次 Id"
    )

    expect_execute_time: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="任务预期执行时间",
        server_default=sa.func.now(),
    )

    lasted_execute_time: Mapped[Optional[datetime.datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="任务最终执行时间",
    )

    owner: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        comment="任务所有者",
        index=True,
    )

    owner_timezone: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        default="UTC",
        comment="所有者所在时区",
        server_default=sa.text("'UTC'"),
    )

    original_user_input: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="任务原始输入",
    )

    keywords: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="关键字信息")

    workspace_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks_workspace.id"),
        nullable=False,
        index=True,
        comment="任务工作空间",
    )

    # --- 关系, 这里就是依赖的 units ..
    units: Mapped[list["TasksUnit"]] = relationship(
        "TasksUnit",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TasksUnit.created_at.desc()",
    )

    chats: Mapped[list["TasksChat"]] = relationship(
        "TasksChat",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TasksChat.created_at.desc()",
    )

    histories: Mapped[list["TasksHistory"]] = relationship(
        "TasksHistory",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TasksHistory.created_at.desc()",
    )

    workspace: Mapped["TasksWorkspace"] = relationship(back_populates="task")

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks/service.py`

```python
from collections.abc import Sequence

from core.shared.models.http import Paginator
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import Tasks
from .models import TaskCreateModel, TaskUpdateModel
from .repository import TasksCrudRepository


async def get_or_404(repo: TasksCrudRepository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务: {pk} 不存在")

    return db_obj


async def get(task_id: int, session: AsyncSession) -> Tasks:
    repo = TasksCrudRepository(session=session)
    return await get_or_404(repo=repo, pk=task_id)


async def create(create_model: TaskCreateModel, session: AsyncTxSession) -> Tasks:
    repo = TasksCrudRepository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj


async def update(
    task_id: int, update_model: TaskUpdateModel, session: AsyncTxSession
) -> Tasks:
    repo = TasksCrudRepository(session=session)
    db_obj = await get_or_404(repo=repo, pk=task_id)
    db_obj = await repo.update(db_obj, update_model=update_model)
    return db_obj


async def delete(task_id: int, session: AsyncTxSession) -> bool:
    repo = TasksCrudRepository(session=session)
    db_obj = await get_or_404(repo=repo, pk=task_id)
    db_obj = await repo.delete(db_obj=db_obj)
    return bool(db_obj.is_deleted)


async def upget_paginator(paginator: Paginator, session: AsyncSession) -> Paginator:
    repo = TasksCrudRepository(session=session)
    return await repo.upget_paginator(paginator=paginator)


async def get_dispatch_tasks_id(session: AsyncTxSession) -> Sequence[int]:
    repo = TasksCrudRepository(session=session)
    return await repo.get_dispatch_tasks_id()



```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_audit/models.py`

```python
import datetime

from core.shared.enums import TaskState, TaskAuditSource
from core.shared.base.model import BaseModel


class TaskAuditInCrudModel(BaseModel):
    from_state: TaskState
    to_state: TaskState
    source: TaskAuditSource
    source_context: str
    comment: str
    created_at: datetime.datetime


class TaskAuditCreateModel(BaseModel):
    task_id: int
    from_state: TaskState
    to_state: TaskState
    source: TaskAuditSource
    source_context: str
    comment: str

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_audit/repository.py`

```python
import sqlalchemy as sa

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .scheme import TasksAudit


class TasksAuditCrudRepository(BaseCRUDRepository[TasksAudit]):
    async def upget_paginator(
        self,
        task_id: int,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(
            self.model.task_id == task_id, sa.not_(self.model.is_deleted)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_audit/router.py`

```python
import fastapi
from fastapi import Depends

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)
from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service
from .models import (
    TaskAuditInCrudModel,
    TaskAuditCreateModel,
)


controller = fastapi.APIRouter(prefix="/audits", tags=["audits"])


@controller.get(
    path="/{task_id}",
    name="获取某个任务下的所有审计记录",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_all(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
    session: AsyncSession = Depends(get_async_session),
) -> PaginationResponse:
    paginator = Paginator(request=request, serializer_cls=TaskAuditInCrudModel)
    paginator = await service.upget_paginator(
        task_id=task_id, paginator=paginator, session=session
    )
    return paginator.response


@controller.post(
    path="",
    name="创建审计记录",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskAuditInCrudModel],
)
async def create(
    create_model: TaskAuditCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskAuditInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskAuditInCrudModel.model_validate(db_obj))

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_audit/scheme.py`

```python
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from core.shared.util.func import to_enum_values
from core.shared.base.scheme import BaseTableScheme
from core.shared.enums import TaskState, TaskAuditSource


class TasksAudit(BaseTableScheme):
    __tablename__ = "tasks_audit"
    __table_args__ = (
        sa.Index("idx_tasks_audit_task_id_created_at", "task_id", "created_at"),
        {"comment": "任务状态审计表"},
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    from_state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="任务执行状态",
    )

    to_state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="任务执行状态",
    )

    source: Mapped[TaskAuditSource] = mapped_column(
        sa.Enum(TaskAuditSource, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="触发变更的来源",
    )

    source_context: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="变更来源的上下文信息, 如 user_id, worker_id 等等 ..",
    )

    comment: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="变更上下文的注释, 为什么要变更. 变更背景是什么 ..",
    )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_audit/service.py`

```python
from core.shared.models.http import Paginator
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksAudit
from .models import TaskAuditCreateModel
from .repository import TasksAuditCrudRepository


async def get_or_404(repo: TasksAuditCrudRepository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务审计记录: {pk} 不存在")

    return db_obj


async def create(
    create_model: TaskAuditCreateModel, session: AsyncTxSession
) -> TasksAudit:
    repo = TasksAuditCrudRepository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj


async def upget_paginator(
    task_id: int, paginator: Paginator, session: AsyncSession
) -> Paginator:
    repo = TasksAuditCrudRepository(session=session)
    return await repo.upget_paginator(task_id=task_id, paginator=paginator)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_chat/models.py`

```python
import datetime

from core.shared.enums import MessageRole
from core.shared.base.model import BaseModel


class TaskChatInCrudModel(BaseModel):
    message: str
    role: MessageRole
    created_at: datetime.datetime


class TaskChatCreateModel(BaseModel):
    task_id: int
    message: str
    role: MessageRole

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_chat/repository.py`

```python
import sqlalchemy as sa

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .scheme import TasksChat


class TasksChatCrudRepository(BaseCRUDRepository[TasksChat]):
    async def upget_paginator(
        self,
        task_id: int,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(
            self.model.task_id == task_id, sa.not_(self.model.is_deleted)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_chat/router.py`

```python
import fastapi
from fastapi import Depends

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)
from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service
from .models import (
    TaskChatInCrudModel,
    TaskChatCreateModel,
)


controller = fastapi.APIRouter(
    prefix="/chats",
    tags=["chats"],
)


@controller.get(
    path="/{task_id}",
    name="获取某个任务下的所有聊天记录",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_all(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
    session: AsyncSession = Depends(get_async_session),
) -> PaginationResponse:
    paginator = Paginator(request=request, serializer_cls=TaskChatInCrudModel)
    paginator = await service.upget_paginator(
        task_id=task_id, paginator=paginator, session=session
    )
    return paginator.response


@controller.post(
    path="",
    name="创建聊天记录",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskChatInCrudModel],
)
async def create(
    create_model: TaskChatCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskChatInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskChatInCrudModel.model_validate(db_obj))

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_chat/scheme.py`

```python
import typing

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.util.func import to_enum_values
from core.shared.enums import MessageRole
from core.shared.base.scheme import BaseTableScheme

if typing.TYPE_CHECKING:
    from ..tasks.scheme import Tasks


class TasksChat(BaseTableScheme):
    __tablename__ = "tasks_chat"
    __table_args__ = (
        sa.Index("idx_tasks_chat_task_role", "task_id", "role"),
        {"comment": "任务聊天记录表"},
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    role: Mapped[MessageRole] = mapped_column(
        sa.Enum(MessageRole, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="发送消息的角色",
    )

    message: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="对话消息")

    task: Mapped["Tasks"] = relationship(
        "Tasks",
        back_populates="chats",
    )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_chat/service.py`

```python
from core.shared.models.http import Paginator
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksChat
from .models import TaskChatCreateModel
from .repository import TasksChatCrudRepository


async def get_or_404(repo: TasksChatCrudRepository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务对话记录: {pk} 不存在")

    return db_obj



async def create(
    create_model: TaskChatCreateModel, session: AsyncTxSession
) -> TasksChat:
    repo = TasksChatCrudRepository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj



async def upget_paginator(
    task_id: int, paginator: Paginator, session: AsyncSession
) -> Paginator:
    repo = TasksChatCrudRepository(session=session)
    return await repo.upget_paginator(task_id=task_id, paginator=paginator)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_history/models.py`

```python
import datetime

from core.shared.enums import TaskState
from core.shared.base.model import BaseModel


class TaskHistoryInCrudModel(BaseModel):
    state: TaskState
    process: str
    thinking: str
    created_at: datetime.datetime


class TaskHistoryCreateModel(BaseModel):
    task_id: int
    state: TaskState
    process: str
    thinking: str

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_history/repository.py`

```python
import sqlalchemy as sa

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .scheme import TasksHistory


class TasksHistoryCrudRepository(BaseCRUDRepository[TasksHistory]):
    async def upget_paginator(
        self,
        task_id: int,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(
            self.model.task_id == task_id, sa.not_(self.model.is_deleted)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_history/router.py`

```python
import fastapi
from fastapi import Depends

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)
from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service
from .models import (
    TaskHistoryInCrudModel,
    TaskHistoryCreateModel,
)


controller = fastapi.APIRouter(prefix="/histories", tags=["Histories"])


@controller.get(
    path="/{task_id}",
    name="获取某个任务下的所有执行记录",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_all(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
    session: AsyncSession = Depends(get_async_session),
) -> PaginationResponse:
    paginator = Paginator(request=request, serializer_cls=TaskHistoryInCrudModel)
    paginator = await service.upget_paginator(
        task_id=task_id, paginator=paginator, session=session
    )
    return paginator.response


@controller.post(
    path="",
    name="创建执行记录",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskHistoryInCrudModel],
)
async def create(
    create_model: TaskHistoryCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskHistoryInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskHistoryInCrudModel.model_validate(db_obj))

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_history/scheme.py`

```python
import typing

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.enums import TaskState
from core.shared.util.func import to_enum_values
from core.shared.base.scheme import BaseTableScheme

if typing.TYPE_CHECKING:
    from ..tasks.scheme import Tasks


class TasksHistory(BaseTableScheme):
    __tablename__ = "tasks_history"
    __table_args__ = (
        sa.Index("idx_tasks_history_task_state", "task_id", "state"),
        {"comment": "任务历史记录表"},
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="任务执行状态",
    )

    process: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="任务执行过程"
    )

    thinking: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="Agent 的思考过程"
    )

    task: Mapped["Tasks"] = relationship(
        "Tasks",
        back_populates="histories",
    )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_history/service.py`

```python
from core.shared.models.http import Paginator
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksHistory
from .models import TaskHistoryCreateModel
from .repository import TasksHistoryCrudRepository


async def get_or_404(repo: TasksHistoryCrudRepository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务执行记录: {pk} 不存在")

    return db_obj


async def create(
    create_model: TaskHistoryCreateModel, session: AsyncTxSession
) -> TasksHistory:
    repo = TasksHistoryCrudRepository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj


async def upget_paginator(
    task_id: int, paginator: Paginator, session: AsyncSession
) -> Paginator:
    repo = TasksHistoryCrudRepository(session=session)
    return await repo.upget_paginator(task_id=task_id, paginator=paginator)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_unit/models.py`

```python
import uuid
import datetime

from core.shared.enums import TaskUnitState
from core.shared.base.model import BaseModel


class TaskUnitInCrudModel(BaseModel):
    id: int
    name: str
    task_id: int
    objective: str
    invocation_id: uuid.UUID
    state: TaskUnitState
    output: str | None = None
    created_at: datetime.datetime


class TaskUnitCreateModel(BaseModel):
    name: str
    task_id: int
    objective: str
    invocation_id: uuid.UUID


class TaskUnitUpdateModel(BaseModel):
    state: TaskUnitState
    output: str | None = None

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_unit/repository.py`

```python
import sqlalchemy as sa

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .scheme import TasksUnit


class TasksUnitCrudRepository(BaseCRUDRepository[TasksUnit]):
    async def upget_paginator(
        self,
        task_id: int,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(
            self.model.task_id == task_id, sa.not_(self.model.is_deleted)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_unit/router.py`

```python
import fastapi
from fastapi import Depends

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)
from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service
from .models import TaskUnitInCrudModel, TaskUnitCreateModel, TaskUnitUpdateModel


controller = fastapi.APIRouter(
    prefix="/units",
    tags=["Units"],
    deprecated=True,
)


@controller.get(
    path="/{task_id}",
    name="获取某个任务下的所有执行单元",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_all(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
    session: AsyncSession = Depends(get_async_session),
) -> PaginationResponse:
    paginator = Paginator(request=request, serializer_cls=TaskUnitInCrudModel)
    paginator = await service.upget_paginator(
        task_id=task_id, paginator=paginator, session=session
    )
    return paginator.response


@controller.post(
    path="",
    name="创建执行单元",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskUnitInCrudModel],
)
async def create(
    create_model: TaskUnitCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskUnitInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskUnitInCrudModel.model_validate(db_obj))


@controller.put(
    path="/{unit_id}",
    name="更新执行单元",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskUnitInCrudModel],
)
async def update(
    update_model: TaskUnitUpdateModel,
    unit_id: int = fastapi.Path(description="主键"),
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskUnitInCrudModel]:
    db_obj = await service.update(
        unit_id=unit_id, update_model=update_model, session=session
    )
    return ResponseModel(result=TaskUnitInCrudModel.model_validate(db_obj))

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_unit/scheme.py`

```python
import uuid
import typing

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.enums import TaskUnitState
from core.shared.util.func import to_enum_values
from core.shared.base.scheme import BaseTableScheme

if typing.TYPE_CHECKING:
    from ..tasks.scheme import Tasks


class TasksUnit(BaseTableScheme):
    __tablename__ = "tasks_unit"
    __table_args__ = (
        sa.Index(
            "idx_tasks_unit_task_invocation_state",
            "task_id",
            "invocation_id",
            "state",
        ),
        {"comment": "任务执行单元表"},
    )

    name: Mapped[str] = mapped_column(
        sa.String(255), index=True, nullable=False, comment="执行单元的名称"
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    objective: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="执行单元的目标"
    )

    invocation_id: Mapped[uuid.UUID] = mapped_column(
        sa.CHAR(36), index=True, nullable=False, comment="任务的调用 ID"
    )

    state: Mapped[TaskUnitState] = mapped_column(
        sa.Enum(TaskUnitState, values_callable=to_enum_values),
        nullable=False,
        default=TaskUnitState.CREATED,
        index=True,
        comment="执行单元当前状态",
        server_default=TaskUnitState.CREATED.value,
    )

    output: Mapped[str] = mapped_column(
        sa.Text, nullable=True, comment="执行单元的产出结果"
    )

    task: Mapped["Tasks"] = relationship(
        "Tasks",
        back_populates="units",
    )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_unit/service.py`

```python
from core.shared.models.http import Paginator
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksUnit
from .models import TaskUnitCreateModel, TaskUnitUpdateModel
from .repository import TasksUnitCrudRepository


async def get_or_404(repo: TasksUnitCrudRepository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务执行单元: {pk} 不存在")

    return db_obj


async def create(
    create_model: TaskUnitCreateModel, session: AsyncTxSession
) -> TasksUnit:
    repo = TasksUnitCrudRepository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj


async def update(
    unit_id: int, update_model: TaskUnitUpdateModel, session: AsyncTxSession
) -> TasksUnit:
    repo = TasksUnitCrudRepository(session=session)
    db_obj = await get_or_404(repo=repo, pk=unit_id)
    db_obj = await repo.update(db_obj, update_model=update_model)
    return db_obj


async def upget_paginator(
    task_id: int, paginator: Paginator, session: AsyncSession
) -> Paginator:
    repo = TasksUnitCrudRepository(session=session)
    return await repo.upget_paginator(task_id=task_id, paginator=paginator)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_workspace/models.py`

```python
import datetime
from core.shared.base.model import BaseModel


class TaskWorkspaceInCrudModel(BaseModel):
    id: int
    prd: str
    process: str | None = None
    result: str | None = None
    created_at: datetime.datetime


class TaskWorkspaceCreateModel(BaseModel):
    prd: str


class TaskWorkspaceUpdateModel(BaseModel):
    process: str | None = None
    result: str | None = None

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_workspace/repository.py`

```python
from core.shared.base.repository import BaseCRUDRepository
from .scheme import TasksWorkspace


class TasksWorkspaceCrudRepository(BaseCRUDRepository[TasksWorkspace]):
    pass

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_workspace/router.py`

```python
import fastapi
from fastapi import Depends

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)
from core.shared.models.http import (
    ResponseModel,
)

from . import service
from .models import (
    TaskWorkspaceInCrudModel,
    TaskWorkspaceCreateModel,
    TaskWorkspaceUpdateModel,
)


controller = fastapi.APIRouter(
    prefix="/workspaces", tags=["Workspaces"], deprecated=True
)


@controller.get(
    path="/{workspace_id}",
    name="获取工作空间",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskWorkspaceInCrudModel],
)
async def get(
    workspace_id: int = fastapi.Path(description="主键"),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel[TaskWorkspaceInCrudModel]:
    db_obj = await service.get(workspace_id=workspace_id, session=session)
    return ResponseModel(result=TaskWorkspaceInCrudModel.model_validate(db_obj))


@controller.post(
    path="",
    name="创建工作空间",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskWorkspaceInCrudModel],
)
async def create(
    create_model: TaskWorkspaceCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskWorkspaceInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskWorkspaceInCrudModel.model_validate(db_obj))


@controller.put(
    path="/{workspace_id}",
    name="更新工作空间",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskWorkspaceInCrudModel],
)
async def update(
    update_model: TaskWorkspaceUpdateModel,
    workspace_id: int = fastapi.Path(description="主键"),
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskWorkspaceInCrudModel]:
    db_obj = await service.update(
        workspace_id=workspace_id, update_model=update_model, session=session
    )
    return ResponseModel(result=TaskWorkspaceInCrudModel.model_validate(db_obj))


@controller.delete(
    path="/{workspace_id}",
    name="删除工作空间",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[bool],
)
async def delete(
    workspace_id: int = fastapi.Path(description="主键"),
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[bool]:
    is_deleted = await service.delete(workspace_id=workspace_id, session=session)
    return ResponseModel(result=is_deleted)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_workspace/scheme.py`

```python
import typing

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.base.scheme import BaseTableScheme

if typing.TYPE_CHECKING:
    from ..tasks.scheme import Tasks


class TasksWorkspace(BaseTableScheme):
    __tablename__ = "tasks_workspace"
    __table_args__ = {"comment": "任务工作空间表"}

    prd: Mapped[str] = mapped_column(sa.TEXT, nullable=False, comment="需求 Prd.")

    process: Mapped[str] = mapped_column(
        sa.TEXT, nullable=True, comment="执行 Process."
    )

    result: Mapped[str] = mapped_column(sa.TEXT, nullable=True, comment="执行 Result.")

    task: Mapped["Tasks"] = relationship(
        back_populates="workspace",
        uselist=False,  # 表示这是一对一关系
    )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/features/tasks_workspace/service.py`

```python
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksWorkspace
from .models import TaskWorkspaceCreateModel, TaskWorkspaceUpdateModel
from .repository import TasksWorkspaceCrudRepository


async def get_or_404(repo: TasksWorkspaceCrudRepository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务工作空间: {pk} 不存在")

    return db_obj


async def get(workspace_id: int, session: AsyncSession) -> TasksWorkspace:
    repo = TasksWorkspaceCrudRepository(session=session)
    return await get_or_404(repo=repo, pk=workspace_id)


async def create(
    create_model: TaskWorkspaceCreateModel, session: AsyncTxSession
) -> TasksWorkspace:
    repo = TasksWorkspaceCrudRepository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj


async def update(
    workspace_id: int, update_model: TaskWorkspaceUpdateModel, session: AsyncTxSession
) -> TasksWorkspace:
    repo = TasksWorkspaceCrudRepository(session=session)
    db_obj = await get_or_404(repo=repo, pk=workspace_id)
    db_obj = await repo.update(db_obj, update_model=update_model)
    return db_obj


async def delete(workspace_id: int, session: AsyncTxSession) -> bool:
    repo = TasksWorkspaceCrudRepository(session=session)
    db_obj = await get_or_404(repo=repo, pk=workspace_id)
    db_obj = await repo.delete(db_obj=db_obj)
    return bool(db_obj.is_deleted)

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/handle.py`

```python
import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse

from core.shared.models.http import ResponseModel
from core.shared.exceptions import (
    ServiceNotFoundException,
    ServiceMissMessageException,
)


async def service_exception_handler(request: Request, exc: Exception):
    status_code = fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR
    message = str(exc)

    if isinstance(exc, ServiceNotFoundException):
        status_code = fastapi.status.HTTP_404_NOT_FOUND
    if isinstance(exc, ServiceMissMessageException):
        status_code = fastapi.status.HTTP_400_BAD_REQUEST

    return JSONResponse(
        status_code=status_code,
        content=ResponseModel(
            code=status_code,
            message=message,
            is_failed=True,
            result=None,
        ).model_dump(by_alias=True),
    )


async def exception_handler(request: Request, exc: Exception):
    status_code = fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR
    message = str(exc)

    return JSONResponse(
        status_code=status_code,
        content=ResponseModel(
            code=status_code,
            message=message,
            is_failed=True,
            result=None,
        ).model_dump(by_alias=True),
    )

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/logger.py`

```python
import sys
import logging
from typing import override

from colorlog import ColoredFormatter

from core.shared.globals import g


class Formatter(ColoredFormatter):
    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        super_time = super().formatTime(record, datefmt)
        return f"{super_time}.{int(record.msecs):03d}"

    @override
    def format(self, record: logging.LogRecord) -> str:
        record.space = " "
        record.trace_id = g.get("trace_id", "X-Trace-ID")

        record.timestamp = self.formatTime(record, self.datefmt)
        return super().format(record)


formatter = (
    "%(log_color)s%(levelname)s%(reset)s:"
    "%(white)s%(space)-5s%(reset)s"
    "[%(light_green)s%(timestamp)s%(reset)s] "
    "[%(light_blue)s%(name)s%(reset)s] - "
    "[%(light_yellow)s%(funcName)s:%(lineno)s]%(reset)s - "
    "[%(cyan)s%(trace_id)s%(reset)s] "
    "%(bold_white)s%(message)s%(reset)s"
)

console_formatter = Formatter(
    formatter,
    reset=True,
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
    datefmt="%Y-%m-%d %H:%M:%S",
    secondary_log_colors={},
    style="%",
)


def setup_logging(level: int | str = logging.INFO) -> None:
    root_logger = logging.getLogger()

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    root_logger.addHandler(console_handler)

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_errors_logger = logging.getLogger("uvicorn.error")

    uvicorn_errors_logger.handlers.clear()
    uvicorn_access_logger.handlers.clear()

    uvicorn_errors_logger.propagate = True
    uvicorn_access_logger.propagate = False

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/router.py`

```python
import fastapi

from core.features.dispatch.router import controller as dispatch_controller

from core.features.tasks.router import controller as tasks_controller
from core.features.tasks_unit.router import controller as units_controller
from core.features.tasks_chat.router import controller as chats_controller
from core.features.tasks_audit.router import controller as audits_controller
from core.features.tasks_history.router import controller as histories_controller
from core.features.tasks_workspace.router import controller as workspaces_controller


api_router = fastapi.APIRouter()


api_router.include_router(dispatch_controller)

api_router.include_router(tasks_controller)
api_router.include_router(units_controller)
api_router.include_router(chats_controller)
api_router.include_router(audits_controller)
api_router.include_router(histories_controller)
api_router.include_router(workspaces_controller)


```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/schemes.py`

```python
from core.features.tasks.scheme import Tasks
from core.features.tasks_unit.scheme import TasksUnit
from core.features.tasks_chat.scheme import TasksChat
from core.features.tasks_audit.scheme import TasksAudit
from core.features.tasks_history.scheme import TasksHistory
from core.features.tasks_workspace.scheme import TasksWorkspace

__all__ = [
    "Tasks",
    "TasksUnit",
    "TasksChat",
    "TasksAudit",
    "TasksHistory",
    "TasksWorkspace",
]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/__init__.py`

```python

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/base/model.py`

```python
import json
import inspect
import datetime
from typing import get_origin, get_args, Union, Any, TypeVar

import pytz
import pydantic
from pydantic import Field
from pydantic.alias_generators import to_camel


T = TypeVar("T")

model_config = pydantic.ConfigDict(
    # 自动将 snake_case 字段名生成 camelCase 别名，用于 JSON 输出
    alias_generator=to_camel,
    # 允许在创建模型时使用别名（如 'taskId'）
    populate_by_name=True,
    # 允许从 ORM 对象等直接转换
    from_attributes=True,
    # 允许任意类型作为字段
    arbitrary_types_allowed=True,
    # 统一处理所有 datetime 对象的 JSON 序列化格式
    json_encoders={datetime.datetime: lambda dt: dt.isoformat().replace("+00:00", "Z")},
)


class BaseModel(pydantic.BaseModel):
    model_config = model_config

    @pydantic.model_validator(mode="after")
    def set_naive_datetime_to_utc(self) -> "BaseModel":
        """
        遍历模型中的所有字段，如果字段是天真的 datetime 对象，
        则将其时区设置为 UTC。
        """
        for field_name, value in self.__dict__.items():
            if isinstance(value, datetime.datetime):
                if value.tzinfo is None:
                    aware_value = value.replace(tzinfo=datetime.timezone.utc)
                    setattr(self, field_name, aware_value)
        return self

    def pretty_json(self):
        return self.model_dump_json(indent=2)


class LLMInputModel(BaseModel):
    def model_dump_markdown(self) -> str:
        md = f"```json\n{self.model_dump_json(indent=2)}\n```\n"

        return md


class LLMTimeField(BaseModel):
    """
    大模型输出时的时间字段.
    """

    year: int = Field(
        description="The year of task execution, a 4-digit number", examples=[2025]
    )
    month: int = Field(
        description="The month of task execution, a number from 1-12", examples=[8]
    )
    day: int = Field(
        description="The specific day of task execution, a number from 1-31",
        examples=[7],
    )
    hour: int = Field(
        description="The specific hour of task execution, a number from 1-24",
        examples=[14],
    )
    min: int = Field(
        description="The specific minute of task execution, a number from 1-60",
        examples=[30],
    )

    def get_utc_datetime(self, from_timezone: str = "UTC") -> datetime.datetime:
        return (
            pytz.timezone(from_timezone)
            .localize(
                datetime.datetime(self.year, self.month, self.day, self.hour, self.min)
            )
            .astimezone(pytz.utc)
        )


class LLMOutputModel(BaseModel):
    thinking: str = Field(description="思考过程", examples=["The user's request is..."])

    @classmethod
    def output_example(cls) -> str:
        """
        Generates a representative JSON example string from the model's fields,
        using the 'examples' provided in each Field.
        """
        example_dict = cls._build_example_dict(model_cls=cls)
        # Use ensure_ascii=False to correctly handle non-ASCII characters like Chinese
        return json.dumps(example_dict, indent=2, ensure_ascii=False)

    # --- NEW: Recursive helper to build the example dictionary ---
    @classmethod
    def _build_example_dict(cls, model_cls: type[BaseModel]) -> dict[str, Any]:
        """
        (Helper) Recursively builds a dictionary from field examples.
        """
        example_data: Any = {}
        for name, field in model_cls.model_fields.items():
            field_type = field.annotation

            # 1. Check if the field contains a nested model for recursion
            sub_model_to_build = cls._extract_model_for_recursion(field_type)

            if sub_model_to_build:
                # We found a nested model. Now, check if it was in a list.
                origin = get_origin(field_type)
                if origin and issubclass(origin, list):
                    # Case: list[MyModel] -> build an example and wrap it in a list
                    example_data[name] = [
                        cls._build_example_dict(model_cls=sub_model_to_build)
                    ]
                else:
                    # Case: MyModel or Union[MyModel, None] -> build a nested example
                    example_data[name] = cls._build_example_dict(
                        model_cls=sub_model_to_build
                    )
                continue  # Move to the next field

            # 2. If not a nested model, it's a simple field. Use its example.
            if field.examples:
                example_data[name] = field.examples[0]
            else:
                # Fallback if no example is provided for a simple field
                type_name = cls._format_type(field_type)
                example_data[name] = f"({type_name} example)"

        return example_data

    @classmethod
    def model_description(cls) -> str:
        return "\n".join(cls._build_lines(model=cls))

    @classmethod
    def _build_lines(cls, model: type[BaseModel], indent_level: int = 0) -> list[str]:
        lines: list[str] = []
        indent_str = "    " * indent_level
        for name, field in model.model_fields.items():
            description = field.description or "No description"
            type_str = cls._format_type(field.annotation)
            lines.append(f"{indent_str}{name} [<{type_str}>]: {description}")
            if sub_model := cls._extract_model_for_recursion(field.annotation):
                lines.extend(
                    cls._build_lines(model=sub_model, indent_level=indent_level + 1)
                )
        return lines

    @classmethod
    def _format_type(cls, tp: Any) -> str:
        if origin := get_origin(tp):
            args = get_args(tp)
            if origin is Union:
                return " | ".join(
                    cls._format_type(arg) for arg in args if arg is not type(None)
                )
            if issubclass(origin, list):
                return f"list[{cls._format_type(args[0]) if args else 'Any'}]"
            if issubclass(origin, dict):
                key_type = cls._format_type(args[0]) if args else "Any"
                val_type = cls._format_type(args[1]) if len(args) > 1 else "Any"
                return f"dict[{key_type}, {val_type}]"
            arg_str = ", ".join(cls._format_type(arg) for arg in args)
            return f"{origin.__name__}[{arg_str}]"
        return getattr(tp, "__name__", str(tp))

    @classmethod
    def _extract_model_for_recursion(cls, tp: Any) -> type[BaseModel] | None:
        if origin := get_origin(tp):
            if origin is Union:
                for arg in get_args(tp):
                    if model := cls._extract_model_for_recursion(arg):
                        return model
                return None
            if issubclass(origin, list):
                args = get_args(tp)
                tp = args[0] if args else None
        if inspect.isclass(tp) and issubclass(tp, BaseModel):
            return tp
        return None

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/base/repository.py`

```python
import typing
from typing import Any, Generic, TypeVar
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.asyncio import AsyncSession

from .scheme import BaseTableScheme
from .types import ModelDumpProtocol
from core.shared.models.http import Paginator

ModelType = TypeVar("ModelType", bound=BaseTableScheme)


class BaseCRUDRepository(Generic[ModelType]):
    """
    基本的 Crud Repository. 将自动提供 get/get_all/create/delete 等方法.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.model: type[ModelType] = typing.get_args(self.__class__.__orig_bases__[0])[  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            0
        ]

    async def exists(self, pk: int) -> bool:
        exists_stmt = (
            sa.select(self.model.id)
            .where(self.model.id == pk, sa.not_(self.model.is_deleted))
            .exists()
        )

        stmt = sa.select(sa.literal(True)).where(exists_stmt)

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none() is not None

    async def get(
        self, pk: int, joined_loads: list[InstrumentedAttribute[Any]] | None = None
    ) -> ModelType | None:
        """根据主键 ID 获取单个对象"""
        stmt = sa.select(self.model).where(
            self.model.id == pk, sa.not_(self.model.is_deleted)
        )

        if joined_loads:
            for join_field in joined_loads:
                stmt = stmt.options(joinedload(join_field))

        result = await self.session.execute(stmt)

        return result.unique().scalar_one_or_none()

    async def get_all(
        self, joined_loads: list[InstrumentedAttribute[Any]] | None = None
    ) -> Sequence[ModelType]:
        """获取所有未被软删除的对象"""
        stmt = sa.select(self.model).where(sa.not_(self.model.is_deleted))

        if joined_loads:
            for join_field in joined_loads:
                stmt = stmt.options(joinedload(join_field))

        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def create(self, create_model: Any) -> ModelType:
        """创建一个新对象"""
        assert isinstance(create_model, ModelDumpProtocol)
        db_obj = self.model(**create_model.model_dump())
        self.session.add(db_obj)
        await self.session.flush()

        return db_obj

    async def delete(self, db_obj: ModelType) -> ModelType:
        """软删除一个现有对象"""
        db_obj.is_deleted = True

        self.session.add(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, update_model: Any) -> ModelType:
        """更新一个已有的对象"""
        assert isinstance(update_model, ModelDumpProtocol)
        update_info = update_model.model_dump(exclude_unset=True)
        for key, value in update_info.items():
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        return db_obj

    async def upget_paginator_by_self(
        self,
        paginator: Paginator,
        joined_loads: list[InstrumentedAttribute[Any]] | None = None,
    ) -> Paginator:
        """
        更新返回默认的分页器.
        """
        stmt = sa.select(self.model).where(sa.not_(self.model.is_deleted))

        if joined_loads:
            for join_field in joined_loads:
                stmt = stmt.options(joinedload(join_field))

        return await self.upget_paginator_by_stmt(
            paginator=paginator,
            stmt=stmt,
        )

    async def upget_paginator_by_stmt(
        self,
        paginator: Paginator,
        stmt: sa.Select[Any],
    ) -> Paginator:
        """
        执行 stmt 语句. 更新返回分页器.
        """

        # 应用排序逻辑
        for field_name, order_direction in paginator.request.order_by_rule:
            if not hasattr(self.model, field_name):
                raise ValueError(
                    f"{self.model.__name__} is not has field'{field_name}'"
                )
            order_func = sa.asc if order_direction == "asc" else sa.desc
            stmt = stmt.order_by(order_func(getattr(self.model, field_name)))

        # 计算总记录数
        count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        total_items_result = await self.session.execute(count_stmt)

        # 应用分页逻辑
        paginated_stmt = stmt.offset(
            (paginator.request.page - 1) * paginator.request.size
        ).limit(paginator.request.size)

        result = await self.session.execute(paginated_stmt)

        paginator.with_serializer_response(
            total_counts=total_items_result.scalar_one(),
            orm_sequence=result.scalars().unique().all(),
        )

        return paginator

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/base/scheme.py`

```python
from typing import Any
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Mapped, Mapper, mapped_column
from sqlalchemy.orm.attributes import get_history


class BaseTableScheme(DeclarativeBase):
    __abstract__ = True
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        index=True,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa.func.now(),
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        index=True,
        nullable=True,
        onupdate=sa.func.now(),
        server_onupdate=sa.func.now(),
        comment="更新时间",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        comment="删除时间",
    )

    is_deleted: Mapped[bool] = mapped_column(
        sa.Boolean,
        index=True,
        default=False,
        server_default=sa.text("0"),
        nullable=False,
        comment="0：未删除 1：已删除",
    )

    @classmethod
    def __table_cls__(
        cls, table_name: str, metadata: sa.MetaData, *args: Any, **kwargs: Any
    ):
        # 在生成 table 时, 必须确保 ID 排在第一个
        columns = sorted(
            args,
            key=lambda field: 0
            if (isinstance(field, sa.Column) and field.name == "id")
            else 1,
        )
        return sa.Table(table_name, metadata, *columns, **kwargs)


@event.listens_for(BaseTableScheme, "before_update", propagate=True)
def set_deleted_at_on_soft_delete(
    mapper: Mapper[Any], connection: Connection, obj: BaseTableScheme
) -> None:
    """
    当 is_deleted 变更时，自动设置 deleted_at 字段。
    """
    history = get_history(obj, "is_deleted")

    if (
        history.added
        and history.added[0] is True
        and history.deleted
        and history.deleted[0] is False
    ):
        obj.deleted_at = datetime.now(timezone.utc)
    elif (
        history.added
        and history.added[0] is False
        and history.deleted
        and history.deleted[0] is True
    ):
        obj.deleted_at = None

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/base/types.py`

```python
from typing import TypeVar, ParamSpec, Protocol, Any, runtime_checkable

P = ParamSpec("P")
R = TypeVar("R")


@runtime_checkable
class ModelDumpProtocol(Protocol):
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/components/__init__.py`

```python
from .broker import RBroker
from .cacher import RCacher

__all__ = ["RBroker", "RCacher"]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/components/agent.py`

```python
from collections.abc import Callable
from typing import Any

from agents import (
    Agent as BasicAgent,
    Model,
    ModelSettings,
    RunContextWrapper,
    Runner,
    TContext,
)
from agents.agent_output import AgentOutputSchemaBase
from agents.items import TResponseInputItem
from agents.result import RunResult, RunResultStreaming
from agents.util._types import MaybeAwaitable

from core.shared.base.model import LLMInputModel, LLMOutputModel
from .session import RSession


class Agent:
    """
    基于 openai-agents 封装的 Agent.

    - 支持 Agent 多轮会话 session (每次会话用不同的 session 或统一用 Agent 创建时的 session 实现关联对话).
    - 支持 Agent 每次 run 的时候生成不同的结构化对象.
    """

    def __init__(
        self,
        name: str,
        instructions: (
            str
            | Callable[
                [RunContextWrapper[TContext], BasicAgent[TContext]],
                MaybeAwaitable[str],
            ]
            | None
        ) = None,
        model: Model | None | str = None,
        session: RSession | None = None,
        **kwargs: Any,
    ):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.session = session

        self.agent = BasicAgent(
            name=self.name,
            instructions=self.instructions,
            model=self.model,
            **kwargs,
        )

    def run_streamed(
        self,
        input: str | list[TResponseInputItem],
        session: RSession | None = None,
        output_type: type[LLMInputModel] | AgentOutputSchemaBase | None = None,
        **kwargs: Any,
    ) -> RunResultStreaming:
        agent = self.agent.clone(output_type=output_type, **kwargs)
        return Runner.run_streamed(agent, input=input, session=session or self.session)

    async def run(
        self,
        input: str | list[TResponseInputItem],
        session: RSession | None = None,
        output_type: type[LLMOutputModel] | AgentOutputSchemaBase | None = None,
        **kwargs: Any,
    ) -> RunResult:
        agent = self.agent.clone(output_type=output_type, **kwargs)
        run_result = await Runner.run(
            agent,
            input=input,
            session=session or self.session,
        )
        return run_result

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/components/broker.py`

```python
import logging
import asyncio
from typing import Any, TypeAlias
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone

import redis.asyncio as redis
from redis.typing import FieldT, EncodableT
from redis.exceptions import ResponseError
from pydantic import BaseModel, Field

RbrokerMessage: TypeAlias = Any


class RbrokerPayloadMetadata(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RbrokerPayloadExcInfo(BaseModel):
    message: str
    type: str
    failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RbrokerPayload(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
    content: RbrokerMessage
    exc_info: RbrokerPayloadExcInfo | None = Field(default=None)


class RBroker:
    """
    基于 Redis Streams 实现的发布订阅系统
    """

    def __init__(self, redis_client: redis.Redis):
        self._client = redis_client
        self._consumer_tasks: list[asyncio.Task[None]] = []
        self._dlq_maxlen = 1000

    async def _handle_callback_ack(
        self,
        topic: str,
        group_id: str,
        message_id: str,
        rbroker_message: RbrokerPayload,
        callback: Callable[[RbrokerMessage], Coroutine[Any, Any, None]],
    ):
        try:
            await callback(rbroker_message.content)
        except Exception as exc:
            rbroker_message.exc_info = RbrokerPayloadExcInfo(
                message=str(exc), type=exc.__class__.__name__
            )
            # 放入死信队列. 后续可通过消费该死信队列获得新的讯息
            await self._client.xadd(
                f"{topic}-dlq",
                {"message": rbroker_message.model_dump_json()},
                maxlen=self._dlq_maxlen,
            )
            logging.error(
                f"Error in background task for message {message_id}: {exc}",
                exc_info=True,
            )
        finally:
            await self._client.xack(topic, group_id, message_id)

    async def _consume_worker(
        self,
        topic: str,
        group_id: str,
        consumer_name: str,
        callback: Callable[[RbrokerMessage], Coroutine[Any, Any, None]],
    ):
        while True:
            try:
                # xreadgroup 会阻塞，但只会阻塞当前这一个任务，不会影响其他任务
                # block 0 一直阻塞
                response = await self._client.xreadgroup(
                    group_id, consumer_name, {topic: ">"}, count=1, block=0
                )
                if not response:
                    continue

                stream_key, messages = response[0]
                message_id, data = messages[0]

                try:
                    rbroker_message = RbrokerPayload.model_validate_json(
                        data["message"]
                    )

                    asyncio.create_task(
                        self._handle_callback_ack(
                            topic=topic,
                            group_id=group_id,
                            message_id=message_id,
                            rbroker_message=rbroker_message,
                            callback=callback,
                        )
                    )

                except Exception as e:
                    logging.error(
                        f"Error processing message {message_id.decode()}: {e}",
                        exc_info=True,
                    )

            except asyncio.CancelledError:
                logging.info(f"Consumer '{consumer_name}' is shutting down.")
                break

            except Exception as e:
                logging.error(
                    f"Consumer '{consumer_name}' loop error: {e}", exc_info=True
                )
                await asyncio.sleep(5)

    async def send(self, topic: str, message: RbrokerMessage) -> str:
        rbroker_message = RbrokerPayload(content=message)

        message_payload: dict[FieldT, EncodableT] = {
            "message": rbroker_message.model_dump_json()
        }
        message_id = await self._client.xadd(topic, message_payload)
        return message_id

    async def consumer(
        self,
        topic: str,
        callback: Callable[[RbrokerMessage], Coroutine[Any, Any, None]],
        group_id: str | None = None,
        count: int = 1,
        *args: Any,
        **kwargs: Any,
    ):
        """
        创建并启动消费者后台任务。
        """
        group_id = group_id or topic + "_group"

        try:
            await self._client.xgroup_create(topic, group_id, mkstream=True)
            logging.info(f"Consumer group '{group_id}' created for topic '{topic}'.")
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        for i in range(count):
            consumer_name = f"{group_id}-consumer-{i + 1}"
            task = asyncio.create_task(
                self._consume_worker(topic, group_id, consumer_name, callback)
            )
            self._consumer_tasks.append(task)

    async def shutdown(self):
        logging.info("Shutting down consumer tasks...")

        for task in self._consumer_tasks:
            task.cancel()

        await asyncio.gather(*self._consumer_tasks, return_exceptions=True)
        logging.info("All consumer tasks have been shut down.")

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/components/cacher.py`

```python
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

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/components/session.py`

```python
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

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/database/connection.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config import env_helper


engine = create_async_engine(
    env_helper.ASYNC_DB_URL,
    # echo=True,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,  # 明确指定使用 AsyncSession
)

__all__ = ["engine", "AsyncSessionLocal"]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/database/redis.py`

```python
import redis.asyncio as redis

from core.config import env_helper


pool: redis.ConnectionPool = redis.ConnectionPool.from_url(  # pyright: ignore[reportUnknownMemberType]
    url=env_helper.ASYNC_REDIS_URL, decode_responses=True
)

client = redis.Redis(connection_pool=pool)

__all__ = ["pool", "client"]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/database/session.py`

```python
from typing import TypeAlias
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from .connection import engine, AsyncSessionLocal

AsyncTxSession: TypeAlias = AsyncSession


async def get_async_session():
    async with AsyncSessionLocal(bind=engine) as session:
        yield session


async def get_async_tx_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            raise exc


get_async_session_direct = asynccontextmanager(get_async_session)
get_async_tx_session_direct = asynccontextmanager(get_async_tx_session)

__all__ = [
    "get_async_session",
    "get_async_tx_session",
    "get_async_session_direct",
    "get_async_tx_session_direct",
    "AsyncSession",
    "AsyncTxSession",
]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/dependencies.py`

```python
from fastapi import Header

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)



async def global_headers(
    x_trace_id: str | None = Header(
        default=None,
        alias="X-Trace-Id",
        description="用于分布式追踪的唯一 ID. 若未提供. 则 Taxonsk 将自动生成一个 uuid.",
    ),
):
    pass


__all__ = [
    "get_async_session",
    "get_async_tx_session",
    "AsyncSession",
    "AsyncTxSession",
    "global_headers",
]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/enums.py`

```python
from enum import StrEnum


class TaskState(StrEnum):
    # 任务建立状态
    INITIAL = "initial"
    # 任务进入队列
    QUEUING = "enqueued"
    # 任务正在执行
    ACTIVATING = "activating"
    # 任务等待用户输入
    WAITING = "waiting"
    # 任务等待调度
    SCHEDULING = "scheduled"
    # 任务已经完成
    FINISHED = "finished"
    # 任务已经失败
    FAILED = "failed"
    # 任务已被取消
    CANCELLED = "cancelled"
    # 用户已更新任务
    UPDATING = "updating"


class TaskUnitState(StrEnum):
    # 执行单元创建
    CREATED = "CREATED"
    # 执行单元运行
    RUNNING = "RUNNING"
    # 执行单元完成
    COMPLETE = "COMPLETE"
    # 执行单元取消
    CANCELLED = "CANCELLED"


class MessageRole(StrEnum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class TaskAuditSource(StrEnum):
    """
    触发任务状态变更的“来源”枚举
    """

    USER = "user"
    ADMIN = "admin"
    AGENT = "agent"
    SYSTEM = "system"

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/exceptions.py`

```python
class ServiceException(Exception):
    """服务层异常"""
    pass


class ServiceNotFoundException(ServiceException):
    """未找到记录"""
    pass


class ServiceMissMessageException(ServiceException):
    """缺少信息"""
    pass

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/globals.py`

```python
from core.shared.middleware.context import g
from core.shared.database.redis import client
from core.shared.components import RBroker, RCacher

broker = RBroker(client)
cacher = RCacher(client)

__all__ = ["g", "broker", "cacher"]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/middleware/__init__.py`

```python
from .context import GlobalContextMiddleware
from .monitor import GlobalMonitorMiddleware

__all__ = ["GlobalContextMiddleware", "GlobalMonitorMiddleware"]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/middleware/context.py`

```python
from typing import Any, override
from contextvars import ContextVar, copy_context
from dataclasses import dataclass

from starlette.types import ASGIApp, Receive, Scope, Send


class GlobalContextException(Exception):
    pass


@dataclass
class Globals:
    _context_data = ContextVar("context_data", default={})

    def clear(self) -> None:
        self._context_data.set({})

    def get(self, name: str, default: Any = None) -> Any:
        return self._context_data.get().get(name, default)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._context_data.get()[name]
        except KeyError:
            raise GlobalContextException(f"'{name}' is not found from global context.")

    @override
    def __setattr__(self, name: str, value: Any) -> None:
        self._context_data.get()[name] = value


class GlobalContextMiddleware:
    """
    ASGI 层面的中间件. 旨在提供类似于 Flask 的 g 对象.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ctx = copy_context()
        await ctx.run(self.app, scope, receive, send)


g = Globals()

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/middleware/monitor.py`

```python
import time
import json
import logging
import typing
from typing import override

from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
    _StreamingResponse,  # pyright: ignore[reportPrivateUsage]
)
from starlette.types import Message


logger = logging.getLogger("middleware-monitor")


class GlobalMonitorMiddleware(BaseHTTPMiddleware):
    FILTER_API_PATH = ["/", "/docs", "/openapi.json", "/heart"]
    CONTENT_TYPE_PREFIXES = ["application/json", "text/"]
    MAX_BODY_LOG_LENGTH = 500

    def get_request_info(self, request: Request) -> str:
        method = request.method
        path = request.url.path
        query = request.url.query
        http_version = request.scope.get("http_version", "unknown")
        full_path = f"{path}?{query}" if query else path
        return f"{method} {full_path} HTTP/{http_version}"

    def get_body_log(self, body: bytes) -> str:
        if not body:
            return ""

        try:
            parsed = json.loads(body)
            return f", JSON: {json.dumps(parsed, ensure_ascii=False)}"
        except json.JSONDecodeError:
            decoded = body.decode(errors="ignore")
            return f", (Non-JSON): {decoded[: self.MAX_BODY_LOG_LENGTH]}{'...' if len(decoded) > self.MAX_BODY_LOG_LENGTH else ''}"

    async def get_response_body(self, response: _StreamingResponse) -> bytes:
        response_body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            response_body_chunks.append(typing.cast("bytes", chunk))
        return b"".join(response_body_chunks)

    @override
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.FILTER_API_PATH:
            return await call_next(request)

        request_info = self.get_request_info(request)

        request_body = await request.body()

        async def receive() -> Message:
            return {"type": "http.request", "body": request_body, "more_body": False}

        request_log = self.get_body_log(request_body)
        logger.info(f"Request: '{request_info}'{request_log}")

        # Create a safe-to-read request
        new_request = Request(request.scope, receive)

        start_time = time.perf_counter()
        response: _StreamingResponse = await call_next(new_request)
        duration = (time.perf_counter() - start_time) * 1000
        status_code = response.status_code

        content_type = response.headers.get("content-type", "")

        if any(content_type.startswith(t) for t in self.CONTENT_TYPE_PREFIXES):
            response_body = await self.get_response_body(response)
            response_log = self.get_body_log(response_body)

            logger.info(
                f"Response: '{request_info} {status_code}' ({duration:.2f}ms){response_log}"
            )

            return Response(
                content=response_body,
                status_code=status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        logger.info(f"Response: '{request_info} {status_code}' ({duration:.2f}ms)")
        return response

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/models/__init__.py`

```python

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/models/http.py`

```python
import re
from typing import Generic, Literal, Any, TypeAlias
from collections.abc import Sequence

import pydantic
from pydantic import Field, computed_field
from pydantic.alias_generators import to_snake

from core.shared.base.model import BaseModel, T


class BaseHttpResponseModel(BaseModel):
    """
    为 Taxonsk API 设计的、标准化的泛型响应模型。
    """

    code: int = Field(default=200, description="状态码")
    message: str = Field(default="Success", description="响应消息")
    is_failed: bool = Field(default=False, description="是否失败")


class ResponseModel(BaseHttpResponseModel, Generic[T]):
    result: T | None = Field(default=None, description="响应体负载")


PaginationSerializer: TypeAlias = BaseModel


class PaginationRequest(BaseModel):
    """
    分页请求对象
    """

    page: int = Field(default=1, ge=1, description="页码, 从 1 开始")
    size: int = Field(
        default=10, ge=1, le=100, description="单页数量, 最小 1, 最大 100"
    )
    order_by: str | None = Field(
        default=None,
        description="排序字段/方向, 默认按照 id 进行 DESC 排序.",
        examples=["id=asc,createAt=desc", "id"],
    )

    @computed_field
    @property
    def order_by_rule(self) -> list[tuple[str, Literal["asc", "desc"]]]:
        order_by = self.order_by or "id=desc"

        _order_by = [item.strip() for item in order_by.split(",") if item.strip()]
        _struct_order_by: list[tuple[str, Literal["asc", "desc"]]] = []

        for item in _order_by:
            match = re.match(r"([\w_]+)(=(asc|desc))?", item, re.IGNORECASE)
            if match:
                field_name = to_snake(match.group(1))
                order_direction = match.group(3)
                direction: Literal["asc", "desc"] = "desc"
                if order_direction and order_direction.lower() == "asc":
                    direction = "asc"
                _struct_order_by.append((field_name, direction))
            else:
                raise pydantic.ValidationError(f"Invalid order_by format: {item}")

        return _struct_order_by


class PaginationResponse(BaseHttpResponseModel):
    """
    分页响应对象
    """

    current_page: int = Field(default=0, description="当前页")
    current_size: int = Field(default=0, description="当前数")
    total_counts: int = Field(default=0, description="总记录数")
    result: list[Any] = Field(default_factory=list, description="所有记录对象")

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.current_size == 0:
            return 0
        return (self.total_counts + self.current_size - 1) // self.current_size


class Paginator(
    BaseModel,
):
    """
    分页器对象
    """

    serializer_cls: type[PaginationSerializer]
    request: PaginationRequest
    response: PaginationResponse = Field(
        default_factory=PaginationResponse, description="分页响应对象"
    )

    def with_serializer_response(
        self, total_counts: int, orm_sequence: Sequence[Any]
    ) -> None:
        self.response.current_page = self.request.page
        self.response.current_size = self.request.size
        self.response.total_counts = total_counts

        self.response.result = [
            self.serializer_cls.model_validate(obj) for obj in orm_sequence
        ]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/core/shared/util/func.py`

```python
from enum import StrEnum


def to_enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [e.value for e in enum_class]

```

## `/Users/askfiy/project/coding/agent-scheduler-system/main.py`

```python
import uuid
import logging
from contextlib import asynccontextmanager
from collections.abc import Awaitable, Callable

import uvicorn
import fastapi
from fastapi import Request, Response, Depends

from core.router import api_router
from core.logger import setup_logging
from core.handle import exception_handler, service_exception_handler
from core.shared.globals import g
from core.shared.exceptions import ServiceException
from core.shared.dependencies import global_headers
from core.shared.middleware import GlobalContextMiddleware, GlobalMonitorMiddleware
from core.features.dispatch import Dispatch

name = "Agent-Scheduler-System"

logger = logging.getLogger(name)


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    setup_logging()

    await Dispatch.start()
    yield
    await Dispatch.shutdown()


app = fastapi.FastAPI(
    title=name,
    lifespan=lifespan,
    dependencies=[Depends(global_headers)],
)

app.add_middleware(GlobalContextMiddleware)
app.add_middleware(GlobalMonitorMiddleware)
app.add_exception_handler(Exception, exception_handler)
app.add_exception_handler(ServiceException, service_exception_handler)


@app.middleware("http")
async def g_trace(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    g.trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Trace-Id"] = g.trace_id
    return response


@app.get(
    path="/heart",
    name="心跳检测",
    status_code=fastapi.status.HTTP_200_OK,
)
async def heart():
    return {"success": True}


app.include_router(api_router, prefix="/api/v1")


def main():
    uvicorn.run(app="main:app", host="0.0.0.0", port=9091)


if __name__ == "__main__":
    main()

```

## `/Users/askfiy/project/coding/agent-scheduler-system/makefile`

```
# Makefile for agent-schedule-system Project

# --- Variables ---
# Default environment is 'local' if not specified.
# Usage: make serve ENV="test"
ENV ?= local

# Default migration message if not specified.
# Usage: make db-generate M="your message"
M ?= "new migration"

# --- Phony Targets ---
# .PHONY declares targets that are not files.
.PHONY: all help serve db-generate db-upgrade

all: help

help:
	@echo "Usage: make <command> [OPTIONS]"
	@echo ""
	@echo "Commands:"
	@echo "  serve          Start the application server on 0.0.0.0:9091 (default ENV=local)."
	@echo "  db-generate    Generate a new database migration file."
	@echo "  db-upgrade     Upgrade the database to the latest version."
	@echo ""
	@echo "Options:"
	@echo "  ENV=<env>      Specify the environment (e.g., local, test, production). Default: local."
	@echo "  M=<message>    Specify the migration message for db-generate."
	@echo ""
	@echo "Examples:"
	@echo "  make serve"
	@echo "  make serve ENV=test"
	@echo "  make db-generate M=\"create user table\""
	@echo "  make db-upgrade ENV=prod"


# --- Application Commands ---
serve:
	@echo "Starting server in [$(ENV)]..."
	@ENV=$(ENV) uvicorn --host 0.0.0.0 --port 9091 main:app

# --- Database Migration Commands ---
db-generate:
	@echo "Generating DB migration for [$(ENV)]..."
	@ENV=$(ENV) alembic revision --autogenerate -m "$(M)"

db-upgrade:
	@echo "Upgrading DB for [$(ENV)] to head..."
	@ENV=$(ENV) alembic upgrade head

```

## `/Users/askfiy/project/coding/agent-scheduler-system/session.json`

```json
[
  { "content": "你好啊.", "role": "user" },
  {
    "id": "msg_6892f33ed1d0819aaca73d045bc30d1108021ad6d1939c58",
    "content": [
      {
        "annotations": [],
        "text": "你好呀！有什么我可以帮你的吗？",
        "type": "output_text",
        "logprobs": []
      }
    ],
    "role": "assistant",
    "status": "completed",
    "type": "message"
  },
  { "content": "我叫 askfiy\\ 你叫什么", "role": "user" },
  {
    "id": "msg_6892f3450e80819a8d17e584d35c8a2208021ad6d1939c58",
    "content": [
      {
        "annotations": [],
        "text": "你好，askfiy！我是你的AI助手，没有名字，不过你可以随意叫我任何你喜欢的名字。有什么我可以帮你的吗？",
        "type": "output_text",
        "logprobs": []
      }
    ],
    "role": "assistant",
    "status": "completed",
    "type": "message"
  },
  { "content": "你好.", "role": "user" },
  {
    "id": "msg_6892f34a03a0819ab5c1dd2dba6ae14808021ad6d1939c58",
    "content": [
      {
        "annotations": [],
        "text": "你好！有什么我可以为你做的吗？",
        "type": "output_text",
        "logprobs": []
      }
    ],
    "role": "assistant",
    "status": "completed",
    "type": "message"
  },
  { "content": "好吧,你叫小 a", "role": "user" },
  {
    "id": "msg_6892f36391e8819abe90ebbbc9b320b908021ad6d1939c58",
    "content": [
      {
        "annotations": [],
        "text": "好的，叫我小A就行！有什么需要帮忙的吗？",
        "type": "output_text",
        "logprobs": []
      }
    ],
    "role": "assistant",
    "status": "completed",
    "type": "message"
  }
]

```
