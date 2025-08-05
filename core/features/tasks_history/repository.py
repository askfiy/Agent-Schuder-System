import sqlalchemy as sa

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .scheme import TasksHistory


class TasksHistoryCrudRepository(BaseCRUDRepository[TasksHistory]):
    async def upget_paginator(
        self,
        task_id: int,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(
            self.model.task_id == task_id, sa.not_(self.model.is_deleted)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )
