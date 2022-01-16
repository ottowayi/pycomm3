from copy import deepcopy
from enum import IntEnum

from .base import CIPAttribute, CIPObject
from ....data_types import UINT, USINT, Struct, WORD, UDINT, SHORT_STRING, PACKED_EPATH, BYTE, PADDED_EPATH, STRINGI, INT
from ....map import EnumMap


__all__ = [
    'IdentityObject',
    'MessageRouterObject',
    'DeviceNetObject',
    'AssemblyObject',
    'ConnectionObject',
    'FileObject',
    'PortObject',
]


class IdentityObject(CIPObject):
    """
    This object provides general identity and status information about a device.
    It is required by all CIP objects and if a device contains multiple discrete
    components, multiple instances of this object may be created.
    """
    class_code = 0x01

    # --- Required attributes ---
    #: Identification code assigned to the vendor
    vendor_id = CIPAttribute(id=1, type=UINT)
    #: Indication of general type of product
    device_type = CIPAttribute(id=2, type=UINT)
    #: Identification code of a particular product for an individual vendor
    product_code = CIPAttribute(id=3, type=UINT)
    #: Revision of the item the Identity Object represents
    revision = CIPAttribute(id=4, type=Struct(USINT("major"), USINT("minor")))
    #: Summary status of the device
    status = CIPAttribute(id=5, type=WORD)
    #: Serial number of the device
    serial_number = CIPAttribute(id=6, type=UDINT)
    #: Human readable identification of the device
    product_name = CIPAttribute(id=7, type=SHORT_STRING)

    # TODO: add custom type for status that shows what the bits mean

    # --- Optional attributes ---
    #: Present state of the device, see :class:`~IdentityObject.States`
    state = CIPAttribute(id=8, type=USINT, all=False)

    class States(IntEnum):
        """
        Enum of the possible state attribute values,
        any not listed are 'reserved'
        """

        #: The device is powered off
        Nonexistent = 0
        #: The device is currently running self tests
        DeviceSelfTesting = 1
        #: The device requires commissioning, configuration is invalid or incomplete
        Standby = 2
        #: The device is functioning normally
        Operational = 3
        #: The device experienced a fault that it can recover from
        MajorRecoverableFault = 4
        #: The device experienced a fault that it cannot recover from
        MajorUnrecoverableFault = 5
        #: Default value for a ``get_attributes_all`` service response if attribute is not supported
        DefaultGetAttributesAll = 255


class MessageRouterObject(CIPObject):
    """
    The object handles routing service calls to objects within the device from client messages
    """
    class_code = 0x02

    #: List of supported objects (class codes)
    object_list = CIPAttribute(id=1, type=UINT[UINT])
    #: Max number of supported connections
    num_available = CIPAttribute(id=2, type=UINT)
    #: Number of currently active connections
    num_active = CIPAttribute(id=3, type=UINT)
    #: List of connection ids for active connections
    active_connections = CIPAttribute(id=4, type=UINT[...])

    class Services(EnumMap):
        """
        Custom services supported for the Message Router Object
        """

        #: Translates a Symbolic Segment EPATH encoding to the
        #: equivalent Logical Segment EPATH encoding, if it exists
        symbolic_translation = b'\x4B'

    STATUS_CODES = {
        Services.symbolic_translation: {
            0x20: {
                0x00: 'Symbolic Path unknown',
                0x01: 'Symbolic Path destination not assigned',
                0x02: 'Symbolic Path segment error',
            }
        }
    }


class DeviceNetObject(CIPObject):
    """
    The DeviceNet Object provides the configuration and status of a DeviceNet port. Each
    DeviceNet product must support one (and only one) DeviceNet object per physical connection
    to the DeviceNet communication link.

    Not Implemented, this object is defined in Vol. 3 of the CIP Spec
    and currently only have access to volumes 1 & 2
    """
    class_code = 0x03


class AssemblyObject(CIPObject):
    """
    The Assembly Object binds attributes of multiple objects, which allows data to or from each
    object to be sent or received over a single connection. Assembly objects can be used to bind
    input data or output data. The terms ”input” and ”output” are defined from the network’s point
    of view. An input will produce data on the network and an output will consume data from the
    network.
    """
    class_code = 0x04

    num_members = CIPAttribute(id=1, type=UINT, all=False)
    member_list = CIPAttribute(
        id=2,
        type=Struct(
            UINT('member_data_size_bits'),
            UINT('member_path_size_bytes'),
            PACKED_EPATH('member_path'),
        )[...],
        all=False,
    )
    data = CIPAttribute(id=3, type=BYTE[None], all=False)
    size = CIPAttribute(id=4, type=UINT, all=False)  #: size of attr 3


