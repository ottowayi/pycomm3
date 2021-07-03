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

import reprlib
import ipaddress
from io import BytesIO
from itertools import chain
from struct import pack, unpack
from typing import Any, Sequence, Optional, Tuple, Dict, Union, List, Type

from ..exceptions import DataError, BufferEmptyError
from ..map import EnumMap

_BufferType = Union[BytesIO, bytes]


__all__ = [
    "DataType",
    "ElementaryDataType",
    "BOOL",
    "SINT",
    "INT",
    "DINT",
    "LINT",
    "USINT",
    "UINT",
    "UDINT",
    "ULINT",
    "REAL",
    "LREAL",
    "STIME",
    "DATE",
    "TIME_OF_DAY",
    "DATE_AND_TIME",
    "StringDataType",
    "LOGIX_STRING",
    "STRING",
    "BytesDataType",
    "n_bytes",
    "BitArrayType",
    "BYTE",
    "WORD",
    "DWORD",
    "LWORD",
    "STRING2",
    "FTIME",
    "LTIME",
    "ITIME",
    "STRINGN",
    "SHORT_STRING",
    "TIME",
    "EPATH",
    "PACKED_EPATH",
    "PADDED_EPATH",
    "ENGUNIT",
    "STRINGI",
    "DerivedDataType",
    "ArrayType",
    "Array",
    "StructType",
    "Struct",
    "CIPSegment",
    "PortSegment",
    "LogicalSegment",
    "NetworkSegment",
    "SymbolicSegment",
    "DataSegment",
    "ConstructedDataTypeSegment",
    "ElementaryDataTypeSegment",
    "DataTypes",
]


def _repr(buffer: _BufferType) -> str:
    if isinstance(buffer, BytesIO):
        return repr(buffer.getvalue())
    else:
        return repr(buffer)


def _get_bytes(buffer: _BufferType, length: int) -> bytes:
    if isinstance(buffer, bytes):
        return buffer[:length]

    return buffer.read(length)


def _as_stream(buffer: _BufferType):
    if isinstance(buffer, bytes):
        return BytesIO(buffer)
    return buffer


class _DataTypeMeta(type):
    def __repr__(cls):
        return cls.__name__

    def __getitem__(cls, item):
        return Array(item, cls)


class DataType(metaclass=_DataTypeMeta):
    """
    Base class to represent a CIP data type.
    Instances of a type are only used when defining the
    members of a structure.

    Each type class provides ``encode`` / ``decode`` class methods.
    If overriding them, they must catch any unhandled exception
    and raise a ``DataError`` from it. For ``decode``, ``BufferEmptyError``
    should be reraised immediately without modification.
    The buffer empty error is needed for decoding arrays of
    unknown length.  Typically for custom types, overriding the
    private ``_encode``/``_decode`` methods are sufficient. The private
    methods do not need to do any exception handling if using the
    base public methods.  For ``_decode`` use the private ``_stream_read``
    method instead of ``stream.read``, so that ``BufferEmptyError`` exceptions are
    raised appropriately.
    """

    name = None  # class attr so class can be used in a struct w/o making an instance

    def __init__(self, name: Optional[str] = None):
        self.name = name

    @classmethod
    def encode(cls, value: Any) -> bytes:
        """
        Serializes a Python object ``value`` to ``bytes``.

        .. note::
            Any subclass overriding this method must catch any exception and re-raise a ``DataError``
        """
        try:
            return cls._encode(value)
        except Exception as err:
            raise DataError(f"Error packing {value!r} as {cls.__name__}") from err

    @classmethod
    def _encode(cls, value: Any) -> bytes:
        ...

    @classmethod
    def decode(cls, buffer: _BufferType) -> Any:
        """
        Deserializes a Python object from the ``buffer`` of ``bytes``

        .. note::
            Any subclass overriding this method must catch any exception and re-raise as a ``DataError``.
            Except ``BufferEmptyErrors`` they must be re-raised as such, array decoding relies on this.
        """
        try:
            stream = _as_stream(buffer)
            return cls._decode(stream)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(
                    f"Error unpacking {_repr(buffer)} as {cls.__name__}"
                ) from err

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        ...

    @classmethod
    def _stream_read(cls, stream: BytesIO, size: int):
        """
        Reads `size` bytes from `stream`.
        Raises `BufferEmptyError` if stream returns no data.
        """
        data = stream.read(size)
        if not data:
            raise BufferEmptyError()
        return data

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

    __str__ = __repr__


