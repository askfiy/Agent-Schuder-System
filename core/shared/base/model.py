import datetime
from typing import TypeVar
from pydantic.alias_generators import to_camel

import pydantic

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


__all__ = ["BaseModel", "T"]
