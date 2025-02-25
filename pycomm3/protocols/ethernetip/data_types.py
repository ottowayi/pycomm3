from dataclasses import InitVar
from typing import Final, Sequence, cast, ClassVar

from pycomm3 import DataError, as_stream, BufferEmptyError, buff_repr
from pycomm3.data_types import (
    BYTES,
    INT_BE,
    UDINT,
    UINT,
    UINT_BE,
    USINT,
    USINT_BE,
    StructType,
    attr,
    Array,
    WORD,
    SHORT_STRING,
    IPAddress_BE,
)

DEFAULT_CONTEXT: Final[BYTES[8]] = BYTES[8](b"\x00" * 8)


class EncapsulationCommand:
    nop = UINT(0)
    list_services = UINT(0x04)
    list_identity = UINT(0x63)
    list_interfaces = UINT(0x64)
    register_session = UINT(0x65)
    unregister_session = UINT(0x66)
    send_rr_data = UINT(0x6F)
    send_unit_data = UINT(0x70)


ENCAP_COMMAND_NAMES: Final[dict[UINT, str]] = {
    v: k.replace("_", " ").title() for k, v in vars(EncapsulationCommand).items() if isinstance(v, UINT)
}


class EtherNetIPStatus:
    Success = UDINT(0x0000)
    InvalidOrUnsupportedEncapCommand = UDINT(0x0001)
    InsufficientReceiverMemory = UDINT(0x0002)
    BadData = UDINT(0x0003)
    InvalidSessionHandle = UDINT(0x0064)
    InvalidMessageLength = UDINT(0x0065)
    UnsupportedEncapProtocolRevision = UDINT(0x0069)  # nice


ETHERNETIP_STATUS_CODES: dict[UDINT, str] = {
    EtherNetIPStatus.Success: "Success",
    EtherNetIPStatus.InvalidOrUnsupportedEncapCommand: "Invalid or unsupported encapsulation command",
    EtherNetIPStatus.InsufficientReceiverMemory: "Insufficient memory to handle command",
    EtherNetIPStatus.BadData: "Poorly formed or incorrect command data",
    EtherNetIPStatus.InvalidSessionHandle: "Invalid session handle",
    EtherNetIPStatus.InvalidMessageLength: "Invalid message length",
    EtherNetIPStatus.UnsupportedEncapProtocolRevision: "Unsupported encapsulation protocol revision",
}


class EtherNetIPHeader(StructType):
    command: UINT
    length: UINT
    session: UDINT
    status: UDINT = UDINT(0)
    context: BYTES[8] = DEFAULT_CONTEXT
    options: UDINT = UDINT(0)

    def __str__(self) -> str:
        command = f"{self.command:#04x}: '{ENCAP_COMMAND_NAMES.get(self.command, 'UNKNOWN')}'"
        status = f"{self.status:#06x}: '{ETHERNETIP_STATUS_CODES.get(self.status, 'UNKNOWN')}'"
        session = self.session
        return f"{self.__class__.__name__}({command=!s}, {status=!s}, {session=})"


class CPFItemType:
    """
    Common Packet Format Item Types
    """

    # Address Items
    null_address: UINT = UINT(0)
    uccm_address: UINT = null_address
    connected_address: UINT = UINT(0xA1)
    sequenced_address: UINT = UINT(0x8002)
    # Data Items
    connected_data: UINT = UINT(0xB1)
    unconnected_data: UINT = UINT(0xB2)
    sock_addr_info_o_t: UINT = UINT(0x8000)
    sock_addr_info_t_o: UINT = UINT(0x8001)

    # CIP
    cip_identity: UINT = UINT(0x0C)
    cip_communications: UINT = UINT(0x100)


CPF_ITEM_TYPE_NAMES: Final[dict[UINT, str]] = {
    **{v: k.replace("_", " ").title() for k, v in vars(CPFItemType).items() if k.endswith(("_data", "_address"))},
    CPFItemType.sock_addr_info_o_t: "Socket Address Info O->T",
    CPFItemType.sock_addr_info_t_o: "Socket Address Info T->O",
    CPFItemType.cip_identity: "CIP Identity",
    CPFItemType.cip_communications: "CIP Communications",
}


class CPFItem(StructType):
    type_id: UINT
    length: UINT

    __field_descriptions__: ClassVar[dict] = {"type_id": CPF_ITEM_TYPE_NAMES}

    @classmethod
    def decode(cls, buffer) -> "CPFItem":
        try:
            stream = as_stream(buffer)
            type_id = UINT.decode(cls._stream_peek(stream, UINT.size))
            for subcls in CPFItem.__subclasses__():
                if subcls.type_id == type_id:
                    break
            else:
                raise DataError(f"Unsupported Common Packet Format Item Type ID: {type_id}")
            return subcls._decode(stream)
        except BufferEmptyError:
            raise
        except Exception as err:
            raise DataError(f"Error unpacking {buff_repr(buffer)} as {cls.__name__}") from err


class NullAddress(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.null_address)
    length: UINT = attr(init=False, default=UINT(0))


class ConnectedAddress(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.connected_address)
    length: UINT = attr(init=False, default=UINT(4))
    connection_id: UDINT


class SequencedAddress(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.sequenced_address)
    length: UINT = attr(init=False, default=UINT(8))
    connection_id: UDINT
    sequence_num: UDINT


class UnconnectedData(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.unconnected_data)
    length: UINT = attr(init=False)
    data: BYTES = attr(init=True, len_ref="length")


class ConnectedData(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.connected_data)
    length: UINT = attr(init=False)
    data: BYTES = attr(init=True, len_ref="length")


class Sockaddr(StructType):
    sin_family: INT_BE
    sin_port: UINT_BE
    sin_addr: IPAddress_BE
    sin_zero: USINT_BE[8]


class SockaddrInfo(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.connected_data)
    length: UINT = attr(init=False, default=UINT(Sockaddr.size))
    info: Sockaddr


class CIPIdentity(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.cip_identity)
    length: UINT = attr(size_ref=True)
    encap_protocol_version: UINT
    socket_address: Sockaddr
    vendor_id: UINT
    device_type: UINT
    product_code: UINT
    revision: USINT[2]
    status: WORD
    serial_number: UDINT
    product_name: SHORT_STRING
    state: USINT


class ListIdentityData(StructType):
    count: UINT = attr(init=False)
    identities: Array[CPFItem, None] | Sequence[CPFItem] = attr(len_ref="count")


class RegisterSessionData(StructType):
    protocol_version: UINT | int = 1
    options_flags: UINT | int = 0


class ServiceInfo(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.cip_communications)
    length: UINT = attr(init=False, size_ref=True)
    protocol_version: UINT | int = 1
    compatibility_flags: UINT | int = 0b_0000_0000_0010_0000  # support cip = yes, cip class 0/1 udp = no
    service_name: BYTES[16] | bytes = attr(default=b"Communications\x00\x00")


class ListServicesData(StructType):
    count: UINT | int = attr(init=False)
    services: Array[ServiceInfo, None] | Sequence[ServiceInfo] = attr(len_ref="count")


InterfaceInfo = BYTES


class ListInterfacesData(StructType):
    count: UINT | int = attr(init=False)
    interfaces: Array[CPFItem, None] | Sequence[CPFItem] = attr(len_ref="count")


type AddressItemsT = NullAddress | SequencedAddress | ConnectedAddress
type DataItemsT = ConnectedData | UnconnectedData


class CommonPacketFormat[AddrT: AddressItemsT, DataT: DataItemsT](StructType):
    item_count: UINT = attr(init=False)
    items: Array[CPFItem, None] | Sequence[CPFItem] = attr(init=False, len_ref="item_count")

    address_item: InitVar[AddrT] = None
    data_item: InitVar[DataT] = None
    extra_items: InitVar[Array[CPFItem, None] | None] = None

    def __post_init__(self, address_item=None, data_item=None, extra_items=None, *args, **kwargs):
        if None not in (address_item, data_item):
            self.items = [address_item, data_item, *(extra_items or [])]

    @property
    def address(self) -> AddrT:
        return cast(AddrT, self.items[0])

    @property
    def data(self) -> DataT:
        return cast(DataT, self.items[1])


type SendRRDataPacketFormat = CommonPacketFormat[NullAddress, UnconnectedData]
type SendUnitDataPacketFormat = CommonPacketFormat[SequencedAddress, ConnectedData]


class SendRRDataData(StructType):
    interface_handle: UDINT | int = attr(default=0, init=False)  # always 0 for CIP
    timeout: UINT | int = attr(default=0, init=False)  # typically 0 for CIP, which has its own timeout
    packet: CommonPacketFormat | SendRRDataPacketFormat


class SendUnitDataData(StructType):
    interface_handle: UDINT | int = attr(default=0, init=False)
    timeout: UINT | int = attr(default=0, init=False)
    packet: CommonPacketFormat | SendUnitDataPacketFormat
