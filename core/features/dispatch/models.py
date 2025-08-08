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
from ..tasks_unit.models import TaskUnitCreateModel
from . import prompt


class TaskDispatchUpdateStateModel(BaseModel):
    state: TaskState
    source: TaskAuditSource | None = None
    source_context: str | None = None
    comment: str | None = None

    process: str | None = None
    thinking: str | None = None

    @model_validator(mode="after")
    def validate_audit_dependency(self) -> "TaskDispatchUpdateStateModel":
        """
        验证规则 (二选一即可通过):
            - state 和所有审计字段必须“同生共死”。
            - state 和所有历史字段必须“同生共死”
        """

        validation_audit = all(
            {
                bool(self.state),
                bool(self.source),
                bool(self.source_context),
                bool(self.comment),
            }
        )

        validation_histories = all(
            {
                bool(self.state),
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
    invocation_id: uuid.UUID | None = Field(description="当前执行轮次的唯一 ID")

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


class TaskDispatchGeneratorPlanningModel(LLMOutputModel):
    process: str = Field(
        description="任务执行计划. 一个 Markdown 文档, 必须清晰, 可执行.",
        examples=[prompt.get_process_example()],
    )


class TaskDispatchExecuteUnitModel(BaseModel):
    name: str = Field(description="执行单元的名称", examples=["准备会议演示文稿"])
    objective: str = Field(
        description="执行单元的目标",
        examples=[
            "产出一份明确的会议文稿. 包含 Q3 季度的销售情况分析, 产品优化方向, 最终预期收益等."
        ],
    )


class TaskDispatchGeneratorExecuteUnitModel(LLMOutputModel):
    unit_list: list[TaskDispatchExecuteUnitModel] = Field(
        description="包含执行单元的列表"
    )


class TaskDispatchExecuteUnitOutputModel(LLMOutputModel):
    output: str = Field(
        description="执行单元的执行结果",
        examples=[prompt.get_unit_output_example()],
    )


if __name__ == "__main__":
    print(TaskDispatchGeneratorExecuteUnitModel.model_description())
    print(TaskDispatchGeneratorExecuteUnitModel.output_example())
