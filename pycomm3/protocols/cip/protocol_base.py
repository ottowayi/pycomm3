from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol
from pycomm3.data_types import (
    BYTES,
    USINT,
    DataType,
)

if TYPE_CHECKING:
    from .cip_object import CIPObject
    from .base_services import MessageRouterRequest


@dataclass
class CIPRequest:
    message: "MessageRouterRequest"
    response_parser: "CIPResponseParser" = field(repr=False)


class CIPResponseMessage(Protocol):
    general_status: USINT


def default_success_codes_factory() -> set[USINT]:  # 🤢
    return {USINT(0)}


@dataclass
class CIPResponse[T: DataType]:
    request: CIPRequest
    response: CIPResponseMessage
    data: T | None = None
    message: str | None = None
    success_statuses: set[USINT] = field(default_factory=default_success_codes_factory, repr=False)

    def __bool__(self) -> bool:
        return self.response.general_status in self.success_statuses


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
