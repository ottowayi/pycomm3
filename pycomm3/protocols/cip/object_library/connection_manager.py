from pycomm3.util import StatusEnum
from ..cip_object import CIPObject, CIPAttribute, SimpleCIPResponseParser, SimpleCIPService, GeneralStatusCodes
from .._base import CIPRequest, CIPService, MessageRouterRequest, CIPRoute, CIPResponse
from pycomm3.map import EnumMap
from pycomm3.data_types import (
    UINT,
    UDINT,
    attr,
    StructType,
    USINT,
    BYTES,
    PADDED_EPATH_LEN,
    WORD,
    DWORD,
    PADDED_EPATH_PAD_LEN,
    as_stream,
)
from typing import ClassVar, Self
from dataclasses import InitVar
from enum import IntEnum
from dataclasses import field
from io import BytesIO
from dataclasses import dataclass
from pycomm3._logging import get_logger


class ForwardOpenRequest(StructType):
    priority_tick_time: USINT
    timeout_ticks: USINT
    o2t_connection_id: UDINT
    t2o_connection_id: UDINT
    connection_serial: UINT
    originator_vendor_id: UINT
    originator_serial: UDINT
    timeout_multiplier: USINT
    _reserved: BYTES[3] | bytes = attr(reserved=True, default=b"\x00" * 3)
    o2t_rpi: UDINT
    o2t_connection_params: WORD
    t2o_rpi: UDINT
    t2o_connection_params: WORD
    transport_type: USINT
    connection_path: PADDED_EPATH_LEN


class LargeForwardOpenRequest(StructType):
    priority_tick_time: USINT
    timeout_ticks: USINT
    o2t_connection_id: UDINT
    t2o_connection_id: UDINT
    connection_serial: UINT
    originator_vendor_id: UINT
    originator_serial: UDINT
    timeout_multiplier: USINT
    _reserved: BYTES[3] | bytes = attr(reserved=True, default=b"\x00" * 3)
    o2t_rpi: UDINT
    o2t_connection_params: DWORD
    t2o_rpi: UDINT
    t2o_connection_params: DWORD
    transport_type: USINT
    connection_path: PADDED_EPATH_LEN


class ForwardOpenResponse(StructType):
    o2t_connection_id: UDINT
    t20_connection_id: UDINT
    connection_serial: UDINT
    originator_vendor_id: UINT
    originator_serial: UDINT
    o2t_api: UDINT
    t2o_api: UDINT
    application_reply_size: USINT = attr(init=False)
    _reserved: USINT = attr(reserved=True, default=USINT(0))
    application_reply: BYTES = attr(len_ref="application_reply_size")


class ForwardOpenFailedResponse(StructType):
    connection_serial: UDINT
    originator_vendor_id: UINT
    originator_serial: UDINT
    remaining_path_size: USINT
    _reserved: USINT = attr(reserved=True, default=USINT(0))


class ForwardCloseRequest(StructType):
    priority_tick_time: USINT
    timeout_ticks: USINT
    connection_serial: UINT
    originator_vendor_id: UINT
    originator_serial: UDINT
    connection_path: PADDED_EPATH_PAD_LEN


class ForwardCloseResponse(StructType):
    connection_serial: UDINT
    originator_vendor_id: UINT
    originator_serial: UDINT
    application_reply_size: USINT = attr(init=False)
    _reserved: USINT = attr(reserved=True, default=USINT(0))
    application_reply: BYTES = attr(len_ref="application_reply_size")


class ForwardCloseFailedResponse(StructType):
    connection_serial: UDINT
    originator_vendor_id: UINT
    originator_serial: UDINT
    remaining_path_size: USINT
    _reserved: USINT = attr(reserved=True, default=USINT(0))


class TickTime(IntEnum):
    """
    Time per tick (in milliseconds)
    """

    ms_1 = 0b_0000
    ms_2 = 0b_0001
    ms_4 = 0b_0010
    ms_8 = 0b_0011
    ms_16 = 0b_0100
    ms_32 = 0b_0101
    ms_64 = 0b_0110
    ms_128 = 0b_0111
    ms_256 = 0b_1000
    ms_512 = 0b_1001
    ms_1024 = 0b_1010
    ms_2048 = 0b_1011
    ms_4096 = 0b_1100
    ms_8192 = 0b_1101
    ms_16384 = 0b_1110
    ms_32768 = 0b_1111


