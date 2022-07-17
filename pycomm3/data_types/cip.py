from __future__ import annotations

import ipaddress
import reprlib
from typing import Sequence

from ._base import ElementaryDataType, _BufferType, DataType
from .numeric import USINT, UINT, UDINT
from pycomm3.exceptions import DataError

__all__ = (
    'CIPSegment',
    'PortSegment',
    'LogicalSegment',
    'NetworkSegment',
    'SymbolicSegment',
    'DataSegment',
    'ConstructedDataTypeSegment',
    'ElementaryDataTypeSegment',
    'EPATH',
    'PADDED_EPATH',
    'PACKED_EPATH',
    'PADDED_EPATH_WITH_LEN',
    'PADDED_EPATH_WITH_PADDED_LEN',
)


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

    def __init__(self, *args, **kwargs):
        """
        TODO
        :param args:
        :param kwargs:
        """

    @classmethod
    def encode(cls, segment: "CIPSegment", padded: bool = False, *args, **kwargs) -> bytes:
        """
        Encodes an instance of a ``CIPSegment`` to bytes
        """
        try:
            return cls._encode(segment, padded)
        except Exception as err:
            raise DataError(f"Error packing {reprlib.repr(segment)} as {cls.__name__}") from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> "CIPSegment":
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
        port: int | str,
        link_address: int | str | bytes,
        name: str = "",
    ):
        super().__init__(name)
        self.port = port
        self.link_address = link_address

    @classmethod
    def _encode(cls, segment: "PortSegment", padded: bool = False, *args, **kwargs) -> bytes:
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
        if padded and len(_segment) % 2:
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

    def __init__(self, logical_value: int | bytes, logical_type: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logical_value: int | bytes = logical_value
        self.logical_type: str = logical_type

    @classmethod
    def _encode(cls, segment: "LogicalSegment", padded: bool = False, *args, **kwargs) -> bytes:
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

    def __init__(self, data: str | bytes, name: str = "") -> None:
        super().__init__(name)
        self.data = data

    @classmethod
    def _encode(cls, segment: "DataSegment", padded: bool = False, *args, **kwargs) -> bytes:
        _segment = cls.segment_type
        if not isinstance(segment.data, str):
            return USINT.encode(_segment) + USINT.encode(len(segment.data)) + segment.data

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


class EPATH(ElementaryDataType[Sequence[CIPSegment]]):
    """
    CIP path segments
    """

    code = 0xDC  #: 0xDC
    padded = False

    @classmethod
    def encode(
        cls,
        segments: Sequence["CIPSegment" | bytes],
        length: bool = False,
        pad_length: bool = False,
    ) -> bytes:
        try:
            path = b"".join(
                segment if isinstance(segment, bytes) else segment.encode(segment, padded=cls.padded)
                for segment in segments
            )
            if length:
                _len = USINT.encode(len(path) // 2)
                if pad_length:
                    _len += b"\x00"
                path = _len + path
            return path
        except Exception as err:
            raise DataError(f"Error packing {reprlib.repr(segments)} as {cls.__name__}") from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> Sequence[CIPSegment]:
        raise NotImplementedError("Decoding EPATHs not supported")


class PADDED_EPATH(EPATH):  # noqa
    padded = True


class PACKED_EPATH(EPATH):  # noqa
    padded = False


class PADDED_EPATH_WITH_LEN(PADDED_EPATH):  # noqa
    @classmethod
    def encode(
        cls,
        segments: Sequence["CIPSegment" | bytes],
        length: bool = False,
        pad_length: bool = False,
        *args,
        **kwargs,
    ) -> bytes:
        return super().encode(segments, length=True)


class PADDED_EPATH_WITH_PADDED_LEN(PADDED_EPATH):  # noqa
    @classmethod
    def encode(
        cls,
        segments: Sequence["CIPSegment" | bytes],
        length: bool = False,
        pad_length: bool = False,
        *args,
        **kwargs,
    ) -> bytes:
        return super().encode(segments, length=True, pad_length=True)
