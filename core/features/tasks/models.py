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
