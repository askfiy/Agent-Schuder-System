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
