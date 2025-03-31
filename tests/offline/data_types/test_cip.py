from pycomm3 import SymbolicSegment
from pycomm3.data_types import (
    PortSegment,
    PortIdentifier,
    LogicalSegment,
    LogicalSegmentType,
    SegmentType,
    UINT,
    UDINT,
    NetworkSegment,
    NetworkSegmentType,
    USINT,
    SymbolicSegmentExtendedFormat,
)
import pytest
from pycomm3.exceptions import DataError


port_segment_tests = [
    (0, 0, b"\x00\x00"),
    (PortIdentifier.backplane, 1, b"\x01\x01"),
    (1, 1, b"\x01\x01"),
    (PortIdentifier.backplane, "1", b"\x01\x01"),
    (PortIdentifier.backplane, b"\x01", b"\x01\x01"),
    (PortIdentifier.a, 1, b"\x02\x01"),
    (PortIdentifier.a, "1.2.3.4", b"\x12\x071.2.3.4\x00"),
    (16, 3, b"\x0f\x10\x00\x03"),
    (17, "10.20.30.40", b"\x1f\x11\x00\x0b10.20.30.40\x00"),
    (5, "100.101.102.11", b"\x15\x0e100.101.102.11"),
    (32, b"12345", b"\x1f\x20\x00\x0512345\x00"),
    (65_535, 1, b"\x0f\xff\xff\x01"),
    (65_535, 4_294_967_295, b"\x1f\xff\xff\x04\xff\xff\xff\xff"),
    (65_535, "1.2.3.4", b"\x1f\xff\xff\x071.2.3.4\x00"),
    (65_535, "10.2.3.4", b"\x1f\xff\xff\x0810.2.3.4"),
]


@pytest.mark.parametrize("port, link,  encoded", port_segment_tests)
def test_port_segment(port, link, encoded):
    segment = PortSegment(port, link)
    assert bytes(segment) == encoded
    assert PortSegment.decode(encoded) == segment


def test_compare_similar_port_segments():
    assert PortSegment(PortIdentifier.backplane, 1) == PortSegment(1, 1)
    assert PortSegment(PortIdentifier.a, 2) == PortSegment(PortIdentifier.enet, 2)
    assert PortSegment(1, "1.2.3.4") == PortSegment(1, b"1.2.3.4")
    assert PortSegment(1, 1) == PortSegment(1, b"\x01") == PortSegment(1, "1")


_bad_ports = [
    (p, 1, "Invalid port")
    for p in [
        None,
        b"\x01",
        -1,
        "1",
        65_536,
    ]
]

_bad_links = [
    (2, l, "Invalid link")
    for l in [
        None,
        -1,
        "a",
        "-1",
        4_294_967_296,
        "1.2.3.256",
        "1.a.2.3",
    ]
]


@pytest.mark.parametrize("port, link, err_msg", (*_bad_ports, *_bad_links))
def test_bad_port_segments(port, link, err_msg):
    with pytest.raises(DataError, match=err_msg):
        PortSegment(port, link)


bad_port_segment_decode_tests = [
    (b"", ""),
    (bytes([0b_001_0_0001, 1]), "PortSegment (000): 001"),
    (b"\x0f\x00", "extended port id"),
    (b"\x10\x00", "Extended link address size is 0"),
    (b"\x10\x01", "expected 1 byte(s), got: 0"),
    (b"\x10\x04\x01\x02\x03", "expected 4 byte(s), got: 3"),
    (b"\x10\x01\x00", "pad byte"),
    (b"\x10\x03\x01\x02\x03", "pad byte"),
    (b"\x00", "decoding link address"),
    (b"\x0f\x11\x22", "decoding link address"),
]


@pytest.mark.parametrize("encoded, inner_err_msg", bad_port_segment_decode_tests)
def test_bad_port_segment_decode(encoded, inner_err_msg):
    with pytest.raises(DataError) as exc_info:
        PortSegment.decode(encoded)

    if inner_err_msg:
        assert inner_err_msg in str(exc_info.value.__cause__)


