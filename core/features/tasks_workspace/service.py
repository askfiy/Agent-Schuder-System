from core.shared.database.session import (
    AsyncSession,
    AsyncTxSession,
)
from core.shared.exceptions import ServiceNotFoundException
from .scheme import TasksWorkspace
from .models import TaskWorkspaceCreateModel, TaskWorkspaceUpdateModel
from .repository import TasksWorkspaceCrudRespository


async def get_or_404(repo: TasksWorkspaceCrudRespository, pk: int):
    db_obj = await repo.get(pk=pk)
    if not db_obj:
        raise ServiceNotFoundException(f"任务工作空间: {pk} 不存在")

    return db_obj


async def get(workspace_id: int, session: AsyncSession) -> TasksWorkspace:
    repo = TasksWorkspaceCrudRespository(session=session)
    return await get_or_404(repo=repo, pk=workspace_id)


async def create(
    create_model: TaskWorkspaceCreateModel, session: AsyncTxSession
) -> TasksWorkspace:
    repo = TasksWorkspaceCrudRespository(session=session)
    db_obj = await repo.create(create_model)
    return db_obj


async def update(
    workspace_id: int, update_model: TaskWorkspaceUpdateModel, session: AsyncTxSession
) -> TasksWorkspace:
    repo = TasksWorkspaceCrudRespository(session=session)
    db_obj = await repo.get(pk=workspace_id)
    db_obj = await get_or_404(repo=repo, pk=workspace_id)
    db_obj = await repo.update(db_obj, update_model=update_model)
    return db_obj


async def delete(workspace_id: int, session: AsyncTxSession) -> bool:
    repo = TasksWorkspaceCrudRespository(session=session)
    db_obj = await repo.get(pk=workspace_id)
    db_obj = await get_or_404(repo=repo, pk=workspace_id)
    db_obj = await repo.delete(db_obj=db_obj)
    return bool(db_obj.is_deleted)
