import ipaddress
from io import BytesIO
from typing import Any, Type, Dict, Tuple

from .cip import (DataType, DerivedDataType, BufferEmptyError, Struct, UINT, USINT,
                  UDINT, SHORT_STRING, n_bytes, WORD, StructType, StringDataType, PRODUCT_TYPES, VENDORS, INT, ULINT)

__all__ = ['IPAddress', 'ModuleIdentityObject', 'ListIdentityObject', 'StructTemplateAttributes',
           'sized_string', 'Revision', 'StructTag']


def sized_string(size_: int, len_type_: DataType = UDINT):
    """
    Creates a custom string tag type
    """

    class FixedSizeString(StringDataType):
        size = size_
        len_type = len_type_

        @classmethod
        def _encode(cls, value: str, *args, **kwargs) -> bytes:
            return cls.len_type.encode(len(value)) + value.encode(cls.encoding) + b'\x00' * (cls.size - len(value))

        @classmethod
        def _decode(cls, stream: BytesIO) -> str:
            _len = cls.len_type.decode(stream)
            _data = cls._stream_read(stream, cls.size)[:_len]
            return _data.decode(cls.encoding)

    return FixedSizeString


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


class Revision(Struct(
    USINT('major'),
    USINT('minor')
)):
    ...


class ModuleIdentityObject(Struct(
    UINT('vendor'),
    UINT('device_type'),
    UINT('product_code'),
    Revision('revision'),
    n_bytes(2, 'status'),
    UDINT('serial'),
    SHORT_STRING('device_type')
)):

    @classmethod
    def _decode(cls, stream: BytesIO):
        values = super(ModuleIdentityObject, cls)._decode(stream)
        values['device_type'] = PRODUCT_TYPES.get(values['product_type'], 'UNKNOWN')
        values['vendor'] = VENDORS.get(values['vendor'], 'UNKNOWN')
        values['serial'] = f"{values['serial']:08x}"

        return values


class ListIdentityObject(Struct(
    UINT(),
    UINT(),
    UINT('encap_protocol_version'),
    INT(),
    UINT(),
    IPAddress('ip_address'),
    ULINT(),
    UINT('vendor_id'),
    UINT('device_type'),
    UINT('product_code'),
    Revision('revision'),
    WORD('status'),
    UDINT('serial'),
    SHORT_STRING('product_name'),
    USINT('state')
)):

    @classmethod
    def _decode(cls, stream: BytesIO):
        values = super(ListIdentityObject, cls)._decode(stream)
        values['device_type'] = PRODUCT_TYPES.get(values['device_type'], 'UNKNOWN')
        values['vendor_id'] = VENDORS.get(values['vendor_id'], 'UNKNOWN')
        values['serial'] = f"{values['serial']:08x}"

        return values


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





