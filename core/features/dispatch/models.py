import datetime

from pydantic import Field, model_validator

from core.shared.enums import TaskState, TaskAuditSource
from core.shared.base.model import BaseModel, BaseLLMModel

from ..tasks_chat.models import TaskChatInCrudModel
from ..tasks_history.models import TaskHistoryInCrudModel


class TaskInDispatchModel(BaseLLMModel):
    id: int = Field(description="任务主键")
    name: str = Field(description="任务名称")
    state: TaskState = Field(description="当前任务状态")
    priority: int = Field(description="任务优先级")
    workspace_id: int = Field(description="任务关联工作区")

    expect_execute_time: datetime.datetime = Field(description="任务预期执行时间")
    lasted_execute_time: datetime.datetime | None = Field(
        description="任务最后执行时间"
    )

    original_user_input: str = Field(description="原始用户输入")
    chats: list[TaskChatInCrudModel] = Field(description="任务和用户的交互历史")
    histories: list[TaskHistoryInCrudModel] = Field(description="LLM 执行历史")


class TaskInDispatchUpdateModel(BaseModel):
    state: TaskState

    source: TaskAuditSource | None = None
    source_context: str | None = None
    comment: str | None = None

    process: str | None = None
    thinking: str | None = None

    @model_validator(mode="after")
    def validate_audit_dependency(self) -> "TaskInDispatchUpdateModel":
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
