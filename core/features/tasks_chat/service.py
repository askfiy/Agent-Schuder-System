from core.shared.models.http import Paginator
from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksChat
from .models import TaskChatCreateModel
from .repository import TasksChatCrudRepository


async def get_or_404(repo: TasksChatCrudRepository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务对话记录: {pk} 不存在")

    return db_obj



async def create(
    create_model: TaskChatCreateModel, session: AsyncTxSession
) -> TasksChat:
    repo = TasksChatCrudRepository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj



async def upget_paginator(
    task_id: int, paginator: Paginator, session: AsyncSession
) -> Paginator:
    repo = TasksChatCrudRepository(session=session)
    return await repo.upget_paginator(task_id=task_id, paginator=paginator)
