from dataclasses import field
from io import BytesIO
from typing import Final

from pycomm3 import DataError, as_stream, BufferEmptyError, buff_repr
from pycomm3.data_types import BYTES, INT_BE, UDINT, UDINT_BE, UINT, UINT_BE, USINT, USINT_BE, DataType, StructType

DEFAULT_CONTEXT: Final[BYTES[8]] = BYTES[8](b"\x00" * 8)


class EtherNetIPHeader(StructType):
    command: UINT
    length: UINT
    session: UDINT
    status: UDINT = UDINT(0)
    context: BYTES[8] = DEFAULT_CONTEXT
    options: UDINT = UDINT(0)


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


class CPFItem(StructType):
    type_id: UINT
    length: UINT

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
    type_id: UINT = field(init=False, default=CPFItemType.null_address)
    length: UINT = field(init=False, default=UINT(0))


class ConnectedAddress(CPFItem):
    type_id: UINT = field(init=False, default=CPFItemType.connected_address)
    length: UINT = field(init=False, default=UINT(4))
    connection_id: UDINT


class SequencedAddress(CPFItem):
    type_id: UINT = field(init=False, default=CPFItemType.sequenced_address)
    length: UINT = field(init=False, default=UINT(8))
    connection_id: UDINT
    sequence_num: UDINT


class UnconnectedData(CPFItem):
    type_id: UINT = field(init=False, default=CPFItemType.unconnected_data)
    length: UINT = field(init=False)
    data: BYTES

    def __post_init__(self):
        self.length = UINT(len(self.data))


class ConnectedData(CPFItem):
    type_id: UINT = field(init=False, default=CPFItemType.connected_data)
    length: UINT = field(init=False)
    data: BYTES

    def __post_init__(self):
        self.length = UINT(len(self.data))


class Sockaddr(StructType):
    sin_family: INT_BE
    sin_port: UINT_BE
    sin_addr: UDINT_BE
    sin_zero: USINT_BE[8]


class SockaddrInfo(CPFItem):
    type_id: UINT = field(init=False, default=CPFItemType.connected_data)
    length: UINT = field(init=False, default=UINT(Sockaddr.size))
    info: Sockaddr


class CommonPacketFormat(StructType):
    item_count: UINT = field(init=False)
    address_item: CPFItem
    data_item: CPFItem
    extra_items: CPFItem[...] = CPFItem[...]([])

    def __post_init__(self):
        self.item_count = UINT(len(self.extra_items)) + 2  # type: ignore
