import uuid
import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.enums import TaskState
from core.shared.util.func import to_enum_values
from core.shared.base.scheme import BaseTableScheme

from ..tasks_unit.scheme import TasksUnit
from ..tasks_chat.scheme import TasksChat
from ..tasks_history.scheme import TasksHistory
from ..tasks_workspace.scheme import TasksWorkspace


class Tasks(BaseTableScheme):
    __tablename__ = "tasks"
    __table_args__ = (
        sa.Index(
            "idx_tasks_state_priority_time", "state", "priority", "expect_execute_time"
        ),
        sa.Index("idx_keywords_fulltext", "keywords", mysql_prefix="FULLTEXT"),
        {"comment": "任务表"},
    )

    name: Mapped[str] = mapped_column(
        sa.String(255), index=True, nullable=False, comment="任务的名称"
    )

    state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        default=TaskState.INITIAL,
        index=True,
        comment="任务当前状态",
        server_default=TaskState.INITIAL.value,
    )

    priority: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        index=True,
        comment="任务优先级",
        server_default=sa.text("0"),
    )

    trace_id: Mapped[uuid.UUID] = mapped_column(
        sa.CHAR(36),
        nullable=False,
        index=True,
        comment="任务建立时流转的事务 Id.",
    )

    invocation_id: Mapped[uuid.UUID] = mapped_column(
        sa.CHAR(36), nullable=True, index=True, comment="任务的调用批次 Id"
    )

    expect_execute_time: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="任务预期执行时间",
        server_default=sa.func.now(),
    )

    lasted_execute_time: Mapped[Optional[datetime.datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="任务最终执行时间",
    )

    owner: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        comment="任务所有者",
        index=True,
    )

    owner_timezone: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        default="UTC",
        comment="所有者所在时区",
        server_default=sa.text("'UTC'"),
    )

    original_user_input: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="任务原始输入",
    )

    keywords: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="关键字信息")

    workspace_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks_workspace.id"),
        nullable=False,
        index=True,
        comment="任务工作空间",
    )

    # --- 关系, 这里就是依赖的 units ..
    units: Mapped[list["TasksUnit"]] = relationship(
        "TasksUnit",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TasksUnit.created_at.desc()",
    )

    chats: Mapped[list["TasksChat"]] = relationship(
        "TasksChat",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TasksChat.created_at.desc()",
    )

    histories: Mapped[list["TasksHistory"]] = relationship(
        "TasksHistory",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TasksHistory.created_at.desc()",
    )

    workspace: Mapped["TasksWorkspace"] = relationship(back_populates="task")
