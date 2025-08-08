import uuid
import datetime
from collections.abc import Sequence

from core.shared.base.model import BaseModel
from core.shared.enums import TaskState, TaskAuditSource
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
    AsyncSession,
    AsyncTxSession,
)
from ..tasks.scheme import Tasks
from ..tasks_chat.scheme import TasksChat
from ..tasks_unit.scheme import TasksUnit
from ..tasks_audit.scheme import TasksAudit
from ..tasks_history.scheme import TasksHistory
from ..tasks_workspace.scheme import TasksWorkspace
from ..tasks import service as tasks_service
from ..tasks_chat import service as tasks_chat_service
from ..tasks_unit import service as tasks_unit_service
from ..tasks_audit import service as tasks_audit_service
from ..tasks_history import service as tasks_history_service
from ..tasks_workspace import service as tasks_workspace_service
from ..tasks.models import TaskCreateModel, TaskUpdateModel
from ..tasks_audit.models import TaskAuditCreateModel
from ..tasks_history.models import TaskHistoryCreateModel
from ..tasks_workspace.models import TaskWorkspaceCreateModel


async def get_task(task_id: int) -> Tasks:
    """
    获取任务
    """
    async with get_async_session_direct() as session:
        return await tasks_service.get(task_id, session=session)


async def create_dispatch_task(
    prd: str,
    name: str,
    expect_execute_time: datetime.datetime,
    owner: str,
    owner_timezone: str,
    keywords: list[str],
    original_user_input: str,
    trace_id: uuid.UUID,
) -> Tasks:
    """
    创建任务
    """

    async with get_async_tx_session_direct() as session:
        # 1. 先创建工作空间, 生成需求 PRD 等.
        workspace = await tasks_workspace_service.create(
            create_model=TaskWorkspaceCreateModel(prd=prd),
            session=session,
        )

        # 2. 再创建任务
        task = await tasks_service.create(
            create_model=TaskCreateModel(
                name=name,
                workspace_id=workspace.id,
                expect_execute_time=expect_execute_time,
                owner=owner,
                owner_timezone=owner_timezone,
                keywords=keywords,
                original_user_input=original_user_input,
                trace_id=trace_id,
            ),
            session=session,
        )
        return task


async def update_task_state(
    task_id: int, state: TaskState, session: AsyncTxSession
) -> Tasks:
    # 更新任务本身状态
    task = await tasks_service.update(
        task_id=task_id,
        update_model=TaskUpdateModel(state=state),
        session=session,
    )

    return task


async def create_task_audit(
    task_id: int,
    from_state: TaskState,
    to_state: TaskState,
    source: TaskAuditSource,
    source_context: str,
    comment: str,
    session: AsyncTxSession,
) -> TasksAudit:
    # 创建审计日志
    return await tasks_audit_service.create(
        create_model=TaskAuditCreateModel(
            task_id=task_id,
            from_state=from_state,
            to_state=to_state,
            source=source,
            source_context=source_context,
            comment=comment,
        ),
        session=session,
    )


async def update_task_process(
    task_id: int, state: TaskState, process: str, thinking: str, session: AsyncTxSession
) -> TasksHistory:
    return await tasks_history_service.create(
        create_model=TaskHistoryCreateModel(
            task_id=task_id, state=state, process=process, thinking=thinking
        ),
        session=session,
    )


async def update_fields(
    task_id: int, update_model: TaskUpdateModel, session: AsyncTxSession
) -> Tasks:
    return await tasks_service.update(
        task_id=task_id, update_model=update_model, session=session
    )


async def get_task_workspace(workspace_id: int) -> TasksWorkspace:
    async with get_async_session_direct() as session:
        return await tasks_workspace_service.get(
            workspace_id=workspace_id, session=session
        )

