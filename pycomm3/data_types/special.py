"""
For arbitrarily sized bytes, basically Python's `bytes` class made into a `DataType`
Used in some of the exchange between EtherNet/IP and CIP objects for example.

NOTE: just `BYTES` acts like `BYTES[...]` but repr still includes `[...]`
NOTE: don't use `BYTES` or `BYTES[...]` in anything that calculates the size of the struct, since it's -1 for these
"""

__all__ = ("IPAddress", "IPAddress_BE")

from io import BytesIO
from ipaddress import IPv4Address
from types import EllipsisType
from typing import Self

from ._base import ElementaryDataType, _ElementaryDataTypeMeta
from ._core_types import IntDataType
from .numeric import UDINT, UDINT_BE


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
