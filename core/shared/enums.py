from enum import StrEnum


class TaskState(StrEnum):
    # 任务建立状态
    INITIAL = "initial"
    # 任务进入队列
    QUEUING = "enqueued"
    # 任务正在执行
    ACTIVATING = "activating"
    # 任务等待用户输入
    WAITING = "waiting"
    # 任务等待调度
    SCHEDULING = "scheduled"
    # 任务已经完成
    FINISHED = "finished"
    # 任务已经失败
    FAILED = "failed"
    # 任务已被取消
    CANCELLED = "cancelled"


class MessageRole(StrEnum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class TaskAuditSource(StrEnum):
    """
    触发任务状态变更的“来源”枚举
    """

    USER = "user"
    ADMIN = "admin"
    AGENT = "agent"
    SYSTEM = "system"
