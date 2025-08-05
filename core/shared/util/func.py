from enum import StrEnum


def to_enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [e.value for e in enum_class]
