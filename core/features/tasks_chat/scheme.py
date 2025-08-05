import typing

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.util.func import to_enum_values
from core.shared.enums import MessageRole
from core.shared.base.scheme import BaseTableScheme

if typing.TYPE_CHECKING:
    from ..tasks.scheme import Tasks


class TasksChat(BaseTableScheme):
    __tablename__ = "tasks_chat"
    __table_args__ = (
        sa.Index("idx_tasks_chat_task_role", "task_id", "role"),
        {"comment": "任务聊天记录表"},
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    role: Mapped[MessageRole] = mapped_column(
        sa.Enum(MessageRole, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="发送消息的角色",
    )

    message: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="对话消息")

    task: Mapped["Tasks"] = relationship(
        "Tasks",
        back_populates="chats",
    )
