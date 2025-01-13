from dataclasses import InitVar
from textwrap import dedent
from typing import Final, Sequence, cast

from pycomm3 import DataError, as_stream, BufferEmptyError, buff_repr, ArrayType
from pycomm3.data_types import (
    BYTES,
    INT_BE,
    UDINT,
    UDINT_BE,
    UINT,
    UINT_BE,
    USINT,
    USINT_BE,
    DataType,
    StructType,
    attr,
    Array,
    WORD,
    SHORT_STRING,
    IPAddress_BE,
)

DEFAULT_CONTEXT: Final[BYTES[8]] = BYTES[8](b"\x00" * 8)


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


class CPFItem(StructType):
    type_id: UINT
    length: UINT = attr(init=False)

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


class UCCMAddress(NullAddress): ...


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
    data: BYTES = attr(len_ref="length")


class ConnectedData(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.connected_data)
    length: UINT = attr(init=False)
    data: BYTES = attr(len_ref="length")


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
    item_count: UINT = attr(init=False)
    items: Array[CPFItem, None] | Sequence[CPFItem] = attr(len_ref="item_count")


class RegisterSessionData(StructType):
    protocol_version: UINT | int = 1
    options_flags: UINT | int = 0


class InterfaceInfo(CPFItem):
    type_id: UINT = attr(init=False, default=CPFItemType.cip_identity)
    length: UINT = attr(init=False)
    protocol_version: UINT | int = 1
    compatibility_flags: UINT | int = 0b_0000_0000_0010_0000  # support cip = yes, cip class 0/1 udp = no
    service_name: BYTES[...] | bytes = attr(
        default=b"Communications",
        len_ref=("length", lambda x: x - 4),  # 4 = protocol version + compat flags # type: ignore
    )


class ListServicesResponse(StructType):
    count: UINT | int = attr(init=False)
    interfaces: Array[InterfaceInfo, None] | Sequence[InterfaceInfo]


type AddressItemsT = NullAddress | UCCMAddress | SequencedAddress | ConnectedAddress
type DataItemsT = ConnectedData | UnconnectedData


class CommonPacketFormat[AddrT: AddressItemsT, DataT: DataItemsT](StructType):
    item_count: UINT = attr(init=False)
    items: Array[CPFItem, None] | Sequence[CPFItem] = attr(init=False, len_ref="item_count")

    address_item: InitVar[AddrT]
    data_item: InitVar[DataT]
    extra_items: InitVar[Array[CPFItem, None] | None] = None

    def __post_init__(self, address_item, data_item, extra_items=None, *args, **kwargs):
        self.items = [address_item, data_item, *(extra_items or [])]

    @property
    def address(self) -> AddrT:
        return cast(AddrT, self.items[0])

    @property
    def data(self) -> DataT:
        return cast(DataT, self.items[1])


class SendRRDataData(StructType):
    interface_handle: UINT | int = attr(default=0, init=False)  # always 0 for CIP
    timeout: UINT | int = attr(default=0, init=False)  # typically 0 for CIP, which has its own timeout
    packet: CommonPacketFormat[UCCMAddress, UnconnectedData]


class SendUnitDataData(StructType):
    interface_handle: UINT | int = attr(default=0, init=False)
    timeout: UINT | int = attr(default=0, init=False)
    packet: CommonPacketFormat[SequencedAddress, ConnectedData]
