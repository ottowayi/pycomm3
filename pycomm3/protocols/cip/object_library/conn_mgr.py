from copy import deepcopy
from dataclasses import dataclass
from enum import IntEnum

from .base import CIPAttribute, CIPObject, CIPService, SimpleCIPService
from ..cip import CIPRequest, CIPResponse
from ....data_types import UINT, USINT, Struct, UDINT, BYTES, PADDED_EPATH_WITH_LEN, PADDED_EPATH_WITH_PADDED_LEN, StructType
from ....map import EnumMap
from ....exceptions import DataError


_forward_open_request_type = Struct(
    USINT('priority_tick_time'),
    USINT('timeout_ticks'),
    UDINT('o_t_connection_id'),
    UDINT('t_o_connection_id'),
    UINT('connection_serial'),
    UINT('vendor_id'),
    UDINT('originator_serial'),
    USINT('timeout_multiplier'),
    BYTES[3]('reserved'),
    UDINT('o_t_rpi'),
    UINT('o_t_connection_params'),
    UDINT('t_o_rpi'),
    UINT('t_o_connection_params'),
    USINT('transport_type'),
    PADDED_EPATH_WITH_LEN('connection_path'),
)

_large_forward_open_request_type = Struct(
        USINT('priority_tick_time'),
        USINT('timeout_ticks'),
        UDINT('o_t_connection_id'),
        UDINT('t_o_connection_id'),
        UINT('connection_serial'),
        UINT('vendor_id'),
        UDINT('originator_serial'),
        USINT('timeout_multiplier'),
        BYTES[3]('reserved'),
        UDINT('o_t_rpi'),
        UDINT('o_t_connection_params'),
        UDINT('t_o_rpi'),
        UDINT('t_o_connection_params'),
        USINT('transport_type'),
        PADDED_EPATH_WITH_LEN('connection_path'),
)


_forward_open_response_type = Struct(
    UDINT('o_t_connection_id'),
    UDINT('t_o_connection_id'),
    UINT('connection_serial'),
    UINT('vendor_id'),
    UDINT('originator_serial'),
    UDINT('o_t_api'),
    UDINT('t_o_api'),
    BYTES[UINT]('application_reply'),
)

_forward_open_close_failed_response_type = Struct(
    UINT('connection_serial'),
    UINT('vendor_id'),
    UDINT('originator_serial'),
    USINT('remaining_path_size'),
    USINT('reserved'),
)


_forward_close_request_type = Struct(
    USINT('priority_tick_time'),
    USINT('timeout_ticks'),
    UINT('connection_serial'),
    UINT('vendor_id'),
    UDINT('originator_serial'),
    PADDED_EPATH_WITH_PADDED_LEN('connection_path')
)

_forward_close_response_type = Struct(
    UINT('connection_serial'),
    UINT('vendor_id'),
    UDINT('originator_serial'),
    BYTES[UINT]('application_reply'),
)


class UnconnectedSendRequest(CIPRequest):

    def __init__(self, request: CIPRequest, priority: int, timeout_ticks: int, route_path: bytes):
        self.request = request

        msg = b''.join((
            USINT.encode(priority),
            USINT.encode(timeout_ticks),
            UINT.encode(len(self.request.message)),
            self.request.message,
            b"\x00" if len(self.request.message) % 2 else b"",
            route_path,
        ))

        super().__init__(
           service=UnconnectedSendService.id,
           class_code=ConnectionManagerObject.class_code,
           instance=CIPObject.Instance.DEFAULT,
           request_data=msg,
        )


@dataclass(frozen=True)
class UnconnectedSendService(CIPService):
    id: int = 0x52

    def __call__(
        self,
        request: CIPRequest,
        priority: int,
        timeout_ticks: int,
        route_path: bytes,
    ) -> UnconnectedSendRequest:
        return UnconnectedSendRequest(request, priority, timeout_ticks, route_path)


