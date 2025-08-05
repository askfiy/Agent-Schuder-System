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
from .models import TaskUnitInCrudModel, TaskUnitCreateModel, TaskUnitUpdateModel


controller = fastapi.APIRouter(prefix="/units", tags=["Units"])


@controller.get(
    path="/{task_id}",
    name="获取某个任务下的所有执行单元",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_all(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
    session: AsyncSession = Depends(get_async_session),
) -> PaginationResponse:
    paginator = Paginator(request=request, serializer_cls=TaskUnitInCrudModel)
    paginator = await service.upget_paginator(
        task_id=task_id, paginator=paginator, session=session
    )
    return paginator.response


@controller.post(
    path="",
    name="创建执行单元",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskUnitInCrudModel],
)
async def create(
    create_model: TaskUnitCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskUnitInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskUnitInCrudModel.model_validate(db_obj))


@controller.put(
    path="/{unit_id}",
    name="更新执行单元",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskUnitInCrudModel],
)
async def update(
    update_model: TaskUnitUpdateModel,
    unit_id: int = fastapi.Path(description="主键"),
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskUnitInCrudModel]:
    db_obj = await service.update(
        unit_id=unit_id, update_model=update_model, session=session
    )
    return ResponseModel(result=TaskUnitInCrudModel.model_validate(db_obj))


