__all__ = ("IPAddress", "IPAddress_BE", "Revision")

from ipaddress import IPv4Address

from ._base import StructType
from .numeric import UDINT, UDINT_BE, USINT


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


class Revision(StructType):
    major: USINT
    minor: USINT
