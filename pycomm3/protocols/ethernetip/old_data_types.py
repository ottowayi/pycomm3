from enum import IntEnum
from io import BytesIO
from typing import Type, Dict, Any, Sequence, Union, TypedDict, overload

from pycomm3.data_types import StructType, USINT, UINT, UDINT, BYTES, StructType
from pycomm3.exceptions import DataError
from pycomm3.map import EnumMap

from ..cip.cip import CIPRequest, CIPResponse


class EtherNetIPHeader(StructType):
    command: UINT
    length: UINT
    session: UDINT
    status: UDINT = UDINT(0)
    context: BYTES[8] = BYTES[8](b"\x00" * 8)
    option: UDINT = UDINT(0)

    # @classmethod
    # def _decode(cls, stream: BytesIO):
    #     values = super(EtherNetIPHeader, cls)._decode(stream)
    #     values['status'] = ETHERNETIP_STATUS_CODES.get(values['status'], 'RESERVED')
    #     return values


class DataItemTypes(EnumMap):
    connected = b"\xb1\x00"
    unconnected = b"\xb2\x00"


class AddressItemTypes(EnumMap):
    connection = b"\xa1\x00"
    null = b"\x00\x00"
    uccm = b"\x00\x00"


class CommonPacketFormatItem(StructType):
    type_id: int = None

    @classmethod
    def _encode(cls, value) -> bytes:
        """
        `value` should only be the data, type id and length are not inputs
        """
        item_cls = cls._find_item_class(cls.type_id)
        encoded_data = item_cls._encode_data(value)
        return b"".join(
            (
                UINT.encode(cls.type_id),
                UINT.encode(len(encoded_data)),
                encoded_data,
            )
        )

    @classmethod
    def _encode_data(cls, value) -> bytes:
        return b""

    @classmethod
    def _decode(cls, stream: BytesIO) -> dict[str, Any]:
        type_id = UINT.decode(stream)
        item_cls = cls._find_item_class(type_id)
        data_len = UINT.decode(stream)
        data = item_cls._decode_data(stream, data_len)

        return {"type_id": type_id, "data_len": data_len, "data": data}

    @classmethod
    def _decode_data(cls, stream: BytesIO, data_len: int) -> BytesIO:
        return stream

    @classmethod
    def _find_item_class(cls, type_id) -> Type["CommonPacketFormatItem"]:
        # each item type should subclass this class, not subclass a subclass of this class
        # so don't worry about getting the nested subclasses
        for subcls in CommonPacketFormatItem.__subclasses__():
            if getattr(subcls, "type_id", None) == type_id:
                return subcls

        raise DataError(f"Unsupported type_id ({type_id})")


class NullAddressItem(CommonPacketFormatItem):
    type_id = 0x0000

    @classmethod
    def _encode_data(cls, value) -> bytes:
        return b""

    @classmethod
    def _decode_data(cls, stream: BytesIO, data_len: int) -> None:
        return None


# UCMM address item appears to be the same as the null one
UCMMAddressItem = NullAddressItem


class ConnectedAddressItem(CommonPacketFormatItem):
    type_id = 0x00A1

    @classmethod
    def _encode_data(cls, value: Dict[str, Any]) -> bytes:
        return UDINT.encode(value["connection_id"])

    @classmethod
    def _decode_data(cls, stream: BytesIO, data_len: int) -> Dict[str, int]:
        return {"connection_id": UDINT.decode(stream)}


class SequencedAddressItem(CommonPacketFormatItem):
    type_id = 0x8002

    @classmethod
    def _encode_data(cls, value: Dict[str, Any]) -> bytes:
        return b"".join(
            (
                UDINT.encode(value["connection_id"]),
                UDINT.encode(value["sequence_number"]),
            )
        )

    @classmethod
    def _decode_data(cls, stream: BytesIO, data_len: int) -> Dict[str, int]:
        return {
            "connection_id": UDINT.decode(stream),
            "sequence_number": UDINT.decode(stream),
        }


class UnconnectedDataItem(CommonPacketFormatItem):
    type_id = 0x00B2

    @classmethod
    def _encode_data(cls, value: bytes) -> bytes:
        return value

    @classmethod
    def _decode_data(cls, stream: BytesIO, data_len: int) -> bytes:
        return stream.read(data_len)


class ConnectedDataItem(CommonPacketFormatItem):
    type_id = 0x00B1

    @classmethod
    def _encode_data(cls, value: bytes) -> bytes:
        return value

    @classmethod
    def _decode_data(cls, stream: BytesIO, data_len: int) -> bytes:
        return stream.read(data_len)


class CommonPacketFormat(
    Struct(
        UINT("item_count"),
        CommonPacketFormatItem("address_item"),
        CommonPacketFormatItem("data_item"),
    )
):
    """ """
