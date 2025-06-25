from typing import Literal, Self, overload, Iterable
from collections import UserList
from pycomm3.data_types import (
    PACKED_EPATH,
    PADDED_EPATH,
    PADDED_EPATH_LEN,
    PADDED_EPATH_PAD_LEN,
    PortIdentifier,
    PortSegment,
)
from pycomm3.data_types import EPATH, PORT_ALIASES
from pycomm3.exceptions import DataError


class CIPRoute(UserList):
    def __init__(self, value: str | Iterable[PortSegment] | None = None) -> None:
        if isinstance(value, str):
            segments = self._str_to_port_segments(value)
        elif value is None:
            segments = []
        else:
            segments = value

        if any(not isinstance(x, PortSegment) for x in segments):
            raise DataError("segments all must be instances of PortSegment")

        super().__init__(segments)

    def __truediv__(
        self,
        other: "PortSegment | tuple[int | PortIdentifier | str, int | str | bytes] | EPATH | CIPRoute | str",
    ) -> Self:
        new_segments: tuple[PortSegment, ...] | list[PortSegment]
        match other:
            case PortSegment():
                new_segments = (other,)
            case str():
                new_segments = self._str_to_port_segments(other)
            case (str(), int() | str() | bytes()):
                _port, link = other
                if _port.lower() not in PORT_ALIASES:
                    raise DataError(f"invalid port alias: {_port!r}")
                new_segments = (PortSegment(PORT_ALIASES[_port.lower()], link),)
            case CIPRoute():
                new_segments = other.data
            case EPATH():
                new_segments = other.segments
            case _:
                raise DataError(f"unsupported type {other!r}")

        return self.__class__((*self.data, *new_segments))

    # fmt: off
    @overload
    def epath(self, padded: Literal[False] = False, length: Literal[False] = False, padded_len: Literal[False] = False) -> PACKED_EPATH: ...
    @overload
    def epath(self, padded: Literal[True], length: Literal[False] = False, padded_len: Literal[False] = False) -> PADDED_EPATH: ...
    @overload
    def epath(self, padded: Literal[True], length: Literal[True], padded_len: Literal[False] = False) -> PADDED_EPATH_LEN: ...
    @overload
    def epath(self, padded: Literal[True], length: Literal[True], padded_len: Literal[True]) -> PADDED_EPATH_PAD_LEN: ...
    # fmt: on
    def epath(
        self,
        padded: bool = False,
        length: bool = False,
        padded_len: bool = False,
    ) -> PADDED_EPATH | PACKED_EPATH | PADDED_EPATH_LEN | PADDED_EPATH_PAD_LEN:
        match (padded, length, padded_len):
            case (False, False, False):
                return PACKED_EPATH(self.data)
            case (True, False, False):
                return PADDED_EPATH(self.data)
            case (True, True, False):
                return PADDED_EPATH_LEN(self.data)
            case (True, True, True):
                return PADDED_EPATH_PAD_LEN(self.data)
            case _:
                raise DataError(f"unsupported options for creating EPATH ({padded=}, {length=}, {padded_len})")

    @staticmethod
    def _str_to_port_segments(route: str) -> list[PortSegment]:
        _split_route = route.replace(",", "/").replace("\\", "/").split("/")
        if len(_split_route) % 2:
            raise DataError(f"route must be pairs of port and link, odd number of segments: {_split_route}")
        _pairs = [(_split_route[i], _split_route[i + 1]) for i in range(0, len(_split_route), 2)]
        return [PortSegment(port, link) for port, link in _pairs]
