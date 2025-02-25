from __future__ import annotations

import ipaddress
import reprlib
from io import BytesIO
from math import log
from dataclasses import dataclass, field
from enum import IntFlag
from typing import ClassVar, cast, Self

from ._base import BufferT, DataType, buff_repr, as_stream, BYTES, array
from .numeric import USINT, UINT, UDINT
from .string import SHORT_STRING

from pycomm3.exceptions import DataError, BufferEmptyError

__all__ = (
    "CIPSegment",
    "ConstructedDataTypeSegment",
    "DataSegment",
    "DataSegmentType",
    "ElementaryDataTypeSegment",
    "EPATH",
    "LogicalSegment",
    "LogicalSegmentType",
    "NetworkSegment",
    "NetworkSegmentType",
    "PACKED_EPATH",
    "PADDED_EPATH",
    "PADDED_EPATH_LEN",
    "PADDED_EPATH_PAD_LEN",
    "PORT_ALIASES",
    "PortIdentifier",
    "PortSegment",
    "PortSegmentFormat",
    "SegmentType",
    "SymbolicSegment",
    "SymbolicSegmentExtendedFormat",
    "SymbolicSegmentType",
)


class SegmentType(IntFlag):
    port = 0b_000_00000
    logical = 0b_001_00000
    network = 0b_010_00000
    symbolic = 0b_011_00000
    data = 0b_100_00000
    constructed_data_type = 0b_101_00000
    elementary_data_type = 0b_110_00000
    reserved = 0b_111_00000
    mask = 0b_111_00000


def _segment_type_bits(segment_type: int) -> str:
    return f"{segment_type:08b}"[:3]


@dataclass
class CIPSegment(DataType):
    """
    Base type for a CIP path segment

    +----+----+----+----+----+----+----+----+
    | Segment Type | Segment Format         |
    +====+====+====+====+====+====+====+====+
    | 7  | 6  | 5  | 4  | 3  | 2  | 1  | 0  |
    +----+----+----+----+----+----+----+----+

    """

    segment_type: ClassVar[SegmentType] = SegmentType.port

    @classmethod
    def encode(cls, value: CIPSegment, padded: bool = False, *args, **kwargs) -> bytes:
        """
        Encodes an instance of a ``CIPSegment`` to bytes
        """
        try:
            return cls._encode(value, padded)
        except Exception as err:
            raise DataError(f"Error packing {reprlib.repr(value)} as {cls.__name__}") from err

    @classmethod
    def _decode_segment_type(cls, buffer: BytesIO) -> USINT:
        segment_type = USINT.decode(buffer)
        if (segment_type & SegmentType.mask) != cls.segment_type:
            raise DataError(
                f"Segment type invalid for {cls.__name__} ({_segment_type_bits(cls.segment_type)}): {_segment_type_bits(segment_type)}"
            )

        return segment_type

    @classmethod
    def decode(cls, buffer: BufferT, padded: bool = False) -> CIPSegment:
        try:
            stream = as_stream(buffer)
            return cls._decode(stream, padded)
        except BufferEmptyError:
            raise
        except Exception as err:
            raise DataError(f"Error unpacking {buff_repr(buffer)} as {cls.__name__}") from err

    @classmethod
    def _decode(cls, stream: BytesIO, padded: bool = False) -> CIPSegment:
        _peek = stream.getvalue()[stream.tell() : stream.tell() + 1]
        if not _peek:
            raise BufferEmptyError()

        segment_type = _peek[0] & SegmentType.mask
        for subcls in CIPSegment.__subclasses__():
            if subcls.segment_type == segment_type:
                return subcls.decode(stream, padded)

        raise DataError(f"Unknown segment type: {_segment_type_bits(segment_type)}")


class PortIdentifier(IntFlag):
    backplane = 0b_000_0_0001
    bp = 0b_000_0_0001
    enet = 0b_000_0_0010
    a = 0b_000_0_0010
    b = 0b_000_0_0011
    a1 = 0b_000_0_0011
    a2 = 0b_000_0_0100


PORT_ALIASES: dict[str, PortIdentifier] = PortIdentifier._member_map_  # noqa # type: ignore


class PortSegmentFormat(IntFlag):
    ex_link_address = 0b_000_1_0000
    mask_port_id = 0b_000_0_1111


def _find_best_uint_type(value: int) -> USINT | UINT | UDINT:
    if value == 0:
        return USINT(0)
    num_bytes = int(log(value, 256)) + 1
    if num_bytes <= USINT.size:
        return USINT(value)
    elif num_bytes <= UINT.size:
        return UINT(value)
    elif num_bytes <= UDINT.size:
        return UDINT(value)
    else:
        raise DataError(f"Cannot convert {value}, requires too many bytes ({num_bytes})")


@dataclass
class PortSegment(CIPSegment):
    """
    Port segment of a CIP path.

    +----+----+----+--------------------+----+----+----+----+
    | Segment Type | Extended Link Addr | Port Identifier   |
    +====+====+====+====================+====+====+====+====+
    |  7 |  6 | 5  |         4          |  3 |  2 |  1 |  0 |
    +----+----+----+--------------------+----+----+----+----+

    """

    segment_type: ClassVar[SegmentType] = SegmentType.port

    # don't use these fields when comparing segments, use the private versions instead
    # since they are the actual encoded values
    port: PortIdentifier | int | str = field(compare=False)
    link_address: int | str | bytes = field(compare=False)

    _port: USINT = field(init=False)
    _link: bytes | DataType = field(init=False)
    _ex_link: bool = field(default=False, init=False)
    _link_addr_size: USINT = field(default=USINT(0), init=False)
    _ex_port: UINT = field(default=UINT(0), init=False)

    def __post_init__(self) -> None:
        try:
            if isinstance(self.port, str):
                self.port = PORT_ALIASES[self.port.lower()]
            if self.port > PortSegmentFormat.mask_port_id:
                self._port = USINT(PortSegmentFormat.mask_port_id)
                self._ex_port = UINT(self.port)
            else:
                self._port = USINT(self.port)
        except Exception as err:
            raise DataError(f"Invalid port: {self.port!r}") from err

        try:
            if isinstance(self.link_address, str):
                if self.link_address.isnumeric():
                    self._link = bytes(_find_best_uint_type(int(self.link_address)))
                else:
                    try:
                        ip = ipaddress.ip_address(self.link_address)
                    except ValueError:
                        raise DataError(f"cannot convert link_address ({self.link_address!r}) to ip address")
                    else:
                        self._link = str(ip).encode()
            elif isinstance(self.link_address, int):
                self._link = bytes(_find_best_uint_type(self.link_address))
            else:
                self._link = self.link_address

            if len(self._link) > 1:
                self._ex_link = True
                self._link_addr_size = USINT(len(self._link))
        except Exception as err:
            raise DataError("Invalid link") from err

    @classmethod
    def _encode(cls, value: "PortSegment", padded: bool = False, *args, **kwargs) -> bytes:
        segment_type = cls.segment_type | value._port
        if value._ex_link:
            segment_type |= PortSegmentFormat.ex_link_address

        msg = b"".join(
            (
                bytes(x)  # type: ignore
                for x in (
                    USINT(segment_type),
                    value._ex_port if value._ex_port else b"",
                    value._link_addr_size if value._ex_link else b"",
                    value._link,
                )
            )
        )
        if len(msg) % 2:
            msg += b"\x00"

        return msg

    @classmethod
    def _decode(cls, stream: BytesIO, padded: bool = False) -> "PortSegment":
        segment_type = cls._decode_segment_type(stream)
        ex_link = bool(segment_type & PortSegmentFormat.ex_link_address)
        port = segment_type & PortSegmentFormat.mask_port_id

        if port == PortSegmentFormat.mask_port_id:
            try:
                port = UINT.decode(stream)
            except Exception as err:
                raise DataError("Error decoding extended port id") from err

        link: bytes | USINT
        if ex_link:
            link_addr_size = USINT.decode(stream)
            if not link_addr_size:
                raise DataError("Extended link address size is 0")
            try:
                link = cls._stream_read(stream, link_addr_size)
            except BufferEmptyError:
                link = b""
            if len(link) != link_addr_size:
                raise DataError(
                    f"Extended link address invalid, expected {int(link_addr_size)} byte(s), got: {len(link)}"
                )

            if link_addr_size % 2:
                try:
                    _pad = cls._stream_read(stream, 1)
                except BufferEmptyError:
                    raise DataError("Expected a pad byte following link address")
        else:
            try:
                link = USINT.decode(stream)
            except Exception:
                raise DataError("Error decoding link address")

        return PortSegment(port, link)


