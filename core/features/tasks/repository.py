import asyncio
from typing import override, Any

import sqlalchemy as sa
from sqlalchemy.orm import aliased, subqueryload, with_loader_criteria, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.strategy_options import _AbstractLoad  # pyright: ignore[reportPrivateUsage]
from sqlalchemy.orm.util import LoaderCriteriaOption

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .models import TaskCreateRequestModel
from .scheme import Tasks
from ..tasks_chat.scheme import TasksChat
from ..tasks_unit.scheme import TasksUnit
from ..tasks_audit.scheme import TasksAudit
from ..tasks_history.scheme import TasksHistory
from ..tasks_workspace.service import delete as workspace_delete


class TasksCrudRepository(BaseCRUDRepository[Tasks]):
    def __init__(self, session: AsyncSession):
        super().__init__(session=session)

        self.default_limit_count = 10
        self.default_joined_loads = [Tasks.chats, Tasks.histories]

    def _get_history_loader_options(
        self, limit_count: int
    ) -> list[_AbstractLoad | LoaderCriteriaOption]:
        history_alias_for_ranking = aliased(TasksHistory)
        ranked_histories_cte = (
            sa.select(
                history_alias_for_ranking.id,
                sa.func.row_number()
                .over(
                    partition_by=history_alias_for_ranking.task_id,
                    order_by=history_alias_for_ranking.created_at.desc(),
                )
                .label("rn"),
            )
            .where(history_alias_for_ranking.task_id == Tasks.id)
            .cte("ranked_histories_cte")
        )

        return [
            subqueryload(Tasks.histories),
            with_loader_criteria(
                TasksHistory,
                TasksHistory.id.in_(
                    sa.select(ranked_histories_cte.c.id).where(
                        ranked_histories_cte.c.rn <= limit_count
                    )
                ),
            ),
        ]

    def _get_chat_loader_options(
        self, limit_count: int
    ) -> list[_AbstractLoad | LoaderCriteriaOption]:
        chat_alias_for_ranking = aliased(TasksChat)
        ranked_chats_cte = (
            sa.select(
                chat_alias_for_ranking.id,
                sa.func.row_number()
                .over(
                    partition_by=chat_alias_for_ranking.task_id,
                    order_by=chat_alias_for_ranking.created_at.desc(),
                )
                .label("rn"),
            )
            .where(chat_alias_for_ranking.task_id == Tasks.id)
            .cte("ranked_chats_cte")
        )

        return [
            subqueryload(Tasks.chats),
            with_loader_criteria(
                TasksChat,
                TasksChat.id.in_(
                    sa.select(ranked_chats_cte.c.id).where(
                        ranked_chats_cte.c.rn <= limit_count
                    )
                ),
            ),
        ]

    @override
    async def create(self, create_model: TaskCreateRequestModel) -> Tasks:
        task = await super().create(create_model=create_model)

        # 创建 task 后需要手动 load 一下 chats 和 histories.
        await self.session.refresh(task, [Tasks.chats.key, Tasks.histories.key])
        return task

    @override
    async def get(
        self, pk: int, joined_loads: list[InstrumentedAttribute[Any]] | None = None
    ) -> Tasks | None:
        extend_joined_loads = self.default_joined_loads.copy()
        extend_joined_loads.extend(joined_loads or [])

        stmt = sa.select(self.model).where(
            self.model.id == pk, sa.not_(self.model.is_deleted)
        )

        if extend_joined_loads:
            for join_field in extend_joined_loads:
                if Tasks.chats is join_field:
                    stmt = stmt.options(
                        *self._get_chat_loader_options(self.default_limit_count)
                    )
                elif Tasks.histories is join_field:
                    stmt = stmt.options(
                        *self._get_history_loader_options(self.default_limit_count)
                    )
                else:
                    stmt = stmt.options(joinedload(join_field))

        result = await self.session.execute(stmt)

        return result.unique().scalar_one_or_none()

    @override
    async def delete(self, db_obj: Tasks) -> Tasks:
        task = db_obj

        # 软删除 tasks
        task = await super().delete(db_obj)

        # 软删除其他依赖关系 ....
        workspace_delete_coroutine = workspace_delete(
            workspace_id=task.workspace_id, session=self.session
        )

        soft_delete_coroutines = [
            self.session.execute(
                sa.update(table)
                .where(
                    # 注意：这里需要检查表是否有 task_id 属性，这些表都有
                    table.task_id == task.id,
                    sa.not_(table.is_deleted),
                )
                .values(is_deleted=True, deleted_at=sa.func.now())
            )
            for table in [
                TasksChat,
                TasksUnit,
                TasksAudit,
                TasksHistory,
            ]
        ]

        await asyncio.gather(workspace_delete_coroutine, *soft_delete_coroutines)

        # 因为有事务装饰器的存在， 故这里所有的操作均为原子操作.
        await self.session.refresh(task)

        return task

    async def upget_paginator(
        self,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(sa.not_(self.model.is_deleted))
        query_stmt = query_stmt.options(
            *self._get_chat_loader_options(self.default_limit_count)
        )
        query_stmt = query_stmt.options(
            *self._get_history_loader_options(self.default_limit_count)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )
