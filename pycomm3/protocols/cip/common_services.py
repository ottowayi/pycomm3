from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Sequence, Any, overload

from pycomm3.data_types import BYTES, UINT, USINT, StructType, attr, DataType


from .protocol_base import CIPRequest, CIPResponseParser, CIPService
from .msg_router_services import MessageRouterRequest, MsgRouterResponseParser

if TYPE_CHECKING:
    from .cip_object import CIPAttribute, CIPObject


class StandardClassAttrs(StructType):
    object_revision: UINT
    max_instance: UINT
    num_instances: UINT
    optional_attrs_list: UINT[UINT]
    optional_service_list: UINT[UINT]
    max_class_attr: UINT
    max_instance_attr: UINT


class UnsupportedGetAttrsAll(StructType):
    data: BYTES


@dataclass
class GetAttributesAllService[TObj: CIPObject, Tins: StructType, Tcls: StructType](CIPService[TObj, Tins | Tcls]):
    id: USINT = field(init=False, default=USINT(0x01))
    response_parser: Any = field(init=False, default=None)
    instance_struct: type[Tins]
    class_struct: type[Tcls]

    # @overload
    # def __call__(self, instance: None = None, *args, **kwargs) -> CIPRequest[Tcls]: ...
    # @overload
    # def __call__(self, instance: int = 1, *args, **kwargs) -> CIPRequest[Tins]: ...
    def __call__(self, instance: int | None = 1, *args, **kwargs) -> CIPRequest[Tins | Tcls]:
        if not instance:
            resp_type = self.class_struct
            instance = 0
        else:
            resp_type = self.instance_struct
        parser = MsgRouterResponseParser(response_type=resp_type)
        return CIPRequest(
            message=MessageRouterRequest.build(service=self.id, class_code=self.object.class_code, instance=instance),
            response_parser=parser,
        )


class AttrListItem(StructType):
    id: UINT
    status: UINT

    def __bool__(self) -> bool:
        return self.status == 0


@dataclass
class GetAttributeListService(CIPService):
    id: USINT = field(init=False, default=USINT(0x03))
    response_parser: CIPResponseParser[StructType] | None = field(init=False, default=None)

    def __call__(self, attributes: Sequence["CIPAttribute"], instance: int = 1) -> CIPRequest:
        resp_struct = StructType.create(
            name="GetAttrListResp",
            members=[
                ("count", UINT),
                *(
                    (
                        a.name,
                        AttrListItem.create(
                            name="GetAttrListItem", members=[("data", a.data_type, attr(conditional_on="status"))]
                        ),
                    )
                    for a in attributes
                ),
            ],
        )

        parser = MsgRouterResponseParser(response_type=resp_struct)
        return CIPRequest(
            message=MessageRouterRequest.build(
                service=self.id,
                class_code=self.object.class_code,
                instance=instance,
                data=UINT[UINT](a.id for a in attributes),
            ),
            response_parser=parser,
        )


@dataclass
class GetAttributeSingleService[T: DataType](CIPService):
    id: USINT = field(init=False, default=USINT(0x0E))
    response_parser: CIPResponseParser[T] | None = field(init=False, default=None)

    def __call__(self, attribute: "CIPAttribute", instance: int = 1) -> CIPRequest[T]:
        parser = MsgRouterResponseParser(response_type=attribute.data_type)
        return CIPRequest(
            message=MessageRouterRequest.build(
                service=self.id, class_code=attribute.object.class_code, instance=instance, attribute=attribute.id
            ),
            response_parser=parser,
        )
