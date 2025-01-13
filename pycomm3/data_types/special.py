"""
For arbitrarily sized bytes, basically Python's `bytes` class made into a `DataType`
Used in some of the exchange between EtherNet/IP and CIP objects for example.

NOTE: just `BYTES` acts like `BYTES[...]` but repr still includes `[...]`
NOTE: don't use `BYTES` or `BYTES[...]` in anything that calculates the size of the struct, since it's -1 for these
"""

__all__ = ("BYTES", "IPAddress", "IPAddress_BE")

from io import BytesIO
from ipaddress import IPv4Address
from types import EllipsisType
from typing import Self

from ._base import ElementaryDataType, _ElementaryDataTypeMeta
from ._core_types import IntDataType
from .numeric import UDINT, UDINT_BE


class BYTES(ElementaryDataType[bytes], bytes, metaclass=_ElementaryDataTypeMeta):  # type: ignore
    """
    Base type for placeholder bytes, sized to `size`. if `size` is -1, then unlimited

    ignore comment b/c decode() method incompatible w/ bytes.decode(), but it's supposed to be
    b/c we're overriding the bytes behavior to return BYTES not str
    """

    size: int = -1
    _int_type: type[IntDataType] | None = None

    def __new__(cls, value: bytes | int, *args, **kwargs):
        if isinstance(value, int):
            value = bytes([value])
        value = value[: cls.size] if cls.size != -1 else value[:]
        return super().__new__(cls, value, *args, **kwargs)

    def __class_getitem__(cls, item: int | EllipsisType | type[IntDataType]) -> type["BYTES"]:
        size = item if isinstance(item, int) else -1
        _int_type = item if not isinstance(item, (int, EllipsisType)) else None
        klass = type("BYTES", (cls,), {"size": size, "_int_type": _int_type})
        return klass

    @classmethod
    def _encode(cls, value: bytes, *args, **kwargs) -> bytes:
        val = value[: cls.size] if cls.size != -1 else value
        if cls._int_type is not None:
            val = bytes(cls._int_type(len(value))) + value
        return val

    @classmethod
    def _decode(cls, stream: BytesIO) -> Self:
        if cls._int_type is not None:
            size = cls._int_type.decode(stream)
        else:
            size = cls.size
        data = cls._stream_read(stream, size)
        return cls(data)

    def __getitem__(self, item) -> bytes:  # type: ignore
        if isinstance(item, int):
            return super().__getitem__(slice(item, item + 1))

        return super().__getitem__(item)

    def __repr__(self) -> str:
        if self._int_type is not None:
            size = self._int_type.__name__
        else:
            size = "..." if self.size == -1 else self.size
        return f"{self.__class__.__name__}[{size}]({self})"


class IPAddress(UDINT):
    ip: IPv4Address | None = None

    def __new__(cls, value, *args, **kwargs):
        obj = super().__new__(cls, value, *args, **kwargs)
        try:
            obj.ip = IPv4Address(value)
        except ValueError:
            obj.ip = None

        return obj

    def __repr__(self) -> str:
        if self.ip is not None:
            return f"{self.__class__.__name__}('{self.ip}')"
        return f"{self.__class__.__name__}({int.__str__(self)}: 'INVALID')"


class IPAddress_BE(UDINT_BE):
    ip: IPv4Address | None = None

    def __new__(cls, value, *args, **kwargs):
        obj = super().__new__(cls, value, *args, **kwargs)
        try:
            obj.ip = IPv4Address(value)
        except ValueError:
            obj.ip = None
        return obj

    def __repr__(self) -> str:
        if self.ip is not None:
            return f"{self.__class__.__name__}('{self.ip}')"
        return f"{self.__class__.__name__}({int.__str__(self)}: 'INVALID')"
