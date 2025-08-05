from core.shared.models.http import Paginator
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksUnit
from .models import TaskUnitCreateModel, TaskUnitUpdateModel
from .repository import TasksUnitCrudRespository


async def get_or_404(repo: TasksUnitCrudRespository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务执行单元: {pk} 不存在")

    return db_obj


async def create(
    create_model: TaskUnitCreateModel, session: AsyncTxSession
) -> TasksUnit:
    repo = TasksUnitCrudRespository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj


async def update(
    unit_id: int, update_model: TaskUnitUpdateModel, session: AsyncTxSession
) -> TasksUnit:
    repo = TasksUnitCrudRespository(session=session)
    db_obj = await get_or_404(repo=repo, pk=unit_id)
    db_obj = await repo.update(db_obj, update_model=update_model)
    return db_obj


async def upget_paginator(
    task_id: int, paginator: Paginator, session: AsyncSession
) -> Paginator:
    repo = TasksUnitCrudRespository(session=session)
    return await repo.upget_paginator(task_id=task_id, paginator=paginator)