class UnconnectedSendRequest(StructType):
    """

    Request timeout = tick_time * num_ticks
    Default timeout is 1024ms

    TODO: size may be off by 1 due to padding if `message_request_size` is odd or not
    """

    priority_tick_time: USINT = attr(init=False)
    timeout_ticks: USINT = attr(init=False)
    message_request_size: UINT = attr(init=False)
    message_request: MessageRouterRequest
    route_path: PADDED_EPATH_PAD_LEN

    tick_time: InitVar[TickTime]
    num_ticks: InitVar[int]
    priority: InitVar[bool] = False
    PRIORITY: ClassVar[USINT] = USINT(0b_000_1_0000)

    def __post_init__(
        self, tick_time: TickTime = TickTime.ms_1024, num_ticks: int = 1, priority: bool = False, *args, **kwargs
    ) -> None:
        _priority = self.PRIORITY if priority else USINT(0)
        self.priority_tick_time = USINT(_priority | tick_time)
        self.timeout_ticks = USINT(num_ticks)
        self.message_request_size = UINT(len(bytes(self.message_request)))

    @classmethod
    def _decode(cls, stream: BytesIO) -> Self:
        ptt = USINT.decode(stream)
        tick_time = TickTime(ptt | 0b_0000_1111)
        priority = bool(ptt & cls.PRIORITY)
        ticks = USINT.decode(stream)
        request_size = UINT.decode(stream)
        request_data = cls._stream_read(stream, request_size)
        request = MessageRouterRequest.decode(request_data)
        if request_size % 2:
            pad = cls._stream_read(stream, 1)
        route_path = PADDED_EPATH_PAD_LEN.decode(stream)

        return cls(
            message_request=request,
            route_path=route_path,
            tick_time=tick_time,
            num_ticks=ticks,
            priority=priority,
        )

    @classmethod
    def _encode(cls, value: Self, *args, **kwargs) -> bytes:
        return b"".join(
            bytes(x)
            for x in (
                value.priority_tick_time,
                value.timeout_ticks,
                value.message_request_size,
                value.message_request,
                b"\x00" if value.message_request_size % 2 else b"",
                value.route_path,
            )
        )


class UnconnectedSendResponseHeader(StructType):
    reply_service: USINT
    _reserved: USINT = attr(reserved=True, default=USINT(0))
    general_status: USINT


class UnconnectedSendSuccessResponse(StructType):
    _reserved2: USINT = attr(reserved=True, default=USINT(0))
    service_response_data: BYTES


class UnconnectedSendFailedResponse(StructType):
    additional_status: UINT[USINT]
    remaining_path_size: USINT


def _unconnected_send_parser():
    return SimpleCIPResponseParser(response_type=BYTES, failed_response_type=BYTES)


@dataclass
class UnconnectedSendResponseParser(SimpleCIPResponseParser):
    __log = get_logger(__qualname__)

    failed_response_type: type[BYTES] = field(init=False, default=BYTES)

    def parse(self, data: BYTES, request: CIPRequest) -> CIPResponse:
        buff = as_stream(data)
        header = UnconnectedSendResponseHeader.decode(buff)
        self.__log.debug("decoded unconnected send response header: %r", header)
        self.__log.debug(f"status={header.general_status}")
        if header.general_status in self.success_statuses:
            resp_data = UnconnectedSendSuccessResponse.decode(buff)
            msg_data = self.response_type.decode(resp_data.service_response_data)
        else:
            msg_data = UnconnectedSendFailedResponse.decode(buff)
        self.__log.debug("decoded unconnected send response data: %r", header)
        return CIPResponse(request=request, message=header, data=msg_data)


