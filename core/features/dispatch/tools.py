import uuid
from typing import Any

from agents import function_tool, FunctionTool, RunContextWrapper

from core.shared.base.model import LLMTimeField, BaseModel

from . import action
from . import models


class CreateDispatchTaskFuncToolArgs(BaseModel):
    prd: str
    name: str
    expect_execute_time: LLMTimeField
    owner: str
    owner_timezone: str
    keywords: list[str]
    original_user_input: str
    trace_id: uuid.UUID


async def create_dispatch_task_tool(
    ctx: RunContextWrapper[Any], args: str
) -> dict[str, Any]:
    try:
        parsed = CreateDispatchTaskFuncToolArgs.model_validate_json(args)
        call_tool_args = {
            "expect_execute_time": parsed.expect_execute_time.get_utc_datetime(),
        }
        call_tool_args.update(parsed.model_dump(exclude={"expect_execute_time"}))

        task = await action.create_dispatch_task(**call_tool_args)  # pyright: ignore[reportArgumentType]

        return models.TaskInDispatchModel.model_validate(task).model_dump()
    except Exception as exc:
        print(exc)
        return {"error_message": str(exc)}


create_dispatch_task_tool = FunctionTool(
    name="create_dispatch_task_tool",
    description=(
        "为用户创建一个后台调度任务，用于编排和执行一个复杂的工作流。这是处理多步骤、高复杂度用户请求的首选工具。"
        "在以下情况下必须调用此工具："
        "1. 当请求需要被分解成多个顺序或并行的步骤时 (例如：先搜索，再分析，最后总结)。"
        "2. 当需要调用多个不同的工具，并将它们的结果组合起来才能满足最终需求时 (例如：查询天气，然后根据天气搜索餐厅)。"
        "3. 当用户指定了未来的执行时间或要求周期性执行时 (例如：'明晚8点提醒我' 或 '每天早上报告新闻')。"
        "4. 当请求的本质是一个需要规划和执行的长期任务时 (例如：'帮我规划一次旅行' 或 '帮我写一份市场分析报告')。"
        "注意：如果一个简单的、单一功能的工具就能直接回答用户，请不要使用此工具。"
    ),
    params_json_schema=CreateDispatchTaskFuncToolArgs.model_json_schema(),
    on_invoke_tool=create_dispatch_task_tool,
)