class ConnectionObject(CIPObject):
    """
    The Connection Object handles explicit messaging and I/O connection services for the device.
    """
    class_code = 0x05

    # --- Instance Attributes ---

    #: State of the object, see :class:`States`
    state = CIPAttribute(id=1, type=USINT)
    #: Indicates either I/O or Messaging connection, see :class:`InstanceTypes`
    instance_type = CIPAttribute(id=2, type=USINT)
    #: Defines behavior of the connection
    transport_class_trigger = CIPAttribute(id=3, type=BYTE)

    class Services(EnumMap):
        """
        Custom services support by the Connection Object.
        """

        #: Binds two connections
        connection_bind = b'\x4B'
        #: Finds the connections that are producing data from the specified application object
        producing_app_lookup = b'\x4C'

    STATUS_CODES = {
        Services.connection_bind: {
            0x02: {
                0x01: 'One or both of the connection instances is non-existent',
                0x02: 'The connection class and/or instance is out of resources to bind instances',
            },
            0x0c: {
                0x01: 'Both of he connection instances exist, but at least on is not in the Established state',
            },
            0x20: {
                0x01: 'Both connection instances are the same value',
            },
            0xD0: {
                0x01: 'One or both of the connection instances is not a dynamically created I/O connection',
                0x02: (
                    'One of both of the connection instances were created internally '
                    'and the device is not allowing a binding to it'
                ),
            },
        },
        Services.producing_app_lookup: {
            0x02: {
                0x01: 'The connection path was not found in any connection instance in the Established state',
            },
        },
    }

    class States(IntEnum):
        """
        Enum of the possible ``state`` attribute values
        """
        #: The connection is not yet instantiated
        Nonexistent = 0
        #: The connection is instantiated but waiting to be configured or to apply configuration
        Configuring = 1
        #: The connection is waiting for the connection ID (either produced or consumed) attribute to be set
        #: (DeviceNet Only)
        WaitingForConnectionId = 2
        #: The connection has been successfully configured
        Established = 3
        #: The connection has timed out on inactivity/watchdog
        TimedOut = 4
        #: If explicit messaging connection has timed out, it may enter this state (DeviceNet Only)
        DeferredDelete = 5
        #: A bridged connection has received and is currently processing a Forward Close request
        Closing = 6

    class InstanceTypes(IntEnum):
        """
        Enum of the possible values for the ``instance_type`` attribute
        """
        #: Connection is one endpoint of an Explicit Messaging Connection
        ExplicitMessaging = 0
        #: Connection is one endpoint of an I/O Connection
        IO = 1
        #: Connection is an intermediate hop of a bridged (I/O or Explicit Messaging connection)
        CIPBridged = 2


