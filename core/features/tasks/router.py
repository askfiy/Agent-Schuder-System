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
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service
from .models import (
    TaskInCrudModel,
    TaskCreateModel,
    TaskUpdateModel,
)


controller = fastapi.APIRouter(prefix="/tasks", tags=["tasks"])


@controller.get(
    path="",
    name="获取所有 task",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_all(
    request: PaginationRequest = Depends(PaginationRequest),
    session: AsyncSession = Depends(get_async_session),
) -> PaginationResponse:
    paginator = Paginator(request=request, serializer_cls=TaskInCrudModel)
    paginator = await service.upget_paginator(paginator=paginator, session=session)
    return paginator.response


@controller.get(
    path="/{task_id}",
    name="根据 pk 获取某个 task",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskInCrudModel],
)
async def get(
    task_id: int = fastapi.Path(description="任务 ID"),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel[TaskInCrudModel]:
    db_obj = await service.get(task_id=task_id, session=session)
    return ResponseModel(result=TaskInCrudModel.model_validate(db_obj))


@controller.post(
    path="",
    name="创建 Task",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskInCrudModel],
)
async def create(
    create_model: TaskCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskInCrudModel.model_validate(db_obj))


@controller.put(
    path="/{task_id}",
    name="更新 Task",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskInCrudModel],
)
async def update(
    update_model: TaskUpdateModel,
    task_id: int = fastapi.Path(description="任务 ID"),
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskInCrudModel]:
    db_obj = await service.update(
        task_id=task_id, update_model=update_model, session=session
    )
    return ResponseModel(result=TaskInCrudModel.model_validate(db_obj))


@controller.delete(
    path="/{task_id}",
    name="删除 Task",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[bool],
)
async def delete(
    task_id: int = fastapi.Path(description="任务 ID"),
    session: AsyncTxSession = Depends(get_async_tx_session),
):
    result = await service.delete(task_id=task_id, session=session)
    return ResponseModel(result=result)
