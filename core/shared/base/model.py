import datetime
import typing
from typing import TypeVar

import pydantic
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


class BaseLLMModel(BaseModel):
    def model_dump_markdown(self) -> str:
        md = f"```json\n{self.model_dump_json(indent=2)}\n```\n"

        return md

    @classmethod
    def model_description(cls) -> str:
        fields_meta_information: list[str] = []

        for field_name, field_attr in cls.model_fields.items():
            field_type = field_attr.annotation
            field_description = field_attr.description or "No field description"

            if field_type and hasattr(field_type, "__name__"):
                field_type = field_type.__name__

            fields_meta_information.append(
                f"{field_name} [<{field_type}>]: {field_description}"
            )

        return "\n".join(fields_meta_information)


__all__ = ["BaseModel", "BaseLLMModel", "T"]
