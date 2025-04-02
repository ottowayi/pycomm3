"""
Base objects for explicit messaging with the MessageRouter object.
Includes request/response types and base service and parser classes
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pycomm3._logging import get_logger
from pycomm3.data_types import (
    BYTES,
    PADDED_EPATH_LEN,
    UINT,
    USINT,
    Array,
    DataType,
    LogicalSegment,
    LogicalSegmentType,
    StructType,
    EPATH,
    attr,
)
from pycomm3.exceptions import DataError

from .protocol_base import CIPRequest, CIPResponse, CIPResponseParser, CIPService, default_success_codes_factory

if TYPE_CHECKING:
    from .cip_object import CIPAttribute, CIPObject


def cip_object_from_path(path: EPATH) -> "type[CIPObject]":
    """
    Return the CIPObject class for the first LogicalSegment of type class id in the `path`,
    else `CIPObject` if not found.
    """
    from .cip_object import CIPObject  # fuck it, I give up on circular imports

    _log_segs = (x.value for x in path if x.segment_type == LogicalSegmentType.type_class_id)  # type: ignore
    if not (cls_code := next(_log_segs, None)):
        return CIPObject
    return CIPObject.__cip_objects__.get(cls_code, CIPObject)


class MessageRouterRequest(StructType):
    service: USINT | int
    path: PADDED_EPATH_LEN
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
        _data = BYTES(data if isinstance(data, bytes) else bytes(data))
        return MessageRouterRequest(service=service, path=PADDED_EPATH_LEN(cip_segments), data=_data)


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
        self.__log.debug("decoded message router response: %r", resp)
        if resp.general_status in self.success_statuses:
            resp_data = self.response_type.decode(resp.data)
            msg = "Success"
        else:
            resp_data = self.failed_response_type.decode(resp.data)
            general_msg, ext_msg = cip_object_from_path(request.message.path).get_status_messages(
                service=request.message.service,
                status=resp.general_status,
                ext_status=resp.additional_status,
                extra_data=resp.data,
            )

            msg = f"{general_msg}({resp.general_status:#04x}): {ext_msg}" if ext_msg else general_msg

        self.__log.debug("decoded message router response data: %r", resp_data)
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