class FileObject(CIPObject):
    """
    Provides access to files on the device.

    Instance Ranges:
      - 0x01-0xC7 = Vendor/Product specific
      - 0xC8-0xFF = CIP reserved, publicly defined
      - 0x100-0x4FF = Vendor/Product specific
      - 0x500-0xFFFFFFFF = CIP reserved, publicly defined

    """

    # --- Class Attributes ---
    #: List of all instances available (instance id, instance name, file name)
    directory = CIPAttribute(
        id=32,
        type=Struct(UINT('instance_id'), STRINGI('instance_name'), STRINGI('file_name')),
        class_attr=True,
    )

    # --- Instance Attributes ---
    #: State of the instance, see :class:`States`
    state = CIPAttribute(id=1, type=USINT)
    #: Name of the instance
    instance_name = CIPAttribute(id=2, type=STRINGI)
    #: Format version of the file
    instance_format_version = CIPAttribute(id=3, type=UINT)
    #: Name of the file
    file_name = CIPAttribute(id=4, type=STRINGI)
    #: Revision of the file
    file_revision = CIPAttribute(id=5, type=Struct(USINT('major'), USINT('minor')))
    #: Size of the file
    file_size = CIPAttribute(id=6, type=UDINT)
    #: Checksum of the file
    file_checksum = CIPAttribute(id=7, type=INT)
    #: Method for invoking the downloaded file, see :class:`InvokeMethods`
    invocation_method = CIPAttribute(id=8, type=USINT)
    #: Information about the nonvolatile storage of the file
    #:
    #: Bits:
    #:  - 0 = When set a save (0x16) service request is required
    #:  - 1-3 = Reserved
    #:  - 4 = When set the file has been saved to nonvolatile storage
    #:  - 5-7 = Reserved
    file_save_params = CIPAttribute(id=9, type=BYTE)
    #: File type/access permissions, see :class:`FileTypes`
    file_type = CIPAttribute(id=10, type=USINT)
    #: Encoding format of the file data, see :class:`EncodingFormats`
    file_encoding_format = CIPAttribute(id=11, type=USINT)

    class Services(EnumMap):
        #: Begins a file upload
        initiate_upload = b'\x4B'
        #: Begins a file download
        initiate_download = b'\x4C'
        #: Begins a partial read of a file
        initiate_partial_read = b'\x4D'
        #: Begins a partial write of a file
        initiate_partial_write = b'\x4E'
        #: Uploads the file
        upload_transfer = b'\x4F'
        #: Downloads the file
        download_transfer = b'\x50'
        #: Clears a loaded file
        clear_file = b'\x51'

    _init_service_errors = {
        0x20: {
            0x00: '(OBSOLETE) File size too large',
            0x01: '(OBSOLETE) Instance format version not compatible',
            0x04: 'File size too large',
            0x05: 'Instance format version not compatible',
            0x08: 'Transfer failed - zero size',
        },
        0x15: {
            0x01: 'File name too long',
            0x02: 'Too many languages in file name',
        }
    }
    _init_partial_service_errors = deepcopy(_init_service_errors)
    _init_partial_service_errors[0x20] |= {
            0x02: 'File offset out of range',
            0x03: 'Read/Write size beyond end of file',
    }
    _init_partial_service_errors[0x02] = {
        0xFF: 'File does not exist',
    }

    STATUS_CODES = {
        Services.initiate_upload: _init_service_errors,
        Services.initiate_download: _init_service_errors,
        Services.initiate_partial_read: _init_partial_service_errors,
        Services.initiate_partial_write: _init_partial_service_errors,
    }

    class States(IntEnum):
        """
        Enum of the ``state`` attribute values. Any values not listed are Reserved.
        """

        #: File does not exist
        Nonexistent = 0
        #: File is empty or not loaded
        Empty = 1
        #: File loaded
        Loaded = 2
        #: File upload has been initiated
        UploadInitiated = 3
        #: File download has been initiated
        DownloadInitiated = 4
        #: File upload is in progress
        UploadInProgress = 5
        #: File download is in progress
        DownloadInProgress = 6
        #: File is being stored
        Storing = 7

    class InvokeMethods(IntEnum):
        """
        Enum of the ``invocation_method`` values.

        Not Listed:
          - 4-99 = Reserved by CIP
          - 100-199 = Vendor specific
          - 200-254 = Reserved by CIP
        """

        #: No action required
        NoAction = 0
        #: Power cycle the device
        PowerCycle = 1
        #: Requires a start (0x06) service request
        StartService = 2

    class FileTypes(IntEnum):
        """
        Enum of the ``file_type`` attribute values.  Any not listed are reserved.
        """
        #: Read/Write (default)
        RW = 0
        #: Read-Only
        RO = 1

    class EncodingFormats(IntEnum):
        """
        Enum of the ``file_encoding_format`` attribute values.  Any not listed are reserved.
        """
        #: File is binary data, no additional interpretation required
        Binary = 0
        #: Compressed file(s) using ZLIB compression
        Compressed = 1


class PortObject(CIPObject):
    """
    Represents the CIP ports on the device, one instance per port.
    """

    class_code = 0xf4
    _class_all_exclude = {'optional_attrs_list', 'optional_service_list','max_class_attr', 'max_instance_attr'}

    # --- Class Attributes ---
    #: Gets the instance ID of the Port Object that the request entered through
    entry_port = CIPAttribute(id=8, type=UINT, class_attr=True)
    #: Array of port type and number for each instance (instance attributes 1 & 2)
    port_instance_info = CIPAttribute(id=9, type=Struct(UINT('port_type'), UINT('port_number'))[...], class_attr=True)

    # --- Instance Attributes ---
    #: Indicates the type of port, see :class:`PortTypes`
    port_type = CIPAttribute(id=1, type=UINT)
    #: CIP port number of the port
    port_number = CIPAttribute(id=2, type=UINT)
    #: Logical path that identifies the object for this port
    link_object = CIPAttribute(id=3, type=Struct(UINT('path_length'), PADDED_EPATH('link_path')))
    #: String name that identifies the physical port on the device.
    port_name = CIPAttribute(id=4, type=SHORT_STRING, all=False)
    #: String name of the port type
    port_type_name = CIPAttribute(id=5, type=SHORT_STRING, all=False)
    #: String description of the port
    port_description = CIPAttribute(id=6, type=SHORT_STRING, all=False)
    #: Node number of the device on the port
    node_address = CIPAttribute(id=7, type=PADDED_EPATH)
    #: Range of node numbers on the port, not used with EtherNet/IP
    port_node_range = CIPAttribute(id=8, type=Struct(UINT('min'), UINT('max')), all=False)
    #: Electronic key of network or chassis the port is attached to
    port_key = CIPAttribute(id=9, type=PACKED_EPATH, all=False)

    class PortTypes(IntEnum):
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

...