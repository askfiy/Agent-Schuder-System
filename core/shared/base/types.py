from typing import TypeVar, ParamSpec, Protocol, Any, runtime_checkable

P = ParamSpec("P")
R = TypeVar("R")


@runtime_checkable
class ModelDumpProtocol(Protocol):
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...
