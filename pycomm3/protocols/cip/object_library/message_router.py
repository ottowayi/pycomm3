from pycomm3.data_types import EPATH, UINT, USINT, StructType, attr, BYTES
from pycomm3.data_types.cip import LogicalSegment, SymbolicSegment

from ..protocol_base import CIPRequest
from ..cip_object import CIPAttribute, CIPObject, GeneralStatusCodes, service
from ..msg_router_services import message_router_service
from typing import cast, ClassVar


class MessageRouterInstanceAttrs(StructType):
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

    _svc_get_attrs_all_instance_type = MessageRouterInstanceAttrs

    SYMBOLIC_TRANSLATION_SERVICE_ID: ClassVar[USINT] = USINT(0x4B)

    @service(id=SYMBOLIC_TRANSLATION_SERVICE_ID)
    @classmethod
    def symbolic_translation(cls, symbol: EPATH) -> CIPRequest[EPATH | BYTES]:
        """
        Translates a single `SymbolicSegment` `EPATH` to the equivalent `LogicalSegment` `EPATH` if one exists
        """
        request = message_router_service(
            service=cls.SYMBOLIC_TRANSLATION_SERVICE_ID,
            class_code=cls.class_code,
            instance=None,
            request_data=symbol,
            request_type=EPATH,
            response_type=EPATH,
            failed_response_type=BYTES,
        )

        return cast(CIPRequest[EPATH | BYTES], request)

    STATUS_CODES = {
        SYMBOLIC_TRANSLATION_SERVICE_ID: {
            GeneralStatusCodes.invalid_parameter: {
                0x00: "Symbolic Path unknown",
                0x01: "Symbolic Path destination not assigned",
                0x02: "Symbolic Path segment error",
            }
        }
    }
