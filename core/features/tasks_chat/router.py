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
    TaskChatInCrudModel,
    TaskChatCreateModel,
)


controller = fastapi.APIRouter(prefix="/chats", tags=["chats"])


@controller.get(
    path="/{task_id}",
    name="获取某个任务下的所有聊天记录",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_all(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
    session: AsyncSession = Depends(get_async_session),
) -> PaginationResponse:
    paginator = Paginator(request=request, serializer_cls=TaskChatInCrudModel)
    paginator = await service.upget_paginator(
        task_id=task_id, paginator=paginator, session=session
    )
    return paginator.response


@controller.post(
    path="",
    name="创建聊天记录",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskChatInCrudModel],
)
async def create(
    create_model: TaskChatCreateModel,
    session: AsyncTxSession = Depends(get_async_tx_session),
) -> ResponseModel[TaskChatInCrudModel]:
    db_obj = await service.create(create_model=create_model, session=session)
    return ResponseModel(result=TaskChatInCrudModel.model_validate(db_obj))
