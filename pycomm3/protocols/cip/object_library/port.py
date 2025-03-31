from .message_router import GetAttributesAllService
from ..cip_object import CIPObject, CIPAttribute
from pycomm3.data_types import (
    UINT,
    SHORT_STRING,
    StructType,
    PADDED_EPATH,
    PACKED_EPATH,
    PADDED_EPATH_LEN,
)
from pycomm3.util import IntEnumX


class InstanceInfo(StructType):
    port_type: UINT
    port_number: UINT


class LinkObject(StructType):
    word_length: UINT
    link_path: PADDED_EPATH[2]  # pyright: ignore [reportInvalidTypeArguments]


class PortGetAttrsAllInstance(StructType):
    port_type: UINT
    port_number: UINT
    link_object: LinkObject
    port_name: SHORT_STRING
    node_address: PADDED_EPATH


class PortGetAttrsAllClass(StructType):
    object_revision: UINT
    max_instance: UINT
    num_instances: UINT
    entry_port: UINT


class Port(CIPObject):
    """
    Represents the CIP ports on the device, one instance per port.
    """

    class_code = 0xF4

    # --- Class Attributes ---
    #: Gets the instance ID of the Port Object that the request entered through
    entry_port = CIPAttribute(id=8, data_type=UINT, class_attr=True)
    #: Array of port type and number for each instance (instance attributes 1 & 2)
    port_instance_info = CIPAttribute(id=9, data_type=InstanceInfo[...], class_attr=True)

    # --- Instance Attributes ---
    #: Indicates the type of port, see :class:`PortTypes`
    port_type = CIPAttribute(id=1, data_type=UINT)
    #: CIP port number of the port
    port_number = CIPAttribute(id=2, data_type=UINT)
    #: Logical path that identifies the object for this port
    link_object = CIPAttribute(id=3, data_type=PADDED_EPATH_LEN)
    #: String name that identifies the physical port on the device.
    port_name = CIPAttribute(id=4, data_type=SHORT_STRING)
    #: String name of the port type
    port_type_name = CIPAttribute(id=5, data_type=SHORT_STRING)
    #: String description of the port
    port_description = CIPAttribute(id=6, data_type=SHORT_STRING)
    #: Node number of the device on the port
    node_address = CIPAttribute(id=7, data_type=PADDED_EPATH)
    #: Range of node numbers on the port, not used with EtherNet/IP
    port_node_range = CIPAttribute(id=8, data_type=UINT[2])
    #: Electronic key of network or chassis the port is attached to
    port_key = CIPAttribute(id=9, data_type=PACKED_EPATH)

    class PortTypes(IntEnumX):
        """
        Enum of the different ``port_type`` attribute values.

        Not listed:
          - 6-99 = Reserved for compatability with existing protocols
          - 100-199 = Vendor specific
          - 203 - 65534 = Reserved for future use

        """

        #: Connection terminates in this device
        ConnectionTerminatesInDevice = 0
        #: Reserved for compatability with existing protocols
        Reserved = 1
        #: ControlNet
        ControlNet = 2
        #: ControlNet Redundant
        ControlNetRedundant = 3
        #: EtherNet/IP
        EtherNetIP = 4
        #: DeviceNet
        DeviceNet = 5
        #: CompoNet
        CompoNet = 200
        #: Modbus/TCP
        ModbusTCP = 201
        #: Modbus/SL
        ModbusSL = 202
        #: Port is not configured
        UnconfiguredPort = 65535

    get_attributes_all = GetAttributesAllService(
        instance_struct=PortGetAttrsAllInstance,
        class_struct=PortGetAttrsAllClass,
    )
