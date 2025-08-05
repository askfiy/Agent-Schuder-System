import typing

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.enums import TaskUnitState
from core.shared.util.func import to_enum_values
from core.shared.base.scheme import BaseTableScheme

if typing.TYPE_CHECKING:
    from ..tasks.scheme import Tasks


class TasksUnit(BaseTableScheme):
    __tablename__ = "tasks_unit"
    __table_args__ = (
        sa.Index(
            "idx_tasks_unit_task_invocation_state",
            "task_id",
            "invocation_id",
            "state",
        ),
        {"comment": "任务执行单元表"},
    )

    name: Mapped[str] = mapped_column(
        sa.String(255), index=True, nullable=False, comment="执行单元的名称"
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    objective: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="执行单元的目标"
    )

    invocation_id: Mapped[str] = mapped_column(
        sa.CHAR(36), index=True, nullable=False, comment="任务的调用 ID"
    )

    state: Mapped[TaskUnitState] = mapped_column(
        sa.Enum(TaskUnitState, values_callable=to_enum_values),
        nullable=False,
        default=TaskUnitState.CREATED,
        index=True,
        comment="执行单元当前状态",
        server_default=TaskUnitState.CREATED.value,
    )

    output: Mapped[str] = mapped_column(
        sa.Text, nullable=True, comment="执行单元的产出结果"
    )

    task: Mapped["Tasks"] = relationship(
        "Tasks",
        back_populates="units",
    )
