from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Sequence

from pycomm3.data_types import (
    BYTES,
    UINT,
    USINT,
    StructType,
)

from .protocol_base import CIPRequest, CIPResponseParser, CIPService
from .msg_router_services import MessageRouterRequest, MsgRouterResponseParser

if TYPE_CHECKING:
    from .cip_object import CIPAttribute


class CIPObjectGetAttrsAllClass(StructType):
    object_revision: UINT
    max_instance: UINT
    num_instances: UINT
    optional_attrs_list: UINT[UINT]
    optional_service_list: UINT[UINT]
    max_class_attr: UINT
    max_instance_attr: UINT


@dataclass
class GetAttributesAllService(CIPService):
    id: USINT = field(init=False, default=USINT(0x01))
    response_parser: CIPResponseParser | None = field(init=False, default=None)
    instance_struct: type[StructType]
    class_struct: type[StructType] = CIPObjectGetAttrsAllClass

    def __call__(self, instance: int = 1) -> CIPRequest:
        parser = MsgRouterResponseParser(
            response_type=self.class_struct if instance == self.object.Instance.CLASS else self.instance_struct,
            failed_response_type=BYTES,
        )
        return CIPRequest(
            message=MessageRouterRequest.build(service=self.id, class_code=self.object.class_code, instance=instance),
            response_parser=parser,
        )


@dataclass
class GetAttributeListService(CIPService):
    id: USINT = field(init=False, default=USINT(0x03))
    response_parser: CIPResponseParser | None = field(init=False, default=None)

    def __call__(self, attribute: Sequence["CIPAttribute"], instance: int = 1) -> CIPRequest:
        parser = MsgRouterResponseParser(
            response_type=attribute.data_type,
            failed_response_type=BYTES,
        )
        return CIPRequest(
            message=MessageRouterRequest.build(service=self.id, class_code=self.object.class_code, instance=instance),
            response_parser=parser,
        )


@dataclass
class GetAttributeSingleService(CIPService):
    id: USINT = field(init=False, default=USINT(0x0E))
    response_parser: CIPResponseParser | None = field(init=False, default=None)

    def __call__(self, attribute: "CIPAttribute", instance: int = 1) -> CIPRequest:
        parser = MsgRouterResponseParser(
            response_type=attribute.data_type,
            failed_response_type=BYTES,
        )
        return CIPRequest(
            message=MessageRouterRequest.build(
                service=self.id, class_code=attribute.object.class_code, instance=instance, attribute=attribute.id
            ),
            response_parser=parser,
        )
