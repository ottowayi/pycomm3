from ..cip_object import CIPObject, CIPAttribute, SimpleCIPService
from .._base import MessageRouterRequest
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
)


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
    application_replay_size: USINT = attr(init=False)
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
    application_replay_size: USINT = attr(init=False)
    _reserved: USINT = attr(reserved=True, default=USINT(0))
    application_reply: BYTES = attr(len_ref="application_reply_size")


class ForwardCloseFailedResponse(StructType):
    connection_serial: UDINT
    originator_vendor_id: UINT
    originator_serial: UDINT
    remaining_path_size: USINT
    _reserved: USINT = attr(reserved=True, default=USINT(0))


class UnconnectedSendRequest(StructType):
    priority_tick_time: USINT
    timeout_ticks: USINT
    message_request_size: UINT = attr(init=False)
    message_request: MessageRouterRequest
    _reserved: USINT = attr(reserved=True, default=USINT(0))
    route_path: PADDED_EPATH_PAD_LEN


class UnconnectedSendResponse(StructType):
    reply_service: USINT
    _reserved: USINT = attr(reserved=True, default=USINT(0))
    general_status: USINT
    _reserved2: USINT = attr(reserved=True, default=USINT(0))
    service_response_data: BYTES


class UnconnectedSendFailedResponse(StructType):
    reply_service: USINT
    _reserved: USINT = attr(reserved=True, default=USINT(0))
    general_status: USINT
    additional_status: UINT[USINT]
    remaining_path_size: USINT


# def _bit_count(arr: ArrayType[BOOL, int] ) -> int:
#     return 0  # TODO: need to change encode/decode len_ref to get array and not just len


# class ConnectionEntryList(StructType):
#     num_entries: UINT
#     conn_open_bits: BOOL[...] = attr(len_ref=(
#         'num_entries',
#         lambda x: (x - 8 - 1) // 8,
#         lambda x: _bit_count,
#     ))


class ConnectionManagerObject(CIPObject):
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

    unconnected_send = SimpleCIPService(
        id=USINT(0x52),
        request_type=UnconnectedSendRequest,
        response_type=UnconnectedSendResponse,
        failed_response_type=UnconnectedSendFailedResponse,
    )

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
        "Any": {
            0x01: {
                0x0100: "Connection in use or duplicate forward_open",
                0x0103: "Transport class and trigger combination not supported",
                0x0106: "Ownership conflict",
                0x0107: "Target connection not found",
                0x0108: "Invalid network connection parameter",
                0x0109: "Invalid connection size",
                0x0110: "Target for connection not configured",
                0x0111: "RPI not supported",
                0x0113: "Out of connections",
                0x0114: "Vendor ID of product code mismatch",
                0x0115: "Product type mismatch",
                0x0116: "Revision mismatch",
                0x0117: "Invalid produced or consumed application path",
                0x0118: "Invalid or inconsistent configuration application path",
                0x0119: "Non-listen only connection not opened",
                0x011A: "Target object out of connections",
                0x011B: "RPI is smaller than the production inhibit time",
                0x0203: "Connection timed out",
                0x0204: "Unconnected request timed out",
                0x0205: "Parameter error in unconnected request service",
                0x0206: "Message too large for unconnected_send service",
                0x0207: "Unconnected acknowledge without reply",
                0x0301: "No buffer memory available",
                0x0302: "Network bandwidth not available for data",
                0x0303: "No consumed connection ID filter available",
                0x0304: "Not configured to send scheduled priority data",
                0x0305: "Schedule signature mismatch",
                0x0306: "Schedule signature validation not possible",
                0x0311: "Port not available",
                0x0312: "Link address not valid",
                0x0315: "Invalid segment in connection path",
                0x0316: "Error in forward close service connection path",
                0x0317: "Scheduling not specified",
                0x0318: " Link address to self invalid",
                0x0319: "Secondary resources unavailable",
                0x031A: "Rack connection already established",
                0x031C: "Miscellaneous",
                0x031D: "Redundant connection mismatch",
                0x031E: "No more user configurable link consumer resources available in the producing module",
                0x031F: "No more user configurable link consumer resources available in the producing module",
                0x0800: "Network link in path to module is offline",
                0x0810: "No target application data available",
                0x0811: "No originator application data available",
                0x0812: "Node address has changed since the network was scheduled",
                0x0813: "Not configured for off-subnet multicast",
            },
            0x09: {
                None: "Error in data segment",  # ext. status is the index of the error in the segment
            },
            0x0C: {
                None: "Object state error - (optional) ext. status is the object's state",
            },
            0x10: {
                None: "Device state error - (optional) ext. status is the device's state",
            },
        }
    }