class LogicalSegmentType(IntFlag):
    type_class_id = 0b_000_000_00
    type_instance_id = 0b_000_001_00
    type_member_id = 0b_000_010_00
    type_connection_point = 0b_000_011_00
    type_attribute_id = 0b_000_100_00
    type_special = 0b_000_101_00
    type_service_id = 0b_000_110_00
    type_reserved = 0b_000_111_00
    mask_type = 0b_000_111_00

    format_8bit = 0b_000_000_00
    format_16bit = 0b_000_000_01
    format_32bit = 0b_000_000_10
    format_reserved = 0b_000_000_11
    format_8bit_service_id = 0b_000_000_00
    format_electronic_key = 0b_000_000_00
    mask_format = 0b_000_000_11


def _logical_format_bits(fmt: int) -> str:
    return f"{fmt:08b}"[-2:]


def _logical_type_bits(fmt: int) -> str:
    return f"{fmt:08b}"[3:6]


@dataclass
class LogicalSegment(CIPSegment):
    """
    Logical segment of a CIP path

    +----+----+----+----+----+----+-------+--------+
    | Segment Type | Logical Type | Logical Format |
    +====+====+====+====+====+====+=======+========+
    |  7 |  6 |  5 | 4  |  3 |  2 |   1   |    0   |
    +----+----+----+----+----+----+-------+--------+
    """

    segment_type: ClassVar[SegmentType] = SegmentType.logical
    type: LogicalSegmentType
    value: int | bytes

    _value: bytes = field(default=b"", init=False)
    _format: LogicalSegmentType = field(default=LogicalSegmentType.format_8bit)

    def __post_init__(self) -> None:
        if isinstance(self.value, int):
            self._value = bytes(_find_best_uint_type(self.value))
        else:
            self._value = self.value

        _val_len = len(self._value)

        if self.type == LogicalSegmentType.type_service_id:
            if _val_len != 1:
                raise DataError(f"Invalid logical value for Service ID type, expected 1 byte, got: {_val_len}")
            self._format = LogicalSegmentType.format_8bit_service_id
        elif self.type == LogicalSegmentType.type_special:
            self._format = LogicalSegmentType.format_electronic_key
            # FUTURE: support electronic key
            raise DataError("Logical segments with Special type are not supported")
        else:
            if _val_len == 1:
                self._format = LogicalSegmentType.format_8bit
            elif _val_len == 2:
                self._format = LogicalSegmentType.format_16bit
            elif _val_len == 4:
                if self.type not in (
                    LogicalSegmentType.type_instance_id,
                    LogicalSegmentType.type_connection_point,
                ):
                    raise DataError("32-bit logical value only valid for Instance ID and Connection Point types")
                self._format = LogicalSegmentType.format_32bit
            else:
                raise DataError("logical value too large")

    @classmethod
    def _encode(cls, value: "LogicalSegment", padded: bool = False, *args, **kwargs) -> bytes:
        segment_type = bytes(USINT(cls.segment_type | value.type | value._format))
        if padded and value._format in (
            LogicalSegmentType.format_16bit,
            LogicalSegmentType.format_32bit,
        ):
            segment_type += b"\x00"

        return segment_type + value._value

    @classmethod
    def _decode(cls, stream: BytesIO, padded: bool = False) -> "LogicalSegment":
        segment_type = cls._decode_segment_type(stream)
        _type = segment_type & LogicalSegmentType.mask_type
        _format = segment_type & LogicalSegmentType.mask_format

        if _type == LogicalSegmentType.type_reserved:
            raise DataError("Unsupported logical type: Reserved")

        if _format == LogicalSegmentType.format_reserved:
            raise DataError("Unsupported logical format: Reserved")
        elif _format == LogicalSegmentType.format_32bit and _type not in (
            LogicalSegmentType.type_instance_id,
            LogicalSegmentType.type_connection_point,
        ):
            raise DataError(f"32-bit logical format on unsupported logical type: {_logical_type_bits(_type)}")

        value: int | bytes
        if _type == LogicalSegmentType.type_special:
            if _format != LogicalSegmentType.format_electronic_key:
                raise DataError(f"Unsupported logical format for Special type (00): {_logical_format_bits(_format)}")
            value = cls._stream_read(stream, 6)  # FUTURE: support electronic key
        elif _type == LogicalSegmentType.type_service_id:
            if _format != LogicalSegmentType.format_8bit_service_id:
                raise DataError(f"Unsupported logical format for Service ID type (00): {_logical_format_bits(_format)}")
            try:
                value = USINT.decode(stream)
            except Exception:
                raise DataError("Error decoding service id logical value")
        else:
            try:
                if _format == LogicalSegmentType.format_8bit:
                    value = USINT.decode(stream)
                else:
                    if padded:
                        BYTES[1].decode(stream)
                    if _format == LogicalSegmentType.format_16bit:
                        value = UINT.decode(stream)
                    else:
                        value = UDINT.decode(stream)
            except Exception as err:
                raise DataError("Error decoding logical value") from err

        return LogicalSegment(LogicalSegmentType(_type & LogicalSegmentType.mask_type), value)


