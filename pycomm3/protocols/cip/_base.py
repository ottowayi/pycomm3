from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol, Self, Sequence, overload, Iterable
from collections import UserList
from pycomm3.data_types import (
    BYTES,
    PACKED_EPATH,
    PADDED_EPATH,
    PADDED_EPATH_LEN,
    PADDED_EPATH_PAD_LEN,
    USINT,
    UINT,
    CIPSegment,
    DataType,
    LogicalSegment,
    PortIdentifier,
    PortSegment,
    StructType,
    attr,
)
from pycomm3.data_types.cip import EPATH, PORT_ALIASES, LogicalSegmentType
from pycomm3.exceptions import DataError

if TYPE_CHECKING:
    from .cip_object import CIPObject


def default_success_codes_factory() -> set[USINT]:  # 🤢
    return {USINT(0)}


class MessageRouterRequest(StructType):
    service: USINT | int
    path: PADDED_EPATH_LEN | Sequence[CIPSegment]
    data: BYTES | bytes

    @staticmethod
    def build(
        service: int,
        class_code: int,
        instance: int,
        attribute: int | None = None,
        data: DataType | bytes = b"",
    ) -> "MessageRouterRequest":
        cip_segments = [
            LogicalSegment(LogicalSegmentType.type_class_id, class_code),
            LogicalSegment(LogicalSegmentType.type_instance_id, instance),
        ]
        if attribute is not None:
            cip_segments.append(LogicalSegment(LogicalSegmentType.type_attribute_id, attribute))
        _data = BYTES(data) if isinstance(data, bytes) else bytes(data)
        return MessageRouterRequest(service=service, path=PADDED_EPATH_LEN(cip_segments), data=_data)


class MessageRouterResponse(StructType):
    service: USINT
    _reserved: USINT
    general_status: USINT
    addl_status_size: USINT = attr(init=False)
    additional_status: UINT[...] = attr(len_ref="addl_status_size")
    data: BYTES


@dataclass
class CIPRequest:
    message: MessageRouterRequest
    response_parser: "CIPResponseParser"


class CIPResponseMessage(Protocol):
    general_status: USINT


@dataclass
class CIPResponse[T: DataType]:
    request: CIPRequest
    message: CIPResponseMessage
    data: T | None = None
    success_statuses: set[USINT] = field(default_factory=default_success_codes_factory)

    def __bool__(self) -> bool:
        return self.message.general_status in self.success_statuses


class CIPResponseParser[T: DataType](Protocol):
    response_type: type[T]

    def parse(self, data: BYTES, request: CIPRequest) -> CIPResponse:
        raise NotImplementedError


@dataclass
class CIPService:
    #: Service code
    id: USINT
    #: Parser used to parse response or None if service has no reply
    response_parser: CIPResponseParser | None

    # set by metaclass
    object: type["CIPObject"] = field(init=False)  # object containing the service attribute
    name: str = field(init=False)  # attribute name (variable name of CIPObject class var)

    def __call__(self, *args, **kwargs) -> CIPRequest:
        raise NotImplementedError


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
        other: "PortSegment | tuple[int | PortIdentifier | str, int | str | bytes] | EPATH | CIPRoute",
    ) -> Self:
        new_segments: tuple[PortSegment, ...] | list[PortSegment]
        match other:
            case PortSegment():
                new_segments = (other,)
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