class ElementaryDataType(DataType):
    """
    Type that represents a single primitive value in CIP.
    """

    code: int = 0x00  #: CIP data type identifier
    size: int = 0  #: size of type in bytes
    _format: str = ""

    @classmethod
    def _encode(cls, value: Any) -> bytes:
        return pack(cls._format, value)

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        data = cls._stream_read(stream, cls.size)
        return unpack(cls._format, data)[0]


class BOOL(ElementaryDataType):
    """
    A boolean value, decodes ``0x00`` and ``False`` and ``True`` otherwise.
    ``True`` encoded as ``0xFF`` and ``False`` as ``0x00``
    """

    code = 0xC1  #: 0xC1
    size = 1

    @classmethod
    def _encode(cls, value: Any) -> bytes:
        return b"\xFF" if value else b"\x00"

    @classmethod
    def _decode(cls, stream: BytesIO) -> bool:
        data = cls._stream_read(stream, cls.size)
        return data != b"\x00"


class SINT(ElementaryDataType):
    """
    Signed 8-bit integer
    """

    code = 0xC2  #: 0xC2
    size = 1
    _format = "<b"


class INT(ElementaryDataType):
    """
    Signed 16-bit integer
    """

    code = 0xC3  #: 0xC3
    size = 2
    _format = "<h"


class DINT(ElementaryDataType):
    """
    Signed 32-bit integer
    """

    code = 0xC4  #: 0xC4
    size = 4
    _format = "<i"


class LINT(ElementaryDataType):
    """
    Signed 64-bit integer
    """

    code = 0xC5  #: 0xC5
    size = 8
    _format = "<q"


class USINT(ElementaryDataType):
    """
    Unsigned 8-bit integer
    """

    code = 0xC6  #: 0xC6
    size = 1
    _format = "<B"


class UINT(ElementaryDataType):
    """
    Unsigned 16-bit integer
    """

    code = 0xC7  #: 0xC7
    size = 2
    _format = "<H"


class UDINT(ElementaryDataType):
    """
    Unsigned 32-bit integer
    """

    code = 0xC8  #: 0xC8
    size = 4
    _format = "<I"


class ULINT(ElementaryDataType):
    """
    Unsigned 64-bit integer
    """

    code = 0xC9  #: 0xC9
    size = 8
    _format = "<Q"


class REAL(ElementaryDataType):
    """
    32-bit floating point
    """

    code = 0xCA  #: 0xCA
    size = 4
    _format = "<f"


class LREAL(ElementaryDataType):
    """
    64-bit floating point
    """

    code = 0xCB  #: 0xCB
    size = 8
    _format = "<d"


class STIME(DINT):
    """
    Synchronous time information
    """

    code = 0xCC  #: 0xCC


class DATE(UINT):
    """
    Date information
    """

    code = 0xCD  #: 0xCD


class TIME_OF_DAY(UDINT):
    """
    Time of day
    """

    code = 0xCE  #: 0xCE


class DATE_AND_TIME(ElementaryDataType):
    """
    Date and time of day
    """

    code = 0xCF  #: 0xCF
    size = 8

    @classmethod
    def encode(cls, time: int, date: int, *args, **kwargs) -> bytes:
        try:
            return UDINT.encode(time) + UINT.encode(date)
        except Exception as err:
            raise DataError(f"Error packing {time!r} as {cls.__name__}") from err

    @classmethod
    def _decode(cls, stream: BytesIO) -> Tuple[int, int]:
        return UDINT.decode(stream), UINT.decode(stream)