class NetworkSegmentType(IntFlag):
    scheduled = 0b_000_00001
    fixed_tag = 0b_000_00010
    production_inhibit_time = 0b_000_00011
    safety = 0b_000_10000
    extended = 0b_000_11111

    mask_type = 0b_000_11111
    mask_data_array = 0b_000_10000


_supported_network_segment_types = {
    NetworkSegmentType.scheduled,
    NetworkSegmentType.fixed_tag,
    NetworkSegmentType.production_inhibit_time,
    NetworkSegmentType.safety,
    NetworkSegmentType.extended,
}


def _network_type_bits(typ: int) -> str:
    return f"{typ:08b}"[3:]


@dataclass
class NetworkSegment(CIPSegment):
    segment_type: ClassVar[SegmentType] = SegmentType.network
    type: NetworkSegmentType
    data: bytes

    # unsure of how extended segment subtypes work, for now treated as first 2 bytes of data

    def __post_init__(self):
        if self.type not in _supported_network_segment_types:
            raise DataError(f"Network segment subtype unsupported: {_network_type_bits(self.type)}")
        if not (self.type & NetworkSegmentType.mask_data_array) and len(self.data) != 1:
            raise DataError(
                f"Network segment subtype {_network_type_bits(self.type)} requires exactly one byte of data"
            )

    @classmethod
    def _encode(cls, value: "NetworkSegment", *args, **kwargs) -> bytes:
        _segment_type = bytes(USINT(value.segment_type | value.type))
        if value.type & NetworkSegmentType.mask_data_array:
            _len = len(value.data)
            if value.type == NetworkSegmentType.extended:
                _len -= 2
            return b"".join([_segment_type, bytes(USINT(_len)), value.data])
        else:
            return _segment_type + value.data

    @classmethod
    def _decode(cls, stream: BytesIO, padded: bool = False) -> "NetworkSegment":
        segment_type = cls._decode_segment_type(stream)
        _type = segment_type & NetworkSegmentType.mask_type
        if _type not in _supported_network_segment_types:
            raise DataError(f"Network segment subtype unsupported: {_network_type_bits(_type)}")
        try:
            if _type & NetworkSegmentType.mask_data_array:
                _len = USINT.decode(stream)
                if _type == NetworkSegmentType.extended:
                    _len += 2
                data = BYTES[_len].decode(stream)
            else:
                data = bytes(USINT.decode(stream))
        except Exception as err:
            raise DataError("Error decoding Network segment data") from err

        return NetworkSegment(NetworkSegmentType(_type), data)


