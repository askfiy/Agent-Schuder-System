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
