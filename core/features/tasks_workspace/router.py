import fastapi
from fastapi import Depends

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)
from core.shared.models.http import (
    ResponseModel,
)

from . import service
from .models import (
    TaskWorkspaceInCrudModel,
    TaskWorkspaceCreateModel,
    TaskWorkspaceUpdateModel,
)


controller = fastapi.APIRouter(
    prefix="/workspaces", tags=["Workspaces"], deprecated=True
)


@controller.get(
    path="/{workspace_id}",
    name="获取工作空间",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskWorkspaceInCrudModel],
)
async def get(
    workspace_id: int = fastapi.Path(description="主键"),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel[TaskWorkspaceInCrudModel]:
    db_obj = await service.get(workspace_id=workspace_id, session=session)
    return ResponseModel(result=TaskWorkspaceInCrudModel.model_validate(db_obj))


@controller.post(
    path="",
    name="创建工作空间",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskWorkspaceInCrudModel],
)
async def create(
    create_model: TaskWorkspaceCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskWorkspaceInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskWorkspaceInCrudModel.model_validate(db_obj))


@controller.put(
    path="/{workspace_id}",
    name="更新工作空间",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskWorkspaceInCrudModel],
)
async def update(
    update_model: TaskWorkspaceUpdateModel,
    workspace_id: int = fastapi.Path(description="主键"),
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskWorkspaceInCrudModel]:
    db_obj = await service.update(
        workspace_id=workspace_id, update_model=update_model, session=session
    )
    return ResponseModel(result=TaskWorkspaceInCrudModel.model_validate(db_obj))


@controller.delete(
    path="/{workspace_id}",
    name="删除工作空间",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[bool],
)
async def delete(
    workspace_id: int = fastapi.Path(description="主键"),
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[bool]:
    is_deleted = await service.delete(workspace_id=workspace_id, session=session)
    return ResponseModel(result=is_deleted)