class SymbolicSegmentType(IntFlag):
    mask_symbol_size = 0b_000_11111


class SymbolicSegmentExtendedFormat(IntFlag):
    double_byte_chars = 0b_001_00000
    triple_byte_chars = 0b_010_00000

    _numeric_format = 0b_110_00000
    _numeric_usint = 0b_000_00110
    _numeric_uint = 0b_000_00111
    _numeric_udint = 0b_000_01000

    numeric_symbol_usint = _numeric_format | _numeric_usint
    numeric_symbol_uint = _numeric_format | _numeric_uint
    numeric_symbol_udint = _numeric_format | _numeric_udint

    mask_format = 0b_111_00000
    mask_size = 0b_000_11111


@dataclass
class SymbolicSegment(CIPSegment):
    segment_type: ClassVar[SegmentType] = SegmentType.symbolic
    symbol: str | USINT | UINT | UDINT | bytes

    #: Extended symbol type, only required when ``symbol`` is of type ``bytes``, else set automatically
    #: If using double/triple byte extended format, this value be mutated to include the string length
    ex_type: SymbolicSegmentExtendedFormat | None = None

    def __post_init__(self):
        if isinstance(self.symbol, bytes):
            if self.ex_type is None:
                raise DataError("symbol of type bytes requires 'type' to be provided")
            else:
                _format = self.ex_type & SymbolicSegmentExtendedFormat.mask_format
                if _format == SymbolicSegmentExtendedFormat.double_byte_chars:
                    if len(self.symbol) % 2:
                        raise DataError("length of symbol with double-byte characters is not a multiple of 2")
                    else:
                        self.ex_type = SymbolicSegmentExtendedFormat.double_byte_chars | len(self.symbol) // 2
                elif _format == SymbolicSegmentExtendedFormat.triple_byte_chars:
                    if len(self.symbol) % 3:
                        raise DataError("length of symbol with triple-byte characters is not a multiple of 3")
                    else:
                        self.ex_type = SymbolicSegmentExtendedFormat.triple_byte_chars | len(self.symbol) // 3

        elif isinstance(self.symbol, str):
            if len(self.symbol) > 31:
                raise DataError("symbol size too large, must be <= 31 characters")

        elif isinstance(self.symbol, USINT):
            self.ex_type = SymbolicSegmentExtendedFormat.numeric_symbol_usint
        elif isinstance(self.symbol, UINT):
            self.ex_type = SymbolicSegmentExtendedFormat.numeric_symbol_uint
        elif isinstance(self.symbol, UDINT):
            self.ex_type = SymbolicSegmentExtendedFormat.numeric_symbol_udint

    @classmethod
    def _encode(cls, value: "SymbolicSegment", *args, **kwargs) -> bytes:
        if isinstance(value.symbol, str):
            _type = bytes(USINT(cls.segment_type | len(value.symbol)))
            data = value.symbol.encode("ascii")
        else:
            _type = bytes(USINT(cls.segment_type)) + bytes(USINT(value.ex_type))
            data = bytes(value.symbol)

        return _type + data

    @classmethod
    def _decode(cls, stream: BytesIO, padded: bool = False) -> "SymbolicSegment":
        segment_type = USINT.decode(stream)
        _type = segment_type & SymbolicSegmentType.mask_symbol_size
        if not _type:
            ex_type = SymbolicSegmentExtendedFormat(USINT.decode(stream))
            size = ex_type & SymbolicSegmentExtendedFormat.mask_size
            _format = ex_type & SymbolicSegmentExtendedFormat.mask_format
            symbol: str | USINT | UINT | UDINT | bytes

            if _format == SymbolicSegmentExtendedFormat.double_byte_chars:
                symbol = cls._stream_read(stream, size * 2)
            elif _format == SymbolicSegmentExtendedFormat.triple_byte_chars:
                symbol = cls._stream_read(stream, size * 3)
            elif ex_type == SymbolicSegmentExtendedFormat.numeric_symbol_usint:
                symbol = USINT.decode(stream)
            elif ex_type == SymbolicSegmentExtendedFormat.numeric_symbol_uint:
                symbol = UINT.decode(stream)
            elif ex_type == SymbolicSegmentExtendedFormat.numeric_symbol_udint:
                symbol = UDINT.decode(stream)
            else:
                raise DataError(f"unsupported extended string format type: {_format}")
        else:
            ex_type = None
            symbol = cls._stream_read(stream, _type).decode("ascii")

        return SymbolicSegment(symbol, ex_type=ex_type)