@dataclass
class UnconnectedSendService(CIPService):
    id: USINT = field(default=USINT(0x52), init=False)
    response_parser: None = None  # type: ignore

    def __call__(
        self,
        msg: CIPRequest,
        route_path: CIPRoute,
        tick_time: TickTime,
        num_ticks: int,
        *args,
        **kwargs,
    ):
        return CIPRequest(
            message=MessageRouterRequest.build(
                service=self.id,
                class_code=self.object.class_code,
                instance=1,
                data=UnconnectedSendRequest(
                    message_request=msg.message,
                    route_path=route_path.epath(padded=True, length=True, padded_len=True),
                    tick_time=tick_time,
                    num_ticks=num_ticks,
                ),
            ),
            response_parser=UnconnectedSendResponseParser(response_type=msg.response_parser.response_type),
        )


# def _bit_count(arr: ArrayType[BOOL, int] ) -> int:
#     return 0  # TODO: need to change encode/decode len_ref to get array and not just len


# class ConnectionEntryList(StructType):
#     num_entries: UINT
#     conn_open_bits: BOOL[...] = attr(len_ref=(
#         'num_entries',
#         lambda x: (x - 8 - 1) // 8,
#         lambda x: _bit_count,
#     ))


class ConnMgrExtStatusCodesConnFailure(StatusEnum):
    """
    Connection Manager Extended Status code for General Status Code 0x01 - Connection failure
    """

    connection_in_use = 0x0100, "Connection in use or duplicate forward_open"
    transport_class_trigger_unsupported = 0x0103, "Transport class and trigger combination not supported"
    ownership_conflict = 0x0106, "Connection cannot be established due to another having exclusive ownership of a required resource"  # fmt: skip
    connection_missing = 0x0107, "Target connection not found"
    invalid_network_parameter = 0x0108, "A network connection parameter not supported by target/router"
    invalid_connection_size = 0x0109, "Requested connection size not supported by target/router"
    connection_not_configured = 0x0110, "Requested connection has not configured"
    unsupported_rpi = 0x0111, "Requested rpi or timeout value not supported by device"
    out_of_connections = 0x0113, "Connection Manager out of connections"
    # = 0x0114, "Vendor ID of product code mismatch"
    # = 0x0115, "Product type mismatch"
    # = 0x0116, "Revision mismatch"
    # = 0x0117, "Invalid produced or consumed application path"
    # = 0x0118, "Invalid or inconsistent configuration application path"
    # = 0x0119, "Non-listen only connection not opened"
    # = 0x011A, "Target object out of connections"
    # = 0x011B, "RPI is smaller than the production inhibit time"
    # = 0x0203, "Connection timed out"
    # = 0x0204, "Unconnected request timed out"
    # = 0x0205, "Parameter error in unconnected request service"
    # = 0x0206, "Message too large for unconnected_send service"
    # = 0x0207, "Unconnected acknowledge without reply"
    # = 0x0301, "No buffer memory available"
    # = 0x0302, "Network bandwidth not available for data"
    # = 0x0303, "No consumed connection ID filter available"
    # = 0x0304, "Not configured to send scheduled priority data"
    # = 0x0305, "Schedule signature mismatch"
    # = 0x0306, "Schedule signature validation not possible"
    # = 0x0311, "Port not available"
    # = 0x0312, "Link address not valid"
    # = 0x0315, "Invalid segment in connection path"
    # = 0x0316, "Error in forward close service connection path"
    # = 0x0317, "Scheduling not specified"
    # = 0x0318, " Link address to self invalid"
    # = 0x0319, "Secondary resources unavailable"
    # = 0x031A, "Rack connection already established"
    # = 0x031C, "Miscellaneous"
    # = 0x031D, "Redundant connection mismatch"
    # = 0x031E, "No more user configurable link consumer resources available in the producing module"
    # = 0x031F, "No more user configurable link consumer resources available in the producing module"
    # = 0x0800, "Network link in path to module is offline"
    # = 0x0810, "No target application data available"
    # = 0x0811, "No originator application data available"
    # = 0x0812, "Node address has changed since the network was scheduled"
    # = 0x0813, "Not configured for off-subnet multicast"