class ConnectionManagerObject(CIPObject):
    """
    Manages internal resources for both I/O and Explicit Messaging connections.
    """

    class_code = 0x06
    _class_all_exclude = {'optional_attrs_list', 'optional_service_list'}

    #: Number of received Forward Open requests
    open_requests = CIPAttribute(id=1, type=UINT)
    #: Number of Forward Open requests rejected because of bad formatting
    open_format_rejects = CIPAttribute(id=2, type=UINT)
    #: Number of Forward Open requests rejected for lack of resources
    open_resource_rejects = CIPAttribute(id=3, type=UINT)
    #: Number of Forward Open requests reject for reasons other than bad formatting or lack of resources
    open_other_rejects = CIPAttribute(id=4, type=UINT)
    #: Number of received Forward Close requests
    close_requests = CIPAttribute(id=5, type=UINT)
    #: Number of Forward Close requests rejected because of bad formatting
    close_format_rejects = CIPAttribute(id=6, type=UINT)
    #: Number of Forward Close requests reject for reasons other than bad formatting
    close_other_rejects = CIPAttribute(id=7, type=UINT)
    #: Number of connection timeouts in connections managed by this instance
    connection_timeout = CIPAttribute(id=8, type=UINT)
    # connection_entry_list (9) not implemented, requires a custom type
    # TODO: for get_attributes_all to work connection_entry_list needs to be added
    # attribute 10 is reserved or obsolete
    #: CPU utilization as tenths of a percent, 0-100% scaled to 0-1000
    cpu_utilization = CIPAttribute(id=11, type=UINT)
    #: Total size (in bytes) of the buffer
    max_buffer_size = CIPAttribute(id=12, type=UDINT)
    #: Currently available size (in bytes) of the buffer
    buffer_size_remaining = CIPAttribute(id=13, type=UDINT)

    #  --- services ---
    #: Closes a connection
    forward_close = SimpleCIPService(
        id=0x4E,
        request_type=_forward_close_request_type,
        response_type=_forward_close_response_type,
        failed_response_type=_forward_open_close_failed_response_type,
    )
    #: Opens a connection with a maximum data size of 511 bytes
    forward_open = SimpleCIPService(
        id=0x54,
        request_type=_forward_open_request_type,
        response_type=_forward_open_response_type,
        failed_response_type=_forward_open_close_failed_response_type,
    )
    #: Opens a connection with a maximum data size of 65535 bytes
    large_forward_open = SimpleCIPService(
        id=0x5B,
        request_type=_large_forward_open_request_type,
        response_type=_forward_open_response_type,
        failed_response_type=_forward_open_close_failed_response_type,
    )

    unconnected_send = UnconnectedSendService()

    class Instance(IntEnum):
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
        forward_close = b'\x4E'
        #: TODO: explain unconnected send
        unconnected_send = b'\x52'
        #: Opens a connection with a maximum data size of 511 bytes
        forward_open = b'\x54'
        #: Opens a connection with a maximum data size of 65535 bytes
        large_forward_open = b'\x5B'
        #: For connection diagnostics
        get_connection_data = b'\x56'
        #: For connection diagnostics
        search_connection_data = b'\x57'
        #: Determine the owner of a redundant connection
        get_connection_owner = b'\x5A'

    STATUS_CODES = {
        'Any': {
            0x01: {
                0x0100: 'Connection in use or duplicate forward_open',
                0x0103: 'Transport class and trigger combination not supported',
                0x0106: 'Ownership conflict',
                0x0107: 'Target connection not found',
                0x0108: 'Invalid network connection parameter',
                0x0109: 'Invalid connection size',
                0x0110: 'Target for connection not configured',
                0x0111: 'RPI not supported',
                0x0113: 'Out of connections',
                0x0114: 'Vendor ID of product code mismatch',
                0x0115: 'Product type mismatch',
                0x0116: 'Revision mismatch',
                0x0117: 'Invalid produced or consumed application path',
                0x0118: 'Invalid or inconsistent configuration application path',
                0x0119: 'Non-listen only connection not opened',
                0x011a: 'Target object out of connections',
                0x011b: 'RPI is smaller than the production inhibit time',
                0x0203: 'Connection timed out',
                0x0204: 'Unconnected request timed out',
                0x0205: 'Parameter error in unconnected request service',
                0x0206: 'Message too large for unconnected_send service',
                0x0207: 'Unconnected acknowledge without reply',
                0x0301: 'No buffer memory available',
                0x0302: 'Network bandwidth not available for data',
                0x0303: 'No consumed connection ID filter available',
                0x0304: 'Not configured to send scheduled priority data',
                0x0305: 'Schedule signature mismatch',
                0x0306: 'Schedule signature validation not possible',
                0x0311: 'Port not available',
                0x0312: 'Link address not valid',
                0x0315: 'Invalid segment in connection path',
                0x0316: 'Error in forward close service connection path',
                0x0317: 'Scheduling not specified',
                0x0318: ' Link address to self invalid',
                0x0319: 'Secondary resources unavailable',
                0x031a: 'Rack connection already established',
                0x031c: 'Miscellaneous',
                0x031d: 'Redundant connection mismatch',
                0x031e: 'No more user configurable link consumer resources available in the producing module',
                0x031f: 'No more user configurable link consumer resources available in the producing module',
                0x0800: 'Network link in path to module is offline',
                0x0810: 'No target application data available',
                0x0811: 'No originator application data available',
                0x0812: 'Node address has changed since the network was scheduled',
                0x0813: 'Not configured for off-subnet multicast',
            },
            0x09: {
                None: 'Error in data segment',  # ext. status is the index of the error in the segment
            },
            0x0C: {
                None: "Object state error - (optional) ext. status is the object's state",
            },
            0x10: {
                None: "Device state error - (optional) ext. status is the device's state",
            },
        }
    }

