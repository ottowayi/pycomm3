import ipaddress

from io import BytesIO
from typing import Any, Union, Type, Dict, Tuple

from .cip import (DataType, ElementaryDataType, DerivedDataType, BufferEmptyError, Struct, UINT, USINT,
                  SINT, UDINT, SHORT_STRING, n_bytes, WORD, Array, StructType,)

__all__ = ['IPAddress', 'LogixIdentityObject', 'ListIdentityObject', 'StructTemplateAttributes']


class IPAddress(DerivedDataType):

    @classmethod
    def _encode(cls, value: str) -> bytes:
        return ipaddress.IPv4Address(value).packed

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        data = stream.read(4)
        if not data:
            raise BufferEmptyError()
        return ipaddress.IPv4Address(data).exploded


# TODO: not just logix, make generic
#       added custom decode methods for status, product_type, etc lookups
LogixIdentityObject = Struct(
    UINT('vendor'),
    UINT('product_type'),
    UINT('product_code'),
    USINT('version_major'),
    USINT('version_minor'),
    n_bytes(2, '_keyswitch'),
    UDINT('serial'),
    SHORT_STRING('device_type')
)

ListIdentityObject = Struct(
        UINT('item_type_code'),
        UINT('item_length'),
        UINT('encap_protocol_version'),
        n_bytes(4),
        IPAddress('ip_address'),
        n_bytes(8),
        UINT('vendor_id'),
        UINT('device_type'),
        UINT('product_code'),
        USINT('revision_major'),
        USINT('revision_minor'),
        WORD('status'),
        UDINT('serial_number'),
        SHORT_STRING('product_name'),
        USINT('state')
)


StructTemplateAttributes = Struct(
    UINT('count'),
    Struct(UINT('attr_num'), UINT('status'), UDINT('size'))(name='object_definition_size'),
    Struct(UINT('attr_num'), UINT('status'), UDINT('size'))(name='structure_size'),
    Struct(UINT('attr_num'), UINT('status'), UINT('count'))(name='member_count'),
    Struct(UINT('attr_num'), UINT('status'), UINT('handle'))(name='structure_handle'),

)


def StructTag(*members, bool_members: Dict[str, Tuple[str, int]], host_members: Dict[str, Type[DataType]],
              struct_size: int) -> Type[StructType]:
    """

    bool_members = {member name: (host member, bit)}
    """

    _struct = Struct(*members)

    class StructTag(_struct):
        bits = bool_members
        hosts = host_members
        size = struct_size

        @classmethod
        def _decode(cls, stream: BytesIO):
            values = _struct._decode(stream)
            hosts = set()

            for bit_member, (host_member, bit) in cls.bits.items():
                host_value = values[host_member]
                bit_value = bool(host_value & (1 << bit))
                values[bit_member] = bit_value
                hosts.add(host_member)

            return {k: v for k, v in values.items() if k not in hosts}

        @classmethod
        def _encode(cls, values: Dict[str, Any]):
            # make a copy so that private host members aren't added to the original
            values = {k: v for k, v in values.items()}

            for host in cls.hosts:
                values[host] = 0

            for bit_member, (host_member, bit) in cls.bits.items():
                val = values[bit_member]
                if val:
                    values[host_member] |= 1 << bit
                else:
                    values[host_member] &= ~(1 << bit)

            value = _struct._encode(values)

            if len(value) < cls.size:  # pad to structure size
                value += b'\x00' * (cls.size - len(value))

            return value

    return StructTag





