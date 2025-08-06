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
    # 用户已更新任务
    UPDATING = "updating"


class TaskUnitState(StrEnum):
    # 执行单元创建
    CREATED = "CREATED"
    # 执行单元运行
    RUNNING = "RUNNING"
    # 执行单元完成
    COMPLETE = "COMPLETE"
    # 执行单元取消
    CANCELLED = "CANCELLED"


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
