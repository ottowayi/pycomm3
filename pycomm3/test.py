from dataclasses import Field, field, dataclass
from typing import dataclass_transform, Self, cast, Any, overload


@dataclass_transform(field_specifiers=(Field, field), kw_only_default=True)
class DataclassMeta(type):
    def __new__(mcs, name: str, bases: tuple, cls_dict: dict):
        return dataclass(kw_only=True)(super().__new__(mcs, name, bases, cls_dict))


def attr(*, init: bool = True, default: Any = None, tag: str | None = None):
    ...
    return field(init=init, default=default, metadata={"tag": tag})


class DataType: ...


@dataclass_transform(field_specifiers=(Field, field, attr))
class Struct(DataType, metaclass=DataclassMeta): ...


class ExampleStruct(Struct):
    x: int
    y: int = attr(default=1, init=False)
    z: int


def test_struct():
    class ExampleStruct(Struct):
        x: int
        y: int = attr(
            default=1, init=False
        )  # <--❗Fields with a default value must come after any fields without a default.
        z: int

    ExampleStruct(1, y=2, z=3)
