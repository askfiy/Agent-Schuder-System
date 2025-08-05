import datetime

from core.shared.enums import TaskUnitState
from core.shared.base.model import BaseModel


class TaskUnitInCrudModel(BaseModel):
    id: int
    name: str
    task_id: int
    objective: str
    invocation_id: str
    state: TaskUnitState
    output: str | None = None
    created_at: datetime.datetime


class TaskUnitCreateModel(BaseModel):
    name: str
    task_id: int
    objective: str
    invocation_id: str


class TaskUnitUpdateModel(BaseModel):
    state: TaskUnitState
    output: str | None = None
