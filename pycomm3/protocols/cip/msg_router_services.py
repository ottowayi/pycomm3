"""
Base objects for explicit messaging with the MessageRouter object.
Includes request/response types and base service and parser classes
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

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

from .protocol_base import CIPRequest, CIPResponse, CIPResponseParser, SUCCESS

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

    RESPONSE_SERVICE_MASK: ClassVar[int] = 0b1000_0000

    @property
    def request_service(self):
        return self.service ^ self.RESPONSE_SERVICE_MASK


@dataclass
class MsgRouterResponseParser[TR: DataType, TF: DataType]:
    __log = get_logger(__qualname__)
    response_type: type[TR]
    failed_response_type: type[TF]
    success_statuses: set[USINT] = field(default_factory=lambda: {SUCCESS})

    def parse(self, data: BYTES, request: CIPRequest[TR | TF]) -> CIPResponse[TR | TF]:
        resp = MessageRouterResponse.decode(data)
        self.__log.debug("decoded message router response: %r", resp)
        if resp.general_status in self.success_statuses:
            resp_data = self._parse_response_data(resp.data)
            msg = "Success"
        else:
            resp_data = self._parse_failed_response_data(resp.data)
            general_msg, ext_msg = cip_object_from_path(request.message.path).get_status_messages(
                service=request.message.service,
                status=resp.general_status,
                ext_status=resp.additional_status,
                extra_data=resp.data,
            )

            msg = f"{general_msg}({resp.general_status:#04x}): {ext_msg}" if ext_msg else general_msg

        self.__log.debug("decoded message router response data: %r", resp_data)
        return CIPResponse(request=request, message=resp, data=resp_data, status_message=msg)

    def _parse_response_data(self, data: BYTES) -> TR:
        return self.response_type.decode(data)

    def _parse_failed_response_data(self, data: BYTES) -> TF:
        return self.failed_response_type.decode(data)


def message_router_service[TReq: DataType, TResp: DataType, TFResp: DataType](
    *,
    service: USINT,
    class_code: int,
    instance: int | None = 1,
    attribute: "CIPAttribute | None" = None,
    request_data: TReq | None = None,
    request_type: type[TReq],
    response_type: type[TResp],
    failed_response_type: type[TFResp] = BYTES,
    response_parser: CIPResponseParser[TResp | TFResp] | None = None,
    success_statuses: set[USINT] | None = None,
) -> CIPRequest[TResp | TFResp]:
    if request_type is not None and request_data is None:
        raise DataError("this service requires request `data`")
    if request_type is None and data is not None:
        raise DataError("this service does not accept request `data`")

    attr_id = None if attribute is None else attribute.id

    parser = response_parser or MsgRouterResponseParser(
        response_type=response_type,
        failed_response_type=failed_response_type,
        success_statuses={USINT(0)} if success_statuses is None else success_statuses,
    )
    return CIPRequest(
        message=MessageRouterRequest.build(
            service=service,
            class_code=class_code,
            instance=instance or 0,
            attribute=attr_id,
            data=bytes(request_data) if request_data is not None else b"",
        ),
        response_parser=parser,
    )
