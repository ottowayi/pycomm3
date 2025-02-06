from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, Sequence

from pycomm3.data_types import (
    BYTES,
    PADDED_EPATH_LEN,
    USINT,
    WORD,
    DataType,
    StructType,
    attr,
    CIPSegment,
    LogicalSegment,
)
from pycomm3.data_types.cip import LogicalSegmentType

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
    additional_status: WORD[...] = attr(len_ref=("addl_status_size", lambda x: x * 2, lambda x: x // 2))
    data: BYTES

    # __field_descriptions__: ClassVar[dict] = {'general_status': SERVICE_STATUS}


@dataclass
class CIPRequest:
    message: MessageRouterRequest
    response_parser: "CIPResponseParser"


@dataclass
class CIPResponse[T: DataType]:
    request: CIPRequest
    message: MessageRouterResponse
    data: T | None = None
    success_statuses: set[USINT] = field(default_factory=default_success_codes_factory)

    def __bool__(self) -> bool:
        return self.message.general_status in self.success_statuses


class CIPResponseParser(Protocol):
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