class DataSegmentType(IntFlag):
    simple = 0b_000_00000
    ansi_extended = 0b_000_10001


@dataclass
class DataSegment(CIPSegment):
    """
    +----+----+----+---+---+---+---+---+
    | Segment Type | Segment Sub-Type  |
    +====+====+====+===+===+===+===+===+
    |  7 |  6 | 5  | 4 | 3 | 2 | 1 | 0 |
    +----+----+----+---+---+---+---+---+
    """

    segment_type: ClassVar[SegmentType] = SegmentType.data

    data: str | bytes
    _type: DataSegmentType = field(default=DataSegmentType.simple, init=False)

    def __post_init__(self) -> None:
        self._type = DataSegmentType.simple if isinstance(self.data, bytes) else DataSegmentType.ansi_extended

    @classmethod
    def _encode(cls, value: "DataSegment", *args, **kwargs) -> bytes:
        segment_type = cls.segment_type | value._type

        if value._type == DataSegmentType.simple:
            data = bytes(USINT(len(value.data) // 2)) + value.data  # type: ignore
        else:
            data = bytes(SHORT_STRING(value.data))

        if len(data) % 2:
            data += b"\x00"

        return bytes(USINT(segment_type)) + data


class ConstructedDataTypeSegment(CIPSegment):
    segment_type: ClassVar[SegmentType] = SegmentType.constructed_data_type


class ElementaryDataTypeSegment(CIPSegment):
    segment_type: ClassVar[SegmentType] = SegmentType.elementary_data_type


@dataclass
class EPATH[T: CIPSegment](DataType):
    """
    CIP path segments
    """

    code: ClassVar[int] = 0xDC  #: 0xDC
    padded: ClassVar[bool] = False
    with_len: ClassVar[bool] = False
    pad_len: ClassVar[bool] = False

    segments: list[T]

    def __len__(self) -> int:
        return len(self.segments)

    @classmethod
    def _encode(cls, value: EPATH[T], *args, **kwargs) -> bytes:
        path = b"".join(segment.encode(segment, padded=cls.padded) for segment in value.segments)
        if cls.with_len:
            _len = USINT.encode(len(value.segments))
            if cls.pad_len:
                _len += b"\x00"
            path = _len + path
        return path

    @classmethod
    def _decode(cls, stream: BufferT) -> Self:
        if cls.with_len:
            _len = USINT.decode(stream)
            if cls.pad_len:
                _ = USINT.decode(stream)

        else:
            _len = ...  # type: ignore # no len, treat like unbound array

        segments: list[T] = cast(list[T], [s for s in array(CIPSegment, _len).decode(stream)])

        return cls(segments)


class PADDED_EPATH(EPATH):
    padded = True


class PACKED_EPATH(EPATH):
    padded = False


class PADDED_EPATH_LEN(PADDED_EPATH):
    with_len = True


class PADDED_EPATH_PAD_LEN(PADDED_EPATH):
    with_len = True
    pad_len = True
