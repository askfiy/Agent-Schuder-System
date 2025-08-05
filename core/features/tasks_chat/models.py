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