class ConnectionManager(CIPObject):
    """
    Manages internal resources for both I/O and Explicit Messaging connections.
    """

    class_code = 0x06
    _class_all_exclude = {"optional_attrs_list", "optional_service_list"}

    #: Number of received Forward Open requests
    open_requests = CIPAttribute(id=1, data_type=UINT)
    #: Number of Forward Open requests rejected because of bad formatting
    open_format_rejects = CIPAttribute(id=2, data_type=UINT)
    #: Number of Forward Open requests rejected for lack of resources
    open_resource_rejects = CIPAttribute(id=3, data_type=UINT)
    #: Number of Forward Open requests reject for reasons other than bad formatting or lack of resources
    open_other_rejects = CIPAttribute(id=4, data_type=UINT)
    #: Number of received Forward Close requests
    close_requests = CIPAttribute(id=5, data_type=UINT)
    #: Number of Forward Close requests rejected because of bad formatting
    close_format_rejects = CIPAttribute(id=6, data_type=UINT)
    #: Number of Forward Close requests reject for reasons other than bad formatting
    close_other_rejects = CIPAttribute(id=7, data_type=UINT)
    #: Number of connection timeouts in connections managed by this instance
    connection_timeout = CIPAttribute(id=8, data_type=UINT)
    #: List of connections, each positive bit corresponds to a connection instance
    # TODO connection_entry_list = CIPAttribute(id=9, data_type=...)
    # attribute 10 is reserved or obsolete
    #: CPU utilization as tenths of a percent, 0-100% scaled to 0-1000
    cpu_utilization = CIPAttribute(id=11, data_type=UINT)
    #: Total size (in bytes) of the buffer
    max_buffer_size = CIPAttribute(id=12, data_type=UDINT)
    #: Currently available size (in bytes) of the buffer
    buffer_size_remaining = CIPAttribute(id=13, data_type=UDINT)

    #  --- services ---
    #: Closes a connection
    forward_close = SimpleCIPService(
        id=USINT(0x4E),
        request_type=ForwardCloseRequest,
        response_type=ForwardCloseResponse,
        failed_response_type=ForwardCloseFailedResponse,
    )
    #: Opens a connection with a maximum data size of 511 bytes
    forward_open = SimpleCIPService(
        id=USINT(0x54),
        request_type=ForwardOpenRequest,
        response_type=ForwardOpenResponse,
        failed_response_type=ForwardOpenFailedResponse,
    )
    #: Opens a connection with a maximum data size of 65535 bytes
    large_forward_open = SimpleCIPService(
        id=USINT(0x5B),
        request_type=LargeForwardOpenRequest,
        response_type=ForwardOpenResponse,
        failed_response_type=ForwardOpenFailedResponse,
    )

    unconnected_send = UnconnectedSendService()

    class Instance(CIPObject.Instance):
        open_request = 0x01
        open_format_rejected = 0x02
        open_resource_rejected = 0x03
        open_other_rejected = 0x04
        close_request = 0x05
        close_format_request = 0x06
        close_other_request = 0x07
        connection_timeout = 0x08

    class Services(EnumMap):
        """
        Custom services supported by the Connection Manager
        """

        #: Closes a connection
        forward_close = b"\x4e"
        #: TODO: explain unconnected send
        unconnected_send = b"\x52"
        #: Opens a connection with a maximum data size of 511 bytes
        forward_open = b"\x54"
        #: Opens a connection with a maximum data size of 65535 bytes
        large_forward_open = b"\x5b"
        #: For connection diagnostics
        get_connection_data = b"\x56"
        #: For connection diagnostics
        search_connection_data = b"\x57"
        #: Determine the owner of a redundant connection
        get_connection_owner = b"\x5a"

    STATUS_CODES = {
        "*": {
            GeneralStatusCodes.connection_failure: ConnMgrExtStatusCodesConnFailure,
            GeneralStatusCodes.invalid_attribute: {
                "*": "Error in data segment",  # ext. status is the index of the error in the segment
            },
            0x0C: {
                "*": "Object state error - (optional) ext. status is the object's state",
            },
            0x10: {
                "*": "Device state error - (optional) ext. status is the device's state",
            },
        }
    }
