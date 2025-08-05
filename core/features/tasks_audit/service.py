from core.shared.models.http import Paginator
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksAudit
from .models import TaskAuditCreateRequestModel
from .repository import TasksAuditCrudRespository


async def get_or_404(repo: TasksAuditCrudRespository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务审计记录: {pk} 不存在")

    return db_obj


async def create(
    create_model: TaskAuditCreateRequestModel, session: AsyncTxSession
) -> TasksAudit:
    repo = TasksAuditCrudRespository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj


async def upget_paginator(
    task_id: int, paginator: Paginator, session: AsyncSession
) -> Paginator:
    repo = TasksAuditCrudRespository(session=session)
    return await repo.upget_paginator(task_id=task_id, paginator=paginator)
