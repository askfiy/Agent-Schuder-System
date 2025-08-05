import typing

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.base.scheme import BaseTableScheme

if typing.TYPE_CHECKING:
    from ..tasks.scheme import Tasks


class TasksWorkspace(BaseTableScheme):
    __tablename__ = "tasks_workspace"
    __table_args__ = {"comment": "任务工作空间表"}

    prd: Mapped[str] = mapped_column(sa.TEXT, nullable=False, comment="需求 Prd.")

    process: Mapped[str] = mapped_column(
        sa.TEXT, nullable=True, comment="执行 Process."
    )

    result: Mapped[str] = mapped_column(sa.TEXT, nullable=True, comment="执行 Result.")

    task: Mapped["Tasks"] = relationship(
        back_populates="workspace",
        uselist=False,  # 表示这是一对一关系
    )
