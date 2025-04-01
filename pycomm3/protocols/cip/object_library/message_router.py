from ..cip_object import CIPAttribute, CIPObject
from ....data_types import (
    UINT,
)


class MessageRouter(CIPObject):
    """
    The object handles routing service calls to objects within the device from client messages
    """

    class_code = 0x02

    #: List of supported objects (class codes)
    object_list = CIPAttribute(id=1, data_type=UINT[UINT])
    #: Max number of supported connections
    num_available = CIPAttribute(id=2, data_type=UINT)
    #: Number of currently active connections
    num_active = CIPAttribute(id=3, data_type=UINT)
    #: List of connection ids for active connections
    active_connections = CIPAttribute(id=4, data_type=UINT[...])

    # class Services(EnumMap):
    #     """
    #     Custom services supported for the Message Router Object
    #     """
    #
    #     #: Translates a Symbolic Segment EPATH encoding to the
    #     #: equivalent Logical Segment EPATH encoding, if it exists
    #     symbolic_translation = b"\x4b"
    #
    # STATUS_CODES = {
    #     Services.symbolic_translation: {
    #         0x20: {
    #             0x00: "Symbolic Path unknown",
    #             0x01: "Symbolic Path destination not assigned",
    #             0x02: "Symbolic Path segment error",
    #         }
    #     }
    # }
