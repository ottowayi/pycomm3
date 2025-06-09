from pycomm3.data_types import EPATH, UINT, USINT, StructType, attr

from ..cip_object import CIPAttribute, CIPObject, GeneralStatusCodes
from ..common_services import GetAttributesAllService
from ..msg_router_services import MsgRouterService


class MsgRouterGetAttrsAllInstance(StructType):
    object_list: UINT[UINT]
    num_available: UINT
    num_active: UINT
    active_connections: UINT[...] = attr(len_ref="num_active")


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

    get_attributes_all = GetAttributesAllService(instance_struct=MsgRouterGetAttrsAllInstance)

    #: Translates a single `SymbolicSegment` `EPATH` to the equivalent `LogicalSegment` `EPATH` if one exists
    symbolic_translation = MsgRouterService(id=USINT(0x4B), request_type=EPATH, response_type=EPATH)

    STATUS_CODES = {
        symbolic_translation.id: {
            GeneralStatusCodes.invalid_parameter: {
                0x00: "Symbolic Path unknown",
                0x01: "Symbolic Path destination not assigned",
                0x02: "Symbolic Path segment error",
            }
        }
    }
