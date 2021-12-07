# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Ian Ottoway <ian@ottoway.dev>
# Copyright (c) 2014 Agostino Ruscito <ruscito@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import ipaddress
from io import BytesIO
from typing import Any, Type, Dict, Tuple, Union, Set

from .cip import (
    DataType,
    DerivedDataType,
    Struct,
    UINT,
    USINT,
    DWORD,
    UDINT,
    SHORT_STRING,
    n_bytes,
    StructType,
    StringDataType,
    PRODUCT_TYPES,
    VENDORS,
    INT,
    ULINT,
)
from .cip.data_types import _StructReprMeta


__all__ = [
    "IPAddress",
    "ModuleIdentityObject",
    "ListIdentityObject",
    "StructTemplateAttributes",
    "FixedSizeString",
    "Revision",
    "StructTag",
]


def FixedSizeString(size_: int, len_type_: Union[DataType, Type[DataType]] = UDINT):
    """
    Creates a custom string tag type
    """

    class FixedSizeString(StringDataType):
        size = size_
        len_type = len_type_

        @classmethod
        def _encode(cls, value: str, *args, **kwargs) -> bytes:
            return (
                cls.len_type.encode(len(value))
                + value.encode(cls.encoding)
                + b"\x00" * (cls.size - len(value))
            )

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
        return ipaddress.IPv4Address(cls._stream_read(stream, 4)).exploded


class Revision(Struct(USINT("major"), USINT("minor"))):
    ...


class ModuleIdentityObject(
    Struct(
        UINT("vendor"),
        UINT("product_type"),
        UINT("product_code"),
        Revision("revision"),
        n_bytes(2, "status"),
        UDINT("serial"),
        SHORT_STRING("product_name"),
    )
):
    @classmethod
    def _decode(cls, stream: BytesIO):
        values = super(ModuleIdentityObject, cls)._decode(stream)
        values["product_type"] = PRODUCT_TYPES.get(values["product_type"], "UNKNOWN")
        values["vendor"] = VENDORS.get(values["vendor"], "UNKNOWN")
        values["serial"] = f"{values['serial']:08x}"

        return values

    @classmethod
    def _encode(cls, values: Dict[str, Any]):
        values = values.copy()
        values["product_type"] = PRODUCT_TYPES[values["product_type"]]
        values["vendor"] = VENDORS[values["vendor"]]
        values["serial"] = int.from_bytes(bytes.fromhex(values["serial"]), "big")
        return super(ModuleIdentityObject, cls)._encode(values)


class ListIdentityObject(
    Struct(
        UINT,
        UINT,
        UINT("encap_protocol_version"),
        INT,
        UINT,
        IPAddress("ip_address"),
        ULINT,
        UINT("vendor"),
        UINT("product_type"),
        UINT("product_code"),
        Revision("revision"),
        n_bytes(2, "status"),
        UDINT("serial"),
        SHORT_STRING("product_name"),
        USINT("state"),
    )
):
    @classmethod
    def _decode(cls, stream: BytesIO):
        values = super(ListIdentityObject, cls)._decode(stream)
        values["product_type"] = PRODUCT_TYPES.get(values["product_type"], "UNKNOWN")
        values["vendor"] = VENDORS.get(values["vendor"], "UNKNOWN")
        values["serial"] = f"{values['serial']:08x}"

        return values


StructTemplateAttributes = Struct(
    UINT("count"),
    Struct(UINT("attr_num"), UINT("status"), UDINT("size"))(name="object_definition_size"),
    Struct(UINT("attr_num"), UINT("status"), UDINT("size"))(name="structure_size"),
    Struct(UINT("attr_num"), UINT("status"), UINT("count"))(name="member_count"),
    Struct(UINT("attr_num"), UINT("status"), UINT("handle"))(name="structure_handle"),
)


class _StructTagReprMeta(_StructReprMeta):
    def __repr__(cls):
        members = ", ".join(repr(m) for m in cls.members)
        return f"{cls.__name__}({members}, bool_members={cls.bits!r},  struct_size={cls.size!r})"  # TODO


def StructTag(
    # (datatype, offset) of each member of the struct, does not include bit members aliased to other members
    *members: Tuple[DataType, int],
    bit_members: Dict[str, Tuple[int, int]],  # {member name, (offset, bit #) }
    private_members: Set[str],  # private members that should not be in the final value
    struct_size: int,
) -> Type[StructType]:
    _members = [x[0] for x in members]
    _offsets_ = {member: offset for (member, offset) in members}
    _struct = Struct(*_members)

    class StructTag(_struct, metaclass=_StructTagReprMeta):
        bits = bit_members
        private = private_members
        size = struct_size
        _offsets = _offsets_

        @classmethod
        def _decode(cls, stream: BytesIO):
            stream = BytesIO(stream.read(cls.size))
            raw = stream.getvalue()
            values = {}

            for member in cls.members:
                offset = cls._offsets[member]
                if stream.tell() < offset:
                    stream.read(offset - stream.tell())
                values[member.name] = member.decode(stream)

            for bit_member, (offset, bit) in cls.bits.items():
                bit_value = bool(raw[offset] & (1 << bit))
                values[bit_member] = bit_value

            return {k: v for k, v in values.items() if k not in cls.private}

        @classmethod
        def _encode(cls, values: Dict[str, Any]):
            # make a copy so that private host members aren't added to the original
            values = {k: v for k, v in values.items()}

            value = bytearray(cls.size)
            for member in cls.members:
                if member.name in cls.private:
                    continue
                offset = cls._offsets[member]
                encoded = member.encode(values[member.name])
                value[offset : offset + len(encoded)] = encoded

            for bit_member, (offset, bit) in cls.bits.items():
                val = values[bit_member]

                if val:
                    value[offset] |= 1 << bit
                else:
                    value[offset] &= ~(1 << bit)

            return value

    return StructTag