_logical_types = (
    LogicalSegmentType.type_class_id,
    LogicalSegmentType.type_instance_id,
    LogicalSegmentType.type_member_id,
    LogicalSegmentType.type_connection_point,
    LogicalSegmentType.type_attribute_id,
)

_logical_8bit_formats = [(1, t, bytes([SegmentType.logical | t, 1])) for t in _logical_types]

_logical_16bit_formats = [
    (257, t, bytes([SegmentType.logical | t | LogicalSegmentType.format_16bit]) + bytes(UINT(257)))
    for t in _logical_types
]

logical_segment_tests = [
    *_logical_8bit_formats,
    *_logical_16bit_formats,
    (
        1,
        LogicalSegmentType.type_service_id,
        bytes([SegmentType.logical | LogicalSegmentType.type_service_id, 1]),
    ),
    (
        65_536,
        LogicalSegmentType.type_instance_id,
        bytes(USINT(0b_001_001_10)) + bytes(UDINT(65_536)),
    ),
    (
        65_536,
        LogicalSegmentType.type_connection_point,
        bytes(USINT(0b_001_011_10)) + bytes(UDINT(65_536)),
    ),
]


@pytest.mark.parametrize("value, typ, encoded", logical_segment_tests)
def test_logical_segment(value, typ, encoded):
    segment = LogicalSegment(typ, value)
    assert bytes(segment) == encoded
    assert LogicalSegment.decode(encoded) == segment


padded_logical_segment_tests = [
    (
        1,
        LogicalSegmentType.type_instance_id,
        bytes(
            [
                SegmentType.logical | LogicalSegmentType.type_instance_id | LogicalSegmentType.format_8bit,
                1,
            ]
        ),
    ),
    (
        300,
        LogicalSegmentType.type_instance_id,
        bytes(
            [
                SegmentType.logical | LogicalSegmentType.type_instance_id | LogicalSegmentType.format_16bit,
                0,
            ]
        )
        + bytes(UINT(300)),
    ),
    (
        100_000,
        LogicalSegmentType.type_instance_id,
        bytes(
            [
                SegmentType.logical | LogicalSegmentType.type_instance_id | LogicalSegmentType.format_32bit,
                0,
            ]
        )
        + bytes(UDINT(100_000)),
    ),
]


@pytest.mark.parametrize("value, typ, encoded", padded_logical_segment_tests)
def test_padded_logical_segment(value, typ, encoded):
    segment = LogicalSegment(typ, value)
    assert LogicalSegment.encode(segment, padded=True) == encoded
    assert LogicalSegment.decode(encoded, padded=True) == segment


bad_logical_segment_tests = [
    (256, LogicalSegmentType.type_service_id, "expected 1 byte, got: 2"),
    (1, LogicalSegmentType.type_special, "not supported"),
    (65_536, LogicalSegmentType.type_class_id, "32-bit logical value"),
    (65_536, LogicalSegmentType.type_member_id, "32-bit logical value"),
    (65_536, LogicalSegmentType.type_attribute_id, "32-bit logical value"),
    *((4_294_967_296, t, "requires too many bytes") for t in _logical_types),
    (b"12345", LogicalSegmentType.type_class_id, "logical value too large"),
]


@pytest.mark.parametrize("value, typ, err_msg", bad_logical_segment_tests)
def test_bad_logical_segment(value, typ, err_msg):
    with pytest.raises(DataError, match=err_msg):
        LogicalSegment(typ, value)


