"""
For arbitrarily sized bytes, basically Python's `bytes` class made into a `DataType`
Used in some of the exchange between EtherNet/IP and CIP objects for example.

NOTE: just `BYTES` acts like `BYTES[...]` but repr still includes `[...]`
NOTE: don't use `BYTES` or `BYTES[...]` in anything that calculates the size of the struct, since it's -1 for these
"""

__all__ = ("BYTES",)
from io import BytesIO
from typing import TypeVar

from ._base import ElementaryDataType, _ElementaryDataTypeMeta

_BytesType = TypeVar("_BytesType", bound="BYTES")


class BYTES(ElementaryDataType[bytes], bytes, metaclass=_ElementaryDataTypeMeta):  # type: ignore
    """
    Base type for placeholder bytes, sized to `size`. if `size` is -1, then unlimited

    ignore comment b/c decode() method incompatible w/ bytes.decode(), but it's supposed to be
    b/c we're overriding the bytes behavior to return BYTES not str
    """

    size = -1

    def __new__(cls: type[_BytesType], value: bytes, *args, **kwargs) -> _BytesType:
        if isinstance(value, int):
            value = bytes([value])
        value = value[: cls.size] if cls.size != -1 else value[:]
        return super().__new__(cls, value, *args, **kwargs)  # type: ignore

    def __class_getitem__(cls, item: int | type(Ellipsis)) -> type[_BytesType]:
        if item is Ellipsis:
            item = -1

        class BYTES(cls):  # noqa
            size = item

        return BYTES

    @classmethod
    def _encode(cls: type[_BytesType], value: bytes, *args, **kwargs) -> bytes:
        return value[: cls.size] if cls.size != -1 else value

    @classmethod
    def _decode(cls: type[_BytesType], stream: BytesIO) -> _BytesType:
        data = cls._stream_read(stream, cls.size)
        return cls(data)

    def __getitem__(self, item) -> bytes:  # type: ignore
        if isinstance(item, int):
            return super().__getitem__(slice(item, item + 1))

        return super().__getitem__(item)

    def __repr__(self) -> str:
        size = "..." if self.size == -1 else self.size
        return f"{self.__class__.__name__}[{size}]({self})"
