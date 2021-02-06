import ipaddress

from io import BytesIO
from typing import Any, Union

from .cip import (DataType, ElementaryDataType, DerivedDataType, BufferEmptyError, Struct, UINT, USINT,
                  SINT, UDINT, SHORT_STRING, n_bytes, WORD, Array)

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