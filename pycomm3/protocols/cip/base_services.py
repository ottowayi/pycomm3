from typing import Sequence, TYPE_CHECKING
from dataclasses import dataclass, field
from pycomm3.data_types import DataType, UINT
from .protocol_base import CIPService

from .protocol_base import CIPRequest, CIPResponse, CIPResponseParser, default_success_codes_factory
from pycomm3._logging import get_logger
from pycomm3.data_types import (
    LogicalSegmentType,
    LogicalSegment,
    PADDED_EPATH_LEN,
    BYTES,
    attr,
    USINT,
    CIPSegment,
    StructType,
    Array,
)
from pycomm3.exceptions import DataError

if TYPE_CHECKING:
    from .cip_object import CIPAttribute


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

    # @property
    # def cip_object(self) -> "type[CIPObject]":
    #     _log_segs = (x.value for x in self.path if x.segment_type == LogicalSegmentType.type_class_id)  # type: ignore
    #     if not (cls_code := next(_log_segs, None)):
    #         return CIPObject
    #     return CIPObject._objects.get(cls_code, CIPObject)


class MessageRouterResponse(StructType):
    service: USINT
    _reserved: USINT
    general_status: USINT
    addl_status_size: USINT = attr(init=False)
    additional_status: Array[UINT, None] = attr(len_ref="addl_status_size")
    data: BYTES


@dataclass
class MsgRouterResponseParser[RespT: DataType, FRespT: DataType]:
    __log = get_logger(__qualname__)
    response_type: type[RespT]
    failed_response_type: type[FRespT]
    success_statuses: set[USINT] = field(default_factory=default_success_codes_factory)

    def parse(self, data: BYTES, request: CIPRequest) -> CIPResponse[RespT | FRespT]:
        resp = MessageRouterResponse.decode(data)
        self.__log.debug("decoded message route response: %r", resp)
        if resp.general_status in self.success_statuses:
            resp_data = self.response_type.decode(resp.data)
            msg = "Success"
        else:
            resp_data = self.failed_response_type.decode(resp.data)
            general_msg, ext_msg = request.message.cip_object.get_status_messages(
                service=request.message.service,
                status=resp.general_status,
                ext_status=resp.additional_status,
                extra_data=resp.data,
            )

            msg = f"{general_msg}({resp.general_status:#04x}): {ext_msg}" if ext_msg else general_msg

        self.__log.debug("decoded message route response data: %r", resp_data)
        return CIPResponse(request=request, response=resp, data=resp_data, message=msg)


@dataclass(kw_only=True)
class MsgRouterService[ReqT: DataType, RespT: DataType, FRespT: DataType](CIPService):
    request_type: type[ReqT] | None = None
    response_type: type[RespT]
    failed_response_type: type[FRespT] | None = None
    success_statuses: set[USINT] = field(default_factory=default_success_codes_factory)
    response_parser: CIPResponseParser | None = None

    def __call__(
        self,
        data: ReqT | None = None,
        instance: int = 1,
        attribute: "CIPAttribute | None" = None,
        **kwargs,
    ) -> CIPRequest:
        #
        if self.request_type is not None and data is None:
            raise DataError("this service requires request `data`")
        if self.request_type is None and data is not None:
            raise DataError("this service does not accept request `data`")

        attr_id = None if attribute is None else attribute.id
        failed_resp_type = self.failed_response_type if self.failed_response_type is not None else BYTES

        parser = self.response_parser or MsgRouterResponseParser(
            response_type=self.response_type,
            failed_response_type=failed_resp_type,
            success_statuses=self.success_statuses,
        )
        return CIPRequest(
            message=MessageRouterRequest.build(
                service=self.id,
                class_code=self.object.class_code,
                instance=instance,
                attribute=attr_id,
                data=bytes(data) if data is not None else b"",
            ),
            response_parser=parser,
        )


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