class StringDataType(ElementaryDataType):
    """
    Base class for any string type
    """

    len_type = None  #: data type of the string length
    encoding = "iso-8859-1"  #: encoding of string data

    @classmethod
    def _encode(cls, value: str, *args, **kwargs) -> bytes:
        return cls.len_type.encode(len(value)) + value.encode(cls.encoding)

    @classmethod
    def _decode(cls, stream: BytesIO) -> str:
        str_len = cls.len_type.decode(stream)
        if str_len == 0:
            return ""
        str_data = cls._stream_read(stream, str_len)

        return str_data.decode(cls.encoding)


class LOGIX_STRING(StringDataType):
    """
    Character string, 1-byte per character, 4-byte length
    """

    len_type = UDINT


class STRING(StringDataType):
    """
    Character string, 1-byte per character, 2-byte length
    """

    code = 0xD0  #: 0xD0
    len_type = UINT


class BytesDataType(ElementaryDataType):
    """
    Base type for placeholder bytes.
    """

    @classmethod
    def _encode(cls, value: bytes, *args, **kwargs) -> bytes:
        return value[: cls.size] if cls.size != -1 else value[:]

    @classmethod
    def _decode(cls, stream: BytesIO) -> bytes:
        data = cls._stream_read(stream, cls.size)
        return data


def n_bytes(count: int, name: str = ""):
    """
    Create an instance of a byte string of ``count`` length.
    Setting ``count`` to ``-1`` will consume the entire remaining buffer.
    """

    class BYTES(BytesDataType):
        size = count

    return BYTES(name)


class BitArrayType(ElementaryDataType):
    """
    Array of bits (Python bools) for ``host_type`` integer value
    """

    host_type = None

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        val = cls.host_type.decode(stream)
        bits = [x == "1" for x in bin(val)[2:]]
        bools = [False for _ in range((cls.size * 8) - len(bits))] + bits
        bools.reverse()
        return bools

    @classmethod
    def _encode(cls, value: Any) -> bytes:
        if len(value) != (8 * cls.size):
            raise DataError(f"boolean arrays must be multiple of 8: not {len(value)}")
        _value = 0
        for i, val in enumerate(value):
            if val:
                _value |= 1 << i
        return cls.host_type._encode(_value)


class BYTE(BitArrayType):
    """
    bit string - 8-bits
    """

    code = 0xD1  #: 0xD1
    size = 1
    host_type = USINT


class WORD(BitArrayType):
    """
    bit string - 16-bits
    """

    code = 0xD2  #: 0xD2
    size = 2
    host_type = UINT


class DWORD(BitArrayType):
    """
    bit string - 32-bits
    """

    code = 0xD3  #: 0xD3
    size = 4
    host_type = UDINT


class LWORD(BitArrayType):
    """
    bit string - 64-bits
    """

    code = 0xD4  #: 0xD4
    size = 8
    host_type = ULINT


class STRING2(StringDataType):
    """
    character string, 2-bytes per character
    """

    code = 0xD5  #: 0xD5
    len_type = UINT
    encoding = "utf-16-le"


class FTIME(DINT):
    """
    duration - high resolution
    """

    code = 0xD6  #: 0xD6


class LTIME(LINT):
    """
    duration - long
    """

    code = 0xD7  #: 0xD7


class ITIME(INT):
    """
    duration - short
    """

    code = 0xD8  #: 0xD8


class STRINGN(StringDataType):
    """
    character string, n-bytes per character
    """

    code = 0xD9  #: 0xD9
    ENCODINGS = {1: "utf-8", 2: "utf-16-le", 4: "utf-32-le"}

    @classmethod
    def encode(cls, value: str, char_size: int = 1) -> bytes:
        try:
            encoding = cls.ENCODINGS[char_size]
            return (
                UINT.encode(char_size)
                + UINT.encode(len(value))
                + value.encode(encoding)
            )
        except Exception as err:
            raise DataError(
                f"Error encoding {value!r} as STRINGN using char. size {char_size}"
            ) from err

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        char_size = UINT.decode(stream)
        char_count = UINT.decode(stream)

        try:
            encoding = cls.ENCODINGS[char_size]
        except KeyError as err:
            raise DataError(f"Unsupported character size: {char_size}") from err
        else:
            data = cls._stream_read(stream, char_count * char_size)

            return data.decode(encoding)


