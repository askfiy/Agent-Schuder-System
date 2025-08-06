from collections.abc import Callable
from typing import Any

from agents import (
    Agent as BasicAgent,
    Model,
    ModelSettings,
    RunContextWrapper,
    Runner,
    TContext,
)
from agents.agent_output import AgentOutputSchemaBase
from agents.items import TResponseInputItem
from agents.result import RunResult, RunResultStreaming
from agents.util._types import MaybeAwaitable

from core.shared.base.model import BaseLLMModel
from .session import RSession


class Agent:
    """
    基于 openai-agents 封装的 Agent.

    - 支持 Agent 多轮会话 session (每次会话用不同的 session 或统一用 Agent 创建时的 session 实现关联对话).
    - 支持 Agent 每次 run 的时候生成不同的结构化对象.
    """

    def __init__(
        self,
        name: str,
        instructions: (
            str
            | Callable[
                [RunContextWrapper[TContext], BasicAgent[TContext]],
                MaybeAwaitable[str],
            ]
            | None
        ) = None,
        model: Model | None = None,
        session: RSession | None = None,
        **kwargs: Any,
    ):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.session = session

        self.agent = BasicAgent(
            name=self.name,
            instructions=self.instructions,
            model=self.model,
            model_settings=ModelSettings(include_usage=True),
            **kwargs,
        )

    def run_streamed(
        self,
        input: str | list[TResponseInputItem],
        session: RSession | None = None,
        output_type: type[BaseLLMModel] | AgentOutputSchemaBase | None = None,
        **kwargs: Any,
    ) -> RunResultStreaming:
        agent = self.agent.clone(output_type=output_type, **kwargs)
        return Runner.run_streamed(agent, input=input, session=session or self.session)

    async def run(
        self,
        input: str | list[TResponseInputItem],
        session: RSession | None = None,
        output_type: type[BaseLLMModel] | AgentOutputSchemaBase | None = None,
        **kwargs: Any,
    ) -> RunResult:
        agent = self.agent.clone(output_type=output_type, **kwargs)
        run_result = await Runner.run(
            agent,
            input=input,
            session=session or self.session,
        )
        return run_result