bad_logical_segment_decode_tests = [
    (b"", ""),
    (bytes([0b_000_000_01]), "LogicalSegment (001): 000"),
    (bytes([0b_001_110_01]), "Service ID type (00): 01"),
    (bytes([0b_001_101_01]), "Special type (00): 01"),
    (bytes([0b_001_111_00]), "Unsupported logical type: Reserved"),
    (bytes([0b_001_000_11]), "Unsupported logical format: Reserved"),
    (bytes([0b_001_000_00]), "Error decoding logical value"),  # 8bit, no value
    (bytes([0b_001_000_01, 1]), "Error decoding logical value"),  # 16bit, only 1 byte
    (bytes([0b_001_001_10, 1, 2, 3]), "Error decoding logical value"),  # 32bit, only 3 bytes
    (bytes([0b_001_000_10]), "unsupported logical type: 000"),  # 32bit for class id
    (bytes([0b_001_110_00]), "service id logical value"),
]


@pytest.mark.parametrize("encoded, inner_err_msg", bad_logical_segment_decode_tests)
def test_bad_logical_segment_decode(encoded, inner_err_msg):
    with pytest.raises(DataError) as exc_info:
        LogicalSegment.decode(encoded)

    if inner_err_msg:
        assert inner_err_msg in str(exc_info.value.__cause__)


network_segment_tests = [
    (b"1", NetworkSegmentType.scheduled, bytes([0b_010_00001]) + b"1"),
    (b"1", NetworkSegmentType.fixed_tag, bytes([0b_010_00010]) + b"1"),
    (b"1", NetworkSegmentType.production_inhibit_time, bytes([0b_010_00011]) + b"1"),
    (b"12", NetworkSegmentType.safety, bytes([0b_010_10000]) + b"\x0212"),
    (b"\x00\x00ab", NetworkSegmentType.extended, bytes([0b_010_11111]) + b"\x02\x00\x00ab"),
]


@pytest.mark.parametrize("data, typ, encoded", network_segment_tests)
def test_network_segment(data, typ, encoded):
    segment = NetworkSegment(typ, data)

    assert bytes(segment) == encoded
    assert NetworkSegment.decode(encoded) == segment


bad_network_segment_tests = [
    (b"abc", NetworkSegmentType.scheduled, "00001 requires exactly one byte"),
    (b"1", 0b_000_00111, "unsupported: 00111"),
    (b"", 0b_010_11000, "unsupported: 11000"),
]


@pytest.mark.parametrize("value, typ, err_msg", bad_network_segment_tests)
def test_bad_network_segment(value, typ, err_msg):
    with pytest.raises(DataError, match=err_msg):
        NetworkSegment(typ, value)


bad_network_segment_decode_tests = [
    (b"", ""),
    (bytes([0b_000_00001]), "NetworkSegment (010): 000"),
    (bytes([0b_010_10000]) + b"\x02a", "Error decoding Network segment data"),
    (bytes([0b_010_00111]), "unsupported: 00111"),
    (bytes([0b_010_11000]), "unsupported: 11000"),
]


@pytest.mark.parametrize("encoded, inner_err_msg", bad_network_segment_decode_tests)
def test_bad_network_segment_decode(encoded, inner_err_msg):
    with pytest.raises(DataError) as exc_info:
        NetworkSegment.decode(encoded)

    if inner_err_msg:
        assert inner_err_msg in str(exc_info.value.__cause__)


symbolic_segment_tests = (
    ("her?", None, bytes([SegmentType.symbolic | 4]) + b"her?"),
    (b"\x11\x11\x22\x22", SymbolicSegmentExtendedFormat.double_byte_chars, b"\x60\x22\x11\x11\x22\x22"),
    (b"\x11\x11\x11\x22\x22\x22", SymbolicSegmentExtendedFormat.triple_byte_chars, b"\x60\x42\x11\x11\x11\x22\x22\x22"),
    (USINT(1), None, b"\x60\xc6\x01"),
    (UINT(1), None, b"\x60\xc7\x01\x00"),
    (UDINT(1), None, b"\x60\xc8\x01\x00\x00\x00"),
)


@pytest.mark.parametrize("symbol, ex_type, encoded", symbolic_segment_tests)
def test_symbolic_segment(symbol, ex_type, encoded):
    segment = SymbolicSegment(symbol, ex_type)
    assert bytes(segment) == encoded
    assert SymbolicSegment.decode(encoded) == segment