class SHORT_STRING(StringDataType):
    """
    character string, 1-byte per character, 1-byte length
    """

    code = 0xDA  #: 0xDA
    len_type = USINT


class TIME(DINT):
    """
    duration - milliseconds
    """

    code = 0xDB  #: 0xDB


class EPATH(ElementaryDataType):
    """
    CIP path segments
    """

    code = 0xDC  #: 0xDC
    padded = False

    @classmethod
    def encode(
        cls,
        segments: Sequence[Union["CIPSegment", bytes]],
        length: bool = False,
        pad_length: bool = False,
    ) -> bytes:
        try:
            path = b"".join(
                segment
                if isinstance(segment, bytes)
                else segment.encode(segment, padded=cls.padded)
                for segment in segments
            )
            if length:
                _len = USINT.encode(len(path) // 2)
                if pad_length:
                    _len += b"\x00"
                path = _len + path
            return path
        except Exception as err:
            raise DataError(
                f"Error packing {reprlib.repr(segments)} as {cls.__name__}"
            ) from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> Sequence["CIPSegment"]:
        raise NotImplementedError("Decoding EPATHs not supported")


class PADDED_EPATH(EPATH):
    padded = True


class PACKED_EPATH(EPATH):
    padded = False


class ENGUNIT(WORD):
    """
    engineering units
    """

    code = 0xDD  #: 0xDD
    # TODO: create lookup table of defined eng. units


class STRINGI(StringDataType):
    """
    international character string
    """

    code = 0xDE  #: 0xDE

    STRING_TYPES = {
        STRING.code: STRING,
        STRING2.code: STRING2,
        STRINGN.code: STRINGN,
        SHORT_STRING.code: SHORT_STRING,
    }

    LANGUAGE_CODES = {
        "english": "eng",
        "french": "fra",
        "spanish": "spa",
        "italian": "ita",
        "german": "deu",
        "japanese": "jpn",
        "portuguese": "por",
        "chinese": "zho",
        "russian": "rus",
    }

    CHARACTER_SETS = {
        "iso-8859-1": 4,
        "iso-8859-2": 5,
        "iso-8859-3": 6,
        "iso-8859-4": 7,
        "iso-8859-5": 8,
        "iso-8859-6": 9,
        "iso-8859-7": 10,
        "iso-8859-8": 11,
        "iso-8859-9": 12,
        "utf-16-le": 1000,
        "utf-32-le": 1001,
    }

    @classmethod
    def encode(cls, *strings: Sequence[Tuple[str, StringDataType, str, int]]) -> bytes:
        """
        Encodes ``strings`` to bytes
        """
        try:
            count = len(strings)
            data = USINT.encode(count)

            for (string, str_type, lang, char_set) in strings:
                _str_type = bytes([str_type.code])
                _lang = bytes(lang, "ascii")
                _char_set = UINT.encode(char_set)
                _string = str_type.encode(string)

                data += _lang + _str_type + _char_set + _string

            return data
        except Exception as err:
            raise DataError(
                f"Error packing {reprlib.repr(strings)} as {cls.__name__}"
            ) from err

    @classmethod
    def decode(
        cls, buffer: _BufferType
    ) -> Tuple[Sequence[str], Sequence[str], Sequence[int]]:
        stream = _as_stream(buffer)
        try:
            count = USINT.decode(stream)
            strings = []
            langs = []
            char_sets = []
            for _ in range(count):
                lang = SHORT_STRING.decode(b"\x03" + stream.read(3))
                langs.append(lang)
                _str_type = cls.STRING_TYPES[stream.read(1)[0]]
                char_set = UINT.decode(stream)
                char_sets.append(char_set)
                string = _str_type.decode(stream)
                strings.append(string)

            return strings, langs, char_sets
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(
                    f"Error unpacking {_repr(buffer)} as {cls.__name__}"
                ) from err


class DerivedDataType(DataType):
    """
    Base type for types composed of :class:`ElementaryDataType`
    """

    ...


class _ArrayReprMeta(_DataTypeMeta):
    def __repr__(cls: "ArrayType"):
        return f"{cls.element_type}[{cls.length!r}]"

    __str__ = __repr__


class ArrayType(DerivedDataType, metaclass=_ArrayReprMeta):
    """
    Base type for an array
    """

    ...


def Array(
    length_: Union[USINT, UINT, UDINT, ULINT, int, None],
    element_type_: Union[DataType, Type[DataType]],
) -> Type[ArrayType]:
    """
    Creates a new array type from ``element_type_`` of ``length_``.

    ``length_`` can be 3 possible types:
        - ``int`` - fixed length of the array
        - ``DataType`` - length read from beginning of buffer as type
        - ``None`` - unbound array, consumes entire buffer on decode
    """

    class Array(ArrayType):
        length: Union[USINT, UINT, UDINT, ULINT, int, None] = length_
        element_type: Union[DataType, Type[DataType]] = element_type_

        @classmethod
        def encode(cls, values: List[Any], length: Optional[int] = None) -> bytes:
            _length = length or cls.length
            if isinstance(_length, int):
                if len(values) < _length:
                    raise DataError(
                        f"Not enough values to encode array of {cls.element_type}[{_length}]"
                    )

                _len = _length
            else:
                _len = len(values)

            try:
                if issubclass(cls.element_type, BitArrayType):
                    chunk_size = cls.element_type.size * 8
                    _len = len(values) // chunk_size
                    values = [
                        values[i : i + chunk_size]
                        for i in range(0, len(values), chunk_size)
                    ]

                return b"".join(cls.element_type.encode(values[i]) for i in range(_len))
            except Exception as err:
                raise DataError(
                    f"Error packing {reprlib.repr(values)} into {cls.element_type}[{_length}]"
                ) from err

        @classmethod
        def _decode_all(cls, stream):
            _array = []
            while True:
                try:
                    _array.append(cls.element_type.decode(stream))
                except BufferEmptyError:
                    break
            return _array

        @classmethod
        def decode(cls, buffer: _BufferType, length: Optional[int] = None) -> List[str]:
            _length = length or cls.length
            try:
                stream = _as_stream(buffer)
                if _length is None:
                    return cls._decode_all(stream)

                if isinstance(_length, DataType):
                    _len = _length.decode(stream)
                else:
                    _len = _length

                _val = [cls.element_type.decode(stream) for _ in range(_length)]

                if issubclass(cls.element_type, BitArrayType):
                    return list(chain.from_iterable(_val))

                return _val
            except Exception as err:
                if isinstance(err, BufferEmptyError):
                    raise
                else:
                    raise DataError(
                        f"Error unpacking into {cls.element_type}[{_length}] from {_repr(buffer)}"
                    ) from err

        def __repr__(self) -> str:
            return f"{repr(self.__class__)}(name={self.name!r})"

    return Array


class _StructReprMeta(_DataTypeMeta):
    def __repr__(cls):
        return f'{cls.__name__}({", ".join(repr(m) for m in cls.members)})'


class StructType(DerivedDataType, metaclass=_StructReprMeta):
    """
    Base type for a structure
    """

    ...


def Struct(*members_: Union[DataType, Type[DataType]]) -> Type[StructType]:
    """
    Creates a new structure type comprised of ``members_``.  Members can be
    instances of a ``DataType`` with a ``name``.  The decoded value of a struct
    will a dictionary of ``{member.name: value}``, members without names will be
    excluded from the return value. To encode a struct, the value should be a
    dict of ``{member.name: value}`` or a sequence of just values (nesting as needed).
    Avoid multiple no-name members if planning on encoding the struct using a dict.
    """

    class Struct(StructType):
        members: Tuple[Union[DataType, Type[DataType]]] = members_

        @classmethod
        def _encode(cls, values: Union[Dict[str, Any], Sequence[Any]]) -> bytes:
            if isinstance(values, dict):
                return b"".join(typ.encode(values[typ.name]) for typ in cls.members)
            else:
                return b"".join(
                    typ.encode(val) for typ, val in zip(cls.members, values)
                )

        @classmethod
        def _decode(cls, stream: BytesIO) -> Any:
            values = {typ.name: typ.decode(stream) for typ in cls.members}

            # filter any members w/o a name
            values.pop("", None)
            values.pop(None, None)

            return values

    return Struct


class CIPSegment(DataType):
    """
    Base type for a CIP path segment

    +----+----+----+---+---+---+---+---+
    | Segment Type | Segment Format    |
    +====+====+====+===+===+===+===+===+
    |  7 |  6 | 5  | 4 | 3 | 2 | 1 | 0 |
    +----+----+----+---+---+---+---+---+

    """

    segment_type = 0b_000_00000

    @classmethod
    def encode(cls, segment: "CIPSegment", padded: bool = False) -> bytes:
        """
        Encodes an instance of a ``CIPSegment`` to bytes
        """
        try:
            return cls._encode(segment, padded)
        except Exception as err:
            raise DataError(
                f"Error packing {reprlib.repr(segment)} as {cls.__name__}"
            ) from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> Any:
        """
        .. attention:: Not Implemented
        """
        raise NotImplementedError("Decoding of CIP Segments not supported")


class PortSegment(CIPSegment):
    """
    Port segment of a CIP path.

    +----+----+----+--------------------+----+----+----+----+
    | Segment Type | Extended Link Addr | Port Identifier   |
    +====+====+====+====================+====+====+====+====+
    |  7 |  6 | 5  |         4          |  3 |  2 |  1 |  0 |
    +----+----+----+--------------------+----+----+----+----+

    """

    segment_type = 0b_000_0_0000
    extended_link = 0b_000_1_0000

    #: available port names for use in a CIP path
    port_segments = {
        "backplane": 0b_000_0_0001,
        "bp": 0b_000_0_0001,
        "enet": 0b_000_0_0010,
        "dhrio-a": 0b_000_0_0010,
        "dhrio-b": 0b_000_0_0011,
        "dnet": 0b_000_0_0010,
        "cnet": 0b_000_0_0010,
        "dh485-a": 0b_000_0_0010,
        "dh485-b": 0b_000_0_0011,
    }

    def __init__(
        self,
        port: Union[int, str],
        link_address: Union[int, str, bytes],
        name: str = "",
    ):
        super().__init__(name)
        self.port = port
        self.link_address = link_address

    @classmethod
    def _encode(cls, segment: "PortSegment", padded: bool = False) -> bytes:
        if isinstance(segment.port, str):
            port = cls.port_segments[segment.port]
        else:
            port = segment.port
        if isinstance(segment.link_address, str):
            if segment.link_address.isnumeric():
                link = USINT.encode(int(segment.link_address))
            else:
                ipaddress.ip_address(segment.link_address)
                link = segment.link_address.encode()
        elif isinstance(segment.link_address, int):
            link = USINT.encode(segment.link_address)
        else:
            link = segment.link_address

        if len(link) > 1:
            port |= cls.extended_link
            _len = USINT.encode(len(link))
        else:
            _len = b""

        _segment = USINT.encode(port) + _len + link
        if len(_segment) % 2:
            _segment += b"\x00"

        return _segment

    def __eq__(self, other):
        return self.encode(self) == self.encode(other)

    def __repr__(self):
        return f"{self.__class__.__name__}(port={self.port!r}, link_address={self.link_address!r})"


class LogicalSegment(CIPSegment):
    """
    Logical segment of a CIP path

    +----+----+----+----+----+----+-------+--------+
    | Segment Type | Logical Type | Logical Format |
    +====+====+====+====+====+====+=======+========+
    |  7 |  6 |  5 | 4  |  3 |  2 |   1   |    0   |
    +----+----+----+----+----+----+-------+--------+
    """

    segment_type = 0b_001_00000

    #: available logical types
    logical_types = {
        "class_id": 0b_000_000_00,
        "instance_id": 0b_000_001_00,
        "member_id": 0b_000_010_00,
        "connection_point": 0b_000_011_00,
        "attribute_id": 0b_000_100_00,
        "special": 0b_000_101_00,
        "service_id": 0b_000_110_00,
    }

    logical_format = {
        1: 0b_000_000_00,  # 8-bit
        2: 0b_000_000_01,  # 16-bit
        4: 0b_000_000_11,  # 32-bit
    }

    # 32-bit only valid for Instance ID and Connection Point types

    def __init__(
        self, logical_value: Union[int, bytes], logical_type: str, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.logical_value = logical_value
        self.logical_type = logical_type

    @classmethod
    def _encode(cls, segment: "LogicalSegment", padded: bool = False) -> bytes:
        _type = cls.logical_types.get(segment.logical_type)
        _value = segment.logical_value
        if _type is None:
            raise DataError("Invalid logical type")

        if isinstance(_value, int):
            if _value <= 0xFF:
                _value = USINT.encode(_value)
            elif _value <= 0xFFFF:
                _value = UINT.encode(_value)
            elif _value <= 0xFFFF_FFFF:
                _value = UDINT.encode(_value)
            else:
                raise DataError(f"Invalid segment value: {segment!r}")

        _fmt = cls.logical_format.get(len(_value))

        if _fmt is None:
            raise DataError(f"Segment value not valid for segment type")

        _segment = bytes([cls.segment_type | _type | _fmt])
        if padded and (len(_segment) + len(_value)) % 2:
            _segment += b"\x00"

        return _segment + _value


class NetworkSegment(CIPSegment):
    segment_type = 0b_010_00000


class SymbolicSegment(CIPSegment):
    segment_type = 0b_011_00000


class DataSegment(CIPSegment):
    """
    +----+----+----+---+---+---+---+---+
    | Segment Type | Segment Sub-Type  |
    +====+====+====+===+===+===+===+===+
    |  7 |  6 | 5  | 4 | 3 | 2 | 1 | 0 |
    +----+----+----+---+---+---+---+---+
    """

    segment_type = 0b_100_00000
    extended_symbol = 0b_000_10001

    def __init__(self, data: Union[str, bytes], name: str = ""):
        super().__init__(name)
        self.data = data

    @classmethod
    def _encode(cls, segment: "DataSegment", padded: bool = False) -> bytes:
        _segment = cls.segment_type
        if not isinstance(segment.data, str):
            return (
                USINT.encode(_segment) + USINT.encode(len(segment.data)) + segment.data
            )

        _segment |= cls.extended_symbol
        _data = segment.data.encode()
        _len = len(_data)
        if _len % 2:
            _data += b"\x00"
        return USINT.encode(_segment) + USINT.encode(_len) + _data


class ConstructedDataTypeSegment(CIPSegment):
    segment_type = 0b_101_00000


class ElementaryDataTypeSegment(CIPSegment):
    segment_type = 0b_110_00000


def _by_type_code(typ: ElementaryDataType):
    return typ.code


class DataTypes(EnumMap):
    """
    Lookup table/map of elementary data types.  Reverse lookup is by CIP code for data type.
    """

    _return_caps_only_ = True
    _value_key_ = _by_type_code

    bool = BOOL
    sint = SINT
    int = INT
    dint = DINT
    lint = LINT

    usint = USINT
    uint = UINT
    udint = UDINT
    ulint = ULINT

    real = REAL
    lreal = LREAL

    stime = STIME
    date = DATE
    time_of_day = TIME_OF_DAY
    date_and_time = DATE_AND_TIME

    logix_string = LOGIX_STRING
    string = STRING

    byte = BYTE
    word = WORD
    dword = DWORD
    lword = LWORD

    string2 = STRING2

    ftime = FTIME
    ltime = LTIME
    itime = ITIME

    stringn = STRINGN
    short_string = SHORT_STRING

    time = TIME

    padded_epath = PADDED_EPATH
    packed_epath = PACKED_EPATH

    engunit = ENGUNIT

    stringi = STRINGI

    @classmethod
    def get_type(cls, type_code):
        return cls.get(cls.get(type_code))
