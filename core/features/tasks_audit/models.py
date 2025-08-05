import datetime

from core.shared.enums import TaskState, TaskAuditSource
from core.shared.base.model import BaseModel


class TaskAuditInCRUDResponse(BaseModel):
    from_state: TaskState
    to_state: TaskState
    source: TaskAuditSource
    source_context: str
    comment: str
    created_at: datetime.datetime


class TaskAuditCreateRequestModel(BaseModel):
    task_id: int
    from_state: TaskState
    to_state: TaskState
    source: TaskAuditSource
    source_context: str
    comment: str
