from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from pycomm3.data_types import BYTES, PADDED_EPATH_LEN, UDINT, UINT, USINT, WORD, DataType, StructType, attr

if TYPE_CHECKING:
    from .cip_object import CIPObject


class MessageRouterRequest(StructType):
    service: USINT
    path: PADDED_EPATH_LEN
    data: BYTES


class MessageRouterResponse(StructType):
    service: USINT
    _reserved: USINT = attr(reserved=False)
    general_status: USINT = attr(reserved=False)
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
    success_statuses: set[USINT] = {USINT(0)}

    def __bool__(self) -> bool:
        return self.message.general_status in self.success_statuses


class CIPResponseParser(Protocol):
    def parse(self, data: BYTES, request: CIPRequest) -> CIPResponse: ...


@dataclass
class SimpleCIPResponseParser[T: DataType]:
    response_type: type[T] = attr(default=BYTES)
    failed_response_type: type[T] = attr(default=BYTES)
    success_statuses: set[USINT] = {USINT(0)}

    def parse(self, data: BYTES, request: CIPRequest) -> CIPResponse[T]:
        msg = MessageRouterResponse.decode(data)
        if msg.general_status in self.success_statuses:
            msg_data = self.response_type.decode(msg.data)
        else:
            msg_data = self.failed_response_type.decode(msg.data)
        return CIPResponse(request=request, message=msg, data=msg_data)


@dataclass
class CIPService:
    #: Service code
    id: USINT
    #: Parser used to parse response or None if service has no reply
    response_parser: CIPResponseParser | None = field(default_factory=SimpleCIPResponseParser)

    # set by metaclass
    object: type["CIPObject"] = field(init=False)  # object containing the service attribute
    name: str = field(init=False)  # attribute name (variable name of CIPObject class var)

    def __call__(self, *args, **kwargs) -> CIPRequest: ...
