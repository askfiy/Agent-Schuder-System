import json
import inspect
import datetime
from typing import get_origin, get_args, Union, Any, TypeVar

import pytz
import pydantic
from pydantic import Field
from pydantic.alias_generators import to_camel


T = TypeVar("T")

model_config = pydantic.ConfigDict(
    # 自动将 snake_case 字段名生成 camelCase 别名，用于 JSON 输出
    alias_generator=to_camel,
    # 允许在创建模型时使用别名（如 'taskId'）
    populate_by_name=True,
    # 允许从 ORM 对象等直接转换
    from_attributes=True,
    # 允许任意类型作为字段
    arbitrary_types_allowed=True,
    # 统一处理所有 datetime 对象的 JSON 序列化格式
    json_encoders={datetime.datetime: lambda dt: dt.isoformat().replace("+00:00", "Z")},
)


class BaseModel(pydantic.BaseModel):
    model_config = model_config

    @pydantic.model_validator(mode="after")
    def set_naive_datetime_to_utc(self) -> "BaseModel":
        """
        遍历模型中的所有字段，如果字段是天真的 datetime 对象，
        则将其时区设置为 UTC。
        """
        for field_name, value in self.__dict__.items():
            if isinstance(value, datetime.datetime):
                if value.tzinfo is None:
                    aware_value = value.replace(tzinfo=datetime.timezone.utc)
                    setattr(self, field_name, aware_value)
        return self

    def pretty_json(self):
        return self.model_dump_json(indent=2)


class LLMInputModel(BaseModel):
    def model_dump_markdown(self) -> str:
        md = f"```json\n{self.model_dump_json(indent=2)}\n```\n"

        return md


class LLMTimeField(BaseModel):
    """
    大模型输出时的时间字段.
    """

    year: int = Field(
        description="The year of task execution, a 4-digit number", examples=[2025]
    )
    month: int = Field(
        description="The month of task execution, a number from 1-12", examples=[8]
    )
    day: int = Field(
        description="The specific day of task execution, a number from 1-31",
        examples=[7],
    )
    hour: int = Field(
        description="The specific hour of task execution, a number from 1-24",
        examples=[14],
    )
    min: int = Field(
        description="The specific minute of task execution, a number from 1-60",
        examples=[30],
    )

    def get_utc_datetime(self, from_timezone: str = "UTC") -> datetime.datetime:
        return (
            pytz.timezone(from_timezone)
            .localize(
                datetime.datetime(self.year, self.month, self.day, self.hour, self.min)
            )
            .astimezone(pytz.utc)
        )


class LLMOutputModel(BaseModel):
    thinking: str = Field(description="思考过程", examples=["The user's request is..."])

    @classmethod
    def output_example(cls) -> str:
        """
        Generates a representative JSON example string from the model's fields,
        using the 'examples' provided in each Field.
        """
        example_dict = cls._build_example_dict(model_cls=cls)
        # Use ensure_ascii=False to correctly handle non-ASCII characters like Chinese
        return json.dumps(example_dict, indent=2, ensure_ascii=False)

    # --- NEW: Recursive helper to build the example dictionary ---
    @classmethod
    def _build_example_dict(cls, model_cls: type[BaseModel]) -> dict[str, Any]:
        """
        (Helper) Recursively builds a dictionary from field examples.
        """
        example_data: Any = {}
        for name, field in model_cls.model_fields.items():
            field_type = field.annotation

            # 1. Check if the field contains a nested model for recursion
            sub_model_to_build = cls._extract_model_for_recursion(field_type)

            if sub_model_to_build:
                # We found a nested model. Now, check if it was in a list.
                origin = get_origin(field_type)
                if origin and issubclass(origin, list):
                    # Case: list[MyModel] -> build an example and wrap it in a list
                    example_data[name] = [
                        cls._build_example_dict(model_cls=sub_model_to_build)
                    ]
                else:
                    # Case: MyModel or Union[MyModel, None] -> build a nested example
                    example_data[name] = cls._build_example_dict(
                        model_cls=sub_model_to_build
                    )
                continue  # Move to the next field

            # 2. If not a nested model, it's a simple field. Use its example.
            if field.examples:
                example_data[name] = field.examples[0]
            else:
                # Fallback if no example is provided for a simple field
                type_name = cls._format_type(field_type)
                example_data[name] = f"({type_name} example)"

        return example_data

    @classmethod
    def model_description(cls) -> str:
        return "\n".join(cls._build_lines(model=cls))

    @classmethod
    def _build_lines(cls, model: type[BaseModel], indent_level: int = 0) -> list[str]:
        lines: list[str] = []
        indent_str = "    " * indent_level
        for name, field in model.model_fields.items():
            description = field.description or "No description"
            type_str = cls._format_type(field.annotation)
            lines.append(f"{indent_str}{name} [<{type_str}>]: {description}")
            if sub_model := cls._extract_model_for_recursion(field.annotation):
                lines.extend(
                    cls._build_lines(model=sub_model, indent_level=indent_level + 1)
                )
        return lines

    @classmethod
    def _format_type(cls, tp: Any) -> str:
        if origin := get_origin(tp):
            args = get_args(tp)
            if origin is Union:
                return " | ".join(
                    cls._format_type(arg) for arg in args if arg is not type(None)
                )
            if issubclass(origin, list):
                return f"list[{cls._format_type(args[0]) if args else 'Any'}]"
            if issubclass(origin, dict):
                key_type = cls._format_type(args[0]) if args else "Any"
                val_type = cls._format_type(args[1]) if len(args) > 1 else "Any"
                return f"dict[{key_type}, {val_type}]"
            arg_str = ", ".join(cls._format_type(arg) for arg in args)
            return f"{origin.__name__}[{arg_str}]"
        return getattr(tp, "__name__", str(tp))

    @classmethod
    def _extract_model_for_recursion(cls, tp: Any) -> type[BaseModel] | None:
        if origin := get_origin(tp):
            if origin is Union:
                for arg in get_args(tp):
                    if model := cls._extract_model_for_recursion(arg):
                        return model
                return None
            if issubclass(origin, list):
                args = get_args(tp)
                tp = args[0] if args else None
        if inspect.isclass(tp) and issubclass(tp, BaseModel):
            return tp
        return None
