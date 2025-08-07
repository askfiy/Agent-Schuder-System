import fastapi
from fastapi import Depends

from core.shared.models.http import ResponseModel
from ..tasks.models import TaskInCrudModel
from .agent import TaskAgent


controller = fastapi.APIRouter(prefix="/dispatch", tags=["Dispatch"])


@controller.post(
    path="/create-task",
    name="创建任务并使其加入调度",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskInCrudModel],
)
async def create_task(
    owner: str = fastapi.Body(embed=True),
    original_user_input: str = fastapi.Body(embed=True),
    owner_timezone: str = fastapi.Body(embed=True, default="UTC"),
):
    agent = TaskAgent.create(
        name="Agent-System-Scheduler",
        instructions="创建任务的调度系统",
    )

    await agent.create_task(
        owner=owner,
        original_user_input=original_user_input,
        owner_timezone=owner_timezone,
    )
