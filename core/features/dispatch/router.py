import fastapi

from core.shared.enums import TaskExecuteSource
from core.shared.models.http import ResponseModel

from ..tasks.models import TaskInCrudModel
from ..tasks.scheme import Tasks
from .models import TaskDispatchCreateModel
from . import service


controller = fastapi.APIRouter(prefix="/dispatch", tags=["Dispatch"])


@controller.post(
    path="/create-task",
    name="创建任务并使其加入调度",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskInCrudModel | str],
)
async def create_task(create_model: TaskDispatchCreateModel):
    task_or_str = await service.create_task(create_model=create_model)

    if isinstance(task_or_str, Tasks):
        return ResponseModel(result=TaskInCrudModel.model_validate(task_or_str))

    return ResponseModel(result=task_or_str)


@controller.post(
    path="/execute-task",
    name="立即执行任务",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[bool],
)
async def execute_task(task_id: int = fastapi.Body(embed=True)) -> ResponseModel[bool]:
    await service.execute_task(task_id=task_id, execute_source=TaskExecuteSource.USER)
    return ResponseModel(result=True)
